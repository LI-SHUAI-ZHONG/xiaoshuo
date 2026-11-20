"""All offered world-design methods can be unsuitable for a real project requirement."""
from copy import deepcopy

import pytest

from nw.production_methods.world_gap import schema, validate_gap


@pytest.fixture
def case():
    target = {
        'stage': 'world_design', 'selection_mode': 'ai', 'adaptation_indices': [0],
        'demand': {'brief': {'text': '调查渡口留存的通行记录。'}, 'type_adaptation': {
            'adaptations': [{'parameters': {'visibility': '岸亭与河道之间常年有雾。'}},
                            {'parameters': {'visibility': '另一个类型的假设。'}}]}},
        'candidates': [{'method': {'id': 'signal', 'body': {'title': '目视旗语'}}},
                       {'method': {'id': 'seal', 'body': {'title': '现场核印'}}}],
    }
    reply = {'stage': 'world_design', 'world_method_gap': {
        'design_basis': [{'kind': 'type_adaptation', 'path': ['adaptations', 0, 'parameters', 'visibility']}],
        'exclusions': [{'method_id': 'signal', 'reason': '浓雾使船上的人看不见岸亭旗语。'},
                       {'method_id': 'seal', 'reason': '远处的核验人无法查看船上的印章。'}],
        'missing': '需要可异地传递并能事后追查的放行凭据。',
    }}
    return target, reply


def test_real_requirement_and_every_offered_method_can_be_returned_as_a_gap(case):
    target, reply = case
    before = deepcopy(target)
    gap = reply['world_method_gap']
    gap['exclusions'].reverse()
    reason = validate_gap(reply, target)
    assert reason.startswith('METHOD_DESIGN_REQUIRED:')
    for value in ('岸亭与河道之间常年有雾', gap['missing'], '目视旗语', '现场核印',
                  *(r['reason'] for r in gap['exclusions'])):
        assert value in reason
    assert target == before


@pytest.mark.parametrize('change', [
    lambda gap: gap['exclusions'].pop(),
    lambda gap: gap['exclusions'][0].update(method_id='forged'),
    lambda gap: gap['exclusions'][0].update(method_id='seal'),
    lambda gap: gap['exclusions'][1].update(reason='不适用。'),
    lambda gap: gap.update(missing='   '),
    lambda gap: gap.update(design_basis=[{'kind': 'brief', 'path': ['text']}]),
    lambda gap: gap['design_basis'][0].update(path=['adaptations', 1, 'parameters', 'visibility']),
    lambda gap: gap['design_basis'][0].update(path=['adaptations', 0, 'parameters', 'invented']),
])
def test_gaps_cannot_hide_an_offered_method_or_invent_a_requirement(case, change):
    target, reply = case
    change(reply['world_method_gap'])
    with pytest.raises(ValueError, match='PROJECT_METHOD:'):
        validate_gap(reply, target)


def test_world_gaps_do_not_accept_design_products_or_replace_an_inherited_world(case):
    target, reply = case
    with pytest.raises(ValueError, match='单独提交'):
        validate_gap({**reply, 'products': {'members': []}}, target)
    for changed in ({'selection_mode': 'inherit_world'}, {'stage': 'scene_design'}, {'candidates': []}):
        with pytest.raises(ValueError, match='自动挑选候选'):
            validate_gap(reply, {**target, **changed})


def test_transport_branch_only_offers_the_frozen_method_ids(case):
    target, _ = case
    response = schema(target)
    assert set(response['required']) == {'stage', 'world_method_gap'}
    assert response['additionalProperties'] is False
    assert response['properties']['stage'] == {'const': 'world_design'}
    exclusions = response['properties']['world_method_gap']['properties']['exclusions']
    assert exclusions['minItems'] == exclusions['maxItems'] == 2
    assert exclusions['items']['properties']['method_id']['enum'] == ['signal', 'seal']
