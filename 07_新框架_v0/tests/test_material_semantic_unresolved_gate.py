"""Regress original-workflow rule: unexplained clauses cannot count as execution."""
from copy import deepcopy
import pytest

from nw.materials.source_semantics import compile_semantics
from nw.materials.semantic_application import validate_semantic_applications,unresolved_issues
from test_material_semantic_clauses import source,record,criterion


def project(original: str):
    item=source(original=original);contract=compile_semantics(item)
    before={'character_design':record('character_design',{'capabilities':[{'can_act':True}]})}
    value={'candidates':[{'steps':[{'action':'[FAKE] 先检查铜丝再压低木片绕行'}]}],
        '_uses':[{'source_id':'method'}],'_criteria':[criterion(contract)]}
    context={'require_semantics':True,'brief':{'text':'[FAKE] 调查封条'},'semantic_contracts':[contract]}
    return item,contract,before,value,context


@pytest.mark.parametrize('original',[
    '{"rule":"先核对人物能力再安排动作","unknown_native_field":"未核定原义的原始字段"}',
    '【未核定用途】本字段的创作用途尚未确认\n【指令】先核对人物能力再安排动作',
    '本段原义角色尚未解释\n【指令】先核对人物能力再安排动作'])
def test_uninterpreted_clause_is_linked_and_cannot_silently_apply(original):
    item,contract,before,value,context=project(original)
    assert any(unresolved_issues(contract,o['id']) for o in contract['obligations'])
    with pytest.raises(ValueError,match='unresolved'):
        validate_semantic_applications('action_design',value,before,[item],context)


def test_local_unresolved_clause_does_not_discard_a_separate_readable_instruction():
    item,contract,before,value,context=project(
        '{"rule":"先核对人物能力再安排动作","unknown_native_field":"未核定原义的原始字段"}')
    for clause in value['_criteria'][0]['clauses']:
        issues=unresolved_issues(contract,clause['id'])
        if issues:
            clause.update(applicability='source_unresolved',reason=issues[0]['kind']+'：此原始字段待核',
                          input_refs=[],output_refs=[],operation='',observable='',check='')
    validate_semantic_applications('action_design',value,before,[item],context)


def test_all_unresolved_cannot_be_reported_as_a_used_method():
    item,contract,before,value,context=project('{"unknown_native_field":"未核定原义的原始字段"}')
    for clause in value['_criteria'][0]['clauses']:
        clause.update(applicability='source_unresolved',reason='unclassified_original_field：此原始字段待核',
                      input_refs=[],output_refs=[],operation='',observable='',check='')
    with pytest.raises(ValueError,match='actual applied|unresolved'):
        validate_semantic_applications('action_design',value,before,[item],context)


def test_all_not_applicable_cannot_be_reported_as_a_used_method():
    item,contract,before,value,context=project('【指令】先核对人物能力再安排动作')
    for clause in value['_criteria'][0]['clauses']:
        clause.update(applicability='not_applicable',reason='[FAKE] 本项目当前任务不涉及该项设计',
                      input_refs=[],output_refs=[],operation='',observable='',check='')
    with pytest.raises(ValueError,match='actual applied'):
        validate_semantic_applications('action_design',value,before,[item],context)


def test_unreviewed_meaning_cannot_be_hidden_as_current_task_nonapplicability():
    from fake_binding_reviews import review_fixture
    from nw.task_models import content_sha256
    item,contract,before,value,context=project(
        '{"rule":"先核对人物能力再安排动作","unknown_native_field":"未核定原义的原始字段"}')
    review=review_fixture(item,['action_design'])
    unknown=next(o for o in contract['obligations'] if o['locator']=='/unknown_native_field')
    next(c for c in review['clause_reviews'] if c['text_start']==unknown['source_ref']['text_start'])['status']='needs_review'
    review['sha256']=content_sha256({k:v for k,v in review.items() if k!='sha256'})
    context.update(binding_policy='workflow-source-binding-v1',binding_test_mode=True,binding_reviews={'method':review})
    clause=next(c for c in value['_criteria'][0]['clauses'] if c['id']==unknown['id'])
    clause.update(applicability='not_applicable',reason='[FAKE] 本场当前任务不涉及该项设计',
        input_refs=[],output_refs=[],operation='',observable='',check='')
    with pytest.raises(ValueError,match='needs review|source_unresolved'):
        validate_semantic_applications('action_design',value,before,[item],context)
