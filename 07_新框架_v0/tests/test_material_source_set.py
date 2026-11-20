"""The selected full version is the only operational source, not an item cap."""
import json
import sqlite3

import pytest

from nw.materials.catalog import build_catalog,list_catalog,show_fragment
from nw.materials.unit_catalog import index_units,list_units
from nw.materials.work_catalog import SourceDesk
from nw.task_models import content_sha256
from test_material_catalog import _manifest

FAMILIES=('library','types','type_links','static','dynamic','anchors')


def catalog(tmp_path, *, extra_library=''):
    bodies={'library':('### 1.1_当前方法\n【定义】当前方法依据真实人物目标设计动作后果。\n'
                       '【指令】在决定前展示调查目标，决定后呈现人物选择的代价。\n' + extra_library),
        'types':'SOURCE: 主类型.json\n=====\n'+json.dumps([{'type_id':'GENRE_CURRENT','canonical_name':'当前类型',
            'definition':'通过真实人物目标推动行动并承担代价'}],ensure_ascii=False),
        'type_links':'SOURCE: 类型静态连接总表.json\n=====\n'+json.dumps([{'connection_id':'CURRENT_1',
            'source_id':'GENRE_CURRENT','target_id':'CONCEPT_CURRENT'}]),
        'anchors':'| A1.1 | 当前锚点 | 低头看向门缝 | 紧张时 | 基础 |\n'}
    edge={'source':'1.1_当前方法','target':'1.2_当前目标','type':'绑定','condition':'人物行动时'}
    bodies['static']=json.dumps({'connections':[edge]},ensure_ascii=False)
    bodies['dynamic']=json.dumps({'connections':[{**edge,'effect':'目标人物改变行动'}]},ensure_ascii=False)
    entries=[(f'current-{family}.txt',family,bodies[family].encode('utf-8')) for family in FAMILIES]
    entries.append(('old-library.txt','library','### 1.1_旧版特有方法\n【定义】旧版动作包含具体目标和后果。\n'.encode('utf-8')))
    manifest=_manifest(tmp_path/'sources',tmp_path,entries)
    raw=json.loads(manifest.read_text(encoding='utf-8'));raw['catalog_inputs'][-1]['layer']='historical'
    manifest.write_text(json.dumps(raw,ensure_ascii=False),encoding='utf-8')
    build_catalog(tmp_path,tmp_path/'sources',manifest);index_units(tmp_path,None)
    sources=list_catalog(tmp_path,None,None)['sources']
    old=next(r for r in sources if r['layer']=='historical')
    old_id=list_catalog(tmp_path,old['source_id'],None)['fragments'][0]['fragment_id']
    units=list_units(tmp_path,source_id=old['source_id'],fragment_id=None,key=None,kind=None,limit=100,offset=0)['units']
    selected=[{'id':r['source_id'],'path':r['path'],'family':r['family'],'file_sha256':r['file_sha256']}
        for r in sources if r['layer']=='baseline']
    data={'policy':'single-material-version-v1','version_name':'[FAKE] 已明确选择的整套版本','sources':selected}
    data['sha256']=content_sha256(data)
    config=tmp_path/'materials/active_source_set.json'
    config.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    with sqlite3.connect(tmp_path/'materials/catalog.db') as db:
        db.execute('CREATE TABLE source_set_selection (singleton INTEGER PRIMARY KEY,policy TEXT NOT NULL,sha256 TEXT NOT NULL)')
        db.execute('INSERT INTO source_set_selection VALUES (1,?,?)',(data['policy'],data['sha256']))
    return config,data,old_id,units


def test_only_the_six_selected_files_are_operational_without_deleting_archives(tmp_path):
    config,data,old_id,units=catalog(tmp_path)
    current=list_catalog(tmp_path,None,None)['sources']
    assert {r['source_id'] for r in current}=={r['id'] for r in data['sources']}
    assert len(current)==6
    with sqlite3.connect(tmp_path/'materials/catalog.db') as db:
        assert db.execute('SELECT count(*) FROM sources').fetchone()[0]==7
    assert (tmp_path/'sources/old-library.txt').is_file()


def test_old_direct_fragment_and_unit_reads_cannot_bypass_source_selection(tmp_path):
    config,data,old_id,units=catalog(tmp_path)
    with pytest.raises(ValueError,match='not found|selected|disabled'):
        show_fragment(tmp_path,old_id)
    if units:
        with pytest.raises(ValueError,match='not found|selected|disabled'):
            show_fragment(tmp_path,units[0]['unit_id'])


def test_method_search_and_read_only_use_items_inside_the_selected_version(tmp_path):
    config,data,old_id,units=catalog(tmp_path);desk=SourceDesk(tmp_path)
    assert not desk.search('旧版特有')['items']
    assert old_id not in desk.by_id
    with pytest.raises(ValueError,match='outside|selected|disabled'):desk.read(old_id)
    assert desk.search('当前')['items']


