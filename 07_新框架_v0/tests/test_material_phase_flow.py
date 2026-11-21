import json
import re
import pytest

from nw.call_budget import create_budget
from nw.llm.base import GenResult
from nw.materials.catalog import build_catalog
from nw.materials.unit_catalog import index_units
from nw.materials.adjudication import build_adjudications
from nw.materials.phase_routes import phase_order
from nw.materials.work_session import drive_plan
from nw.planning import prepare_plan_task,propose_plan
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from hashlib import sha256
from story_fixture import baseline
from test_novel_flow import config,Model
from fake_phase_work import add_scene_progress, project_products


def template_catalog(tmp_path):
    raw={'rule_id':'TDR_TEMPLATE_003','rule_scope':'实体状态变化模板','status':'template',
         'preconditions':['实体存在','状态变化有事件依据'],
         'trigger_entities':['人物'],'trigger_event_types':['受伤'],
         'candidate_effects':[{'effect_id':'E','description':'实体状态候选变化'}],
         'selection_constraints':['必须经过外部行动选择','需要连续性验证'],
         'not_guaranteed':['状态变化需要事件证据']}
    data=('SOURCE: 类型动态规则总表.json\n=====\n'+json.dumps([raw],ensure_ascii=False)).encode()
    (tmp_path/'source.txt').write_bytes(data)
    manifest=tmp_path/'sources.json';manifest.write_text(json.dumps({'schema_version':1,'catalog_inputs':[
        {'path':'source.txt','family':'types','layer':'baseline','sha256':sha256(data).hexdigest(),'bytes':len(data)}]}),encoding='utf-8')
    build_catalog(tmp_path,tmp_path,manifest);index_units(tmp_path,None);build_adjudications(tmp_path)
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)


class PhaseModel(Model):
    def generate(self,messages,**params):
        if not any(marker in messages[0]['content'] for marker in ('[MATERIAL_ASSEMBLY]','[MATERIAL_STEP]')):
            return super().generate(messages,**params)
        payload=json.loads(messages[-1]['content']);self.calls.append(messages)
        if '[MATERIAL_ASSEMBLY]' in messages[0]['content']:
            return GenResult(json.dumps(payload['output_contract'],ensure_ascii=False),'complete',{},'test',{})
        assert '[MATERIAL_STEP]' in messages[0]['content']
        stage=payload['stage'];sources=payload['sources']
        from test_planning import Planner
        fixture_scope='book' if stage=='plot_design' and payload['scope']=='book' else 'chapter'
        products=project_products(stage,Planner(fixture_scope).output['candidate_cards'],
                                  payload['inputs'],sources,payload['scope'],native=True,
                                  narration=payload.get('narration_policy', False), narration_bases=payload.get('narration_bases'),
                                  cast_needs=payload.get('cast_needs'), phase_payload=payload)
        add_scene_progress(payload, products)
        if stage=='state_transition':
            assert (payload['inputs']['character_design']['products']['members']
                    or payload['inputs']['character_design']['products']['cast_assignments'])
            assert payload['inputs']['scene_design']['products']['events']
        from nw.materials.phase_contract import output_refs
        refs=sorted(output_refs(stage,products))
        products['_uses']=[{'source_id':s['source']['id'],'operation':'[FAKE] 依本步骤资料完成实际项目产物并交给下游',
                           'output_refs':refs[:1]} for s in sources]
        from fake_semantic_clauses import criteria_for
        products['_criteria']=criteria_for(payload,products)
        return GenResult(json.dumps({'stage':stage,'products':products},ensure_ascii=False),'complete',{},'test',{'isolated_test':True})


def test_normal_driver_places_template_after_inputs_and_never_runs_global_reading(tmp_path):
    template_catalog(tmp_path)
    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('按步骤调用');store.add_brief('调查封条时的动作与状态变化');adopt_story(store,baseline(),{})
        provider=PhaseModel();budget=create_budget(store,'steps',Budget(32,90000,4000))
        request,package=prepare_plan_task(store,1,'book',provider,config(store),budget,'phase-test')
        # Use a detail work package here to exercise the full product graph.
        unselected = '不适用的材料' * 20000
        state_material = ('### TDR_TEMPLATE_003\n【本步用法】\n核对当前变化事件与实际代价。\n\n'
                          '### TDR_TEMPLATE_003_别条\n【本步用法】\n' + unselected)
        package={**package,'scope':'chapter','stage_materials':{**package['stage_materials'],
                                                               'state_transition':state_material}}
        driven,frozen=drive_plan(store,request,package,provider,config(store))
        session=frozen['material_work']
        assert [r['stage'] for r in session['stages']]==phase_order('chapter')
        delivered=[(json.loads(m[-1]['content'])['stage'],s['source']['key'])
                   for m in provider.calls for s in json.loads(m[-1]['content']).get('sources',[])]
        assert delivered==[('state_transition','TDR_TEMPLATE_003')]
        state_prompt=next(m[0]['content'] for m in provider.calls
                          if json.loads(m[-1]['content']).get('stage')=='state_transition')
        [binding] = [body for m in provider.calls if (body := json.loads(m[-1]['content'])).get('stage') == 'bind_scope']
        [source] = session['sources']
        assert binding['required_scene_sources'] == {source['source']['id']: ['scene']}
        assert '核对当前变化事件与实际代价。' in state_prompt
        assert '不适用的材料' not in state_prompt
        assert not any('[MATERIAL_WORK]' in m[0]['content'] for m in provider.calls)
        assert all('directory' not in json.loads(m[-1]['content']) for m in provider.calls)
        assert max(sum(len(v['content']) for v in m) for m in provider.calls)<20000
        assert json.loads(driven.payload['messages'][-1]['content'])['output_contract']
        calls=len(provider.calls)
        again,_=drive_plan(store,request,package,provider,config(store))
        assert again==driven and len(provider.calls)==calls


@pytest.mark.parametrize(('key_state', 'expected_action'), [
    ('钥匙在手', '[FAKE] 持已有钥匙开档柜，再借灯核对封条'),
    ('钥匙已归还', '[FAKE] 先请值守人批准借用钥匙，再借灯核对封条'),
])
def test_action_step_accepts_branch_state_and_keeps_event_needs_in_search(tmp_path, key_state: str,
                                                                     expected_action: str) -> None:
    from dataclasses import asdict
    from nw.cards import decide_card, save_card
    from nw.materials.phase_context import ACTION_STATE_POLICY, visible_facts
    from nw.materials.semantic_application import input_value
    from nw.novel_flow import JobRequest, resume_job, start_job
    from nw.tasks import read_input_manifest
    from test_material_workflow import choose

    class StateModel(PhaseModel):
        def generate(self, messages: list[dict], **params) -> GenResult:
            result = super().generate(messages, **params)
            body = json.loads(messages[-1]['content'])
            if body.get('stage') != 'action_design':
                return result
            assert body['action_state_policy'] == ACTION_STATE_POLICY
            [world_fact] = body['accepted_state']
            assert world_fact['holder'] == 'WORLD' and world_fact['evidence']
            action = ('[FAKE] 持已有钥匙开档柜，再借灯核对封条' if world_fact['value'] == '钥匙在手'
                      else '[FAKE] 先请值守人批准借用钥匙，再借灯核对封条')
            raw = json.loads(result.text)
            raw['products']['candidates'][0]['action'] = action
            result.text = json.dumps(raw, ensure_ascii=False)
            return result

    template_catalog(tmp_path)
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('前次事实影响动作')
        store.add_brief('基调安排与城市氛围。' * 280, '遵守实际调查时间顺序')
        ref = save_card(store, {'card_id': 'key', 'kind': 'world', 'origin': 'author',
                                'body': {'title': '档柜钥匙', 'rule': '使用前核对钥匙可用状态',
                                         'limits': '需保管人批准', 'visibility': 'public'}}, None)
        approval = decide_card(store, ref, 'approved', '批准资源设定')
        fact = {'entity_id': ref.card_id, 'predicate': '钥匙去向', 'value': key_state, 'holder': 'WORLD',
                'claim': 'fact', 'story_order': 0, 'disclosure_order': [0, 0, 0]}
        adopt_story(store, baseline(card_refs=[{**asdict(ref), 'decision_id': approval.id}],
            facts=[fact, {**fact, 'holder': 'yan', 'claim': 'belief', 'value': '猜测钥匙已丢'},
                   {**fact, 'entity_id': 'unrelated', 'value': '未授权对象状态'}]), {})
        provider = StateModel()
        job = start_job(store, JobRequest('design', budget=Budget(32, 90000, 4000))).id
        assert resume_job(store, job, provider, config(store)).step == 'plan:book:confirm'
        preview = resume_job(store, job, provider, config(store), choose)
        assert preview.step == 'plan:chapter:confirm', preview.reason
        action_input = next(json.loads(messages[-1]['content']) for messages in provider.calls
                            if json.loads(messages[-1]['content']).get('stage') == 'action_design')
        assert action_input['accepted_state'][0]['value'] == key_state
        query = action_input['retrieval_need']
        assert len(query) <= 2200 and all(text in query for text in
            (key_state, '查明封条是否被替换', '铜丝藏在纸角下', '遵守实际调查时间顺序'))
        assert '猜测钥匙已丢' not in query and '未授权对象状态' not in query
        result = resume_job(store, job, provider, config(store), choose)
        assert result.status == 'DONE', result.reason

        call = store.connection.execute('SELECT manifest_id FROM task_calls WHERE id=?',
                                        (result.outputs['proposal_id'],)).fetchone()
        _, frozen = read_input_manifest(store, call['manifest_id'])
        session = frozen['material_work']
        stages = {row['stage']: row for row in session['stages']}
        assert stages['action_design']['products']['candidates'][0]['action'] == expected_action
        replayed = visible_facts('action_design', stages, session['context'])
        assert replayed == action_input['accepted_state']
        assert input_value('fact:0:/value', 'action_design', stages, {'accepted_state': replayed}) == key_state
        legacy = {k:v for k,v in session['context'].items() if k != 'action_state_policy'}
        assert not visible_facts('action_design', stages, legacy)


