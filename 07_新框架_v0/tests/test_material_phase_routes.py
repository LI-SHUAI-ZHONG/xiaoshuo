from nw.materials.phase_routes import route_method,readiness,phase_order


def test_tdr_template_waits_for_project_products_instead_of_being_rejected():
    source={'source':{'key':'TDR_TEMPLATE_003','profile':'type_transition'},
            'source_state':'reference','use_mode':'project_method'}
    route=route_method(source)
    assert route['stages']==['state_transition']
    pending=readiness('state_transition',{})
    assert pending['state']=='waiting_for_inputs'
    assert {'character_design','static_relations','scene_design'}<=set(pending['missing'])
    ready=readiness('state_transition',{key:{'sha256':'a'*64,'products':{'actual':'前置实际产物'}}
                                       for key in route['requires']})
    assert ready['state']=='ready'
    assert source['source_state']=='reference'


def test_original_pipeline_order_is_maintained_by_the_scheduler():
    order=phase_order('chapter')
    assert order.index('character_design')<order.index('static_relations')<order.index('state_transition')
    assert order.index('scene_design')<order.index('state_transition')<order.index('anchor_design')<order.index('expression_design')
    assert order[-1]=='bind_scope'


def test_methods_are_routed_by_use_not_given_to_every_step():
    world={'source':{'key':'10.1_力量限制','profile':'world'}}
    emotion={'source':{'key':'64.1_读者情绪','profile':'plot'}}
    expression={'source':{'key':'52.1_动作细化','profile':'expression'}}
    assert route_method(world)['stages']==['world_design']
    assert 'plot_design' in route_method(emotion)['stages']
    assert 'expression_design' in route_method(expression)['stages']
    assert 'type_selection' not in route_method(expression)['stages']



def test_current_identity_anchor_uses_the_existing_step_that_contains_its_exact_row() -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import route_method
    from nw.materials.stage_input import step_material_prompt

    source = {'profile': 'anchor', 'key': 'ID3.13',
              'file_sha256': '9b7ea71e53613a453fe71fa0a862411f65f22328a38ee7b97db7fd5bab7be759',
              'execution_stages': ['anchor_design']}
    routed = route_method(source)
    assert routed['stages'][0] == 'state_transition'
    prompt = step_material_prompt('当前步骤', STAGE_MATERIALS['state_transition'], {source['key']})
    assert prompt.count('### ID3.13\n') == 1 and '已撤回的许可' in prompt
    assert '突发_外部_背叛' not in prompt
    assert route_method({**source, 'file_sha256': '0' * 64})['stages'] == ['anchor_design']

def test_unexpected_anchors_offer_only_their_specific_guidance_in_each_existing_step() -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import _ANCHOR_TABLE_SHA256, _in_step_anchor_routes
    from nw.materials.stage_input import step_material_prompt

    expected = {f'U{group}.{index}' for group in range(1, 4) for index in range(1, 21)}
    actual = {key: stage for key, stage in _in_step_anchor_routes().items() if key.startswith('U')}
    assert actual.keys() == expected
    for key, stage in actual.items():
        source = {'profile': 'anchor', 'key': key, 'file_sha256': _ANCHOR_TABLE_SHA256}
        assert route_method(source)['stages'][0] == stage
        assert route_method({**source, 'file_sha256': '0' * 64})['stages'] == ['anchor_design']
        prompt = step_material_prompt('当前步骤', STAGE_MATERIALS[stage], {key})
        assert prompt.splitlines().count(f'### {key}') == 1
        assert sum(row.startswith('### U') for row in prompt.splitlines()) == 1
        assert '【本步用法】' in prompt
    relative = {
        'U1.1': ('event_design', '前事件的完成门槛'),
        'U1.11': ('state_transition', '可行动能力的前后差异'),
        'U2.1': ('scene_design', '沿用预期对象及参照结果'),
        'U3.1': ('plot_design', '对原有计划或关系造成局部变化'),
        'U3.17': ('anchor_design', '首次注意的线索'),
    }
    for key, (stage, phrase) in relative.items():
        assert actual[key] == stage
        assert phrase in step_material_prompt('当前步骤', STAGE_MATERIALS[stage], {key})