def test_current_source_set_design_uses_authored_step_material_and_pins_original(tmp_path, monkeypatch):
    from nw.call_budget import create_budget
    from nw.llm.base import GenResult
    from nw.materials.adjudication import build_adjudications
    from nw.materials.phase_flow import STAGE_MATERIALS, _step_source_pool
    from nw.materials.stage_input import LEGACY_STEP_SOURCE_POLICY, STEP_SOURCE_POLICY
    from nw.materials.work_session import drive_plan
    from nw.planning import prepare_plan_task
    from nw.store import Store
    from nw.story_state import adopt_story
    from nw.task_models import Budget
    from story_fixture import baseline
    from test_material_phase_flow import PhaseModel
    from test_novel_flow import config

    from nw.materials import library_adjudication

    _, selection, _, _ = catalog(tmp_path, extra_library=(
        '\n### 1.1_当前方法\n【定义】另一处同名原条讨论事后复盘与动机变化。\n'
        '【指令】先记录事后判断变化，再对照实际事件。\n'
        '\n### 1.2_未入步方法\n【定义】依据真实人物目标设计动作后果并描写已发生事件。\n'
        '【指令】呈现当前调查目的和人物承担的实际代价。\n'))
    source_pin = next(row for row in selection['sources'] if row['family'] == 'library')
    monkeypatch.setitem(library_adjudication._PINNED, 'library', source_pin['file_sha256'])
    build_adjudications(tmp_path)
    desk = SourceDesk(tmp_path)
    namesakes = [row for row in desk.rows if row['key'] == '1.1_当前方法']
    spans = desk.source_lines(row['id'] for row in namesakes)
    source, other = sorted(namesakes, key=lambda row: spans[row['id']][0])
    outside = next(row for row in desk.rows if row['key'] == '1.2_未入步方法')
    assert source['id'] not in desk.binding_reviews
    assert source['state'] == outside['state'] == 'design_ready'
    authored = '先核对人物目标与已经批准的调查身份，再限定本步行动选择。'
    material = f'【人物设计的资料】\n人物取材。\n\n### 1.1_当前方法\n【原文位置】第1行\n【本步用法】\n{authored}\n'
    monkeypatch.setitem(STAGE_MATERIALS, 'character_design', material)
    other_use = '按同名原条自己的内容回顾已经发生的判断变化。'
    both = (material + f'\n### 1.1_当前方法\n【原文位置】第{spans[other["id"]][0]}行\n'
            f'【本步用法】\n{other_use}\n')
    def pool(text: str, policy: str) -> dict:
        return _step_source_pool(desk, 'character_design', {'stage_materials': {'character_design': text},
                                                           'stage_source_policy': policy})
    assert pool(both, STEP_SOURCE_POLICY) == {source['id']: authored, other['id']: other_use}
    assert pool(material.replace('第1行','第99999行'), STEP_SOURCE_POLICY) == {}
    assert pool(material, LEGACY_STEP_SOURCE_POLICY) == {row['id']: authored for row in namesakes}

    class StepReader(PhaseModel):
        def __init__(self):
            super().__init__()
            self.read_step_use = False

        def generate(self, messages, **params):
            body = json.loads(messages[-1]['content'])
            if body.get('stage') == 'character_design':
                assert body['stage_source_policy'] == STEP_SOURCE_POLICY
                [selected] = body['sources']
                assert selected['source']['id'] == source['id']
                assert selected['step_use'] == authored
                assert 'original_text' not in selected
                assert '读取全文后才能使用' not in messages[0]['content']
                if not self.read_step_use:
                    self.read_step_use = True
                    requests = [{'action': 'search', 'query': '当前方法'},
                                {'action': 'search', 'query': '未入步方法'}, {'action': 'read', 'id': source['id']}]
                    return GenResult(json.dumps({'stage': 'character_design', 'requests': requests}),
                                     'complete', {}, 'test', {})
                page, outside_page, read = body['responses']
                assert [item['id'] for item in page['items']] == [source['id']]
                assert all(item['id'] == source['id'] for item in outside_page['items'])
                assert read['step_material_delivered'] and 'complete_original_delivered' not in read
            return super().generate(messages, **params)

    with Store(tmp_path / 'project', create=True, test_mode=True) as store:
        store.init_project('六文件正常入口')
        store.add_brief('当前方法依据人物目标设计动作后果')
        adopt_story(store, baseline(), {})
        provider = StepReader()
        budget = create_budget(store, 'selected-source-set', Budget(32, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'six-source-plan')
        assert not package.get('materials')
        assert package['stage_source_policy'] == STEP_SOURCE_POLICY
        from nw.materials.scene_source_bindings import POLICY
        assert package['scene_source_binding_policy'] == POLICY
        _, frozen = drive_plan(store, request, package, provider, config(store))
        session = frozen['material_work']
        assert session['context']['scene_source_binding_policy'] == POLICY
        step = next(row for row in session['stages'] if row['stage'] == 'character_design')
        assert any(use['source_id'] == source['id'] for use in step['products']['_uses'])
        assert any(row['source']['id'] == source['id'] and '人物目标' in row['original_text']
                   for row in session['sources'])
        assert all(row['source']['id'] not in {outside['id'], other['id']} for row in session['sources'])
        from nw.materials.binding_reviews import verify_session_bindings
        verify_session_bindings(session, tmp_path, test_mode=True)


@pytest.mark.parametrize('defect',['missing','modified','wrong_source_hash','missing_family','invalid_source_shape'])
def test_selection_cannot_fall_back_to_all_versions_on_missing_or_invalid_configuration(tmp_path,defect):
    config,data,old_id,units=catalog(tmp_path)
    if defect=='missing':
        config.rename(config.with_suffix('.missing-fixture'))
    else:
        if defect=='modified':data['version_name']='[FAKE] 被修改的版本'
        elif defect=='wrong_source_hash':data['sources'][0]['file_sha256']='f'*64
        elif defect=='invalid_source_shape':data['sources'][0]['id']=[]
        else:data['sources'].pop()
        if defect!='modified':
            data['sha256']=content_sha256({k:v for k,v in data.items() if k!='sha256'})
            with sqlite3.connect(tmp_path/'materials/catalog.db') as db:
                db.execute('UPDATE source_set_selection SET sha256=?',(data['sha256'],))
        config.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    with pytest.raises(ValueError,match='MATERIAL_SOURCE_SET'):
        list_catalog(tmp_path,None,None)