def test_only_the_exact_action_template_precedes_sources_for_the_current_event(monkeypatch) -> None:
    from nw.materials.phase_context import ACTION_STATE_POLICY
    from nw.materials.phase_flow import FUNCTION_QUERIES, _sources
    from nw.materials.work_catalog import SourceDesk

    class FixtureDesk(SourceDesk):
        def __init__(self) -> None:
            keys = {'template': 'TDR_TEMPLATE_005', 'loose_match': 'TDR_019', 'resource': '125.13_资源消耗速率'}
            self.rows = [{'id': ident, 'key': key, 'profile': 'world', 'state': 'design_ready',
                          'meaning': '', 'file_sha256': ident, 'sha256': ident} for ident, key in keys.items()]
            self.by_id = {row['id']: row for row in self.rows}

        def read(self, ident: str) -> dict:
            return {'source': self.by_id[ident], 'use_mode': 'project_method'}

    monkeypatch.setitem(FUNCTION_QUERIES, 'action_design', ())
    desk = FixtureDesk()
    pool = {'template': '核对动作能力', 'loose_match': '其他分类', 'resource': '从钥匙消耗确认当前行动的资源限制'}
    package = {'scope': 'chapter', 'brief': {'text': '125.13_资源消耗速率', 'constraints': ''},
               'action_state_policy': ACTION_STATE_POLICY}
    traces = {'queries': []}
    old = _sources(desk, 'action_design', package, {}, step_pool=pool)
    assert [row['source']['id'] for row in old] == ['template', 'loose_match']
    current = _sources(desk, 'action_design', {**package, 'action_template_priority_enabled': True},
                       {}, step_pool=pool, trace=traces)
    assert [row['source']['id'] for row in current] == ['template', 'resource']
    assert any(row['query'] == 'TDR_TEMPLATE_005' and 'loose_match' in {item['id'] for item in row['returned']}
               for row in traces['queries'])


