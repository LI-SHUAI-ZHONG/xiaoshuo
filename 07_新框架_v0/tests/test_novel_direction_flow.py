"""Direction selection must precede real whole-book planning and survive reopen."""
import json

import pytest

from nw.config import Config
from nw.llm.base import GenResult
from nw.novel_flow import resume_job
from nw.novel_store import JobRequest, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget, content_sha256
from story_fixture import baseline
from test_novel_flow import Model
from test_studio_project_methods import client


OPTIONS = [
    {'title': '[FAKE] 烧毁的登记簿', 'premise': '档案馆失火，夜班登记员在被追责前试图证明账页被调换。',
     'protagonist': '沈砚是保管夜间通行记录的新人，被指控销毁记录。',
     'goal': '寻找交接时已经存在的外抄本，为自证并救下被误抓的值夜同伴。',
     'conflict': '掌握外抄本的商会要求沈砚交出能证明邻馆违规的名单。',
     'world_premise': '各馆共署的交接记录决定不同辖区能否查扣物品。',
     'long_term_drive': '先查当夜交接，再追查旧案中被抹去的通行记录，最终让各区核对权责。',
     'type_fit': '悬疑由错误指控和逐次重建记录推进。', 'author_fit': '始终保留已经明示的线索。'},
    {'title': '[FAKE] 渡口的空席', 'premise': '沈砚替被放逐的摆渡人接班，每趟船都有一位乘客被登记为不存在。',
     'protagonist': '沈砚靠代班偿还旧债，担心未列名乘客无法进入下游。',
     'goal': '在下一次换班前，把失去身份登记的孩子交还家人。',
     'conflict': '巡渡队为掩盖旧事故扣留乘客，合作者靠替换名额谋生。',
     'world_premise': '渡口的来往名册决定航程后由哪个辖区承认乘客身份。',
     'long_term_drive': '从第一次误登追到旧渡契，再串联各渡口的失踪名单，迫使两岸对账。',
     'type_fit': '悬疑由失踪、证人盲点和名册矛盾逐案推进。', 'author_fit': '通过角色实际见闻逐次披露。'},
]


class DirectionModel(Model):
    def generate(self, messages, **params):
        if '[BOOK_DIRECTIONS]' in messages[0]['content']:
            self.calls.append(messages)
            return GenResult(json.dumps({'candidates': OPTIONS}, ensure_ascii=False), 'complete', {}, 'test', {})
        response = super().generate(messages, **params)
        if 'candidate_cards' in messages[0]['content']:
            raw = json.loads(response.text)
            raw['candidate_cards'] = raw['candidate_cards'][:1]
            return GenResult(json.dumps(raw, ensure_ascii=False), 'complete', {}, 'test', {})
        return response


@pytest.fixture
def book(tmp_path):
    with Store(tmp_path / 'isolated', create=True, test_mode=True) as store:
        store.init_project('[FAKE] 新书方向')
        store.add_brief('[FAKE] 某位登记员被卷入旧案', '已经明示的线索不得改写。')
        adopt_story(store, baseline(), {})
    job_request = JobRequest('design', design_scope='book', direction_review=True,
                             budget=Budget(20, 150000, 4096))
    cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, tmp_path, source_driven=False)
    return tmp_path / 'isolated', job_request, cfg, DirectionModel()


def test_selected_direction_is_frozen_and_reused_before_whole_book_planning(book):
    path, request, cfg, model = book
    with Store(path, test_mode=True) as store:
        job = start_job(store, request)
        waiting = resume_job(store, job.id, model, cfg)
        assert waiting.step == 'direction:book:confirm' and waiting.status == 'WAITING'
        assert len(model.calls) == 1
        gate = waiting.outputs['gate']
        assert gate['kind'] == 'book_direction_selection'
        chosen = gate['candidates'][1]
        assert not store.list('chapter')
    with Store(path, test_mode=True) as store:
        reopened = resume_job(store, job.id, model, cfg)
        assert reopened.outputs['gate'] == gate and len(model.calls) == 1
        ready = resume_job(store, job.id, model, cfg, lambda _, target: {
            'action': 'approve', 'reason': '[FAKE] 第二案的困境可形成调查线', 'root': chosen['id']})
        assert ready.status == 'WAITING' and ready.step == 'plan:book:confirm', ready.reason
        assert len(model.calls) == 2
        prompt_package = json.loads(model.calls[1][-1]['content'])
        selected = prompt_package['approved_direction']
        assert selected['candidate'] == chosen and selected['candidate_id'] == chosen['id']
        assert selected['sha256'] == content_sha256(chosen)
        assert ready.outputs['gate']['approved_direction'] == selected
        assert gate['candidates'][0]['premise'] not in model.calls[1][-1]['content']
        done = resume_job(store, job.id, model, cfg, lambda _, target: {
            'action': 'approve', 'reason': '[FAKE] 确认深化方案', 'root': target['candidates'][0]['root']['card_id']})
        assert done.status == 'DONE' and done.step == 'plan:book:apply', done.reason
        assert len(model.calls) == 2


def test_rejecting_direction_does_not_start_detailed_planning(book):
    path, request, cfg, model = book
    with Store(path, test_mode=True) as store:
        job = start_job(store, request)
        assert resume_job(store, job.id, model, cfg).status == 'WAITING'
        rejected = resume_job(store, job.id, model, cfg, lambda *_: {
            'action': 'reject', 'reason': '[FAKE] 改用其他冲突。'})
        assert rejected.status == 'REJECTED' and rejected.step == 'direction:book:confirm'
        assert len(model.calls) == 1
        assert not any(step['step_key'].startswith('plan:') for step in rejected.outputs['steps'])


