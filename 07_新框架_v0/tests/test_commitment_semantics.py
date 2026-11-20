"""Check a frozen promise through collection, concrete use, conflicting results and historical replay."""
from copy import deepcopy

import pytest

from nw.materials import commitment_semantics as semantics
from nw.materials.character_prerequisites import matches
from nw.task_models import content_sha256


def person(name='阿禾', key='he', **body):
    return {'kind': 'character', 'key': key, 'body': {'name': name, **body}}


def snapshot(stage, product):
    return {'stage': stage, 'products': product, 'task_id': '[FAKE] ' + stage, 'sha256': content_sha256(product)}


def evidence(key='C00655', *, policy=semantics.POLICY, relation=True, **fields):
    owner = person(relationship='阿禾依照渡口寄存契约，亲口答应阿婆在冬至前送回旧船。',
                   want='阿禾要亲自把旧船交还给阿婆。', need='阿禾自认对阿婆有交还旧船的责任。',
                   behavior='阿禾要在收工后将旧船交还给阿婆。')
    owner['body'].update(fields)
    draft = {'members': [owner, person('阿婆', 'grandma'), person('阿绫', 'ling')]}
    previous = {'character_design': snapshot('character_design', draft)}
    if relation:
        rel = {'source': 'he', 'target': 'grandma', 'relation': '祖孙', 'condition': '阿禾和阿婆的祖孙身份已由族谱核实。'}
        previous['static_relations'] = snapshot('static_relations', {'relations': [rel]})
    return matches(key, draft, products=previous, context={'design_network_policy': policy})


def validate(row, text, operation='阿禾按冬至前的约定将旧船归还给阿婆。', stage='plot_design'):
    semantics.validate_use(row, text, operation=operation, stage=stage)


@pytest.mark.parametrize('key', sorted(semantics.KEYS))
def test_each_promise_uses_its_own_actor_beneficiary_and_action(key):
    rows = evidence(key)
    assert rows
    p = rows[0]['commitment']
    assert (p['actor'], p['promisee'], p['beneficiary'], p['action'], p['subject']) == ('阿禾', '阿婆', '阿婆', '归还', '旧船')
    validate(rows[0], '阿禾在冬至前亲自把旧船交还给阿婆。')
    if key == 'C01153':
        assert 'input:static_relations:/relations/0/target' in rows[0]['upstream_refs']


@pytest.mark.parametrize('goal', ['她改为替雇主护送一批木材去北山，祖母的旧船与这趟差事全不相干。',
                                 '她在冬至之前把旧船交还给阿绫。', '她在冬至之前把旧账本交还给阿婆。',
                                 '阿婆把旧船交还给阿禾。', '让阿婆去取旧船，自己照顾邻居。'])
def test_new_policy_rejects_unrelated_goal_even_if_benefit_or_subject_is_mentioned(goal):
    # Keep other possible goal fields empty. Each confirmed goal is an independent candidate.
    assert not evidence(want=goal, need='', behavior='收工时要结清本月伙食账。')
    if '雇主' in goal:
        legacy = evidence(policy='frozen-design-prerequisites-v1', want=goal, need='')
        assert legacy and 'commitment' not in legacy[0]


@pytest.mark.parametrize('source', ['阿绫答应阿婆在冬至前归还旧船。', '雇主才是亲口答应阿婆在冬至前归还旧船的人。'])
def test_another_person_cannot_issue_the_owner_promise(source):
    assert not evidence(relationship=source, behavior='她在收工后送回旧船。')


def test_relative_must_be_actual_beneficiary_even_if_both_names_appear():
    assert not evidence('C01153', relation=False)
    assert not evidence('C01153', relationship='阿禾答应阿婆替阿绫修补渔船。',
                        want='阿禾准备为阿绫修好渔船。', need='', behavior='')
    [row] = evidence('C00655', relationship='阿禾向阿婆承诺在冬至前替阿绫修补渔船。',
                     want='阿禾在冬至前替阿绫修好渔船。', need='', behavior='')
    assert row['commitment']['promisee'] == '阿婆' and row['commitment']['beneficiary'] == '阿绫'
    validate(row, '阿禾在冬至前为阿绫修好渔船。')
    with pytest.raises(ValueError):
        validate(row, '阿禾在冬至前替阿婆修好渔船。')


