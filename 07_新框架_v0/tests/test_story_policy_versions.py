from copy import deepcopy

import pytest

from nw.config import Config
from nw.materials import chapter_progress, narration, story_policies
from nw.materials.phase_projection import expand_output
from nw.materials.phase_routes import POLICY
from nw.materials.work_session import drive_plan
from nw.store import Store


@pytest.mark.parametrize('change', ['older', 'missing', 'unknown', 'old_assembler', 'old_staged_assembler'])
def test_staged_assembly_cannot_discard_the_plans_frozen_story_checks(change):
    active = story_policies.current()
    plan = {**active, 'material_mode': 'source_driven_staged',
            'material_work': {'policy': POLICY, 'context': deepcopy(active)}}
    context = plan['material_work']['context']
    if change == 'older':
        context['narration_policy'] = narration.ACCESS_POLICY
    elif change == 'missing':
        del context['chapter_progress_policy']
    elif change == 'unknown':
        plan['cast_demand_policy'] = context['cast_demand_policy'] = 'future-unknown'
    elif change == 'old_assembler':
        plan['material_work'] = {'policy': 'legacy'}
    else:
        plan['material_work']['policy'] = 'artifact-stage-binding-v3'
    with pytest.raises(ValueError, match='校验版本|冻结的版本'):
        expand_output({'candidate_cards': []}, plan)


def test_existing_plans_retain_their_exact_historical_versions():
    old = {'narration_policy': narration.ACCESS_POLICY, 'chapter_progress_policy': chapter_progress.LEGACY_POLICY}
    story_policies.verify_plan({**old, 'material_mode': 'source_driven_staged',
                                'material_work': {'policy': POLICY, 'context': dict(old)}})
    story_policies.verify_plan({'material_mode': 'source_driven_staged',
                                'material_work': {'policy': POLICY, 'context': {}}})


def test_missing_catalog_cannot_switch_a_frozen_task_to_simple_planning(tmp_path):
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('复验冻结任务的资料目录')
        config = Config('fake', 'http://localhost', 'test', '', 1, {}, tmp_path, source_driven=False)
        with pytest.raises(ValueError, match='MATERIAL_CATALOG_REQUIRED'):
            drive_plan(store, None, story_policies.current(), None, config)
