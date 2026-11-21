"""Chapter handoff from accepted prose through the normal planning entry."""
from copy import deepcopy
import json
from pathlib import Path

from nw.acceptance import accept_batch
from nw.call_budget import create_budget
from nw.config import Config
from nw.planning import prepare_plan_task, propose_plan
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from nw.tasks import read_input_manifest
from story_fixture import baseline, draft_for, operation, proposal
from test_planning import Planner, apply, propose


def prepare_story(store: Store) -> tuple[str, list[str]]:
    store.init_project('井下账册')
    store.add_brief('按证据安排后续调查')
    adopt_story(store, baseline(facts=[{'entity_id': 'purse', 'predicate': 'coins',
        'holder': 'WORLD', 'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0],
        'value': 10}]), {})
    parent = propose(store)
    apply(store, parent)
    model = Planner('chapter')
    for candidate in model.output['candidate_cards']:
        second = deepcopy(candidate['members'][-1])
        second['key'] = 'second'
        second['body']['title'] = '井口'
        candidate['members'].append(second)
        candidate['chapters'][0]['scenes'].append({'index': 2, 'card': 'second', 'story_order': 2})
    config = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
    detail = propose_plan(store, 1, 'chapter', model, config, Budget(1, 45000, 2000), parent_id=parent.id)
    apply(store, detail)
    return parent.id, [scene.id for scene in sorted(store.list('scene'), key=lambda scene: scene.index)]


def test_completed_chapter_facts_are_frozen_for_continuation(tmp_path: Path) -> None:
    from nw.story_state import current_head
    from test_cli import invoke

    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        parent, (first, second) = prepare_story(store)
        config = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=False)
        model = Planner('chapter', chapter=2)
        budget = create_budget(store, 'next', Budget(4, 90000, 4000))

        before = current_head(store)
        draft = draft_for(store, first, '沈砚花掉六枚铜钱，换取井口的通行。')
        change = operation(draft, predicate='coins', entity='purse', old=10, new=4)
        plan = operation(draft, holder='yan', claim='plan', predicate='return',
                         entity='yan', new='打算明日返还铜钱')
        head = accept_batch(store, [proposal(store, before, draft, [change, plan])], before, 'part')
        _, partial = prepare_plan_task(store, 1, 'chapter', model, config, budget, 'partial', parent_id=parent)
        assert 'chapter_handoff' not in partial
        partial_head = head

        last = draft_for(store, second, '沈砚在井口停下脚步。')
        head = accept_batch(store, [proposal(store, head, last, [])], head, 'finish')
        request, _ = prepare_plan_task(store, 1, 'chapter', model, config, budget, 'next', parent_id=parent)
        _, frozen = read_input_manifest(store, request.manifest_id)
        handoff = frozen['chapter_handoff']
        assert handoff['head'] == {'branch_id': 'main', 'revision': head.revision}
        assert handoff['chapter']['index'] == 1
        assert handoff['pending_scene_ids'] == []
        assert [r['scene_id'] for r in handoff['drafts']] == [first, second]
        [paid_change] = handoff['changes']
        assert (paid_change['entity_id'], paid_change['expected_old'], paid_change['new_value']) == ('purse', 10, 4)
        assert paid_change['evidence'] == change['evidence']
        assert paid_change['story_order'] == 1
        assert paid_change['disclosure_order'] == [1, 1, 0]
        [intention] = handoff['character_changes']
        assert (intention['holder'], intention['claim'], intention['evidence']) == ('yan', 'plan', plan['evidence'])

    with Store(tmp_path / 'story') as store:
        from nw.chapter_state import chapter_state
        assert chapter_state(store, head, 1) == handoff
        historical = chapter_state(store, partial_head, 1)
        assert historical['scope_complete'] is False
        assert historical['pending_scene_ids'] == [second]
    result = invoke(tmp_path, '--project', 'story', 'story', 'chapter-state', '--chapter', '1',
                    '--revision', str(head.revision))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == handoff


def test_plot_step_receives_chapter_facts_without_sending_them_to_type_selection(tmp_path: Path, monkeypatch) -> None:
    from nw.chapter_records import chapter_review, chapter_summary
    from nw.materials import phase_flow
    from nw.materials.steps.plot_design_chapters import MATERIAL
    from nw.story_state import current_head
    from test_material_phase_flow import PhaseModel, template_catalog

    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        parent, (first, second) = prepare_story(store)
        head = current_head(store)
        first_draft = draft_for(store, first, '沈砚为通行花掉六枚铜钱。')
        second_draft = draft_for(store, second, '沈砚在井口等候。')
        change = operation(first_draft, predicate='coins', entity='purse', old=10, new=4)
        belief = operation(second_draft, time=2, order=(1, 2, 0), holder='yan', claim='suspicion',
                           predicate='entry', entity='well', new='怀疑井下还有通路')
        requests = [proposal(store, head, first_draft, [change]), proposal(store, head, second_draft, [belief])]
        head = accept_batch(store, requests, head, 'accept-chapter')
        review = chapter_summary(store, head, 1)
        recap = chapter_summary(store, head, 1, {'input_sha256': review['input_sha256'],
                                                'summary': '沈砚花钱取得通行，在井口留下等待。'})['record']
        resources = chapter_review(store, head, 1, 'resource-update')
        finding = chapter_review(store, head, 1, 'resource-update', {'input_sha256': resources['input_sha256'],
                                                                     'finding': '后章承接只剩四枚铜钱。'})['record']
        template_catalog(tmp_path)
        # Keep the test within its existing context budget while running the actual phase driver.
        monkeypatch.setattr(phase_flow, 'STAGE_MATERIALS', {'plot_design': MATERIAL})
        model = PhaseModel()
        cfg = Config('fake', 'http://localhost', 'test', '', 5, {}, store.directory, source_driven=True)
        budget = create_budget(store, 'plot-handoff', Budget(32, 90000, 4000))
        task, package = prepare_plan_task(store, 1, 'chapter', model, cfg, budget, 'new-chapter', parent_id=parent)
        phase_flow.drive_phases(store, task, package, model, cfg)
        offered = [(payload['stage'], payload['chapter_handoff']) for messages in model.calls
                   if '[MATERIAL_STEP]' in messages[0]['content']
                   for payload in [json.loads(messages[-1]['content'])] if 'chapter_handoff' in payload]
        assert offered == [('plot_design', package['chapter_handoff'])]
        assert offered[0][1]['character_changes'][0]['claim'] == 'suspicion'
        [scene] = [data for messages in model.calls if (data := json.loads(messages[-1]['content'])).get('stage') == 'scene_design']
        assert any(change['holder'] == 'yan' and change['text'] == '怀疑井下还有通路'
                   for change in scene['chapter_changes'].values())
        summaries = [(payload['stage'], payload['chapter_summary']['id']) for messages in model.calls
                     for payload in [json.loads(messages[-1]['content'])] if 'chapter_summary' in payload]
        assert summaries == [('plot_design', recap['id'])]
        reviews = [(payload['stage'], payload['chapter_reviews'][0]['id']) for messages in model.calls
                   for payload in [json.loads(messages[-1]['content'])] if 'chapter_reviews' in payload]
        assert reviews == [('plot_design', finding['id'])]
