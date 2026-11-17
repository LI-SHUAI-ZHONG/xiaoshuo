"""Runtime translations must remain tied to their actual source and domain."""
from hashlib import sha256
import json
import sqlite3

import pytest

from nw.materials.adjudication import Adjudicator
from nw.materials import library_adjudication
from nw.materials.catalog import _SCHEMA, _fragment_rows
from nw.materials.fragments import Fragment
from nw.materials.route_catalog import _FRAGMENTS, _UNITS
from nw.materials.unit_catalog import _SCHEMA as UNIT_SCHEMA, _row_units


def layer_catalog(*, source_id='1.1_行动目标', layer='baseline', procedural=False):
    key = '106.2_跨章句式比较' if procedural else '1.1_行动目标'
    definition = ('比较不同章节叙述语言的句式与用词，识别无原因的风格断裂。' if procedural else
                  '关键行动必须有明确目标，选择的后果须在下一次行动前生效。')
    original = f'### {key}\n【定义】{definition}\n【指令】必须核对前后因果证据。\n'
    upgrade = {'canonical_source_id': source_id if not procedural else key, 'runtime_calling_layer': [{
        'source_id': source_id if not procedural else key, 'binding_id':'TB-test',
        'model_input_eligible':True, 'prose_write_allowed':True,
        'semantic_interpretation': {'source_semantic_anchor': definition,
            'operational_meaning':'让角色作出选择并付出代价。'},
        'creation_binding': {'prose_strategy':'通过角色身体反应呈现。'},
        'evidence_contract': {'design_required':['stage','creative_action','source_ref']}}]}
    extra = '【运行层升级】\n```json\n'+json.dumps(upgrade,ensure_ascii=False)+'\n```\n'
    data=(original+extra).encode()
    db=sqlite3.connect(':memory:'); db.row_factory=sqlite3.Row
    db.executescript(_SCHEMA+UNIT_SCHEMA)
    db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',
               ('s','library.txt',library_adjudication._PINNED['library'],'library',layer,len(data),'INDEXED'))
    boundary=len(original.encode())
    chunks=[Fragment(0,boundary,'library_entry',key),
            Fragment(boundary,len(data),'library_upgrade',key)]
    db.executemany('INSERT INTO fragments VALUES (?,?,?,?,?,?,?,?,?,?)',_fragment_rows('s',data,chunks))
    for f in db.execute('SELECT id,kind,key,byte_start,line_start,sha256,payload FROM fragments').fetchall():
        db.executemany('INSERT INTO material_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',_row_units(f))
    root=dict(db.execute(_FRAGMENTS+" WHERE f.kind='library_entry'").fetchone())
    return db,root


def test_paired_translation_reaches_the_complete_source_contract(tmp_path):
    db,root=layer_catalog()
    review=Adjudicator(db,tmp_path).review(root)
    layers=review.get('layer_contract')
    assert layers, 'source-qualified runtime layers are currently discarded'
    assert layers['owner_id']==root['id']
    assert len(layers['pairs'])==1
    assert layers['pairs'][0]['binding_ids']==['TB-test']
    assert layers['execution']['domain']=='character'
    assert layers['execution']['evidence_kind']=='action_and_consequence'
    assert layers['pairs'][0]['source_ref']['file_sha256']==root['file_sha256']
    assert 'model_input_eligible' not in layers['execution']


def test_wrong_source_id_cannot_supply_a_translation(tmp_path):
    db,root=layer_catalog(source_id='9.9_别的条目')
    layers=Adjudicator(db,tmp_path).review(root).get('layer_contract')
    assert layers and not layers['pairs']
    assert layers['issues'][0]['kind']=='translation_identity_mismatch'
    assert layers['execution'] is None


def test_narrative_review_is_not_turned_into_character_state(tmp_path):
    db,root=layer_catalog(procedural=True)
    layers=Adjudicator(db,tmp_path).review(root).get('layer_contract')
    assert layers and layers['execution']['evidence_kind']=='complete_draft_comparison'
    assert layers['execution']['domain']=='narration'
    assert any(x['kind']=='semantic_domain_conflict' for x in layers['issues'])
    assert '身体反应' not in json.dumps(layers['execution'],ensure_ascii=False)


def test_historical_translation_does_not_attach_to_current_source(tmp_path):
    db,root=layer_catalog(layer='historical')
    assert not Adjudicator(db,tmp_path).review(root).get('layer_contract')


def test_mismatched_translation_payload_hash_is_detected(tmp_path):
    db,root=layer_catalog()
    db.execute("UPDATE fragments SET payload=CAST(replace(CAST(payload AS TEXT),'TB-test','TB-evil') AS BLOB) WHERE kind='library_upgrade'")
    with pytest.raises(ValueError,match='hash'):
        Adjudicator(db,tmp_path).review(root)