def test_current_chapter_craft_sources_reach_their_in_step_use() -> None:
    from nw.materials.binding_reviews import allows_stage_candidate
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt

    active = '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed'
    materials = {
        '板块45 伏笔与反转#反转合理性': ('expression_design',),
        '板块48 章节结构#结尾规则': ('scene_design',),
        '板块48 章节结构#章节连续性': ('scene_design',),
        '板块62 节奏控制#场景内快慢交替': ('scene_design', 'expression_design'),
        '板块62 节奏控制#情绪承接': ('scene_design', 'expression_design'),
        '板块65 读者认知#读者不确定性管理': ('scene_design',),
        '113.3_时间跳跃规则': ('scene_design', 'expression_design'),
        '155.2_“谁在哪、为什么去”共情铺垫': ('scene_design',),
    }
    context = {'scope': 'chapter', 'current_source_set': True}
    for key, stages in materials.items():
        source = {'source': {'id': key, 'key': key, 'profile': 'plot', 'file_sha256': active},
                  'source_state': 'design_ready', 'use_mode': 'project_method'}
        actual = route_method(source)['stages']
        assert actual[:2] == ['plot_design', 'event_design'] and set(stages) <= set(actual), key
        historical = {**source, 'source': {**source['source'], 'file_sha256': '0' * 64}}
        for stage in stages:
            assert allows_stage_candidate(source, stage, context)
            assert not allows_stage_candidate(historical, stage, context)
            prompt = step_material_prompt('当前步骤', STAGE_MATERIALS[stage], {key})
            assert prompt.splitlines().count('### ' + key) == 1


def test_current_character_and_sensory_sources_use_the_steps_that_contain_their_methods() -> None:
    from nw.materials.binding_reviews import allows_stage_candidate
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.stage_input import step_material_prompt

    active = '1e4c7720fbc745ab952cd749c6faad03cff26c9a8e3f9bce5c4c5a6da91a36ed'
    routes = {
        ('plot', '155.3_节奏类型与情感密度的强制匹配'): ('scene_design',),
        ('anchor', '110.2_氛围与角色情绪的映射'): ('expression_design',),
        ('expression', '板块59 视角规则#配角POV强制性内容'): ('scene_design',),
        ('expression', '板块59 视角规则#配角POV前500字限制'): ('scene_design',),
        ('plot', '44.8_高潮三层情感叠加'): ('expression_design',),
    }
    context = {'scope': 'chapter', 'current_source_set': True}
    for (profile, key), steps in routes.items():
        original = {'id': key, 'key': key, 'profile': profile, 'file_sha256': active}
        source = {'source': original, 'source_state': 'design_ready', 'use_mode': 'project_method'}
        archived = {**source, 'source': {**original, 'file_sha256': '0' * 64}}
        for step in steps:
            assert allows_stage_candidate(source, step, context), (key, step)
            assert not allows_stage_candidate(archived, step, context)
            prompt = step_material_prompt('当前步骤', STAGE_MATERIALS[step], {key})
            assert prompt.splitlines().count('### ' + key) == 1


def test_current_prop_and_appearance_sources_reach_the_steps_with_their_uses() -> None:
    from nw.materials.binding_reviews import allows_stage_candidate
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import _LIBRARY_SHA256
    from nw.materials.stage_input import step_material_prompt

    expected = [
        ('world', '19.3_例外的代价', ('action_design', 'state_transition')),
        ('world', '28.2_道具功能边界', ('plot_design', 'action_design', 'scene_design', 'expression_design')),
        ('world', '28.3_道具代价机制', ('plot_design', 'action_design', 'state_transition', 'expression_design')),
        ('world', '28.4_道具成瘾性', ('plot_design', 'state_transition')),
        ('world', '28.5_道具记忆载体', ('plot_design', 'expression_design')),
        ('world', '28.6_道具象征化', ('plot_design', 'expression_design')),
        ('world', '29.1_道具与角色交互', ('action_design', 'anchor_design', 'expression_design')),
        ('world', '29.2_道具与环境交互', ('action_design', 'scene_design')),
        ('world', '29.3_道具反功能', ('plot_design', 'action_design', 'scene_design', 'expression_design')),
        ('world', '29.4_道具进化', ('plot_design', 'state_transition', 'expression_design')),
        ('world', '30.2_功能边界测试与突破', ('action_design', 'scene_design')),
        ('world', '30.4_道具维护与升级', ('action_design', 'state_transition')),
        ('world', '30.5_道具失效与转化', ('plot_design', 'scene_design', 'state_transition', 'expression_design')),
        ('character', '121.4_配角的登场时机', ('plot_design',)),
        ('expression', '156.3_外貌审美', ('expression_design',)),
    ]
    context = {'scope': 'chapter', 'current_source_set': True}
    original_stages = {'world': ['world_design'], 'character': ['character_design'],
                       'expression': ['plot_design']}
    for profile, key, stages in expected:
        original = {'id': key, 'key': key, 'profile': profile, 'file_sha256': _LIBRARY_SHA256,
                    'execution_stages': original_stages[profile]}
        source = {'source': original, 'source_state': 'design_ready', 'use_mode': 'project_method'}
        retired = {**source, 'source': {**original, 'file_sha256': '0' * 64}}
        for stage in stages:
            assert allows_stage_candidate(source, stage, context), (key, stage)
            assert not allows_stage_candidate(retired, stage, context)
            prompt = step_material_prompt('当前步骤', STAGE_MATERIALS[stage], {key})
            assert prompt.splitlines().count('### ' + key) == 1, (key, stage)


