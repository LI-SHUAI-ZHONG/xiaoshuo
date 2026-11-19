"""Corpus references reach real design calls with bounded evidence and authority."""
from copy import deepcopy
import json

import pytest

from nw.materials.author_references import author_stage_input


def reference():
    return {'id': 'r1', 'book_id': 'b1', 'status': 'approved', 'slot': 'world',
            'option_key': 'world.limits', 'stages': ['world_design'],
            'usage_text': '先展示力量限制，再让人物作出有代价的选择。',
            'evidence': {'quote': '甲' * 800, 'start': 12, 'end': 812},
            'entire_chapter': '绝不传递整章', 'author_approval': True}


def test_reference_is_bounded_and_does_not_acquire_fact_or_gate_authority():
    row = reference()
    package = {'governance_inputs': {'world_design': {'author_references': [row]}}}
    packet = author_stage_input(package, 'world_design')
    delivered = packet['author_references'][0]
    assert delivered['evidence'] == {'start': 12, 'end': 812, 'quote': '甲' * 400}
    assert 'entire_chapter' not in delivered and 'author_approval' not in delivered
    assert packet['method_priority'] == 'design_ready'
    assert len(row['evidence']['quote']) == 800
    assert author_stage_input(package, 'character_design') == {}


@pytest.mark.parametrize('patch', [
    {'status': 'draft'}, {'stages': ['character_design']}, {'evidence': {}}, {'book_id': ''},
])
def test_invalid_or_unapproved_examples_fail_closed(patch):
    row = {**reference(), **patch}
    with pytest.raises(ValueError, match='AUTHOR_REFERENCES'):
        author_stage_input({'governance_inputs': {'world_design': {'author_references': [row]}}}, 'world_design')


def test_upgrade_requires_an_immutable_version():
    raw = {'upgrade_references': [reference()]}
    with pytest.raises(ValueError, match='version'):
        author_stage_input({'governance_inputs': {'world_design': raw}}, 'world_design')
    raw['upgrade_references'][0]['version'] = 2
    assert author_stage_input({'governance_inputs': {'world_design': raw}}, 'world_design')['upgrade_references'][0]['version'] == 2


def test_real_phase_calls_receive_only_their_selected_examples(tmp_path, monkeypatch):
    from nw.call_budget import create_budget
    from nw.materials.work_session import drive_plan
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_material_governance_runtime import runtime
    from test_novel_flow import config

    monkeypatch.setattr('nw.materials.governance_runtime.load_governance', lambda _: runtime())

    class GovernedModel(PhaseModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            if payload.get('stage') == 'type_selection':
                raw = json.loads(result.text)
                config_value = {k: [] for k in ('genre_ids', 'mechanism_ids', 'structure_ids', 'style_ids', 'tone_ids')}
                config_value['genre_ids'] = [r['id'] for r in raw['products']['selection']]
                raw['products']['_governance'] = {'project_config': config_value}
                result.text = json.dumps(raw, ensure_ascii=False)
            return result

    template_catalog(tmp_path)
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('[FAKE] 客户端输入验证')
        store.add_brief('[FAKE] 调查封条与行动代价')
        adopt_story(store, baseline(), {})
        provider = GovernedModel()
        budget = create_budget(store, 'studio-references', Budget(32, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'studio-input')
        package = deepcopy(package)
        package['governance_inputs'] = {'world_design': {'author_references': [reference()]}}
        drive_plan(store, request, package, provider, config(store))
        packets = [json.loads(messages[-1]['content']) for messages in provider.calls]
        world = next(p for p in packets if p.get('stage') == 'world_design')
        assert world['author_input']['author_references'][0]['id'] == 'r1'
        assert all('author_input' not in p for p in packets if p.get('stage') != 'world_design')