def compiled_layers(tmp_path, monkeypatch):
    from nw.materials.catalog import build_catalog, list_catalog
    from nw.materials.unit_catalog import index_units
    from nw.materials.adjudication import build_adjudications
    from nw.materials.route_catalog import route
    from test_material_catalog import _manifest
    db,_=layer_catalog()
    data=b''.join(r[0] for r in db.execute('SELECT payload FROM fragments ORDER BY byte_start'))
    monkeypatch.setitem(library_adjudication._PINNED,'library',sha256(data).hexdigest())
    manifest=_manifest(tmp_path/'source',tmp_path,[('library.txt','library',data)])
    build_catalog(tmp_path,tmp_path/'source',manifest); index_units(tmp_path,None)
    build_adjudications(tmp_path)
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)
    root=list_catalog(tmp_path,None,'1.1_行动目标')['fragments'][0]
    source=route(tmp_path,root['fragment_id'])['source']
    return {**{k:source[k] for k in ('id','file_sha256','sha256')},'disposition':'required','reason':'核对行动目标'}


def test_resolved_layers_require_specific_project_translation(tmp_path,monkeypatch):
    from nw.materials.binding import resolve_materials,validate_bindings
    pin=compiled_layers(tmp_path,monkeypatch)
    material=resolve_materials(tmp_path,[pin])[0]
    assert material['review'].get('layer_contract'), 'paired layer must enter actual design input'
    fields=material['review']['contract']['obligations']
    mapping={'function':'调查行动的因果','parameter':'沈砚调查旧印',
             'observable':'举灯查看封条并承担烧伤','check':'目标、行动、后果相连',
             'source_scope':{f['id']:{'disposition':'required','reason':'本场关键行动'} for f in fields}}
    candidate={'material_bindings':{'scene':{pin['id']:mapping}}}
    with pytest.raises(ValueError,match='MATERIAL_TRANSLATION'):
        validate_bindings(candidate,'chapter',{'scene':{'kind':'scene','body':{}}},{},[material])


@pytest.mark.parametrize('failure',['','omit_layer','unverified_layer'])
def test_layer_translation_is_reviewed_before_acceptance_and_after_restart(tmp_path,monkeypatch,failure):
    from test_material_adjudication import AdjudicatedModel
    from test_material_workflow import design
    from test_novel_flow import config,author
    from story_fixture import baseline
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.novel_flow import JobRequest,start_job,resume_job
    from nw.task_models import Budget
    class LayerModel(AdjudicatedModel):
        def generate(self,messages,**params):
            output=super().generate(messages,**params)
            prompt=messages[0]['content']; package=json.loads(messages[-1]['content'])
            if 'candidate_cards' in prompt and package['scope']!='book':
                raw=json.loads(output.text)
                for candidate in raw['candidate_cards']:
                    for bindings in candidate['material_bindings'].values():
                        for binding in bindings.values():
                            binding['layer_application']={'trigger':'沈砚决定查看封条的这一刻',
                                'operation':'让调查目标引出举灯检查的行动',
                                'result':'看清旧印同时留下手背烧伤',
                                'verification':'核对目标在前、举灯在中、烧伤与线索在后的因果'}
                output.text=json.dumps(raw,ensure_ascii=False)
            elif '{"recommendation"' in prompt and failure!='omit_layer':
                raw=json.loads(output.text)
                for check in raw['material_checks']:
                    if check['id'].startswith('work:'):continue
                    check['layer_check']={'status':'unverified' if failure else 'pass',
                        'reason':'目标引发举灯行动，烧伤和新线索构成可定位后果',
                        'evidence':check['evidence']}
                output.text=json.dumps(raw,ensure_ascii=False)
            return output
    pin=compiled_layers(tmp_path,monkeypatch); model=LayerModel()
    path=tmp_path/'layer_story'
    with Store(path,create=True,test_mode=True) as store:
        store.init_project('隔离转译核验'); store.add_brief('查看封条'); adopt_story(store,baseline(),{})
        scene=design(store,pin,model)
        job=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(12,45000,2000))).id
        result=resume_job(store,job,model,config(store))
        if failure:
            assert result.status=='BLOCKED' and not store.list('accepted')
        else:
            assert result.step=='batch:confirm',result.reason
    if not failure:
        with Store(path,test_mode=True) as store:
            result=resume_job(store,job,model,config(store),author())
            assert result.status=='DONE' and len(store.list('accepted'))==1


