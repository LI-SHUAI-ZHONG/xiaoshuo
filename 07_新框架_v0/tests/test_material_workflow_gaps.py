"""Normal planning must use the full catalog and honor procedural sources."""
import json

import pytest

from nw.materials.adjudication import Adjudicator
from nw.materials.catalog import _SCHEMA, _fragment_rows
from nw.materials.fragments import parse_fragments
from nw.materials.route_catalog import _FRAGMENTS, _UNITS
from nw.materials.unit_catalog import _SCHEMA as UNITS, _row_units
from nw.materials import library_adjudication
from nw.materials.layers import LayerCompiler
from nw.call_budget import create_budget
from nw.planning import prepare_plan_task
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_stage_integration import pins_for
from test_novel_flow import Model, config


def indexed(text):
    import sqlite3
    data = text.encode()
    db = sqlite3.connect(':memory:'); db.row_factory = sqlite3.Row
    db.executescript(_SCHEMA + UNITS)
    db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',
               ('s', 'library.txt', library_adjudication._PINNED['library'], 'library', 'baseline', len(data), 'INDEXED'))
    _, parts = parse_fragments(data, 'library')
    db.executemany('INSERT INTO fragments VALUES (?,?,?,?,?,?,?,?,?,?)', _fragment_rows('s', data, parts))
    for row in db.execute('SELECT id,kind,key,byte_start,line_start,sha256,payload FROM fragments').fetchall():
        db.executemany('INSERT INTO material_units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', _row_units(row))
    return db


@pytest.mark.parametrize('key,profile', [
    ('126.9_时间线模板调用', 'timeline_process'), ('126.10_伏笔网络模板调用', 'promise_process'),
    ('126.11_多视角切换模板调用', 'pov_process'), ('126.12_创作前一次性模板调用', 'preflight_process'),
    ('126.16_模板版本管理', 'usage_process')])
def test_procedural_sources_are_not_discarded_as_example_templates(tmp_path, key, profile):
    db = indexed(f'### {key}\n【定义】必须记录阶段输入、实际操作和核验产物。\n【指令】必须核对对应阶段产物。\n')
    try:
        owner = dict(db.execute(_FRAGMENTS + " WHERE f.kind='library_entry'").fetchone())
        from nw.materials.routing import disposition
        assert disposition(owner)[2] == 'candidate'
        result = Adjudicator(db, tmp_path).review(owner)
        assert result['state'] == 'design_ready'
        assert result['profile'] == profile
    finally:
        db.close()


def test_tail_original_inside_old_upgrade_fragment_is_indexed_and_exactly_paired(tmp_path):
    upgrade = lambda key: '【运行层升级】\n```json\n' + json.dumps({'runtime_calling_layer': [
        {'source_id': key, 'binding_id': 'TB-' + key}]}, ensure_ascii=False) + '\n```\n'
    text = ('### 128.8_执行调用\n【定义】必须按阶段调用资料。\n' + upgrade('128.8_执行调用') +
            '### 129_命名与术语体系\n【定义】专有名词必须采用一致命名。\n【指令】禁止同一对象使用冲突名称。\n' +
            upgrade('129_命名与术语体系'))
    db = indexed(text)
    try:
        row = db.execute(_UNITS + " WHERE u.key='129_命名与术语体系' AND u.kind='embedded_block'").fetchone()
        assert row is not None, 'original section was swallowed by an earlier upgrade fragment'
        result = Adjudicator(db, tmp_path).review(dict(row))
        assert result['state'] == 'design_ready'
        assert result['layer_contract']['pairs'][0]['translation_source_ids'] == ['129_命名与术语体系']
    finally:
        db.close()


def test_whole_number_original_inside_an_entry_keeps_its_exact_declared_identity(tmp_path):
    upgrade={'runtime_calling_layer':[{'source_id':'129_命名与术语体系','binding_id':'naming-one'}]}
    text=('### 1.1_行动动机\n【定义】选择必须有目标。\n'
          '### 129_命名与术语体系\n【定义】专有名词必须采用一致命名。\n【指令】禁止同一对象使用冲突名称。\n'
          '【运行层升级】\n```json\n'+json.dumps(upgrade,ensure_ascii=False)+'\n```\n')
    db=indexed(text)
    try:
        row=db.execute(_UNITS+" WHERE u.key='129_命名与术语体系' AND u.kind='embedded_block'").fetchone()
        assert row is not None
        result=Adjudicator(db,tmp_path).review(dict(row))
        assert result['layer_contract']['pairs'][0]['translation_source_ids']==['129_命名与术语体系']
        old=db.execute(_UNITS+" WHERE u.key LIKE '1.1%#129_%' AND u.kind='embedded_block'").fetchone()
        assert old is not None
        assert not Adjudicator(db,tmp_path).review(dict(old))['can_offer_for_design']
    finally:
        db.close()


