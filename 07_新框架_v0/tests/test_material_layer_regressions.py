"""Regressions found by independent review and the real 13k-position audit."""
from hashlib import sha256
import json
import sqlite3

import pytest

from nw.materials.catalog import _SCHEMA,_fragment_rows
from nw.materials.fragments import parse_fragments
from nw.materials.layers import LayerCompiler
from nw.materials.route_catalog import _FRAGMENTS,_UNITS
from nw.materials.unit_catalog import _SCHEMA as UNIT_SCHEMA,_row_units
from nw.materials.binding import validate_bindings
from test_material_process import scenario


def indexed(text,family):
    data=text.encode(); db=sqlite3.connect(':memory:'); db.row_factory=sqlite3.Row
    db.executescript(_SCHEMA+UNIT_SCHEMA)
    db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',('s','source.txt',sha256(data).hexdigest(),family,'baseline',len(data),'INDEXED'))
    _,fragments=parse_fragments(data,family)
    db.executemany('INSERT INTO fragments VALUES (?,?,?,?,?,?,?,?,?,?)',_fragment_rows('s',data,fragments))
    for f in db.execute('SELECT id,kind,key,byte_start,line_start,sha256,payload FROM fragments').fetchall():
        db.executemany('INSERT INTO material_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',_row_units(f))
    return db


def review(root,profile='anchor'):
    return {'owner_id':root['id'],'profile':profile,'meaning':'原定义的条件与作用','state':'design_ready'}


def test_repeated_anchor_id_keeps_each_inline_upgrade_with_its_own_row():
    def anchor(binding):
        raw={'runtime_calling_layer':[{'source_id':'M1.1','binding_id':binding}]}
        return '| M1.1 | 道具_完整 | 道具完整 | 未损坏 | 物质 |<details><summary>运行层升级</summary>'+json.dumps(raw)+'</details>\n'
    db=indexed(anchor('owner-1')+anchor('owner-2'),'anchors')
    roots=[dict(r) for r in db.execute(_FRAGMENTS+" WHERE f.kind='anchor' ORDER BY f.byte_start")]
    result=LayerCompiler(db).for_owner(roots[0],review(roots[0]))
    assert [b for p in result['pairs'] for b in p['binding_ids']]==['owner-1']


@pytest.mark.parametrize('binding',[None,{'source_id':'M1.1','semantic_interpretation':None},
                                  {'source_id':'M1.1','creation_binding':None}])
def test_malformed_runtime_sections_are_quarantined_as_source_issues(binding):
    raw={'runtime_calling_layer':None if binding is None else [binding]}
    text='| M1.1 | 道具_完整 | 道具完整 | 未损坏 | 物质 |<details><summary>运行层升级</summary>'+json.dumps(raw)+'</details>\n'
    db=indexed(text,'anchors'); root=dict(db.execute(_FRAGMENTS+" WHERE f.kind='anchor'").fetchone())
    result=LayerCompiler(db).for_owner(root,review(root))
    assert result['issues'] and any(i['kind']=='malformed_translation' for i in result['issues'])


def test_static_synthetic_identity_must_match_endpoints_and_exact_edge_ordinal():
    raw={'source':'人物','target':'悬念','type':'绑定','condition':'未调查前保持未知',
         '运行层升级':{'canonical_source_id':'STATIC:人物->悬念#1','runtime_calling_layer':[
             {'source_id':'STATIC:人物->悬念#1','binding_id':'TB-static'}]}}
    db=indexed(json.dumps({'connections':[raw]},ensure_ascii=False),'static')
    root=dict(db.execute(_FRAGMENTS+" WHERE f.kind='network_edge'").fetchone())
    result=LayerCompiler(db).for_owner(root,review(root,'static_relation'))
    assert result['pairs'] and result['execution']['evidence_kind']=='relation_constraints'


