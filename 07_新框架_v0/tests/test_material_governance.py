"""Document governance has real checks and never acquires prose authority."""
from hashlib import sha256
import json

import pytest

from nw.materials.governance import GovernanceRouter
from nw.materials.layers import LayerCompiler
from nw.materials.route_catalog import _UNITS
from test_material_layer_regressions import indexed


def source(name, value, *, identity=None, source_ref=None):
    value={**value,'运行层升级':{'runtime_calling_layer':[{
        'binding_id':'TB-one','source_id':identity if identity is not None else name+':1',
        'source_ref':source_ref or 'source.txt:SOURCE: '+name,
        'model_input_eligible':True,'prose_write_allowed':True,
        'creation_binding':{'creative_action':'让角色作出选择并付出代价'}}]}}
    return 'SOURCE: '+name+'\n=====\n'+json.dumps(value,ensure_ascii=False)+'\n'


def routed(text):
    db=indexed(text,'type_links')
    unit=dict(db.execute(_UNITS+" WHERE u.origin='upgrade'").fetchone())
    return db,GovernanceRouter(db,LayerCompiler(db)),unit


def connections(value):
    return 'SOURCE: 类型静态连接总表.json\n=====\n'+json.dumps(value,ensure_ascii=False)+'\n'


def test_actual_schema_min_max_pattern_and_boolean_number_are_checked():
    schema={'weight':{'type':'number','min':0,'max':1,'description':'连接权重'},
            'confidence':{'type':'number','min':0,'max':1},
            'schema_version':{'type':'string','pattern':r'TYPE_C-\d+\.\d+\.\d+'}}
    text=source('类型静态连接字段说明.json',schema,identity=str(schema['weight']))+connections([
        {'connection_id':'TSC_ONE','source_id':'G','weight':2,'confidence':True,'schema_version':'bad'}])
    db,router,unit=routed(text)
    try:
        result=router.route(unit)
        assert result['exact_locators']==['/weight']
        assert result['validation']['status']=='failed'
        assert {(v['field'],v['error']) for v in result['validation']['violations']}=={
            ('weight','max'),('confidence','type'),('schema_version','pattern')}
    finally:db.close()


@pytest.mark.parametrize('invalid',['UNKNOWN',{'malformed':'value'}])
def test_enumeration_checks_original_records_without_crashing_on_invalid_types(invalid):
    text=source('类型连接枚举.json',{'connection_type':['SUPPORTS'],
                 'forbidden_connection_type':['GUARANTEES']})+connections([
                     {'connection_id':'TSC_ONE','source_id':'G','connection_type':invalid}])
    db,router,unit=routed(text)
    try:
        result=router.route(unit)
        assert result['role']=='enumeration'
        assert result['validation']['status']=='failed'
        assert result['validation']['records_checked']==1
        assert 'not_prose_permission' in result['authority']
        assert 'creation_binding' not in result
    finally:db.close()


def test_missing_inspection_input_is_not_a_passing_zero_record_check():
    db,router,unit=routed(source('类型连接枚举.json',{'connection_type':['SUPPORTS']}))
    try:
        assert router.route(unit)['validation']['status']=='not_checked'
    finally:db.close()


def test_schema_validates_every_actual_collection_position_including_missing_ids():
    schema={'connection_id':{'type':'string','required':True},'weight':{'type':'number','max':1}}
    text=source('类型静态连接字段说明.json',schema)+connections([{'source_id':'G','weight':2},False])
    db,router,unit=routed(text)
    try:
        validation=router.route(unit)['validation']
        assert validation['status']=='failed'
        assert validation['records_checked']==2
        assert {(v['locator'],v['error']) for v in validation['violations']}=={
            ('/0','required'),('/0','max'),('/1','record_type')}
    finally:db.close()


