"""A selected v1 plot receipt must be checked against the actual approved person in a v2 child."""
from copy import deepcopy

import pytest

from nw.materials import design_network
from nw.materials.design_network_catalog import POLICY
from test_character_prerequisites import person, record

KEY = 'C00655'
PIN = {'card_id': 'plan-001-guard', 'version': 1}
PLEDGE = '沈砚答应祖母在冬至前归还旧船。'
GOAL = '沈砚决定把旧船归还给祖母，以履行自己在渡口许下的承诺。'
WRONG = '沈砚替雇主护送木材去北山，把这项差事算作已经兑现对祖母归还旧船的承诺。'
FALSE_GOAL = '沈砚决定替雇主护送木材去北山，木材要在大雪封山前抵达。'
KEEP = '沈砚在冬至前归还旧船，把旧船交还给祖母。'
SPLIT_TIME = '沈砚把旧船归还给祖母，渡口的船簿登记了收船人。'
BREAK = '沈砚拒绝把旧船归还给祖母，决定食言。'
AFTER = '祖母因此只得另租一条船回乡。'
DEFAULT_OP = '沈砚把冬至前归还旧船的约定落实到本章选择。'


def legacy_receipt(*, placement=KEEP, operation=DEFAULT_OP, goal=GOAL, aftermath='港口在两夜后另派渡船。'):
    pins = {'owner': 'character_design', 'source': {'id': '[FAKE]-C00655'}, 'static': {'id': '[FAKE]-stat'},
            'basis_stage': 'character_design', 'valid_types': ['悬疑']}
    ctx = {'design_network_policy': 'frozen-design-prerequisites-v1', 'design_network_catalog': {KEY: pins},
           'network_type_scope': {'mystery': ['悬疑']}, 'scope': 'book'}
    guard = person(relationship=PLEDGE, want=goal, behavior='沈砚天一亮就去检查旧船系绳。')
    old = {'character_design': record('character_design', {'members': [guard]})}
    [row] = design_network.candidates('plot_design', old, ctx)
    assert row['member'] == 'guard' and not {'commitment', 'semantic_policy'}.intersection(row)
    direction = {'title': '还船', 'conflict': placement, 'consequence': aftermath}
    use = {'id': row['id'], 'operation': operation, 'output_refs': ['/directions/0/conflict']}
    plot = record('plot_design', {'directions': [direction], '_network_design_uses': [use]})
    plot['network_design_candidates'] = [row]
    # Prove this use really could have been accepted under the frozen v1 policy.
    design_network.validate('plot_design', plot['products'], [row], old, ctx)
    [receipt] = design_network.inherited({'selected_direction': direction, 'stages': [plot]}, {'guard': PIN})
    assert receipt['card'] == PIN and receipt['row']['member'] == 'guard' and receipt['value'] == placement
    return guard, ctx, receipt


def child(old, *, published, stage='plot_design', additional_card=None, new_member=None, local_fields=None):
    guard, ctx, receipt = old
    # A child can retain the approved card and design its state, or issue local character fields.
    state = {'entity': PIN['card_id'], 'status': 'candidate', 'state': {'住处': '临川渡口'}}
    local = {**guard, 'body': {**guard['body'], **(local_fields or {})}}
    person_input = {'members': [] if published else [local], 'states': [state] if published else []}
    ctx = {**ctx, 'scope': 'chapter', 'design_network_policy': POLICY, 'parent_design_network': [receipt],
           'approved_cards': [{**PIN, 'kind': 'character', 'body': deepcopy(guard['body'])}]}
    if new_member:
        person_input['members'].append(new_member)
    if additional_card:
        person_input['states'].append({'entity': additional_card['card_id'], 'status': 'candidate', 'state': {'住处': '北渡口'}})
        ctx['approved_cards'].append(additional_card)
    current = {'character_design': record('character_design', person_input)}
    for upstream, field in [('plot_design', 'directions'), ('action_design', 'candidates'), ('event_design', 'candidates')]:
        current[upstream] = record(upstream, {field: []})
    return design_network.candidates(stage, current, ctx)


