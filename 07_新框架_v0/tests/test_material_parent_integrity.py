"""Child plans must consume the parent's approved, frozen method products."""
import json

import pytest

from nw.call_budget import create_budget
from nw.planning import prepare_plan_task, propose_plan
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_phase_flow import PhaseModel, template_catalog
from test_novel_flow import config
from test_planning import Planner, apply


def parent_plan(store, provider):
    store.init_project('父方案产物完整性')
    store.add_brief('调查封条')
    adopt_story(store, baseline(), {})
    parent = propose_plan(store, 1, 'book', provider, config(store), Budget(30, 90000, 4000))
    apply(store, parent)
    row = store.connection.execute('SELECT mapping_json FROM plan_applications WHERE proposal_id=?',
                                   (parent.id,)).fetchone()
    return parent, json.loads(row[0])


def child_plan(store, provider, parent_id, entrypoint):
    if entrypoint == 'propose':
        return propose_plan(store, 1, 'chapter', provider, config(store), Budget(30, 90000, 4000),
                            parent_id=parent_id)
    budget = create_budget(store, 'child', Budget(30, 90000, 4000))
    return prepare_plan_task(store, 1, 'chapter', provider, config(store), budget, 'child',
                             parent_id=parent_id)


@pytest.mark.parametrize('entrypoint', ['prepare', 'propose'])
@pytest.mark.parametrize('tamper', ['edit', 'remove'])
def test_child_rejects_changed_parent_work_before_any_model_call(tmp_path, entrypoint, tamper):
    template_catalog(tmp_path)
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        provider = PhaseModel()
        parent, mapping = parent_plan(store, provider)
        design = mapping['material_design']
        if tamper == 'edit':
            design['work_application']['stage_uses'][0]['sha256'] = 'a' * 64
        else:
            for key in ('work_session', 'work_application', 'work_context'):
                design.pop(key)
        with store.connection:
            store.connection.execute('UPDATE plan_applications SET mapping_json=? WHERE proposal_id=?',
                                     (json.dumps(mapping, ensure_ascii=False), parent.id))
        before = len(provider.calls)
        with pytest.raises(ValueError, match='MATERIAL_WORK'):
            child_plan(store, provider, parent.id, entrypoint)
        assert len(provider.calls) == before


@pytest.mark.parametrize('entrypoint', ['prepare', 'propose'])
def test_child_can_continue_from_unchanged_parent_work(tmp_path, entrypoint):
    template_catalog(tmp_path)
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        provider = PhaseModel()
        parent, mapping = parent_plan(store, provider)
        result = child_plan(store, provider, parent.id, entrypoint)
        if entrypoint == 'prepare':
            _, package = result
            assert package['parent_material_work']['application'] == mapping['material_design']['work_application']
            assert package['parent_material_work']['stages'] == mapping['material_design']['work_session']['stages']
        else:
            assert result.candidate_cards


def test_legacy_parent_without_material_work_can_prepare_child(tmp_path):
    with Store(tmp_path / 'legacy', create=True, test_mode=True) as store:
        parent, _ = parent_plan(store, Planner('book'))
        _, package = child_plan(store, Planner('chapter'), parent.id, 'prepare')
        assert 'parent_material_work' not in package