def test_normal_plan_recalls_catalog_without_the_author_passing_source_hashes(tmp_path, monkeypatch):
    text = ('### 1.1_行动动机\n【定义】人物行动必须有具体目标，选择必须承担行动后果。\n'
            '【指令】在决定前展示目标，决定后兑现代价。\n')
    pin = pins_for(tmp_path, monkeypatch, text, ['1.1_行动动机'])[0]
    with Store(tmp_path / 'project', create=True, test_mode=True) as store:
        store.init_project('自动选材'); store.add_brief('行动动机推动调查，选择必须付出代价')
        adopt_story(store, baseline(), {})
        bid = create_budget(store, 'auto-plan', Budget(2, 90000, 4000))
        _, package = prepare_plan_task(store, 1, 'book', Model(), config(store), bid, 'normal-plan')
        assert any(row['source']['id'] == pin['id'] for row in package.get('materials', []))
        assert package['material_recall']['policy'] == 'catalog-functional-recall-v1'
        assert package['material_recall']['selected'][0]['reason']


def test_catalog_recall_matches_actual_function_even_without_the_source_title(tmp_path, monkeypatch):
    from nw.materials.recall import recall_materials
    text = ('### 1.1_行动动机\n【定义】人物选择必须由具体目标驱动，选择必须承担后果。\n'
            '【指令】必须在决定前建立目标，并在决定后呈现行动代价。\n')
    pin = pins_for(tmp_path, monkeypatch, text, ['1.1_行动动机'])[0]
    selected, _ = recall_materials(tmp_path, '写清人物的具体目标，让决定造成代价和后果')
    assert any(row['source']['id'] == pin['id'] for row in selected)


def test_named_type_section_translation_is_not_interpreted_as_an_ordinal(tmp_path):
    from test_material_layer_regressions import indexed as type_catalog, review
    owner={'type_id':'GENRE_A','canonical_name':'仙侠','definition':'以修行规则和资源代价推动人物探索'}
    upgrade={'runtime_calling_layer':[{'source_id':'仙侠','binding_id':'section-one',
        'source_ref':'原始资料/类型系统.txt:SECTION: 仙侠'}]}
    text=('SOURCE: 主类型.json\n=====\n'+json.dumps([owner],ensure_ascii=False)+
          '\n## 类型系统原版条目补全\n### 仙侠\n【运行层升级】\n```json\n'+json.dumps(upgrade,ensure_ascii=False)+'\n```\n')
    db=type_catalog(text,'types')
    try:
        row=dict(db.execute(_UNITS+" WHERE u.kind='record'").fetchone())
        layers=LayerCompiler(db).for_owner(row,review(row,'type_identity'))
        assert layers['pairs'][0]['translation_source_ids']==['仙侠']
    finally:
        db.close()


def test_normal_recall_can_propose_an_existing_combination_for_the_selected_type(tmp_path):
    from test_type_adjudication import catalog,genre
    from nw.materials.adjudication import build_adjudications
    from nw.materials.recall import recall_materials
    combo={'combination_id':'COMBO_ONE','primary_type_id':'GENRE_ONE','type_ids':['GENRE_ONE'],
           'description':'类型一通过调查选择与资源代价形成困境','status':'candidate','selection_status':'candidate'}
    db,_,_=catalog(tmp_path,{'主类型.json':[genre()],'类型组合总表.json':[combo]}); db.close()
    workspace=tmp_path/'workspace'; build_adjudications(workspace)
    selected,_=recall_materials(workspace,'类型一，围绕调查选择与资源代价设计故事')
    assert {r['profile'] for r in selected}=={'type_identity','type_combination'}