def test_selected_prop_and_decision_anchors_use_their_source_row_step() -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import _ANCHOR_TABLE_SHA256
    from nw.materials.stage_input import step_material_prompt

    cases = [
        ('M9.1', 'anchor_design', '当前视角的位置和光线'),
        ('D2.18', 'expression_design', '此人后悔的是哪次选择'),
        ('D2.21', 'action_design', '具体要改动的一步'),
        ('D3.15', 'static_relations', '受托者能自行决定的范围'),
        ('D3.32', 'scene_design', '各人作出选择时持有的不同证据'),
        ('D4.1', 'plot_design', '从哪个动作起不能照旧'),
        ('D4.2', 'anchor_design', '承诺和生效各落在哪个动作'),
        ('D4.7', 'state_transition', '仍然留下的代价'),
        ('D4.34', 'scene_design', '已经生效的结果何时才被看见'),
        ('P1.19', 'expression_design', '先给读者看方向和停顿'),
        ('P5.31', 'state_transition', '他自己的情绪后来是否改变'),
        ('B2.37', 'expression_design', '旁人只能从他停手或说出的描述获得线索'),
        ('B3.14', 'anchor_design', '当事人觉得跳动顿了一下的瞬间'),
        ('B3.32', 'action_design', '本场可验证的成功操作'),
        ('E1.44', 'scene_design', '重大意外何时到达'),
        ('E1.47', 'state_transition', '把收到意外和后来理解它分成不同节点'),
        ('P5.5', 'action_design', '怀疑与已查明的欺骗各自有证据'),
        ('C2.47', 'state_transition', '已经符合、实际不符和仍待判断的部分'),
        ('C2.55', 'scene_design', '结果实际发生的时间'),
        ('L2.11', 'expression_design', '两种解读都有具体依据'),
        ('L2.15', 'scene_design', '听者首次能理解真实含义的时点'),
        ('S4.4', 'world_design', '停住的变化与仍能行动的人或事物'),
        ('S4.11', 'scene_design', '到哪个地点与时段'),
        ('S2.21', 'state_transition', '已毁、被遮住还是失去入口'),
        ('P1.3', 'anchor_design', '看到的一角'),
        ('A1.7', 'action_design', '冲刺后的实际体力或行动限制'),
        ('A1.21', 'scene_design', '上场原位置接到本场真正到达的地点'),
        ('C1.23', 'anchor_design', '确实改变局面的那一步'),
        ('T3.12', 'action_design', '已做的部分与本次真要修改'),
        ('T3.22', 'expression_design', '私下答应自己要改变哪件事'),
        ('A5.24', 'scene_design', '所执行的计划步骤'),
        ('A5.28', 'state_transition', '哪些目标已经达成'),
        ('M9.2', 'anchor_design', '能看见遮蔽物与能辨认其中的物件'),
        ('M9.3', 'anchor_design', '容器已打开或另有可见依据'),
        ('M9.9', 'anchor_design', '是什么实际细节让视线停留'),
        ('M9.10', 'anchor_design', '视线、听觉或注意此时正在何处'),
        ('M9.4', 'state_transition', '实际拿到的持有者'),
        ('M9.14', 'static_relations', '分别记录可以使用的人'),
        ('M9.15', 'static_relations', '谁能实际阻止他人使用'),
        ('M9.20', 'state_transition', '区分销毁动作和销毁已经完成'),
        ('A2.8', 'scene_design', '门开后哪些位置可由本场视角看见'),
        ('A2.11', 'state_transition', '锁的状态单独记录'),
        ('A2.15', 'state_transition', '实际扣合或生效的证据'),
    ]
    for key, stage, detail in cases:
        source = {'profile': 'anchor', 'key': key, 'file_sha256': _ANCHOR_TABLE_SHA256}
        assert route_method(source)['stages'][0] == stage, key
        assert route_method({**source, 'file_sha256': '0' * 64})['stages'] == ['anchor_design']
        prompt = step_material_prompt('当前步骤', STAGE_MATERIALS[stage], {key})
        assert prompt.splitlines().count('### ' + key) == 1
        assert detail in prompt