def test_internal_responsibility_and_external_obligation_each_have_own_evidence():
    assert not evidence('C01585', relationship='阿禾亲口答应阿婆在冬至前送回旧船。', background='北岸巡夜是官差的职务。')
    assert not evidence('C01585', relationship='阿禾依照契约替雇主巡夜，另外阿禾答应阿婆在冬至前送回旧船。')
    assert not evidence('C01585', need='她只对阿绫自愿承担赡养责任。', want='阿禾将带旧船回去。')
    assert not evidence('C01573', behavior='她仍旧整晚替雇主守仓，不去码头。')
    assert not evidence('C00655', relationship='阿禾答应阿婆归还旧船。', behavior='码头每日收工后由水手收灯。')


@pytest.mark.parametrize('stage', ['plot_design', 'action_design', 'scene_design'])
def test_explicit_breach_has_promise_and_observable_consequence(stage):
    row = evidence()[0]
    validate(row, '阿禾拒绝归还旧船，因此阿婆只得另租一条船回乡。', stage=stage)
    validate(row, '阿禾违约，扣下了答应给阿婆的旧船，阿婆因此被困在渡口。', stage=stage)
    with pytest.raises(ValueError):
        validate(row, '阿禾拒绝归还旧船，因此阿婆只得另租船。', operation='她已经如约把旧船还给阿婆。', stage=stage)
    for text in ('阿禾食言，没有依约归还阿婆的旧船。',
                 '阿禾违约扣下阿婆的旧船，因此今夜的月光很亮。',
                 '阿禾把旧船转给雇主，却声称这是兑现对阿婆的承诺。',
                 '阿禾把阿婆的旧船交还雇主，却声称这是兑现原先的约定。',
                 '阿禾违约扣下阿婆的旧船，害阿婆失去生计，却仍称自己已经履约。',
                 '阿禾在冬至后才把旧船还给阿婆，一切如约。'):
        with pytest.raises(ValueError):
            validate(row, text, stage=stage)


def test_consequence_in_the_same_product_accepts_the_breach_but_cannot_be_borrowed_from_another_person():
    row = evidence()[0]
    breach = '阿禾拒绝把旧船归还阿婆，决定食言。'
    validate({**row, 'commitment_aftermath': '阿婆因此只得另租一船回乡。'}, breach, operation='她决定违约。')
    for missing in ('', '雇主因此只得另租一船安置木材。', '阿婆在岸边休息。'):
        with pytest.raises(ValueError):
            validate({**row, 'commitment_aftermath': missing}, breach, operation='她决定违约。')


def test_prose_aliases_resolve_without_anonymous_or_cross_person_grafting():
    rows = evidence(relationship='阿禾向祖母许诺冬至前归还旧船。', want='把旧船奉还奶奶。', need='', behavior='')
    assert rows
    validate(rows[0], '阿禾冬至前把旧船交还给奶奶。')
    with pytest.raises(ValueError):
        validate(rows[0], '祖母如约归还旧船给阿禾。')
    with pytest.raises(ValueError):
        validate(rows[0], '阿禾把旧船还给魏安，算是兑现对祖母的承诺。')


def test_changed_result_cannot_count_as_fulfilment_of_unrelated_work():
    row = evidence()[0]
    semantics.check_conflict(row, '浮市的雇主请阿禾另送一船木材。', stage='scene_design')
    semantics.check_conflict(row, '阿禾决定违约，留下旧船，阿婆因此被困在渡口。', stage='scene_design')
    for result in ('阿禾改把旧船交给雇主，当作已对阿婆履约。',
                   '阿禾决定替雇主运一船木材，声称这就算兑现对阿婆的承诺。'):
        with pytest.raises(ValueError):
            semantics.check_conflict(row, result, stage='scene_design')
    with pytest.raises(ValueError):
        semantics.check_conflict(row, '阿禾替雇主运了一船木材，把这件事算作已经兑现替阿婆归还旧船的承诺。', stage='state_transition')
    # Old session snapshots contain no semantic promise object.
    legacy = deepcopy(row)
    del legacy['commitment']
    validate(legacy, '阿禾把旧船转给雇主，却声称是兑现承诺。')


def test_trigger_can_be_delivered_in_the_receipt_but_not_invented_to_cover_missing_goal():
    row = evidence()[0]
    validate(row, '阿禾将旧船交还给阿婆。', operation='她要赶在冬至前完成原约。')
    with pytest.raises(ValueError):
        validate(row, '阿禾将旧船交还给阿婆。', operation='她在明年另择时间交船。')
    with pytest.raises(ValueError):
        validate(row, '阿禾为了雇主运送木材，祖母的旧船留在原地。')