@pytest.mark.parametrize('enum_value',[None,{'connection_type':'malformed'}])
def test_missing_or_invalid_declared_enum_dependency_cannot_pass(enum_value):
    schema={'connection_type':{'type':'string','enum_ref':'类型连接枚举.json'}}
    text=source('类型静态连接字段说明.json',schema)+connections([
        {'connection_id':'TSC_ONE','source_id':'G','connection_type':'UNKNOWN'}])
    if enum_value is not None:
        text+='SOURCE: 类型连接枚举.json\n=====\n'+json.dumps(enum_value)+'\n'
    db,router,unit=routed(text)
    try:assert router.route(unit)['validation']['status']=='not_checked'
    finally:db.close()


@pytest.mark.parametrize('count,status',[(0,'pass'),(1,'failed'),(False,'failed')])
def test_empty_active_container_cannot_invent_creative_records(count,status):
    db,router,unit=routed(source('作品人物关系搭配库.json',{'status':'active','items':[],'count':count}))
    try:
        result=router.route(unit)
        assert result['role']=='declared_collection_container'
        assert result['validation']['status']==status
        assert result['validation']['creative_rules_available']==0
        assert result['original_source_ref']['sha256']
        assert result['document_ref']['sha256']
    finally:db.close()


@pytest.mark.parametrize('identity,reference',[
    ('wrong:1','source.txt:SOURCE: 类型连接枚举.json'),
    ({'malformed':'identity'},'source.txt:SOURCE: 类型连接枚举.json'),
    (['malformed'],'source.txt:SOURCE: 类型连接枚举.json'),
    ('类型连接枚举.json:1','different.txt:SOURCE: 类型连接枚举.json')])
def test_wrong_document_or_wrong_source_file_remains_unresolved(identity,reference):
    text=source('类型连接枚举.json',{'connection_type':['SUPPORTS']},identity=identity,source_ref=reference)
    db,router,unit=routed(text)
    try:assert router.route(unit) is None
    finally:db.close()


def test_ambiguous_descriptor_never_selects_an_arbitrary_schema_field():
    descriptor={'type':'string','description':'同一描述'}
    db,router,unit=routed(source('类型静态连接字段说明.json',{'one':descriptor,'two':descriptor},identity=str(descriptor)))
    try:assert router.route(unit) is None
    finally:db.close()


def test_declared_validation_rules_preserve_unexecuted_semantic_work():
    rules=[{'rule_id':'V07','rule':'不包含固定剧情结果'}]
    db,router,unit=routed(source('类型连接验证规则.json',{'rules':rules}))
    try:
        result=router.route(unit)
        assert result['role']=='validation_contract'
        assert result['validation']['rules']==rules
        assert result['pending']
        assert not result['validation']['rules_executed_as_creative_methods']
    finally:db.close()


def test_normal_audit_reports_container_routes_separately_from_creative_pairing(tmp_path):
    from nw.materials.adjudication import build_adjudications
    from nw.materials.catalog import build_catalog
    from nw.materials.layer_audit import audit_layers
    from nw.materials.unit_catalog import index_units
    data=source('作品人物关系搭配库.json',{'status':'active','items':[],'count':0}).encode()
    (tmp_path/'source.txt').write_bytes(data)
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'schema_version':1,'catalog_inputs':[
        {'path':'source.txt','family':'type_links','layer':'baseline','sha256':sha256(data).hexdigest(),'bytes':len(data)}]}),encoding='utf-8')
    workspace=tmp_path/'workspace'
    build_catalog(workspace,tmp_path,manifest);index_units(workspace,None);build_adjudications(workspace)
    report=audit_layers(workspace,details=True)
    assert report['summary']['governance_routed_positions']==1
    assert report['summary']['governance_validation_statuses']=={'pass':1}
    assert report['summary']['governance_pending_consumers']==0
    assert report['summary']['paired_layer_positions']==0
    assert report['summary']['unresolved_translation_positions']==0
    assert report['governance_routes'][0]['role']=='declared_collection_container'
