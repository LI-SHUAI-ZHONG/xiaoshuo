
from dataclasses import asdict
import json

import pytest

from nw.cards import decide_card, save_card
from nw.config import Config
from nw.llm.base import GenResult
from nw.llm.fake import FakeProvider
from nw.novel_flow import JobRequest, resume_job, show_job, start_job
from nw.store import Store
from nw.story_state import adopt_story, current_head
from nw.task_models import Budget
from story_fixture import baseline
from test_planning import Planner


class Model(FakeProvider):
    def __init__(self, *, revisions=False, core=False):
        super().__init__()
        self.revisions = revisions
        self.core = core

    def generate(self, messages, **params):
        if '[CASTING_EDITOR]' in messages[0]['content']:
            self.calls.append(messages)
            data = json.loads(messages[-1]['content'])
            judgments = [{'id': row['id'], 'verdict': 'accept', 'reason': '[FAKE] 隔离用例中的行动会造成已设计的结果'}
                         for row in data['demands']]
            return GenResult(json.dumps({'judgments': judgments}, ensure_ascii=False), 'complete', {}, 'test', {})
        if '[MATERIAL_STEP]' in messages[0]['content']:
            from fake_phase_work import phase_output
            return phase_output(self,messages)
        if '[MATERIAL_ASSEMBLY]' in messages[0]['content']:
            from fake_phase_work import assembly_output
            return assembly_output(self,messages)
        self.calls.append(messages)
        prompt, payload = messages[0]['content'], json.loads(messages[-1]['content'])
        if '[MATERIAL_WORK]' in prompt:
            from fake_material_work import study_output
            return GenResult(json.dumps(study_output(payload),ensure_ascii=False),'complete',{},'test',{'isolated_test':True})
        if 'candidate_cards' in prompt:
            result = Planner(payload['scope']).output
            if payload.get('material_work'):
                from fake_material_work import apply_work
                result['candidate_cards']=[apply_work(row,payload['material_work']) for row in result['candidate_cards']]
        elif '{"recommendation"' in prompt:
            result = {'recommendation': 'revise' if self.revisions else 'pass',
                      'notes': '查看证据', 'core_changes': ['改变主角核心目标'] if self.core else []}
            if payload.get('material_review'):
                contract=payload['material_review'];text=payload['draft']['text']
                span={**contract['draft'],'start':0,'end':len(text),'quote':text}
                result['material_checks']=[]
                for check in contract['checks']:
                    row={'id':check['id'],'status':'pass','reason':'[FAKE] 对照所读方法与本次完整测试稿的实际表现','evidence':[span]}
                    if check.get('source_contract'):
                        row['source_checks']=[{'id':field['id'],'status':'pass','reason':'[FAKE] 原义与测试段落相符',
                            'evidence':[span]} for field in check['source_contract'].get('obligations',[])]
                    if check.get('layer_contract') and check['id'].startswith('work:'):
                        row['layer_check']={'status':'pass','reason':'[FAKE] 对照当前项目转译与完整测试稿的因果表现',
                                            'evidence':[span]}
                    result['material_checks'].append(row)
        elif '{"operations"' in prompt:
            if payload['disclosure_order'][:2] == [1, 1] and '取得小钥匙' in payload['draft']['text']:
                actor = next(card['card_id'] for card in payload['context']['settings']
                             if card['kind'] == 'character' and card['body']['name'] == '沈砚')
                result = {'operations': [{'op': 'set', 'entity_id': 'key', 'predicate': 'owner',
                    'holder': actor, 'claim': 'fact', 'story_order': 1, 'disclosure_order': [1, 1, 0],
                    'expected_old': None, 'new_value': '小钥匙', 'evidence': [payload['evidence_format']]}]}
            else:
                result = {'operations': []}
        elif '{"findings"' in prompt:
            result = {'findings': []}
        else:
            return GenResult('[FAKE] 沈砚取得小钥匙。', 'complete', {}, 'test', {})
        return GenResult(json.dumps(result, ensure_ascii=False), 'complete', {}, 'test', {})


def author(action='accept', **fields):
    def decide(step, data):
        return {'action': action, 'reason': '已核对', **fields}
    return decide


def config(store):
    return Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory,source_driven=False)


def setup_story(store, count=3):
    store.init_project('钥匙')
    store.add_brief('追查封条', '受限第三人称')
    approvals = []
    for key, kind, body in [
        ('yan', 'character', {'name': '沈砚', 'role': '主角', 'want': '调查', 'visibility': 'public'}),
        *((f'card{i}', 'scene', {'title': f'场{i}', 'pov': 'yan', 'goal': '调查', 'story_time': str(i)})
          for i in range(1, count + 1)),
    ]:
        ref = save_card(store, {'card_id': key, 'kind': kind, 'origin': 'author', 'body': body}, None)
        decision = decide_card(store, ref, 'approved', '确认')
        approvals.append({**asdict(ref), 'decision_id': decision.id})
    chapter = store.add_chapter(1, '封条')
    scenes = [store.add_scene(chapter.id, i, json.dumps({'story': {
        'scene_ref': {'card_id': f'card{i}', 'version': 1}, 'story_order': i}})).id
              for i in range(1, count + 1)]
    adopt_story(store, baseline(card_refs=approvals), {})
    return scenes