def test_combination_recall_does_not_substitute_a_different_source_version_of_the_same_type(tmp_path):
    from test_type_adjudication import catalog,genre
    from nw.materials.adjudication import build_adjudications
    from nw.materials.recall import recall_materials
    main,other=genre(),genre()
    main['canonical_name']='类型甲';other['canonical_name']='类型乙';other['definition']='以另一种世界机制呈现不同人物困境'
    combo={'combination_id':'COMBO_ONE','primary_type_id':'GENRE_ONE','type_ids':['GENRE_ONE'],
           'description':'通过调查选择与资源代价形成困境','status':'candidate','selection_status':'candidate'}
    db,_,_=catalog(tmp_path,{'主类型.json':[main],'类型本体\\类型总表.json':[other],'类型组合总表.json':[combo]});db.close()
    workspace=tmp_path/'workspace';build_adjudications(workspace)
    selected,report=recall_materials(workspace,'类型乙，围绕调查选择与资源代价设计故事')
    assert {r['profile'] for r in selected}=={'type_identity'}
    assert report['excluded_counts']['TYPE_COMBINATION_REQUIRES_EXACT_SELECTED_SOURCE_VERSIONS']==1


def test_book_model_receives_current_stage_data_while_full_future_rules_stay_frozen(tmp_path,monkeypatch):
    text=('### 1.1_行动动机\n【定义】人物行动必须有目标并承担后果。\n【指令】必须核对目标、行动和代价。\n'
          '【补充说明】'+('只用于后续章场的独立补充细则。'*1500)+'\n')
    pin=pins_for(tmp_path,monkeypatch,text,['1.1_行动动机'])[0]
    from nw.materials.binding import resolve_materials
    with Store(tmp_path/'stage-input',create=True,test_mode=True) as store:
        store.init_project('分阶段输入');store.add_brief('行动动机推动调查');adopt_story(store,baseline(),{})
        budget=create_budget(store,'stage-size',Budget(2,12000,2000))
        request,full=prepare_plan_task(store,1,'book',Model(),config(store),budget,'stage-size-plan',
                                       materials=resolve_materials(tmp_path,[pin]))
        sent=json.loads(request.payload['messages'][-1]['content'])
        assert len(request.payload['messages'][-1]['content'])<12000
        assert len(json.dumps(full['materials'],ensure_ascii=False))>12000
        assert sent['materials'][0]['source']['id']==pin['id']
        assert full['material_input']['complete_material_snapshots_preserved']


def test_actual_usage_definition_is_an_operation_even_without_the_word_must(tmp_path):
    text=('### 126.16_模板版本管理\n【定义】模板调用的记录和优化。写作前记录：记录本章调用了哪些板块和模板。'
          '写作后记录：记录模板使用效果（有效/无效/需调整）。单元复盘：每完成一个故事单元（一个完整篇章或3-5章），'
          '复盘调用记录，优化下一次调用的模板组合。\n【指令】无\n')
    db=indexed(text)
    try:
        owner=dict(db.execute(_FRAGMENTS+" WHERE f.kind='library_entry'").fetchone())
        assert Adjudicator(db,tmp_path).review(owner)['can_offer_for_design']
    finally:
        db.close()


def test_recall_chooses_at_most_one_triggered_variant_per_core_process(tmp_path,monkeypatch):
    from nw.materials.recall import recall_materials
    keys=['127.1_对话转译甲','127.2_对话转译乙','128.1_对话选材甲','128.2_对话选材乙']
    text=''.join(f'### {key}\n【定义】对话任务必须明确设计参数、行动代价和资料选择。\n'
                 '【指令】必须记录具体阶段产物。\n' for key in keys)
    pins_for(tmp_path,monkeypatch,text,keys)
    selected,_=recall_materials(tmp_path,'对话任务需要选择资料并设计代价')
    from collections import Counter
    counts=Counter(r['profile'] for r in selected)
    assert counts=={'material_selection':1,'material_conversion':1}


def test_manually_reviewed_type_is_recalled_by_its_real_name(tmp_path,monkeypatch):
    from test_type_adjudication import catalog,genre,root
    from nw.materials.reviews import _REVIEWS,Review
    from nw.materials.adjudication import build_adjudications
    from nw.materials.recall import recall_materials
    db,rows,_=catalog(tmp_path,{'主类型.json':[genre()]})
    owner=root(rows,'主类型.json');db.close()
    monkeypatch.setitem(_REVIEWS,owner['id'],Review(owner['file_sha256'],owner['sha256'],'type_identity',
        '经原始定义核读的类型约束','当前项目须给出具体承诺','核对兑现与边界'))
    workspace=tmp_path/'workspace';build_adjudications(workspace)
    selected,_=recall_materials(workspace,'类型一，写一个有选择代价的故事')
    assert any(r['source']['id']==owner['id'] for r in selected)