def test_dynamic_filter_uses_actual_type_and_scene_inputs(tmp_path, monkeypatch):
    from nw.materials.phase_projection import verify_chain
    from nw.tasks import read_input_manifest

    template_catalog(tmp_path)
    contract = {
        'filter_id': 'TDF_001', 'source_ref': {'id': 'fixture'},
        'limits': {'max_type_dynamic_rules': 5, 'max_original_dynamic_rules': 5},
        'sources': {'type_dynamic': {'path': 'types.txt', 'file_sha256': 'a' * 64},
                    'original_dynamic': {'path': 'dynamic.txt', 'file_sha256': 'b' * 64}},
    }
    monkeypatch.setattr('nw.materials.dynamic_screening.load_dynamic_screening', lambda _: contract)
    with Store(tmp_path/'story', create=True, test_mode=True) as store:
        store.init_project('动态筛选前置')
        store.add_brief('调查封条')
        adopt_story(store, baseline(), {})
        provider = PhaseModel()
        budget = create_budget(store, 'filter', Budget(32, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'filter-input')
        _, frozen = drive_plan(store, request, {**package, 'scope': 'chapter'}, provider, config(store))
        stage_material = frozen['material_work']
        packets = {raw['study_input']['stage']: raw['study_input'] for receipt in stage_material['calls']
                   for _, raw in [read_input_manifest(store, receipt['manifest_id'])] if 'stage' in raw['study_input']}
        assert 'type_adaptation' in packets['state_propagation']['inputs']
        assert packets['state_propagation']['inputs']['type_selection']['products']['selection']
        assert packets['state_propagation']['inputs']['scene_design']['products']['selected_actions']
        assert packets['state_propagation']['dynamic_filter']['source_ref'] == contract['source_ref']
        assert packets['scene_design']['dynamic_filter']['limits'] == contract['limits']
        assert packets['bind_scope']['dynamic_filter']['limits'] == contract['limits']
        assert 'dynamic_filter' not in packets['action_design']
        scene_prompt = next(call[0]['content'] for call in provider.calls
                            if json.loads(call[-1]['content']).get('stage') == 'scene_design')
        assert '本场采用《类型信息揭示适配》时' in scene_prompt
        assert '38969｜"信息仍然需要传播路径"' in scene_prompt
        assert '38970｜"角色可能误解、怀疑或拒绝相信"' in scene_prompt
        assert '33535｜"信息仍然需要传播路径"' in scene_prompt
        assert '33536｜"角色仍然可能误解、怀疑或拒绝相信"' in scene_prompt
        assert 'ADAPT_B_00064–ADAPT_B_00067 原条均为伏笔偏好' in scene_prompt
        plot_prompt = next(call[0]['content'] for call in provider.calls
                           if json.loads(call[-1]['content']).get('stage') == 'plot_design')
        assert '33532｜"类型不得自动创建伏笔"' in plot_prompt
        assert '33533｜"类型不得自动回收伏笔"' in plot_prompt
        assert '33534｜"伏笔仍然需要建立事件或来源"' in plot_prompt
        action_prompt = next(call[0]['content'] for call in provider.calls
                             if json.loads(call[-1]['content']).get('stage') == 'action_design')
        assert 'TDR_TEMPLATE_005' in action_prompt
        report = stage_material['stages'][-1]['dynamic_screening']
        assert report['filter_id'] == 'TDF_001' and report['scenes']
        verify_chain(stage_material)
        report['scenes'].clear()
        with pytest.raises(ValueError, match='dynamic screening report changed'):
            verify_chain(stage_material)


def test_dynamic_filter_can_retry_the_stage_that_exceeds_the_limit(tmp_path, monkeypatch):
    from nw.materials.work_catalog import SourceDesk

    template_catalog(tmp_path)
    ref = next(row for row in SourceDesk(tmp_path).rows if row['key'] == 'TDR_TEMPLATE_003')
    contract = {'filter_id': 'TDF_001', 'source_ref': {'id': 'fixture'},
                'limits': {'max_type_dynamic_rules': 0, 'max_original_dynamic_rules': 5},
                'sources': {'type_dynamic': {key: ref[key] for key in ('path', 'file_sha256')}}}
    monkeypatch.setattr('nw.materials.dynamic_screening.load_dynamic_screening', lambda _: contract)

    class CandidateModel(PhaseModel):
        retract = False

        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            data = json.loads(messages[-1]['content'])
            if self.retract and data.get('stage') == 'state_transition':
                response = json.loads(result.text)
                value = response['products']
                value['_excluded'] = [
                    {'source_id': row['source']['id'], 'reason': '本场现有证据不足以采用该资料'}
                    for row in data['sources']]
                value['_uses'] = []
                value['_criteria'] = []
                result.text = json.dumps(response, ensure_ascii=False)
            return result

    with Store(tmp_path/'story', create=True, test_mode=True) as store:
        store.init_project('动态规则限额重试')
        store.add_brief('调查封条')
        adopt_story(store, baseline(), {})
        provider = CandidateModel()
        budget = create_budget(store, 'filter-retry', Budget(32, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'filter-retry')
        package = {**package, 'scope': 'chapter'}
        with pytest.raises(ValueError, match='TDF_001 scene candidate limit'):
            drive_plan(store, request, package, provider, config(store))
        assert json.loads(provider.calls[-1][-1]['content'])['stage'] == 'state_transition'
        provider.retract = True
        _, frozen = drive_plan(store, request, package, provider, config(store), retry_failed=True)
        calls = [json.loads(messages[-1]['content']).get('stage') for messages in provider.calls]
        assert calls.count('scene_design') == 1 and calls.count('state_transition') == 2
        assert not frozen['material_work']['stages'][-1]['dynamic_screening']['violations']


def test_normal_plan_propose_assembles_only_real_step_products(tmp_path):
    template_catalog(tmp_path)
    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('方向');store.add_brief('封条调查');adopt_story(store,baseline(),{})
        provider = PhaseModel()
        proposal=propose_plan(store,1,'book',provider,config(store),Budget(32,90000,4000))
        assert len(proposal.candidate_cards)==2
        rows=store.connection.execute("SELECT kind FROM task_calls ORDER BY rowid").fetchall()
        assert [r[0] for r in rows]==['material_work']*8+['plan']
        assert sum('[CASTING_EDITOR]' in messages[0]['content'] for messages in provider.calls) == 1


def test_type_selection_reads_hierarchy_with_its_exact_source(tmp_path):
    from nw.materials.type_hierarchy import TYPE_TABLE
    from nw.materials.work_catalog import SourceDesk
    from nw.tasks import read_input_manifest
    from test_material_catalog import _manifest
    from test_type_adjudication import genre

    parent = genre(level=1, ancestor_ids=[], child_ids=[])
    child = {**genre(), 'type_id': 'SUB_ONE', 'canonical_name': '类型一的细分',
             'type_kind': 'SUBGENRE', 'parent_id': 'GENRE_ONE', 'ancestor_ids': ['GENRE_ONE'], 'level': 2}
    data = ('SOURCE: ' + TYPE_TABLE + '\n=====\n' + json.dumps([parent, child], ensure_ascii=False)).encode('utf-8')
    manifest = _manifest(tmp_path / 'sources', tmp_path, [('types.txt', 'types', data)])
    build_catalog(tmp_path, tmp_path / 'sources', manifest)
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    root = next(row for row in SourceDesk(tmp_path).rows if row['key'] == 'GENRE_ONE')

    class Reader(PhaseModel):
        lookups = 0

        def generate(self, messages, **params):
            payload = json.loads(messages[-1]['content'])
            if payload.get('stage') != 'type_selection':
                assert 'type_hierarchy' not in payload
                return super().generate(messages, **params)
            if self.lookups == 2:
                assert not payload['source_readings'][0]['execution_admitted']
                assert payload['type_hierarchy'] == [{'parent_id': 'GENRE_ONE', 'parent_source_id': root['id'],
                                                      'subtype_ids': ['SUB_ONE'], 'open_source_issues': 0}]
                assert '校对父级' in messages[0]['content']
                return super().generate(messages, **params)
            if self.lookups == 0:
                action = {'action': 'search', 'query': 'GENRE_ONE'}
            else:
                assert root['id'] in payload['readable_source_ids']
                action = {'action': 'read', 'id': root['id']}
            self.lookups += 1
            self.calls.append(messages)
            response = {'stage': 'type_selection', 'requests': [action]}
            return GenResult(json.dumps(response), 'complete', {}, 'test', {})

    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('类型层级')
        store.add_brief('封条调查')
        adopt_story(store, baseline(), {})
        provider = Reader()
        budget = create_budget(store, 'hierarchy', Budget(20, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'hierarchy-test')
        driven, frozen = drive_plan(store, request, package, provider, config(store))
        receipts = frozen['material_work']['calls']
        assert any('type_hierarchy' in read_input_manifest(store, item['manifest_id'])[1]['study_input']
                   for item in receipts)
        used_calls = len(provider.calls)
        assert drive_plan(store, request, package, provider, config(store))[0] == driven
        assert len(provider.calls) == used_calls


def test_step_search_filters_functions_before_pagination():
    from nw.materials.work_catalog import SourceDesk
    from nw.materials.phase_flow import _stage_search
    desk=object.__new__(SourceDesk)
    desk.rows=[{'id':str(i),'key':'动作'+str(i),'profile':'world','state':'design_ready',
                'meaning':'动作','function_text':'','file_sha256':'a'*64,'sha256':'b'*64} for i in range(50)]
    desk.rows.append({**desk.rows[0],'id':'expression','profile':'expression'})
    assert [r['id'] for r in _stage_search(desk,'expression_design','动作')['items']]==['expression']


def test_method_selection_searches_stage_function_even_without_shared_story_words(tmp_path,monkeypatch):
    from test_material_stage_integration import pins_for
    from nw.materials.work_catalog import SourceDesk
    from nw.materials.phase_flow import _sources
    pins_for(tmp_path,monkeypatch,'### 64.1_读者情绪\n【定义】读者情绪由信息顺序和人物遭遇共同形成。\n',['64.1_读者情绪'])
    selected=_sources(SourceDesk(tmp_path),'plot_design',{'brief':{'text':'沈砚调查药铺封条','constraints':''}}, {})
    assert any(r['source']['key']=='64.1_读者情绪' for r in selected)


def test_navigation_matches_do_not_hide_a_later_actual_method():
    from nw.materials.work_catalog import SourceDesk
    from nw.materials.phase_flow import _sources
    desk=object.__new__(SourceDesk)
    desk.rows=[{'id':str(i),'key':'世界设定规则限制导航'+str(i),'profile':'world','state':'reference','meaning':'',
                'function_text':'','file_sha256':'a'*64,'sha256':'b'*64} for i in range(45)]
    desk.rows.append({**desk.rows[0],'id':'actual','key':'资源库一致性','meaning':'世界规则限制'})
    desk.read=lambda ident:{'source':{'id':ident,'key':ident,'profile':'world'},
                            'use_mode':'project_method' if ident=='actual' else 'navigation_only'}
    result=_sources(desk,'world_design',{'brief':{'text':'调查封条','constraints':''}}, {})
    assert [r['source']['id'] for r in result]==['actual']


def test_retrieval_uses_actual_upstream_voice_instead_of_only_the_brief():
    from nw.materials.work_catalog import SourceDesk
    from nw.materials.phase_flow import _sources
    from test_material_phase_contract import record
    desk=object.__new__(SourceDesk)
    desk.rows=[{'id':'short','key':'短句','profile':'expression','state':'reference','meaning':'','function_text':'',
                'file_sha256':'a'*64,'sha256':'b'*64}]
    desk.read=lambda ident:{'source':{'id':ident,'key':'短句','profile':'expression'},'use_mode':'project_method'}
    products={'character_design':record('character_design',{'members':[{'key':'yan','kind':'character',
        'body':{'name':'沈砚','role':'主角','want':'调查','voice':'说话只用短句','visibility':'public'}}],'states':[],'_uses':[]})}
    result=_sources(desk,'expression_design',{'brief':{'text':'调查封条','constraints':''}},products)
    assert result and result[0]['source']['id']=='short'


def test_expression_receives_actual_character_plot_and_world_products(tmp_path):
    template_catalog(tmp_path)
    with Store(tmp_path/'expression',create=True,test_mode=True) as store:
        store.init_project('表达前置');store.add_brief('调查封条');adopt_story(store,baseline(),{})
        provider=PhaseModel();budget=create_budget(store,'expression',Budget(32,90000,4000))
        request,package=prepare_plan_task(store,1,'book',provider,config(store),budget,'expression-test')
        drive_plan(store,request,{**package,'scope':'chapter'},provider,config(store))
        data=next(json.loads(m[-1]['content']) for m in provider.calls if json.loads(m[-1]['content']).get('stage')=='expression_design')
        assert {'world_design','character_design','plot_design'}<=data['inputs'].keys()


def test_plain_plan_retry_resumes_failed_step_without_repeating_paid_upstream_calls(tmp_path):
    from nw.planning import retry_plan
    class Flaky(PhaseModel):
        failed=False
        def generate(self,messages,**params):
            data=json.loads(messages[-1]['content'])
            if data.get('stage')=='world_design' and not self.failed:
                self.failed=True;self.calls.append(messages)
                return GenResult('not JSON','complete',{},'test',{})
            return super().generate(messages,**params)
    template_catalog(tmp_path);path=tmp_path/'retry';provider=Flaky()
    with Store(path,create=True,test_mode=True) as store:
        store.init_project('断点');store.add_brief('调查封条');adopt_story(store,baseline(),{})
        with pytest.raises(ValueError) as error:
            propose_plan(store,1,'book',provider,config(store),Budget(32,90000,4000))
        checkpoint=re.search(r'plan_checkpoint=([a-f0-9]+)',str(error.value))
        assert checkpoint,'plain plan must expose a durable retry ID even before the assembly task exists'
        ident=checkpoint[1]
        from types import SimpleNamespace
        from nw.novel_cli import _plan
        assert len(_plan(store,SimpleNamespace(action='show',id=ident))['stage_calls'])==3
    with Store(path,test_mode=True) as store:
        proposal=retry_plan(store,ident,provider,config(store))
        assert proposal.candidate_cards
        assert sum(json.loads(m[-1]['content']).get('stage')=='type_selection' for m in provider.calls)==1
        attempts=store.connection.execute("SELECT attempt FROM task_calls WHERE kind='material_work' ORDER BY rowid").fetchall()
        assert [r[0] for r in attempts]==[1,1,1,2,1,1,1,1,1]


def test_current_step_can_request_full_original_without_loading_other_steps(tmp_path):
    class Reader(PhaseModel):
        read=False
        def generate(self,messages,**params):
            data=json.loads(messages[-1]['content'])
            if data.get('stage')=='state_transition':
                if not self.read:
                    self.read=True;self.calls.append(messages)
                    ident=data['sources'][0]['source']['id']
                    return GenResult(json.dumps({'stage':'state_transition','requests':[{'action':'read','id':ident}]}),
                                     'complete',{},'test',{})
                assert 'projection' not in data['sources'][0]
                assert data['responses'][0]['complete_original_delivered']
            return super().generate(messages,**params)
    template_catalog(tmp_path)
    with Store(tmp_path/'read',create=True,test_mode=True) as store:
        store.init_project('分步补调');store.add_brief('封条调查');adopt_story(store,baseline(),{})
        provider=Reader();budget=create_budget(store,'read',Budget(32,90000,4000))
        request,package=prepare_plan_task(store,1,'book',provider,config(store),budget,'read-test')
        _,frozen=drive_plan(store,request,{**package,'scope':'chapter'},provider,config(store))
        assert len(frozen['material_work']['calls'])==16
        assert sum(json.loads(m[-1]['content']).get('stage')=='state_transition' for m in provider.calls)==2


def test_stage_reads_exact_unreviewed_original_and_can_continue_its_own_lookup(tmp_path):
    from nw.materials.work_catalog import SourceDesk
    from test_material_catalog import _manifest

    originals = {
        'plot': '### 122.1_调查线索的推进\n【指令】以当前事件的封条检查决定下一步调查目标。\n',
        'another': '### 122.2_次线的推进\n【指令】在已出现的事件结果中安排下一条线索。\n',
        'world': '### 33.1_封条保管规则\n【指令】查验人只接触交到自己手里的封条。\n',
    }
    manifest = _manifest(tmp_path / 'sources', tmp_path, [
        (f'{name}.txt', 'library', text.encode('utf-8')) for name, text in originals.items()
    ])
    build_catalog(tmp_path, tmp_path / 'sources', manifest)
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    desk = SourceDesk(tmp_path)
    plot = next(row for row in desk.rows if row['key'] == '122.1_调查线索的推进')

    class Reader(PhaseModel):
        reads = 0

        def generate(self, messages, **params):
            body = json.loads(messages[-1]['content'])
            assert not body.get('source_readings') or body['stage'] == 'plot_design'
            if body.get('stage') != 'plot_design':
                return super().generate(messages, **params)
            if self.reads == 0:
                actions = [{'action': 'search', 'query': '122.1_调查线索的推进'}]
            elif self.reads == 1:
                assert any(item['id'] == plot['id'] for item in body['responses'][0]['items'])
                actions = [{'action': 'read', 'id': plot['id']}]
            elif self.reads == 2:
                [reading] = body.get('source_readings', [])
                assert reading['source']['original_text'] == originals['plot'].strip()
                assert reading['source']['source']['sha256'] == plot['sha256']
                assert reading['status'] == 'needs_review'
                assert reading['execution_admitted'] is False
                assert plot['id'] not in {item['source']['id'] for item in body['sources']}
                actions = [{'action': 'search', 'query': '122.2_次线的推进'}]
            else:
                assert body['responses'][0]['items']
                return super().generate(messages, **params)
            self.reads += 1
            self.calls.append(messages)
            return GenResult(json.dumps({'stage': 'plot_design', 'requests': actions}, ensure_ascii=False),
                             'complete', {}, 'test', {})

    with Store(tmp_path / 'read-unreviewed', create=True, test_mode=True) as store:
        store.init_project('原文补读')
        store.add_brief('调查封条')
        adopt_story(store, baseline(), {})
        provider = Reader()
        budget = create_budget(store, 'unreviewed-read', Budget(32, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'source-read')
        _, frozen = drive_plan(store, request, package, provider, config(store))
        session = frozen['material_work']
        record = next(row for row in session['stages'] if row['stage'] == 'plot_design')
        [reading] = record['source_selection']['read']
        assert reading['source']['id'] == plot['id']
        assert reading['status'] == 'needs_review'
        assert record['products']['_uses'] == []
        assert record['source_ids'] == []
        from nw.tasks import read_input_manifest
        manifests = [read_input_manifest(store, item['manifest_id'])[1] for item in session['calls']]
        assert any(any(s['source']['id'] == plot['id'] for s in call['frozen_sources']) for call in manifests)


@pytest.mark.parametrize(('omit_change','multi','pressure_confirmed'),
                         [(False,False,True),(True,False,True),(False,True,True),(False,False,False)])
def test_template_change_traverses_normal_design_write_review_and_acceptance(tmp_path,omit_change,multi,pressure_confirmed):
    from nw.novel_flow import start_job,resume_job,JobRequest
    from test_material_workflow import choose
    from test_novel_flow import author
    from nw.story_state import current_head,revision_state,replay,baseline_for,selected_operations
    from nw.materials.scene_actions import MULTI_ACTION_POLICY, action_choice

    first = '[FAKE] 举灯辨认封条铜丝'
    second = '[FAKE] 用木片托起纸角查看旧印'
    first_sentence = '[FAKE] 沈砚举灯辨认封条下的铜丝，手背碰到铜丝被划伤。'
    second_sentence = '他收回手，压低木片托住纸角，看清了旧印。'
    next_duty = '[FAKE] 将前日印痕的拓片和印坊日簿对照'
    next_result = '[FAKE] 找到换印当日值班人的签名'
    outstanding = '换印是哪一天，他还得查日簿。' if pressure_confirmed else ''
    class StateModel(PhaseModel):
        reviews = 0

        def generate(self,messages,**params):
            prompt=messages[0]['content'];payload=json.loads(messages[-1]['content'])
            if '只输出正文' in prompt or multi and '修订本场' in prompt:
                self.calls.append(messages)
                if multi:
                    return GenResult(first_sentence + second_sentence + outstanding + ('他记下印痕。' if self.reviews else ''),
                                     'complete',{},'test',{})
                return GenResult('[FAKE] 沈砚用手试探封条下的铜丝，手背被划伤。他收回手，改用木片托住封条，看清了旧印。' + outstanding,
                                 'complete',{},'test',{})
            if '{"operations"' in prompt:
                self.calls.append(messages)
                facts={(f['entity_id'],f['predicate'],f['holder']):f['value'] for f in payload['context'].get('facts',[]) if f['claim']=='fact'}
                operations=[]
                for h in ([] if omit_change else payload['context'].get('material_hypotheses',[])):
                    for t in h['transitions']:
                        key=t['entity_id'],t['predicate'],t['holder']
                        operations.append({**t,'expected_old':t.get('expected_old',facts.get(key)),'op':'set','claim':'fact',
                            'story_order':payload['story_order'],'disclosure_order':payload['disclosure_order'],
                            'evidence':[payload['evidence_format']]})
                        facts[key]=t['new_value']
                return GenResult(json.dumps({'operations':operations},ensure_ascii=False),'complete',{},'test',{})
            result = super().generate(messages,**params)
            if 'material_review' in payload and pressure_confirmed:
                raw = json.loads(result.text)
                [check] = [r for r in payload['material_review']['checks'] if r.get('pressure_review')]
                reviewed = next(r for r in raw['material_checks'] if r['id'] == check['id'])
                reviewed['reason'] += '\n【未决原文】' + outstanding
                result.text = json.dumps(raw, ensure_ascii=False)
            if payload.get('stage') == 'world_design' and payload.get('reviewed_cast_work'):
                raw = json.loads(result.text)
                duty = raw['products']['cast_demands'][0]
                ref, quote = next((k, v) for k, v in payload['cast_plot_sources'].items()
                                  if v == '换印的日期仍待调查')
                duty.update(action=next_duty, result=next_result, need_ref=ref, need_quote=quote)
                result.text = json.dumps(raw, ensure_ascii=False)
            if payload.get('stage') == 'action_design' and any(
                    row['action'] == next_duty for row in payload.get('cast_work', [])):
                raw = json.loads(result.text)
                raw['products']['candidates'][0]['steps'][0].update(action=next_duty, result=next_result)
                result.text = json.dumps(raw, ensure_ascii=False)
            if payload.get('stage') == 'scene_design' and payload.get('chapter_progress_policy'):
                raw = json.loads(result.text)
                raw['products']['scene_progress'][0]['next_pressure'] = '换印的日期仍待调查'
                if payload.get('chapter_changes'):
                    for chapter in raw['products']['chapters']:
                        chapter['index'] = 2
                        for entry in chapter['scenes']:
                            entry['story_order'] += 1
                    raw['products']['events'][0]['before_state'] = {'hand': '划伤'}
                result.text = json.dumps(raw, ensure_ascii=False)
            if payload.get('stage') == 'state_transition' and any(
                    row['before_state'] == {'hand': '划伤'} for row in payload['inputs']['scene_design']['products']['events']):
                raw = json.loads(result.text)
                raw['products']['transitions'][0].update(action='对照日簿时给手背重新包扎', after_state={'hand': '已包扎'})
                result.text = json.dumps(raw, ensure_ascii=False)
            if not multi:
                return result
            stage = payload.get('stage')
            if stage in ('action_design', 'scene_design', 'anchor_design', 'state_transition'):
                from copy import deepcopy
                raw = json.loads(result.text)
                products = raw['products']
                if stage == 'action_design':
                    assert payload['multi_action_policy'] == MULTI_ACTION_POLICY
                    [base] = products['candidates']
                    base['action'] = first
                    extra = deepcopy(base)
                    extra.update(id='archive', action=second)
                    products['candidates'].append(extra)
                    products['candidates'].append(dict(extra, id='alternative', action='[FAKE] 改从侧门调查'))
                elif stage == 'scene_design':
                    assert '一条或多条' in payload['output_schema']
                    selected = products['selected_actions']
                    selected.append(dict(selected[0], action='archive'))
                    candidates = payload['inputs']['action_design']['products']['candidates']
                    products['members'][0]['body']['choice'] = action_choice(candidates[:2])
                elif stage == 'anchor_design':
                    [beat] = products['beats']
                    selected = payload['inputs']['scene_design']['products']['selected_actions']
                    products['beats'] = [dict(beat, action_ref=entry['action']) for entry in selected]
                else:
                    products['patches'][0]['choice'] = second
                result.text = json.dumps(raw, ensure_ascii=False)
            if 'material_review' in payload:
                raw = json.loads(result.text)
                draft = payload['draft']['text']
                contract = payload['material_review']
                actions = [row for row in contract['checks'] if 'action_order' in row]
                assert [row['action_order'] for row in actions] == [1, 2]
                assert [row['method_artifact']['action'] for row in actions] == [first, second]
                assert not any(row['id'].endswith(':alternative') for row in contract['checks'])
                if self.reviews:
                    checks = {row['id']: row for row in raw['material_checks']}
                    split = len(first_sentence)
                    for check, start, end in zip(actions, [0, split], [split, len(draft)], strict=True):
                        checks[check['id']]['evidence'] = [{**contract['draft'], 'start': start, 'end': end,
                                                           'quote': draft[start:end]}]
                self.reviews += 1
                result.text = json.dumps(raw, ensure_ascii=False)
            return result
    template_catalog(tmp_path);provider=StateModel()
    with Store(tmp_path/'normal',create=True,test_mode=True) as store:
        store.init_project('模板正常路径');store.add_brief('调查封条与触碰铜丝后的变化');adopt_story(store,baseline(),{})
        job=start_job(store,JobRequest('design',budget=Budget(32,90000,4000))).id
        assert resume_job(store,job,provider,config(store)).step=='plan:book:confirm'
        detail=resume_job(store,job,provider,config(store),choose)
        assert detail.step=='plan:chapter:confirm',detail.reason
        design=resume_job(store,job,provider,config(store),choose);assert design.status=='DONE',design.reason
        scene=design.outputs['application']['chapters'][0]['scenes'][0]['scene_id']
        if multi:
            from nw.context.story import build_story_context, scene_scope
            with Store(store.directory,test_mode=True) as reopened:
                package = build_story_context(reopened, scene, scene_scope(reopened, scene), 90000).package
            actions = [json.loads(row['text']) for row in package['items']
                       if row['source'].startswith('material:work:selected:action:')]
            assert [json.loads(row['observable'])['action'] for row in actions] == [first, second]
            [scene_body] = [json.loads(row['text']) for row in package['items'] if row['source'].startswith('scene:')]
            assert scene_body['choice'] == first + '；' + second
        write=start_job(store,JobRequest('write',scene_ids=[scene],budget=Budget(12,90000,4000,int(multi)))).id
        result=resume_job(store,write,provider,config(store),author())
        if omit_change:
            assert result.status=='BLOCKED' and 'MATERIAL_STATE_EVIDENCE' in result.reason
            assert not store.list('accepted')
        else:
            assert result.status=='DONE',result.reason
            head=current_head(store);facts=replay(baseline_for(store,'main'),selected_operations(store,revision_state(store,head)))
            assert any(f.predicate=='hand' and f.value=='划伤' for f in facts)
            from nw.chapter_state import continuation_chapter_state
            with Store(store.directory, test_mode=True) as reopened:
                handoff = continuation_chapter_state(reopened, head, revision_state(reopened, head))
                [advance] = handoff['reviewed_progress']
                performances = handoff['reviewed_cast_work']
                assert performances and all(r['scene_id'] == scene and r['actor'] and
                    r['draft_ref'] == advance['draft_ref'] and r['evidence'] for r in performances)
                assert advance['change'] == 'knowledge' and advance['scene_id'] == scene
                assert advance['evidence']
                if not pressure_confirmed:
                    assert advance['possible_next_pressure'] is None and not advance['pressure_evidence']
                    return
                assert advance['possible_next_pressure'] == '换印的日期仍待调查'
                assert [p['quote'] for p in advance['pressure_evidence']] == [outstanding]
                if not multi:
                    from nw.materials.phase_projection import method_checks
                    from nw.context.story import build_story_context, scene_scope
                    from nw.planning import plan_input
                    from nw.story_state import fork_story
                    from test_planning import apply
                    parent = reopened.connection.execute('SELECT proposal_id FROM plan_applications WHERE proposal_id != ?',
                                                         (design.outputs['proposal_id'],)).fetchone()[0]
                    branch = fork_story(reopened, head, 'next-chapter').branch_id
                    proposal = propose_plan(reopened, 1, 'chapter', provider, config(reopened),
                                            Budget(32, 90000, 4000), parent_id=parent, branch=branch)
                    _, following = plan_input(reopened, proposal.id)
                    session = following['material_work']
                    for stage in ('world_design', 'character_design'):
                        packet = next(p for call in reversed(provider.calls)
                                      if (p := json.loads(call[-1]['content'])).get('stage') == stage)
                        assert packet['reviewed_cast_work'] == performances
                    steps = {s['stage']: s['products'] for s in session['stages']}
                    [reassigned] = steps['world_design']['cast_demands']
                    assert reassigned['reuse_actor'] == performances[0]['actor']
                    assert reassigned['action'] == next_duty != performances[0]['designed_action']
                    assert not steps['character_design']['members']
                    assert steps['action_design']['candidates'][0]['steps'][0]['result'] == next_result
                    assert steps['scene_design']['chapters'][0]['index'] == 2
                    [continuation] = steps['plot_design']['continuations']
                    progress = next(r for r in method_checks(session, 'scene') if r['id'].startswith('work:progress:'))
                    assert progress['continuations'][0]['ref'] == continuation['ref']
                    assert progress['continuations'][0]['prior']['draft_ref'] == advance['draft_ref']
                    assert progress['chapter_task'] == {'goal': '入井', 'consequence': '受阻'}
                    apply(reopened, proposal)
                    next_scene = next(s.id for s in reopened.list('scene') if s.id != scene)
                    package = build_story_context(reopened, next_scene, scene_scope(reopened, next_scene, branch), 90000).package
                    items = [r['text'] for r in package['items'] if r['source'].startswith('material:work:')]
                    assert any(next_duty in text and next_result in text for text in items)
            if multi:
                assert provider.reviews == 2
                [accepted] = store.list('accepted')
                assert store.get('draft', accepted.draft_id).text.endswith('他记下印痕。')


def test_type_source_mapping_follows_an_adopted_definition_to_adaptation(tmp_path, monkeypatch):
    from fake_binding_reviews import install_review_fixtures
    from nw.materials import phase_flow
    from nw.materials.type_hierarchy import TYPE_TABLE
    from nw.materials.work_catalog import SourceDesk
    from test_material_catalog import _manifest
    from test_type_adjudication import genre

    a = genre(level=1, ancestor_ids=[], child_ids=[], schema_version='TYPE_A-1.0.0')
    b = {**a, 'canonical_name': '同号总表类型', 'schema_version': 'TYPE_H1A-1.0.0'}
    mapping = {'mapping_id': 'MAP_0001', 'source_name': a['canonical_name'],
               'source_type': 'genre_standard', 'target_id': a['type_id'], 'mapping_type': 'normalized',
               'evidence_type': 'template', 'source_refs': ['web_novel_taxonomy_standard'], 'status': 'active'}
    blocks = {TYPE_TABLE: [b], '主类型.json': [a], '类型来源映射.json': {'mappings': [mapping]}}
    data = '\n'.join('SOURCE: '+key+'\n=====\n'+json.dumps(value,ensure_ascii=False)
                     for key,value in blocks.items()).encode('utf-8')
    manifest = _manifest(tmp_path / 'sources', tmp_path, [('types.txt', 'types', data)])
    build_catalog(tmp_path, tmp_path / 'sources', manifest)
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    install_review_fixtures(tmp_path)
    desk = SourceDesk(tmp_path, test_mode=True)
    exact = next(r['id'] for r in desk.rows if r['fragment_key']=='主类型.json' and r['key']==a['type_id'])
    original = phase_flow._sources

    def supplied(desk, stage, *args, **kwargs):
        if stage == 'type_selection':
            return [desk.read(exact)]
        return original(desk, stage, *args, **kwargs)

    monkeypatch.setattr(phase_flow, '_sources', supplied)
    class MappingReader(PhaseModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            if json.loads(messages[-1]['content']).get('stage') != 'type_selection':
                return result
            response = json.loads(result.text)
            for use in response['products']['_uses']:
                use['output_refs'] = ['selection']
            for criterion in response['products']['_criteria']:
                for clause in criterion['clauses']:
                    if clause['applicability'] == 'applies':
                        clause['output_refs'] = ['/selection/0/basis']
            result.text = json.dumps(response, ensure_ascii=False)
            return result

    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('类型来源映射')
        store.add_brief('封条调查')
        adopt_story(store, baseline(), {})
        provider = MappingReader()
        budget = create_budget(store, 'type-mapping', Budget(20, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'type-mapping')
        _, frozen = drive_plan(store, request, package, provider, config(store))
        messages = {json.loads(call[-1]['content']).get('stage'): call for call in provider.calls}
        assert exact in {v['source_id'] for v in frozen['material_work']['stages'][0]['products']['_uses']}
        for stage in ('type_selection','type_adaptation'):
            payload = json.loads(messages[stage][-1]['content'])
            [proof] = payload['type_source_mappings']
            assert proof['original'] == mapping
            assert proof['target']['source_ref']['id'] == exact and proof['qualification'] == 'reference'
            assert proof['source_ref']['id'] not in {v['source']['id'] for v in payload['sources']}
        assert 'type_source_mappings' not in json.loads(messages['world_design'][-1]['content'])


def test_checkpoint_keeps_original_inputs_when_a_material_reference_changes(tmp_path, monkeypatch):
    from nw.materials.work_catalog import SourceDesk

    template_catalog(tmp_path)
    with Store(tmp_path / 'story', create=True, test_mode=True) as store:
        store.init_project('来源更新后重开')
        store.add_brief('封条调查')
        adopt_story(store, baseline(), {})
        provider = PhaseModel()
        budget = create_budget(store, 'stale-source', Budget(32, 90000, 4000))
        request, package = prepare_plan_task(store, 1, 'book', provider, config(store), budget, 'stale-source')
        package = {**package, 'scope': 'chapter'}
        drive_plan(store, request, package, provider, config(store))
        sent = len(provider.calls)
        read = SourceDesk.read

        def changed(desk, ident):
            source = read(desk, ident)
            if source['source']['key'] == 'TDR_TEMPLATE_003':
                return {**source, 'related_sources': ['f' * 64]}
            return source

        monkeypatch.setattr(SourceDesk, 'read', changed)
        with pytest.raises(ValueError, match='STALE_MATERIAL: checkpoint sources changed'):
            drive_plan(store, request, package, provider, config(store), retry_failed=True)
        assert len(provider.calls) == sent


def test_type_name_evidence_follows_only_current_planning_inputs(tmp_path):
    from nw.materials.type_hierarchy import TYPE_TABLE
    from test_material_catalog import _manifest
    from test_type_adjudication import genre

    parent = genre(level=1, ancestor_ids=[], child_ids=[], schema_version='TYPE_H1A-1.0.0')
    children = [{**parent, 'type_id':'SUB_'+key, 'canonical_name':name, 'type_kind':'SUBGENRE',
                 'parent_id':'GENRE_ONE', 'ancestor_ids':['GENRE_ONE'], 'level':2}
                for key,name in (('TRAVEL','穿越'), ('MEDICAL','医疗'))]
    tags = [{**parent, 'type_id':'SUBJECT_TAG_'+key, 'canonical_name':name, 'type_kind':'SUBJECT_TAG'}
            for key,name in (('TRAVEL','穿越'), ('MEDICAL','医疗'))]
    mechanism = {**parent,'type_id':'PLOT_MECHANISM_TRANSMIGRATION','canonical_name':'穿越机制',
                 'type_kind':'PLOT_MECHANISM'}
    for row in (parent,*children,*tags,mechanism):
        row['definition'] = row['canonical_name']
    source = ('SOURCE: '+TYPE_TABLE+'\n=====\n'+json.dumps([parent,*children,*tags,mechanism],
                                                          ensure_ascii=False)).encode('utf-8')
    manifest = _manifest(tmp_path/'sources',tmp_path,[('types.txt','types',source)])
    build_catalog(tmp_path,tmp_path/'sources',manifest)
    index_units(tmp_path,None)
    build_adjudications(tmp_path)

    class TypeReader(PhaseModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            if json.loads(messages[-1]['content']).get('stage')=='type_selection':
                output = json.loads(result.text)
                concept = output['products']['concepts'][0]
                concept.update(label='穿越', activation_basis='[FAKE] 作者在项目要求中确定了穿越题材')
                result.text = json.dumps(output,ensure_ascii=False)
            return result

    with Store(tmp_path/'story',create=True,test_mode=True) as store:
        store.init_project('类型同名范围')
        store.add_brief('作者指定穿越题材，提及医疗作为背景，待核故事选型')
        adopt_story(store,baseline(),{})
        reader = TypeReader()
        budget = create_budget(store,'type-name-proof',Budget(16,90000,4000))
        request, package = prepare_plan_task(store,1,'book',reader,config(store),budget,'type-name-proof')
        drive_plan(store,request,package,reader,config(store))
        calls = {json.loads(m[-1]['content']).get('stage'):m for m in reader.calls}
        selection = json.loads(calls['type_selection'][-1]['content'])['type_name_evidence']
        adaptation = json.loads(calls['type_adaptation'][-1]['content'])['type_name_evidence']
        assert {row['term'] for row in selection} == {'穿越','医疗'}
        [travel] = adaptation
        assert travel['term']=='穿越'
        assert {row['type_kind'] for row in travel['alternatives']} == {'SUBGENRE','SUBJECT_TAG','PLOT_MECHANISM'}
        assert 'boundaries 记待核' in calls['type_selection'][0]['content']
        assert 'type_name_evidence' not in json.loads(calls['world_design'][-1]['content'])
        n = len(reader.calls)
        _, again = prepare_plan_task(store,1,'book',reader,config(store),budget,'type-name-proof')
        drive_plan(store,request,again,reader,config(store),retry_failed=True)
        assert len(reader.calls)==n


@pytest.mark.parametrize(('stage', 'key', 'checks'), [
    ('bind_scope', '126.1_板块调用原则', ('取材流程', '采用的子项', '第140158行')),
    ('bind_scope', '126.16_模板版本管理', ('冻结', '写后效果', '第140723行')),
    ('review_scope', '126.16_模板版本管理', ('冻结调用记录', '完整章稿', '写后效果')),
    ('bind_scope', '127.4_设计到正文的转化路径', ('写作指令', 'method_guidance', '确需表现角色情感')),
    ('plot_design', '120.1_多视角必要性判定', ('单视角', '独立认知弧光', '主角认同')),
    ('scene_design', '120.1_多视角必要性判定', ('已选视角', '场景卡', '允许披露')),
    ('writer', '127.15_设计应用的创造性发挥规则', ('即兴', '不可逆性', '128.1')),
    ('writer', '127.16_设计应用中的修正与补全', ('作者确认', '新参数', '128.2')),
    ('writer', '128.8_执行实现类板块的调用', ('当段任务', '第141884行', '119.10「读者自反时刻」')),
    ('review_scope', '127.16_设计应用中的修正与补全', ('修改前后稿件', '新参数', '128.2')),
    ('expression_design', '127.17_设计应用的场景适配规则', ('已定章型', '场景功能', '原件没有给出实际反例')),
    ('bind_scope', '128.1_精准调用核心原则', ('最小调用清单', '直接用途', '当前预算')),
    ('bind_scope', '128.2_按创作场景确定调用范围', ('实际前置产物', '调用记录', '正文证据')),
])
def test_step_prompt_preserves_selected_library_guidance_across_original_views(stage, key, checks):
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt
    from nw.materials.steps.review_scope import MATERIAL as SCOPE_MATERIAL
    from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL

    material = {**STAGE_MATERIALS, 'writer': WRITING_MATERIAL, 'review_scope': SCOPE_MATERIAL}[stage]
    prompt = step_material_prompt('当前步骤', material, [key])

    # Early and detailed source views share a key. The selected step guidance
    # should reach the model once, with the original quotes on the source side.
    assert prompt.count(f'\n### {key}\n') == 1
    for fragment in checks:
        assert fragment in prompt
    assert '【原文位置】' not in prompt


@pytest.mark.parametrize('stage,key,detail', [
    ('scene_design','120.4_视角切换时机','新观察者有剧情所需的独有内容'),
    ('scene_design','板块58 视角类型#受限视角','具体的知情来源和披露边界'),
    ('write','120.5_视角切换标记','新场首段三句内'),
    ('review','120.5_视角切换标记','从场景分界和首段前三句'),
    ('expression_design','板块50 词汇控制#精确动词鼓励使用','动作确已用力收紧'),
    ('expression_design','板块57 对话技术#非台词元素','被截断的话语'),
    ('expression_design','板块56 对话目的#对话目的规则','再改成角色会在当下说的话'),
    ('write','156.3_外貌审美','开头三句内'),
    ('write','7.2_情感在对话中的呈现','措辞、语速、停顿或打断'),
    ('write','板块49 句子控制#短句使用时机','已定的高强度对抗'),
    ('write','板块57 对话技术#非台词元素','项目已确认的文风'),
    ('review','156.5_动作审美','动作后的确切结果'),
    ('review','板块95 对话规则检查#非台词元素','引用停顿前后的回应'),
    ('scope_review','板块94 语言规则检查#句长比例','整章比例用整章稿核对'),
    ('scope_review','板块95 对话规则检查#说话风格一致','变化前后的台词'),
])
def test_selected_prose_guidance_matches_the_full_source_key(stage, key, detail):
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt
    from nw.materials.steps.review import MATERIAL as review
    from nw.materials.steps.review_scope import MATERIAL as scope_review
    from nw.materials.steps.writing import MATERIAL as write

    material = {'expression_design': STAGE_MATERIALS['expression_design'],
                'scene_design': STAGE_MATERIALS['scene_design'],
                'write': write, 'review': review, 'scope_review': scope_review}[stage]
    prompt = step_material_prompt('当前步骤', material, {key})
    assert prompt.splitlines().count('### ' + key) == 1
    assert detail in prompt
    if key.startswith('板块'):
        assert not any(line.startswith('### ') for line in
                       step_material_prompt('当前步骤', material, {key.split('#')[-1]}).splitlines()
                       if key.split('#')[-1] in line)


@pytest.mark.parametrize('stage,key,detail', [
    ('plot_design', '板块45 伏笔与反转#反转合理性', '先前支持旧判断的线索'),
    ('write', '板块45 伏笔与反转#反转合理性', '同一线索为何也能支持新解释'),
    ('review', '板块45 伏笔与反转#反转合理性', '反转前的线索和反转当场的证据'),
    ('scene_design', '板块46 场景结构#场景内部因果链', '已建立的前场结果'),
    ('write', '板块46 场景结构#场景内部因果链', '当前视角能察觉的触发'),
    ('scene_design', '板块46 场景结构#场景结局不可逆', '失去的条件或需要付出的新代价'),
    ('review', '板块91 场景结构检查#场景结局不可逆', '确有从前值到后值的改变'),
    ('write', '板块48 章节结构#结尾规则', '写出决定如何落地或威胁如何显现'),
    ('plot_design', '板块48 章节结构#信息释放节奏', '分开安排角色获知与读者获知的时点'),
    ('write', '板块48 章节结构#信息释放节奏', '决策发生后才揭示已安排的隐藏原因'),
    ('scene_design', '板块48 章节结构#章节连续性', '本章首场前1/3'),
    ('write', '板块48 章节结构#章节连续性', '部分回应时交付已经安排的一项答案或后果'),
    ('scope_review', '板块48 章节结构#章节连续性', '回想旧问题只能用于唤回记忆'),
    ('expression_design', '板块62 节奏控制#场景内快慢交替', '已承担余波的段落放缓'),
    ('expression_design', '板块62 节奏控制#情绪承接', '从同一处可感细节引出新的不安'),
    ('write', '板块62 节奏控制#情绪承接', '从同一处可感细节引出新的不安'),
    ('scope_review', '板块62 节奏控制#情绪承接', '前章末的情绪依据和次章开头的感知变化'),
    ('write', '板块65 读者认知#读者不确定性管理', '已确认的封闭终章'),
    ('scope_review', '板块96 结尾规则检查#全章结尾', '按终章已确认的收束任务核对'),
    ('write', '123.16_连载节奏设计', '立即兑现的章尾问题'),
    ('scope_review', '123.16_连载节奏设计', '钩子与长线伏笔分别引用实际段落'),
    ('plot_design', '122.16_推进的反转效应', '至少两个可由当前事实推出的新走向'),
    ('scene_design', '115.4_空间转换规则', '开始移动、已经抵达或由新观察者接手'),
    ('write', '115.4_空间转换规则', '先让读者辨认新的地点和观察者'),
    ('review', '115.4_空间转换规则', '场景分隔是否接住前场的行动'),
    ('write', '155.2_“谁在哪、为什么去”共情铺垫', '首章或临时转向缺少前章铺垫时'),
    ('write', '112.7_结尾类型', '延续式交代故事结束后仍在运转的事物'),
    ('write', '113.3_时间跳跃规则', '省略期间发生的事由既定前置确认'),
    ('scope_review', '122.17_推进的不可逆性量化检查', '用下一章首场实际段落核对后果是否保留'),
])
def test_chapter_craft_guidance_reaches_the_step_for_its_exact_source(stage, key, detail) -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt
    from nw.materials.steps.review import MATERIAL as review
    from nw.materials.steps.review_scope import MATERIAL as scope_review
    from nw.materials.steps.writing import MATERIAL as write

    steps = {**STAGE_MATERIALS, 'write': write, 'review': review, 'scope_review': scope_review}
    prompt = step_material_prompt('当前步骤', steps[stage], {key})
    assert prompt.splitlines().count('### ' + key) == 1
    assert detail in prompt
    assert detail not in step_material_prompt('当前步骤', steps[stage], {'本批以外的条目'})


@pytest.mark.parametrize('stage,key,detail', [
    ('character_design', '2.2_角色嗓音', '语调和音量'),
    ('expression_design', '2.2_角色嗓音', '语速、用词、打断及停顿'),
    ('write', '2.2_角色嗓音', '只有前文或已确认场景表明是作品中的首次开口'),
    ('review', '2.2_角色嗓音', '引用第一句前后'),
    ('action_design', '2.3_角色动作', '力度、速度、幅度和方向'),
    ('character_design', '2.6_角色状态', '身体、精神、能量和关系'),
    ('action_design', '7.3_情感在冲突中的使用', '区分情绪驱动争夺、参与回合和改变信息判断'),
    ('write', '7.4_情感与身体反应', '人物意图要有当事人说做的事情及其他情境线索支持'),
    ('scene_design', '7.9_情感密度控制', '四种章型按实际已确认的章任务'),
    ('write', '7.9_情感密度控制', '展开已分配的触发和反应'),
    ('scope_review', '155.3_节奏类型与情感密度的强制匹配', '同一触发下的同一反应只计一次'),
    ('write', '板块52 感官描写#五感规则', '视、听、触安排到相应稿段'),
    ('scope_review', '板块53 叙述距离#距离变化规则', '两种距离各自至少连续一个段落'),
    ('write', '板块55 语言风格#音律与节奏控制', '把该段已有的感受和动作放到停顿前后'),
    ('expression_design', '110.2_氛围与角色情绪的映射', '分别设计外景映照与主观感知变化'),
    ('write', '110.2_氛围与角色情绪的映射', '用具体的光线、声响、温度或距离感'),
    ('write', '116.3_角色知道但读者不知道', '写出实际发生的回避或非直接作答'),
    ('review', '116.3_角色知道但读者不知道', '读者现在能看见怎样的保留'),
    ('write', '板块59 视角规则#配角POV强制性内容', '配角自身的目标或利害'),
    ('review', '板块59 视角规则#配角POV强制性内容', '对照主要人物已定的目的或能做的事'),
    ('action_design', '159.2_行动中思想描写', '按已有动作链中产生可见作用的完整动作'),
    ('write', '159.2_行动中思想描写', '让角色根据刚出现的反馈改变下一步'),
    ('review', '159.2_行动中思想描写', '观察怎样实际改变下一步'),
])
def test_character_and_sensory_source_guidance_reaches_the_selected_step(stage, key, detail) -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt
    from nw.materials.steps.review import MATERIAL as review
    from nw.materials.steps.review_scope import MATERIAL as scope_review
    from nw.materials.steps.writing import MATERIAL as write

    steps = {**STAGE_MATERIALS, 'write': write, 'review': review, 'scope_review': scope_review}
    prompt = step_material_prompt('当前步骤', steps[stage], {key})
    assert prompt.splitlines().count('### ' + key) == 1
    assert detail in prompt
    assert detail not in step_material_prompt('当前步骤', steps[stage], {'本批以外的条目'})


@pytest.mark.parametrize(('stage', 'key', 'detail'), [
    ('scene_design', '28.2_道具功能边界', '记录本场可见的一项功能迹象'),
    ('write', '28.2_道具功能边界', '读者能看到的最小效果'),
    ('review', '28.2_道具功能边界', '早期证据需指向这项新用途'),
    ('expression_design', '28.3_道具代价机制', '谁在什么时候失去了什么'),
    ('write', '28.3_道具代价机制', '让承担代价的人'),
    ('review', '28.3_道具代价机制', '哪项后效仍在'),
    ('write', '28.4_道具成瘾性', '原本能用的选择怎样变窄'),
    ('write', '28.5_道具记忆载体', '人物确切所知和他由此产生的推断'),
    ('write', '28.6_道具象征化', '保留读者能认出的相同细节'),
    ('write', '29.1_道具与角色交互', '手能不能稳住'),
    ('scene_design', '29.2_道具与环境交互', '哪个地点或环境状态使动作生效'),
    ('write', '29.2_道具与环境交互', '环境变化与道具变化的先后'),
    ('scene_design', '29.3_道具反功能', '保留前置规则允许的不同结果'),
    ('expression_design', '29.3_道具反功能', '读者当时能看出的不确定之处'),
    ('write', '29.3_道具反功能', '人实际察觉到哪一处偏离'),
    ('review', '29.3_道具反功能', '故障前的可知条件'),
    ('state_transition', '29.4_道具进化', '仍然有效的限制'),
    ('write', '30.2_功能边界测试与突破', '本次尝试比上一次改变了什么'),
    ('write', '30.5_道具失效与转化', '本场动作结束后还能留下什么'),
    ('state_transition', '30.5_道具失效与转化', '沿用的身份与原物已经结束'),
    ('review', '107.1_道具功能不能改变', '上次可确认的功能和状态'),
    ('scene_design', '1.4_背景角色', '原文每场不超过3人'),
    ('write', '1.4_背景角色', '融入已有的环境或他人动作'),
    ('write', '121.3_配角的叙事功能层级', '行动这一步本身'),
    ('write', '156.3_外貌审美', '转入新视角按其当下能看见的部分'),
])
def test_prop_and_appearance_source_guidance_reaches_the_selected_step(stage, key, detail) -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt
    from nw.materials.steps.review import MATERIAL as review
    from nw.materials.steps.writing import MATERIAL as write

    steps = {**STAGE_MATERIALS, 'write': write, 'review': review}
    material = steps[stage]
    prompt = step_material_prompt('当前步骤', material, {key})
    assert prompt.splitlines().count('### ' + key) == 1
    assert detail in prompt
    assert detail not in step_material_prompt('当前步骤', material, {'本批以外的条目'})


@pytest.mark.parametrize(('stage', 'key', 'detail'), [
    ('scene_design', '板块48 章节结构#视角分配规则', '前500字的感知证据属于已选配角'),
    ('scope_review', '板块48 章节结构#视角分配规则', '按完整章稿核对配角视角场数'),
    ('scene_design', '板块59 视角规则#主角POV功能', '开场三句让读者辨认现任观察者'),
    ('scene_design', '板块59 视角规则#配角POV功能', '同章限制和跨章频率分别取证'),
    ('write', '板块59 视角规则#视角与不可见信息', '读者已知的事实继续留在他此前看过的章场'),
    ('review', '板块59 视角规则#信息差设计', '分别引用读者先前已获信息和本场人物的判断'),
    ('scene_design', '121.11_配角信息承载功能', '此人从哪里、何时知道这项信息'),
    ('expression_design', '121.11_配角信息承载功能', '可观察的行动怎样露出信息'),
    ('write', '121.11_配角信息承载功能', '把说出口、能被察觉和仍然不知道的内容分开'),
    ('review', '121.11_配角信息承载功能', '来源、听者及读者各自掌握的证据'),
    ('event_design', '121.9_配角独立行动规则', '哪项后果随后进入主角的视线'),
    ('write', '121.9_配角独立行动线', '从痕迹、他人消息或改变后的处境'),
    ('write', '121.27_配角的“欠账”与“还账”系统', '先前帮过谁和这次为谁做了什么'),
    ('state_transition', '121.27_配角的“欠账”与“还账”系统', '已承诺偿还和实际偿还分别登记'),
    ('write', '板块57 对话技术#未说之言设计', '读者能察觉回避的证据'),
    ('review', '板块57 对话技术#说话风格一致性', '记录哪次状态、弧光或场景变化'),
    ('expression_design', '116.6_信息释放时机控制', '决定之前需要的事实'),
    ('write', '116.6_信息释放时机控制', '先写行动依据，再写到时才揭示的部分'),
])
def test_selected_dialogue_and_supporting_character_guidance(stage, key, detail) -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt
    from nw.materials.steps.review import MATERIAL as review
    from nw.materials.steps.review_scope import MATERIAL as scope
    from nw.materials.steps.writing import MATERIAL as write

    steps = {**STAGE_MATERIALS, 'write': write, 'review': review, 'scope_review': scope}
    section = steps[stage]
    selected = step_material_prompt('当前步骤', section, {key})
    assert selected.splitlines().count('### ' + key) == 1
    assert detail in selected
    assert detail not in step_material_prompt('当前步骤', section, {'本批以外的条目'})


@pytest.mark.parametrize(('stage', 'key', 'detail'), [
    ('scene_design', '板块47 场景冲突#冲突锋利度', '两个目标能否同时成立'),
    ('review', '板块93 冲突规则检查#冲突锋利度', '指出同一条件下无法兼得的结果'),
    ('write', '板块47 场景冲突#冲突锋利度', '双方的行动怎样改变同一个机会'),
    ('scene_design', '43.1_资源争夺', '同一个可争夺对象'),
    ('write', '43.1_资源争夺', '谁因此失去或暂时拿不到'),
    ('write', '43.2_信息博弈', '各自说出了什么、保留了什么'),
    ('scene_design', '43.4_道德困境', '两种仍然可行的选择'),
    ('write', '43.4_道德困境', '实际付出和仍然受影响的对象'),
    ('review', '43.4_道德困境', '哪项价值被优先保住'),
    ('scene_design', '43.9_冲突叠加', '同时压在同一个决定上'),
    ('event_design', '42.6_岔路设计与回撤机制', '选择怎样改变下一事件的条件'),
    ('write', '42.8_失败设计', '能看到原计划在哪里失效'),
    ('review', '42.8_失败设计', '哪项旧条件此后已经不能照旧'),
    ('write', '15.4_突破的代价类型', '当场支付的具体过程'),
    ('plot_design', '板块145 五节点链条', '角色忽略的已有反证'),
    ('write', '板块145 五节点链条', '从同一目标回查选择和实际后果'),
    ('state_transition', '118.3_代价叠加规则', '不同代价之间需要可回查的影响'),
    ('review', 'D2.15', '各次已经实际承担的损失'),
])
def test_selected_conflict_result_and_cost_guidance(stage, key, detail) -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt
    from nw.materials.steps.review import MATERIAL as review
    from nw.materials.steps.writing import MATERIAL as write

    steps = {**STAGE_MATERIALS, 'write': write, 'review': review}
    material = steps[stage]
    prompt = step_material_prompt('当前步骤', material, {key})
    assert prompt.splitlines().count('### ' + key) == 1
    assert detail in prompt
    assert detail not in step_material_prompt('当前步骤', material, {'本批以外的条目'})