@pytest.fixture
def story(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        yield store, setup_story(store)


def job(store, scenes, calls=30, mode='write'):
    return start_job(store, JobRequest(mode, 'main', scenes, None, Budget(calls, 45000, 2000))).id


def test_design_job_starts_from_brief_and_applies_selected_plan(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('暗井')
        store.add_brief('暗井调查')
        adopt_story(store, baseline(), {})
        ident = job(store, [], mode='design')
        provider = Model()
        result = resume_job(store, ident, provider, config(store))
        assert result.status == 'WAITING' and result.step == 'plan:book:confirm'
        def choose(step, data):
            return {'action': 'approve', 'root': data['candidates'][0]['root']['card_id'], 'reason': '采用'}
        second = resume_job(store, ident, provider, config(store), choose)
        assert second.step == 'plan:chapter:confirm'
        final = resume_job(store, ident, provider, config(store), choose)
        assert final.status == 'DONE', final.reason
        assert len(provider.calls) == 2 and len(store.list('scene')) == 1
        assert current_head(store).revision == 2


def test_two_revisions_and_budget_stop(story):
    store, scenes = story
    provider = Model(revisions=True)
    ident = job(store, scenes[:1], calls=5)
    first = resume_job(store, ident, provider, config(store))
    assert first.status == 'BLOCKED' and 'CALL_LIMIT' in first.reason
    assert len(store.drafts(scenes[0])) == 3 and len(provider.calls) == 5
    second = resume_job(store, ident, provider, config(store), max_calls=10)
    assert second.status == 'WAITING' and 'review-limit' in second.step
    assert len(store.drafts(scenes[0])) == 3 and len(provider.calls) == 6


def test_rejected_first_scene_invalidates_candidate_descendants(story):
    store, scenes = story
    ident = job(store, scenes)
    provider = Model()
    waiting = resume_job(store, ident, provider, config(store))
    assert waiting.step == 'batch:confirm'
    assert store.list('accepted') == []
    rejected = resume_job(store, ident, provider, config(store), author('reject', scene_id=scenes[0]))
    assert rejected.status == 'REJECTED'
    assert rejected.outputs['stale_scenes'] == scenes[1:]
    assert store.list('accepted') == [] and current_head(store).revision == 0
    assert any(row['status'] == 'STALE' for row in show_job(store, ident).outputs['steps'])
    with pytest.raises(ValueError, match='complete source draft'):
        job(store, scenes[1:2], mode='revise')


def test_core_change_requires_decision(story):
    store, scenes = story
    ident = job(store, scenes[:1])
    provider = Model(core=True)
    waiting = resume_job(store, ident, provider, config(store))
    assert waiting.status == 'WAITING' and waiting.step.endswith(':core:0')
    assert len(provider.calls) == 2
    next_gate = resume_job(store, ident, provider, config(store), author('approve'))
    assert next_gate.step == 'batch:confirm'


def test_write_without_valid_context_is_blocked(story):
    store, _ = story
    chapter = store.list('chapter')[0]
    missing = store.add_scene(chapter.id, 4, '{}')
    provider = Model()
    result = resume_job(store, job(store, [missing.id]), provider, config(store))
    assert result.status == 'BLOCKED' and 'CONTEXT_PROVIDER_REQUIRED' in result.reason
    assert not provider.calls


def test_candidate_projection_keeps_earlier_knowledge_disclosed_later(story):
    from nw.acceptance import accept_batch
    from nw.context.story import build_story_context, scene_scope
    from nw.story_delta import draft_ref, read_delta
    from story_fixture import draft_for, operation, proposal

    store, scenes = story
    later = draft_for(store, scenes[2], '暗井的密码写在封条上。')
    head = current_head(store)
    late_delta = proposal(store, head, later, [
        operation(later, time=1, order=(1, 3, 0), holder='yan', claim='fact',
                  entity='well', predicate='password', new='FLASHBACK_FACT')])
    accept_batch(store, [late_delta], head, 'third-first')

    head = current_head(store)
    first = draft_for(store, scenes[0])
    early = proposal(store, head, first, [])
    candidate = read_delta(store, early.delta_id)
    work = build_story_context(store, scenes[1], scene_scope(store, scenes[1]), 45000,
                               candidate_refs=((candidate.id, candidate.sha256),))
    assert 'FLASHBACK_FACT' in json.dumps(work.package)
    assert draft_ref(later) in work.dependency_refs


def test_novel_extract_and_check_share_the_chronology_of_the_writer(story):
    from nw.acceptance import accept_batch
    from story_fixture import draft_for, operation, proposal

    store, scenes = story
    later = draft_for(store, scenes[2], '旧密码写在封条上。')
    head = current_head(store)
    recorded = proposal(store, head, later, [
        operation(later, time=1, order=(1, 3, 0), holder='yan', claim='fact',
                  entity='well', predicate='password', new='旧密码')])
    accept_batch(store, [recorded], head, 'flashback')

    class Update(Model):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            if '{"operations"' in messages[0]['content'] and payload['disclosure_order'][:2] == [1, 2]:
                assert any(fact['value'] == '旧密码' for fact in payload['context']['facts'])
                result.text = json.dumps({'operations': [{
                    'op': 'set', 'entity_id': 'well', 'predicate': 'password', 'holder': 'yan',
                    'claim': 'fact', 'story_order': 2, 'disclosure_order': [1, 2, 0], 'expected_old': '旧密码',
                    'new_value': '新密码', 'evidence': [payload['evidence_format']]}]}, ensure_ascii=False)
            return result

    provider = Update()
    result = resume_job(store, job(store, scenes[:2]), provider, config(store))
    assert result.step == 'batch:confirm', result.reason
    assert len(provider.calls) == 8