def test_source_block_upgrade_binds_only_its_uniquely_named_nested_record():
    wrapper={'原始条目':[{'connection_id':'TSC_A','description':'关系甲的条件与限制'},
                        {'connection_id':'TSC_B','description':'关系乙的条件与限制'}],
             '运行层升级':{'canonical_source_id':'TYPE-SOURCE:1','runtime_calling_layer':[
                 {'source_id':'TSC_B','binding_id':'TB-B'}]}}
    db=indexed('SOURCE: 类型连接.json\n=====\n'+json.dumps(wrapper,ensure_ascii=False),'type_links')
    roots={r['key']:dict(r) for r in db.execute(_UNITS+" WHERE u.kind='record'")}
    compiler=LayerCompiler(db)
    assert not compiler.for_owner(roots['TSC_A'],review(roots['TSC_A'],'type_link'))
    result=compiler.for_owner(roots['TSC_B'],review(roots['TSC_B'],'type_link'))
    assert result['pairs'][0]['binding_ids']==['TB-B']


def test_writer_receives_visible_expression_without_hidden_translation_context():
    from nw.materials.evidence import writer_checks
    hidden='幕后主使正在密室中指使凶手'
    material={'source':{'id':'rule'},'request':{'disposition':'required'},'profile':'character',
              'review':{'evidence_required':'核对当前稿','layer_contract':{'execution':{'domain':'character'}}}}
    design={'materials':[material],'bindings':{'rule':{'observable':'看到信封封口未拆','check':'观察前封口保持原样',
        'layer_application':{'trigger':hidden,'operation':'查看信封','result':'第十章才公布主使','verification':'全书对照'}}}}
    payload=json.dumps(writer_checks(design),ensure_ascii=False)
    assert hidden not in payload and '第十章' not in payload
    assert '看到信封封口未拆' in payload


def test_author_deferral_is_an_exclusion_in_current_selection_artifact():
    candidate,members,materials=scenario('material_selection')
    later={**materials[0],'source':{'id':'later','key':'后章线索','fragment_id':'block-later'}}
    materials.append(later)
    candidate['process_bindings']={'process':{'task_function':'本章完成现有调查',
        'selections':[{'id':'rule','block_id':'block','reason':'本章目标'},
                      {'id':'later','block_id':'block-later','reason':'以后也会用到'}],'exclusions':[]}}
    with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
        validate_bindings(candidate,'chapter',members,{},materials,{'later':'下一章再核对'})


def test_invalid_conversion_binding_structure_returns_a_validation_error():
    candidate,members,materials=scenario('material_conversion')
    candidate['material_bindings']=[]
    candidate['process_bindings']={'process':{'mappings':[]}}
    with pytest.raises(ValueError,match='MATERIAL_PROCESS'):
        validate_bindings(candidate,'chapter',members,{},materials)


def test_manual_type_identity_remains_usable_after_adjudication(tmp_path,monkeypatch):
    from test_type_adjudication import catalog,genre,root
    from nw.materials.reviews import _REVIEWS,Review
    from nw.materials.adjudication import build_adjudications
    from nw.materials.binding import resolve_materials
    db,rows,_=catalog(tmp_path,{'主类型.json':genre()})
    owner=root(rows,'主类型.json'); ws=tmp_path/'workspace'
    monkeypatch.setitem(_REVIEWS,owner['id'],Review(owner['file_sha256'],owner['sha256'],'type_identity',
        '核读的类型定义','保留该版本的适用范围','核对类型承诺'))
    build_adjudications(ws)
    material=resolve_materials(ws,[{**{k:owner[k] for k in ('id','file_sha256','sha256')},
                                   'disposition':'required','reason':'采用已核读的当前版本'}])[0]
    assert material['original']['type_id']=='GENRE_ONE'


def test_type_profile_supplements_its_exact_named_type_without_inheriting_completed_status():
    data={'type_id':'GENRE_A','canonical_name':'类型甲','definition':'类型甲通过规则探索展示人物选择'}
    text=('SOURCE: 主类型.json\n=====\n'+json.dumps(data,ensure_ascii=False)+'\n\n# 类型画像补全\n'
          '## 类型甲\n【核心元素】规则探索与人物选择。\n【读者期待】行动能够揭示规则的代价。\n'
          '【风格约束】保持受限视角与可核查的因果。\n【篇幅适配】多章兑现类型期待。\n'
          '【风险点】不能把类型标签当作正文效果。\n【类型画像补全】状态：completed\n')
    db=indexed(text,'types'); owner=dict(db.execute(_UNITS+" WHERE u.kind='record'").fetchone())
    result=LayerCompiler(db).for_owner(owner,review(owner,'type_identity'))
    assert result and result['pairs'][0]['mode']=='type_profile_supplement'
    assert len(result['pairs'][0]['aligned_fields'])==5
    assert 'completed' not in json.dumps(result['pairs'],ensure_ascii=False)