def test_audit_counts_actual_pairing_and_refuses_stale_ledger(tmp_path,monkeypatch):
    from nw.materials.layer_audit import audit_layers
    compiled_layers(tmp_path,monkeypatch)
    report=audit_layers(tmp_path)
    assert report['summary']['runtime_positions']==1
    assert report['summary']['paired_runtime_positions']==1
    assert report['summary']['executable_owners_with_layers']==1
    assert report['summary']['formal_novel_effects_verified']==0
    with sqlite3.connect(tmp_path/'materials'/'adjudication.db') as saved:
        saved.execute("UPDATE metadata SET value='\"stale\"' WHERE key='code_sha256'")
    with pytest.raises(ValueError,match='STALE'):
        audit_layers(tmp_path)


@pytest.mark.parametrize('family,profile,kind,key,expected',[
    ('static','static_relation','network_edge','S-1','relation_constraints'),
    ('dynamic','dynamic_relation','network_edge','D-1','cause_and_state_delta'),
    ('anchors','anchor','anchor','M1.1','pov_condition_and_observation'),
    ('types','type_identity','source_block','A.json','type_promise_and_boundary'),
])
def test_networks_and_type_records_use_their_own_domain(family,profile,kind,key,expected):
    from nw.materials.layers import LayerCompiler
    logical='GENRE_A' if family=='types' else key
    upgrade={'canonical_source_id':logical,'runtime_calling_layer':[{
        'binding_id':'TB-domain','source_id':logical,'semantic_interpretation':{
            'source_semantic_anchor':'原条件成立时保持明确的关系约束'}}]}
    legacy_costs = {
        'static': '关系被重新确认后，至少一方失去原有权限、资源或安全余量，新的关系边界限制后续行动。',
        'dynamic': '传播会消耗行动窗口或暴露关系来源，后续对象必须在已改变的状态上重新决策。',
        'anchors': '角色为确认或避开该锚点付出时间、暴露位置或承受身体不适，场景状态因此不可完全复原。',
    }
    if family in legacy_costs:
        binding = upgrade['runtime_calling_layer'][0]
        binding['semantic_interpretation']['operational_meaning'] = '原条件成立时保持明确的关系约束'
        binding['creation_binding'] = {'creative_strategy': {
            'cost_or_change': legacy_costs[family],
            'source_specific_trigger': '视角出现通用现象时展开一次动作',
        }}
        if family == 'static':
            upgrade['runtime_calling_layer'].append(binding)
    if family=='anchors':
        text='| M1.1 | 道具_完整 | 原条件成立时保持明确的关系约束 | 未损坏 | 物质 | <details><summary>运行层升级</summary>'+json.dumps(upgrade,ensure_ascii=False)+'</details>\n'
    else:
        obj={'type_id':logical,'canonical_name':'类型甲','definition':'原条件成立时保持明确的关系约束'} if family=='types' else {
            'id':logical,'source':'人物','target':'悬念','type':'约束','condition':'原条件成立时保持明确的关系约束'}
        obj['运行层升级']=upgrade
        text=('SOURCE: A.json\n=====\n' if family=='types' else '')+json.dumps(obj,ensure_ascii=False)
    data=text.encode(); db=sqlite3.connect(':memory:'); db.row_factory=sqlite3.Row
    db.executescript(_SCHEMA+UNIT_SCHEMA)
    db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',('s','source.txt',sha256(data).hexdigest(),family,'baseline',len(data),'INDEXED'))
    db.executemany('INSERT INTO fragments VALUES (?,?,?,?,?,?,?,?,?,?)',_fragment_rows('s',data,[Fragment(0,len(data),kind,key)]))
    for f in db.execute('SELECT id,kind,key,byte_start,line_start,sha256,payload FROM fragments').fetchall():
        db.executemany('INSERT INTO material_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',_row_units(f))
    root=dict(db.execute((_UNITS+" WHERE u.kind='record'") if family=='types' else _FRAGMENTS).fetchone())
    layers=LayerCompiler(db).for_owner(root,{'owner_id':root['id'],'profile':profile,'meaning':'原条件成立时保持明确的关系约束','state':'design_ready'})
    assert layers and layers['pairs']
    assert layers['execution']['evidence_kind']==expected
    if family in legacy_costs:
        pair = layers['pairs'][0]
        assert len(pair['aligned_fields']) == 1
        assert pair['aligned_fields'][0]['text'] == '原条件成立时保持明确的关系约束'
        rejected = {field['field'] for field in pair['rejected_fields']}
        assert 'creation_binding/creative_strategy/cost_or_change' in rejected
        if family == 'anchors':
            assert 'creation_binding/creative_strategy/source_specific_trigger' in rejected