def test_editing_brief_invalidates_pending_direction_approval(book):
    path, request, cfg, model = book
    with Store(path, test_mode=True) as store:
        job = start_job(store, request)
        gate = resume_job(store, job.id, model, cfg).outputs['gate']
        store.add_brief('[FAKE] 改为双重登记调查', '保留原有线索。')
        stale = resume_job(store, job.id, model, cfg, lambda *_: {
            'action': 'approve', 'reason': '[FAKE] 核对方向', 'root': gate['candidates'][0]['id']})
        assert stale.status == 'STALE' and stale.reason == 'STALE_BRIEF'
        assert len(model.calls) == 1


@pytest.mark.parametrize('client', ['world'], indirect=True)
def test_studio_manual_direction_gate_retains_feedback_and_drives_source_stages(client):
    from ai_world_method_fixture import BRIEF, TAXON, WorldModel

    request, settled, server, _ = client
    production = server.production
    config, _ = production._runtime()

    class StudioDirectionModel(WorldModel):
        def generate(self, messages, **params):
            if '[BOOK_DIRECTIONS]' in messages[0]['content']:
                self.calls.append(messages)
                return GenResult(json.dumps({'candidates': OPTIONS}, ensure_ascii=False), 'complete', {}, 'test', {})
            response = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            if payload.get('approved_direction') and payload.get('stage') == 'plot_design':
                raw = json.loads(response.text)
                products = raw['products']
                products['directions'] = products['directions'][:1]
                for row in products.get('_method_receipts', []):
                    row['placements'] = [p for p in row['placements'] if p['path'][:2] != ['directions', 1]]
                response.text = json.dumps(raw, ensure_ascii=False)
            return response

    model = StudioDirectionModel()
    production.runtime_factory = lambda: (config, model)
    status, created = request('POST', '/api/novels', {'title': '[FAKE] 临川渡方向', 'idea': BRIEF,
        'genre_ids': [TAXON], 'design_mode': 'manual', 'direction_review': True})
    assert status == 201, created
    ident = created['novel']['id']
    route = f'/api/novels/{ident}'
    current = settled(ident)
    gate = current['gates'][0]
    assert current['current_step'] == '全书方向与确认' and len(model.calls) == 1
    node = current['tree'][0]['children'][0]
    assert node['kind'] == 'book_direction' and node['status'] == 'waiting'
    assert node['output']['candidates'] == gate['target']['candidates']
    assert request('POST', route + '/gates/' + gate['id'], {
        'action': 'approve', 'token': gate['token'], 'reason': '隔离验证', 'root': 'invalid'})[0] == 400
    assert len(model.calls) == 1
    reason = '[FAKE] 下一批请让过河后的管辖冲突更明确。'
    assert request('POST', route + '/gates/' + gate['id'], {
        'action': 'reject', 'token': gate['token'], 'reason': reason})[0] == 200
    assert settled(ident)['status'] == 'REJECTED' and len(model.calls) == 1
    status, result = request('POST', route + '/run', {})
    assert status == 200, result
    retried = settled(ident)
    second = retried['gates'][0]
    assert second['job_id'] != gate['job_id'] and second['token'] != gate['token']
    feedback = json.loads(model.calls[1][-1]['content'])['previous_rejection']
    assert feedback['job_id'] == gate['job_id'] and feedback['reason'] == reason
    chosen = second['target']['candidates'][1]
    assert request('POST', route + '/gates/' + second['id'], {
        'action': 'approve', 'token': second['token'], 'reason': '[FAKE] 确认渡口方向', 'root': chosen['id']})[0] == 200
    detailed = settled(ident)
    assert detailed['status'] == 'WAITING', detailed['reason']
    final_gate = detailed['gates'][0]
    assert final_gate['step'] == 'plan:book:confirm'
    assert len(final_gate['target']['candidates']) == 1
    assert final_gate['target']['approved_direction']['candidate'] == chosen
    stage_packets = [json.loads(messages[-1]['content']) for messages in model.calls[2:]]
    assert all(p['approved_direction']['candidate'] == chosen for p in stage_packets if p.get('stage') in (
        'type_selection', 'type_adaptation', 'world_design', 'character_design', 'static_relations', 'plot_design'))
    assert any(p.get('stage') == 'world_design' and p.get('production_methods') for p in stage_packets)
    active = next(row['children'][0] for row in detailed['tree'] if row['id'] == f"{second['job_id']}:book")
    assert active['status'] == 'done' and active['output']['selected_id'] == chosen['id']
    assert request('POST', route + '/gates/' + final_gate['id'], {'action': 'approve', 'token': final_gate['token'],
        'reason': '[FAKE] 确认细化全书方案', 'root': final_gate['target']['candidates'][0]['root']['card_id']})[0] == 200
    assert settled(ident)['status'] == 'DONE'


def test_studio_type_only_auto_waits_for_author_direction_when_all_boards_are_ready(client, monkeypatch):
    from nw.production_methods.sources import MethodReader
    from test_studio_project_methods import seven_automatic_methods

    request, settled, server, source = client
    rows = seven_automatic_methods(source)
    monkeypatch.setattr(MethodReader, 'current_methods', lambda _: rows)
    monkeypatch.setattr(MethodReader, 'world_source', lambda *_: (None, None))
    config, _ = server.production._runtime()
    model = DirectionModel()
    server.production.runtime_factory = lambda: (config, model)
    response, result = request('POST', '/api/novels', {
        'genre_ids': ['GENRE_XUANYI'], 'design_mode': 'auto', 'direction_review': True, 'auto_recommendations': True})
    assert response == 201, result
    progress = settled(result['novel']['id'])
    assert progress['status'] == 'WAITING'
    assert progress['gates'][0]['target']['kind'] == 'book_direction_selection'
    assert len(model.calls) == 1 and '[BOOK_DIRECTIONS]' in model.calls[0][0]['content']