@pytest.mark.parametrize('published', [False, True], ids=['local', 'approved-card-id'])
@pytest.mark.parametrize('stage', ['plot_design', 'scene_design'])
@pytest.mark.parametrize(('placement', 'operation', 'aftermath'), [
    (KEEP, DEFAULT_OP, '港口在两夜后另派渡船。'),
    (SPLIT_TIME, DEFAULT_OP, '港口在两夜后另派渡船。'),
    (BREAK, '沈砚选择食言，留下旧船。', AFTER),
], ids=['self-contained', 'deadline-in-operation', 'breach-consequence-in-same-direction'])
def test_selected_v1_character_receipt_becomes_required_with_the_right_v2_proof(
        published, stage, placement, operation, aftermath):
    old = legacy_receipt(placement=placement, operation=operation, aftermath=aftermath)
    [row] = child(old, published=published, stage=stage)
    assert row['member'] == (PIN['card_id'] if published else 'guard')
    assert row['required'] and [r['value'] for r in row['deliveries']] == [placement]
    assert (row['commitment']['beneficiary'], row['commitment']['subject'], row['commitment']['trigger']) == (
        '祖母', '旧船', '冬至前')
    if published:
        assert 'approved:' + PIN['card_id'] + ':/body/relationship' in {e['ref'] for e in row['evidence']}
        assert row['approved'] == [PIN]


@pytest.mark.parametrize('published', [False, True], ids=['local', 'approved-card-id'])
@pytest.mark.parametrize('problem', ['false-fulfilment', 'false-goal', 'false-aftermath'])
def test_invalid_or_unprovable_v1_selection_is_never_reissued_as_a_v2_obligation(published, problem):
    if problem == 'false-fulfilment':
        old = legacy_receipt(placement=WRONG)
    elif problem == 'false-goal':
        old = legacy_receipt(placement=WRONG, goal=FALSE_GOAL)
    else:
        old = legacy_receipt(placement=KEEP, aftermath=WRONG)
    with pytest.raises(ValueError, match='承诺|C00655.+缺少可复核'):
        child(old, published=published)


@pytest.mark.parametrize('value', [KEEP, SPLIT_TIME, WRONG])
def test_intermediate_legacy_receipt_uses_only_the_fields_it_really_saved(value):
    person_card, ctx, receipt = legacy_receipt(placement=value)
    retained = {k: receipt[k] for k in ('signature', 'producer', 'path', 'value', 'row', 'card')}
    old = person_card, ctx, retained
    if value == KEEP:
        [row] = child(old, published=True)
        assert row['required'] and row['deliveries'][0]['value'] == KEEP
    else:
        with pytest.raises(ValueError, match='承诺|履责|C00655.+缺少可复核'):
            child(old, published=True)


def test_a_different_approved_person_with_the_same_name_and_debt_remains_optional():
    old = legacy_receipt()
    twin = {'card_id': 'plan-002-other', 'version': 1, 'kind': 'character', 'body': deepcopy(old[0]['body'])}
    rows = child(old, published=True, additional_card=twin)
    assert {r['member']: r['required'] for r in rows} == {PIN['card_id']: True, twin['card_id']: False}


@pytest.mark.parametrize('name', ['程冉', '沈砚'], ids=['different-name', 'duplicate-name'])
def test_reused_temporary_key_cannot_reassign_a_selected_v1_receipt_to_someone_else(name):
    old = legacy_receipt()
    newcomer = person(key='guard', name=name, relationship=PLEDGE.replace('沈砚', name),
                      want=GOAL.replace('沈砚', name), behavior=name + '天一亮就去检查旧船系绳。')
    rows = child(old, published=True, new_member=newcomer)
    assert {r['member']: r['required'] for r in rows} == {PIN['card_id']: True, 'guard': False}


def test_an_unrelated_second_promise_cannot_take_or_invalidate_the_selected_old_receipt():
    old = legacy_receipt()
    rows = child(old, published=False, local_fields={
        'background': '沈砚答应雇主在夏至前修好货车。', 'independent_goal': '沈砚要替雇主修补货车。'})
    assert {(r['commitment']['beneficiary'], r['required']) for r in rows} == {('祖母', True), ('雇主', False)}