def test_separate_anchor_upgrade_resolves_unique_original_with_leading_whitespace():
    raw={'canonical_source_id':'M1.1','runtime_calling_layer':[{'source_id':'M1.1','binding_id':'TB-separate'}]}
    text=('\n| M1.1 | 道具_完整 | 道具完整 | 未损坏 | 物质 |\n'
          '### M1.1\n【运行层升级】\n```json\n'+json.dumps(raw)+'\n```\n')
    db=indexed(text,'anchors')
    owner=dict(db.execute(_FRAGMENTS+" WHERE f.kind='anchor' ORDER BY f.byte_start LIMIT 1").fetchone())
    result=LayerCompiler(db).for_owner(owner,review(owner))
    assert result and result['pairs'][0]['binding_ids']==['TB-separate']


@pytest.mark.parametrize('block',['类型关系.json','另一来源.json'])
def test_tail_translation_uses_explicit_source_block_and_native_record_id(block):
    raw={'runtime_calling_layer':[{'source_id':'TSC_A','binding_id':'TB-tail',
        'source_ref':f'原始资料/类型连接.txt:{block}[0]'}]}
    text=('SOURCE: 类型关系.json\n=====\n'+json.dumps([{'connection_id':'TSC_A','description':'角色关系的适用条件'}],ensure_ascii=False)+
          '\nSOURCE: 末尾.json\n=====\n{}\n\n## 类型系统原版条目补全\n### TSC_A\n```json\n'+
          json.dumps(raw,ensure_ascii=False)+'\n```\n')
    db=indexed(text,'type_links'); owner=dict(db.execute(_UNITS+" WHERE u.kind='record'").fetchone())
    result=LayerCompiler(db).for_owner(owner,review(owner,'type_link'))
    if block=='类型关系.json':
        assert result and result['pairs'][0]['binding_ids']==['TB-tail']
    else:
        assert not result


@pytest.mark.parametrize('ordinal',[2,3])
def test_legacy_one_based_record_reference_keeps_native_identity_and_exact_pointer(ordinal):
    upgrade={'runtime_calling_layer':[{'source_id':'类型静态搭配库.json:2','binding_id':'TB-second',
        'source_ref':f'原始资料/类型连接.txt:类型静态搭配库.json[{ordinal}]'}]}
    text=('SOURCE: 类型静态搭配库.json\n=====\n'+json.dumps({'原始条目':[
        {'static_combination_id':'COMBO_A','description':'第一条候选组合'},
        {'static_combination_id':'COMBO_B','description':'第二条候选组合'}]},ensure_ascii=False)+
        '\nSOURCE: 末尾.json\n=====\n{}\n## 类型系统原版条目补全\n### 类型静态搭配库.json:2\n```json\n'+
        json.dumps(upgrade,ensure_ascii=False)+'\n```\n')
    db=indexed(text,'type_links'); owners={r['key']:dict(r) for r in db.execute(_UNITS+" WHERE u.kind='record'")}
    compiler=LayerCompiler(db)
    assert not compiler.for_owner(owners['COMBO_A'],review(owners['COMBO_A'],'type_combination'))
    paired=compiler.for_owner(owners['COMBO_B'],review(owners['COMBO_B'],'type_combination'))
    if ordinal==2:
        assert paired and paired['pairs'][0]['binding_ids']==['TB-second']
        assert paired['owner_id']==owners['COMBO_B']['id']
    else:
        assert not paired or not paired['pairs']


@pytest.mark.parametrize('raw',[
    {'canonical_source_id':17,'runtime_calling_layer':[{'source_id':'M1.1'}]},
    {'runtime_calling_layer':[{'source_id':['M1.1']}]},
])
def test_invalid_translation_identifiers_are_source_issues_not_batch_crashes(raw):
    text='| M1.1 | 道具_完整 | 道具完整 | 未损坏 | 物质 |<details><summary>运行层升级</summary>'+json.dumps(raw)+'</details>\n'
    db=indexed(text,'anchors'); root=dict(db.execute(_FRAGMENTS+" WHERE f.kind='anchor'").fetchone())
    result=LayerCompiler(db).for_owner(root,review(root))
    assert result['issues'] and not result['pairs']