def test_dialogue_and_viewpoint_sources_reach_the_steps_holding_their_methods() -> None:
    from nw.materials.binding_reviews import allows_stage_candidate
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import _LIBRARY_SHA256
    from nw.materials.stage_input import step_material_prompt

    expected = [
        ('plot', '板块48 章节结构#视角分配规则', ('scene_design',)),
        ('expression', '板块59 视角规则#主角POV功能', ('scene_design',)),
        ('expression', '板块59 视角规则#配角POV功能', ('scene_design',)),
        ('expression', '板块59 视角规则#场景内视角一致', ('scene_design',)),
        ('expression', '板块59 视角规则#视角切换标记', ('scene_design',)),
        ('expression', '板块59 视角规则#视角与不可见信息', ('scene_design',)),
        ('expression', '板块59 视角规则#信息差设计', ('plot_design', 'scene_design')),
        ('character', '121.9_配角独立行动线', ('plot_design',)),
        ('character', '121.9_配角独立行动规则', ('event_design',)),
        ('character', '121.11_配角之间的互动关系', ('static_relations',)),
        ('character', '121.19_配角群的网络关系', ('static_relations',)),
        ('knowledge', '116.6_信息释放时机控制', ('expression_design',)),
    ]
    context = {'scope': 'chapter', 'current_source_set': True}
    for profile, key, stages in expected:
        method = {'id': key, 'key': key, 'profile': profile, 'file_sha256': _LIBRARY_SHA256}
        source = {'source': method, 'source_state': 'design_ready', 'use_mode': 'project_method'}
        retired = {**source, 'source': {**method, 'file_sha256': '0' * 64}}
        for stage in stages:
            assert allows_stage_candidate(source, stage, context), (key, stage)
            assert not allows_stage_candidate(retired, stage, context)
            prompt = step_material_prompt('当前步骤', STAGE_MATERIALS[stage], {key})
            assert prompt.splitlines().count('### ' + key) == 1, (key, stage)


def test_dialogue_anchors_reach_their_own_stage_use() -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import _ANCHOR_TABLE_SHA256
    from nw.materials.stage_input import step_material_prompt

    expected = [
        ('action_design', 'T1.2', '所要核实的具体问题'),
        ('action_design', 'T1.3', '原有权限与实际请求'),
        ('action_design', 'T1.4', '保留对方可以拒绝的条件'),
        ('action_design', 'T1.6', '条件足不足以采用'),
        ('action_design', 'T1.7', '听者来得及做出什么实际回应'),
        ('expression_design', 'P2.17', '听见说法和确认事实'),
        ('expression_design', 'P2.18', '字面所问和话外的试探'),
        ('expression_design', 'P2.19', '身份、权力和拒绝的后果'),
        ('expression_design', 'P2.20', '若不照做将发生的后果'),
        ('expression_design', 'P2.29', '听见哪一处上扬'),
        ('expression_design', 'T1.1', '能由说话者得知的内容'),
        ('expression_design', 'T1.5', '抱怨指向的具体不满'),
        ('expression_design', 'T1.41', '双方实际共有的线索'),
        ('scene_design', 'T1.40', '哪些保留仍只有本人知道'),
        ('scene_design', 'T1.42', '此前留存、当场说出与听者得知'),
        ('scene_design', 'T2.10', '谁从哪个动作或发言中得知'),
        ('action_design', 'A4.4', '被打断的那半句话'),
        ('scene_design', 'A4.5', '实际接收'),
        ('state_transition', 'A4.19', '实际恢复的权利或信任'),
        ('expression_design', 'L1.18', '已经拒绝原提议'),
        ('expression_design', 'L2.27', '当前听距'),
        ('anchor_design', 'L3.6', '实际回话开始定位等待'),
        ('state_transition', 'T1.46', '确认实际理解'),
    ]
    for stage, key, phrase in expected:
        source = {'profile': 'anchor', 'key': key, 'file_sha256': _ANCHOR_TABLE_SHA256}
        assert route_method(source)['stages'][0] == stage, key
        assert route_method({**source, 'file_sha256': '0' * 64})['stages'] == ['anchor_design']
        material = STAGE_MATERIALS[stage]
        selected = step_material_prompt('当前步骤', material, {key})
        assert selected.splitlines().count('### ' + key) == 1
        assert phrase in selected
        assert phrase not in step_material_prompt('当前步骤', material, {'本批以外的条目'})


