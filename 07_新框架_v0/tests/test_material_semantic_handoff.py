import pytest

from nw.materials.semantic_handoff import handoffs_for,input_stages,validate_handoffs
from nw.task_models import content_sha256


def upstream():
    value={'members':[{'key':'yan','body':{'want':'[FAKE] 查明封条被谁破坏'}}],
        '_criteria':[{'source_id':'motivation','contract_sha256':'pin','clauses':[{
            'id':'motive-clause','consumer':'event_design','applicability':'applies',
            'output_refs':['/members/0/body/want'],'check':'[FAKE] 核对本步事件有前置动机'}]}]}
    return {'character_design':{'stage':'character_design','task_id':'fake-design',
        'products':value,'sha256':content_sha256(value)}}


def test_source_clause_reaches_its_actual_named_stage_with_original_input_value():
    products=upstream();rows=handoffs_for('event_design',products)
    assert rows[0]['actual_inputs'][0]['value']=='[FAKE] 查明封条被谁破坏'
    assert 'character_design' in input_stages('event_design',products)
    with pytest.raises(ValueError,match='disappeared'):
        validate_handoffs('event_design',{'candidates':[]},products)
    value={'candidates':[{'event':'[FAKE] 人物发现封条边缘仍有未干的胶水'}],
        '_receipts':[{'id':rows[0]['id'],'operation':'[FAKE] 根据人物查封条的动机设计当前发现事件',
                      'output_refs':['/candidates/0/event']}]}
    validate_handoffs('event_design',value,products)


def test_handoff_cannot_be_satisfied_by_a_status_or_an_invented_receipt():
    products=upstream();row=handoffs_for('event_design',products)[0]
    value={'status':'pass','_receipts':[{'id':row['id'],'operation':'[FAKE] 根据前置动机执行本项目当前设计',
                                     'output_refs':['/status']}]}
    with pytest.raises(ValueError,match='identity|status|self proof'):
        validate_handoffs('event_design',value,products)
