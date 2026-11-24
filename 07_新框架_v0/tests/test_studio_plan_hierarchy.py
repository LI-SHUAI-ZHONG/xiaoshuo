"""The Studio must keep each approved planning level on the actual production path."""
import json

import pytest

from nw.llm.base import GenResult
from nw.studio.api import StudioService
from nw.studio.library import LibraryService
from nw.studio.production import ProductionService
from test_novel_direction_flow import OPTIONS
from test_studio_project_methods import client


def test_hierarchy_choice_is_frozen_in_the_real_new_book_job(tmp_path):
    studio = StudioService(tmp_path / 'workspace', config_path=tmp_path / 'missing.toml')
    production = ProductionService(studio, LibraryService(studio.workspace))
    result = production.create({'title': '[FAKE] 渡口卷章', 'idea': '查清覆写的渡口登记记录。',
                                'genre_ids': ['GENRE_XUANYI'], 'design_mode': 'manual',
                                'direction_review': True, 'planning_hierarchy': True})
    novel = result['novel']
    assert novel['wizard']['planning_hierarchy'] is True
    assert result['run']['status'] == 'CONFIG_REQUIRED'
    with production.open_store(novel) as store:
        request = json.loads(store.connection.execute('SELECT request_json FROM novel_jobs').fetchone()[0])
        assert request['planning_hierarchy'] is True
        assert request['design_scope'] == 'book' and request['outline_lineage'] == []


@pytest.mark.parametrize('client', ['world'], indirect=True)
def test_studio_runs_approved_book_volume_chapter_and_scene_in_order(client):
    from ai_world_method_fixture import BRIEF, TAXON, WorldModel

    send, settled, server, _ = client
    config, _ = server.production._runtime()

    class Model(WorldModel):
        def generate(self, messages, **params):
            if '[BOOK_DIRECTIONS]' in messages[0]['content']:
                self.calls.append(messages)
                return GenResult(json.dumps({'candidates': OPTIONS}, ensure_ascii=False), 'complete', {}, 'test', {})
            response = super().generate(messages, **params)
            packet = json.loads(messages[-1]['content'])
            if packet.get('stage') not in ('type_selection', 'type_adaptation', 'plot_design'):
                return response
            raw = json.loads(response.text)
            products = raw['products']
            if locked := packet.get('locked_type_products'):
                products.update(locked)
            if packet['stage'] == 'plot_design':
                products['directions'] = products['directions'][:1]
                for row in products.get('_method_receipts', []):
                    row['placements'] = [p for p in row['placements'] if p['path'][:2] != ['directions', 1]]
                if packet.get('scope') == 'volume':
                    others = [m for m in products['members'] if m['kind'] not in ('volume', 'chapter')]
                    products['members'] = [*others, {'key': 'current_volume', 'kind': 'volume', 'body': {
                        'title': '[FAKE] 渡口旧印', 'goal': '[FAKE] 核实被调换登记记录的依据',
                        'turn': '[FAKE] 复核印痕发现更早一次调包',
                        'ending_direction': '[FAKE] 留下可核对的外抄本，将更早调包交给后续追查'}}]
            response.text = json.dumps(raw, ensure_ascii=False)
            return response

    model = Model()
    server.production.runtime_factory = lambda: (config, model)
    status, created = send('POST', '/api/novels', {'title': '[FAKE] 逐级审核', 'idea': BRIEF,
        'genre_ids': [TAXON], 'design_mode': 'manual', 'direction_review': True, 'planning_hierarchy': True})
    assert status == 201, created
    novel_id = created['novel']['id']
    base = f'/api/novels/{novel_id}'

    def approve(gate, root=None):
        body = {'action': 'approve', 'token': gate['token'], 'reason': '[FAKE] 核对本级目标和交付'}
        if root is not None:
            body['root'] = root
        status, reply = send('POST', f"{base}/gates/{gate['id']}", body)
        assert status == 200, reply
        return settled(novel_id)

    def run(body=None):
        status, reply = send('POST', base + '/run', body or {})
        return status, reply

    direction = settled(novel_id)['gates'][0]
    book_review = approve(direction, direction['target']['candidates'][0]['id'])['gates'][0]
    book = approve(book_review, book_review['target']['candidates'][0]['root']['card_id'])
    assert book['status'] == 'DONE' and book['next_design']['scope'] == 'volume', book['reason']
    assert book['next_design']['approved_parent']['proposal_id'] == book_review['target']['proposal_id']
    before = len(model.calls)
    status, reply = run({'mode': 'design', 'scope': 'chapter', 'parent_id': book_review['target']['proposal_id']})
    assert status == 400 and len(model.calls) == before, reply
    status, reply = run()
    assert status == 200, reply
    volume_progress = settled(novel_id)
    assert volume_progress['status'] == 'WAITING', volume_progress['reason']
    volume_gate = volume_progress['gates'][0]
    assert volume_gate['target']['scope'] == 'volume'
    assert volume_gate['target']['approved_parent']['scope'] == 'book'
    volume_plan = volume_gate['target']['candidates'][0]
    assert len([row for row in volume_plan['members'] if row['kind'] == 'volume']) == 1
    assert not any(row['kind'] in ('chapter', 'scene') for row in volume_plan['members'])
    assert not any(json.loads(call[-1]['content']).get('stage') in ('event_design', 'action_design', 'scene_design')
                   for call in model.calls[before:])
    volume = approve(volume_gate, volume_plan['root']['card_id'])
    assert volume['status'] == 'DONE' and volume['next_design']['scope'] == 'chapter', volume['reason']
    proof = volume['next_design']['approved_parent']
    assert proof['artifact']['body']['turn'] == '[FAKE] 复核印痕发现更早一次调包'
    assert send('GET', base)[1]['project']['chapters'] == []
    before = len(model.calls)
    status, reply = run()
    assert status == 200, reply
    awaiting_outline = settled(novel_id)
    assert awaiting_outline['status'] == 'WAITING', awaiting_outline['reason']
    chapter_gate = awaiting_outline['gates'][0]
    assert chapter_gate['target']['kind'] == 'chapter_outline_approval'
    assert chapter_gate['target']['outline_lineage'][-1] == proof
    assert not any(json.loads(call[-1]['content']).get('stage') in ('event_design', 'action_design', 'scene_design')
                   for call in model.calls[before:])
    before = len(model.calls)
    scene_review = approve(chapter_gate)
    assert scene_review['status'] == 'WAITING', scene_review['reason']
    scene_gate = scene_review['gates'][0]
    assert scene_gate['target']['approved_chapter'] == chapter_gate['target']['chapter']
    assert scene_gate['target']['approved_parent'] == proof
    later = [json.loads(call[-1]['content']) for call in model.calls[before:]]
    downstream = [row for row in later if row.get('stage') in ('event_design', 'action_design', 'scene_design')]
    assert {row['stage'] for row in downstream} == {'event_design', 'action_design', 'scene_design'}
    assert all(row['approved_chapter']['target']['chapter'] == chapter_gate['target']['chapter']
               and row['outline_lineage'][-1] == proof for row in downstream)
    final = approve(scene_gate, scene_gate['target']['candidates'][0]['root']['card_id'])
    assert final['status'] == 'DONE', final['reason']
    detail = send('GET', base)[1]
    assert len(detail['project']['chapters']) == 1 and len(detail['project']['scenes']) == 1
    assert detail['volumes'][0]['chapter_ids'] == [detail['project']['chapters'][0]['id']]
