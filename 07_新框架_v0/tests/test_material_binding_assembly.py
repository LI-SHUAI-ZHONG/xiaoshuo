from copy import deepcopy
import pytest

from nw.materials.phase_contract import validate_phase
from test_material_phase_projection import chain
from test_material_semantic_clauses import source
from fake_binding_reviews import review_fixture
from nw.materials.binding_assembly import validate_assembly
from nw.task_models import content_sha256


def test_final_bindings_cannot_add_a_design_method_not_executed_in_its_reviewed_step():
    session=chain();before={r['stage']:r for r in session['stages'][:-1]}
    value=deepcopy(session['stages'][-1]['products']);item=source()
    value['material_bindings']={'scene':{'method':{'function':'[FAKE] 用动作方法',
        'parameter':'[FAKE] 检查封条','observable':'[FAKE] 压低木片','check':'[FAKE] 动作有后果'}}}
    context={'scope':'chapter','binding_policy':'workflow-source-binding-v1','binding_test_mode':True,
        'binding_reviews':{'method':review_fixture(item,['action_design'])},
        'material_source_snapshots':{'method':item}}
    with pytest.raises(ValueError,match='executed.*step|binding.*assembly'):
        validate_phase({'stage':'bind_scope','products':value},'bind_scope',before,[],context)


def test_final_bindings_keep_an_action_method_already_executed_in_its_correct_step():
    session=chain();before={r['stage']:r for r in session['stages'][:-1]};item=source()
    value=deepcopy(session['stages'][-1]['products'])
    value['material_bindings']={'scene':{'method':{'function':'[FAKE] 用动作方法',
        'parameter':'[FAKE] 检查封条','observable':'[FAKE] 压低木片','check':'[FAKE] 动作有后果'}}}
    action=before['action_design'];action['products']['_uses']=[{'source_id':'method',
        'operation':'[FAKE] 根据人物目标设计实际行动链',
        'output_refs':['action:'+action['products']['candidates'][0]['id']]}]
    action['sha256']=content_sha256(action['products'])
    value['method_guidance']=[{'scene':'scene','source_ids':['method'],
        'observable':'[FAKE] 压低木片','check':'[FAKE] 动作有后果'}]
    context={'scope':'chapter','binding_policy':'workflow-source-binding-v1','binding_test_mode':True,
        'binding_reviews':{'method':review_fixture(item,['action_design'])},
        'material_source_snapshots':{'method':item}}
    validate_phase({'stage':'bind_scope','products':value},'bind_scope',before,[],context)


def test_review_configuration_does_not_pretend_the_unwritten_draft_was_reviewed():
    item=source();value={'material_bindings':{},'process_bindings':{'method':{'scope':'[FAKE] 本场审稿'}},'_uses':[]}
    review=review_fixture(item,['review'])
    context={'scope':'chapter','binding_policy':'workflow-source-binding-v1','binding_test_mode':True,
        'binding_reviews':{'method':review},'material_source_snapshots':{'method':item}}
    validate_assembly(value,{},[],context)
    assert not value['_uses']


def test_historical_final_bindings_remain_readable_but_need_review_for_new_execution(tmp_path):
    from nw.materials.phase_projection import verify_chain
    from nw.materials.binding_reviews import verify_session_bindings
    session=chain();binder=session['stages'][-1]
    binder['products']['material_bindings']={'scene':{'method':{'function':'[FAKE] 旧绑定',
        'parameter':'[FAKE] 封条','observable':'[FAKE] 托起纸角','check':'[FAKE] 动作有因果'}}}
    binder['sha256']=content_sha256(binder['products'])
    verify_chain(session)
    with pytest.raises(ValueError,match='historical candidate routes need review'):
        verify_session_bindings(session,tmp_path,test_mode=True)