def test_conflict_sources_can_be_used_in_the_responsible_existing_steps() -> None:
    from nw.materials.binding_reviews import allows_stage_candidate
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import _LIBRARY_SHA256
    from nw.materials.stage_input import step_material_prompt

    routes = [
        ('world', '15.4_突破的代价类型', ('action_design', 'state_transition')),
        ('world', '15.5_突破失败后果', ('plot_design', 'action_design', 'state_transition')),
        ('plot', '42.8_失败设计', ('action_design', 'state_transition')),
        ('plot', '43.1_资源争夺', ('action_design', 'scene_design')),
        ('plot', '43.2_信息博弈', ('scene_design', 'expression_design')),
        ('plot', '43.3_制度压迫', ('action_design',)),
        ('plot', '43.4_道德困境', ('action_design', 'scene_design', 'expression_design')),
        ('plot', '43.5_信任危机', ('state_transition', 'expression_design')),
        ('plot', '43.6_时间压力', ('action_design', 'expression_design')),
        ('plot', '43.7_身份冲突', ('action_design', 'scene_design')),
        ('plot', '43.9_冲突叠加', ('scene_design',)),
        ('plot', '板块145 五节点链条', ('action_design',)),
    ]
    context = {'scope': 'chapter', 'current_source_set': True}
    for profile, key, stages in routes:
        pin = {'profile': profile, 'id': key, 'key': key, 'file_sha256': _LIBRARY_SHA256}
        selected = {'source': pin, 'source_state': 'design_ready', 'use_mode': 'project_method'}
        retired = {**selected, 'source': {**pin, 'file_sha256': '0' * 64}}
        for stage in stages:
            assert allows_stage_candidate(selected, stage, context), (key, stage)
            assert not allows_stage_candidate(retired, stage, context)
            prompt = step_material_prompt('当前步骤', STAGE_MATERIALS[stage], {key})
            assert prompt.splitlines().count('### ' + key) == 1, (stage, key)


def test_decision_anchors_use_the_steps_where_their_original_rows_appear() -> None:
    from nw.materials.phase_flow import STAGE_MATERIALS
    from nw.materials.phase_routes import _ANCHOR_TABLE_SHA256
    from nw.materials.stage_input import step_material_prompt

    examples = [
        ('scene_design', 'D2.1', '确认采用的方案及本场开始的第一步'),
        ('scene_design', 'D2.2', '尚未执行到哪里'),
        ('action_design', 'D2.3', '已经执行的部分与仍可更改的部分'),
        ('action_design', 'D2.4', '停止之后实际留下的影响'),
        ('state_transition', 'D2.6', '对照同一目标的预期条件'),
        ('state_transition', 'D2.8', '结果朝相反方向发生'),
        ('state_transition', 'D2.11', '实际支付方及已支付的部分'),
        ('action_design', 'D2.12', '替代方案实际免掉哪项预计代价'),
        ('state_transition', 'D2.13', '仍待兑现的条件和时间'),
        ('state_transition', 'D2.15', '由前次实际代价累计的现值'),
        ('expression_design', 'D2.16', '代价已经显现的证据'),
        ('action_design', 'E4.35', '两项确有冲突的判断标准'),
        ('state_transition', 'E4.39', '此前选择及当事人已经承受的后果'),
        ('action_design', 'T1.28', '两项都属于该人物的理由'),
        ('state_transition', 'T1.29', '哪一点真正被解决'),
    ]
    for stage, key, phrase in examples:
        source = {'profile': 'anchor', 'key': key, 'file_sha256': _ANCHOR_TABLE_SHA256}
        assert route_method(source)['stages'][0] == stage, key
        assert route_method({**source, 'file_sha256': '0' * 64})['stages'] == ['anchor_design']
        material = STAGE_MATERIALS[stage]
        prompt = step_material_prompt('当前步骤', material, {key})
        assert prompt.splitlines().count('### ' + key) == 1
        assert phrase in prompt
        assert phrase not in step_material_prompt('当前步骤', material, {'本批以外的条目'})
