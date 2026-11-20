"""Stage responses made from existing explicit fixtures, only in isolated tests."""
from copy import deepcopy
import json
from typing import Any

from nw.llm.base import GenResult
from nw.materials.phase_contract import output_refs

TEST_STAGES = ('type_selection', 'type_adaptation', 'world_design', 'character_design',
    'static_relations', 'plot_design', 'event_design', 'action_design', 'scene_design',
    'state_transition', 'state_propagation', 'anchor_design', 'expression_design', 'bind_scope')


def _input(inputs: dict, stage: str) -> dict:
    return inputs.get(stage, {}).get('products', {})


def _process_bindings(candidate: dict, inputs: dict, scope: str) -> dict:
    bindings = deepcopy(candidate.get('process_bindings', {}))
    if scope == 'book' or not any('checks' in artifact for artifact in bindings.values()):
        return bindings
    actual = {row['key']: deepcopy(row) for stage in
        ('world_design', 'character_design', 'plot_design', 'scene_design')
        for row in _input(inputs, stage).get('members', [])}
    for patch in _input(inputs, 'state_transition').get('patches', []):
        body = actual[patch['scene']]['body']
        if body['choice'] != patch['choice']:
            body['choice'] += '；' + patch['choice']
        body['planned_result'] = patch['planned_result']
    checks = [{'kind': 'character_creation' if row['kind'] == 'character' else 'world_creation',
        'target': key, 'artifact': row['body']} for key, row in actual.items()
        if row['kind'] in ('character', 'world')]
    checks += [{'kind': 'opening', 'target': row['card'], 'artifact': actual[row['card']]['body']}
        for chapter in _input(inputs, 'scene_design').get('chapters', []) if chapter['index'] == 1
        for row in chapter['scenes'] if row['index'] == 1]
    checks += [{'kind': 'ending', 'target': key, 'artifact': row['body']} for key, row in actual.items()
        if row['kind'] == 'scene' and any(word in row['body'].get('title', '') for word in ('终章', '收尾'))]
    for artifact in bindings.values():
        if 'checks' in artifact:
            artifact['checks'] = deepcopy(checks)
    return bindings


def project_products(stage: str, candidates: list[dict], inputs: dict, sources: list[dict],
                     scope: str, *, native: bool = False) -> dict:
    """Explicit isolated-test designs, each linked to actual preceding products."""
    candidate = deepcopy(candidates[0]); members = candidate['members']
    scenes = [row for row in members if row['kind'] == 'scene']
    ids = [row['source']['id'] for row in sources]
    people = _input(inputs, 'character_design').get('members', [])
    nodes = _input(inputs, 'plot_design').get('event_nodes', [])
    if stage == 'type_selection':
        return {'selection': [{'id': 'investigation', 'label': '[FAKE] 制度谜团调查',
            'basis': '[FAKE] 当前项目选择以可见证据推动调查'}],
            'concepts': [{'id': 'old_seal', 'label': '[FAKE] 两代印痕差异', 'type_refs': ['investigation'],
                'activation_basis': '[FAKE] 调查类型已选，当前项目以印痕异常激活换印疑问'}], 'boundaries': []}
    if stage == 'type_adaptation':
        selected = _input(inputs, 'type_selection')
        types = [row['id'] for row in selected['selection']]
        return {'adaptations': [{'id': 'seal_adaptation', 'type_refs': types,
            'parameters': {'investigation': '[FAKE] 先观察封条，再核实更换者'},
            'limits': ['[FAKE] 不把推断写成已知事实']}],
            'focuses': [{'id': 'seal_focus', 'concept': row['id'], 'from_focus': '[FAKE] 门禁是否完整',
                'to_focus': '[FAKE] 谁更换过封条', 'application': '[FAKE] 依两代印痕差异安排调查重点'}
                for row in selected['concepts'][:1]], 'boundaries': []}
    if stage == 'world_design':
        worlds = [row for row in members if row['kind'] == 'world']
        return {'members': worlds or [{'key': 'seal', 'kind': 'world', 'body': {
            'title': '[FAKE] 药铺封条', 'rule': '[FAKE] 封条下藏有可划伤手背的铜丝',
            'limits': '[FAKE] 木片折断后不能继续抬起纸角', 'visibility': 'public'}}],
            'limitations': [], 'unknowns': candidate['open_world_rules']}
    if stage == 'character_design':
        characters = [row for row in members if row['kind'] == 'character']
        return {'members': characters, 'states': [], 'capabilities': [{'entity': row['key'],
            'can_act': True, 'abilities': ['观察印痕', '移动木片'],
            'basis': '[FAKE] 当前项目能力提案：因调查目标能借灯观察并用木片检查纸角',
            'limits': ['[FAKE] 不会拆除铜丝机关']} for row in characters]}
    if stage == 'static_relations':
        return {'relations': [], 'requirements': []}
    if stage == 'plot_design':
        people_ids = {row['key'] for row in people}
        node_scenes = scenes or [{'body': {'pov': people[0]['key'], 'characters': []}}]
        children=[row for row in members if row['kind'] not in ('world','character','scene')]
        promise=next((r for r in children if r['kind']=='promise'),None)
        if promise is None:
            promise={'key':'seal_promise','kind':'promise','body':{'title':'[FAKE] 换印来源',
                'setup':'[FAKE] 旧印留下来源疑问','payoff':'[FAKE] 后续用证据回收疑问','visibility':'public'}}
            children.append(promise)
        return {'directions': [row['body'] for row in (candidates if scope == 'book' else candidates[:1])],
            'members': children,'static_bindings':[],
            'reader_plan': [{'id':'emotion_1','event':'inspect_1','order':1,
                'information':'[FAKE] 先见封条限制，再发现旧印差异','before_emotion':'疑问','after_emotion':'担忧',
                'trigger':'[FAKE] 原来完整的纸角露出不同年代的印痕','intended_effect':'[FAKE] 促使读者期待调查换印的后果',
                'check':'[FAKE] 核对信息出现次序及其造成的认知变化'}],
            'promise_plan': [{'id':'foreshadow_1','promise':promise['key'],'plant_event':'inspect_1',
                'payoff_event':None,'plant_chapter':1,'payoff_chapter':None,
                'payoff_window':{'min_offset':2,'max_offset':10},'setup':promise['body']['setup'],
                'expected_meaning':'[FAKE] 旧印年代将关联换印者的行动','payoff':promise['body']['payoff'],
                'check':'[FAKE] 后续揭示时对照埋设内容与回收窗口'}],
            'event_nodes': [{'id': f'inspect_{index}',
                'actors': [row['body']['pov']] if row['body']['pov'] in people_ids else [people[0]['key']],
                'goal': '[FAKE] 查明封条是否被替换', 'setting': '[FAKE] 药铺门口',
                'obstacle': '[FAKE] 铜丝藏在纸角下',
                'completion_condition': f'[FAKE] 看清第{index}处纸角下的旧印', 'status': 'planned'}
                for index, row in enumerate(node_scenes, 1)]}
    if stage == 'event_design':
        return {'candidates': [{'id': f'follow_{index}', 'source_ids': ids, 'predecessor': row['id'],
            'event': '[FAKE] 带旧印拓片向印坊核查换印日期', 'actors': row['actors'],
            'completion_gate': row['completion_condition'], 'status': 'conditional_candidate'}
            for index, row in enumerate(nodes, 1)]}
    if stage == 'action_design':
        capabilities = {row['entity']: row for row in _input(inputs, 'character_design')['capabilities']}
        return {'candidates': [{'id': f'lift_{index}', 'source_ids': ids, 'event': row['id'], 'actor': row['actors'][0],
            'action': '[FAKE] 借灯观察封条，再以木片托住纸角查看旧印',
            'steps': [{'object': '[FAKE] 封条纸角', 'action': '[FAKE] 将木片伸到纸角下方',
                'obstacle': '[FAKE] 铜丝绷紧挡住木片', 'response': '[FAKE] 压低木片绕过铜丝',
                'result': '[FAKE] 露出旧印的半枚字形'}],
            'requires': capabilities[row['actors'][0]]['abilities'][:2],
            'cost': '[FAKE] 纸角破损会留下调查痕迹', 'limits': ['[FAKE] 木片折断即停止'], 'status': 'candidate'}
            for index, row in enumerate(nodes, 1)], 'waiting': []}
    if stage == 'scene_design':
        actions = _input(inputs, 'action_design')['candidates']; selected = []
        selected_events = []
        for index, scene in enumerate(scenes):
            action = next((row for row in actions[index:] if row['actor'] == scene['body']['pov']), actions[0])
            scene['body']['choice'] = action['action']
            selected.append({'scene': scene['key'], 'action': action['id']})
            selected_events.append({'scene': scene['key'], 'event': action['event']})
        return {'members': scenes, 'chapters': candidate['chapters'],
            'events': [{'id': row['key'] + '_change', 'scene': row['key'], 'entity': row['body']['pov'],
                'trigger': '[FAKE] 手背触碰纸角下的铜丝', 'before_state': {'hand': '完好'}} for row in scenes],
            'selected_events': selected_events, 'selected_actions': selected}
    if stage == 'state_transition':
        applicable = native or any(row['source']['key'].startswith('TDR_TEMPLATE_003') or
            row['source'].get('profile') in ('dynamic_relation', 'dynamic_binding') for row in sources)
        events = _input(inputs, 'scene_design')['events'] if applicable else []
        return {'patches': [{'scene': row['scene'], 'choice': '[FAKE] 收手改用木片查看封条',
            'planned_result': '[FAKE] 手背划伤后看清旧印'} for row in events],
            'transitions': [{'scene': row['scene'], 'entity': row['entity'], 'event': row['id'],
                'before_state': row['before_state'], 'action': '[FAKE] 伸手试探受伤后收手，改用木片',
                'after_state': {'hand': '划伤'}, 'cost': '[FAKE] 手背流血并留下痕迹',
                'failure': '[FAKE] 木片折断时停止', 'continuity': '[FAKE] 后续保留铜丝造成的手伤'} for row in events]}
    if stage == 'state_propagation':
        changes = _input(inputs, 'state_transition')['transitions']
        targets = _input(inputs, 'world_design').get('members', [])
        return {'candidates': [{'id': f'trace_{index}', 'source_ids': ids, 'root_kind': 'planned_change',
            'root_id': row['event'], 'source_entity': row['entity'], 'target_entity': targets[0]['key'],
            'external_action': '[FAKE] 主动把带血木片贴在封条旁',
            'proposed_effect': {'trace': '[FAKE] 封条旁可能新增供后来人检查的血迹'},
            'continuity': '[FAKE] 血迹来自本次铜丝造成的手伤', 'scene': row['scene'],
            'status': 'conditional_candidate',
            'activation_condition': '[FAKE] 仅在根状态变化经情节证据确认，且人物选择留下木片后，才考虑传播候选',
            'gates':{'require_root_confirmation':True,'require_external_action_selection':True,'require_continuity_validation':True}}
            for index, row in enumerate(changes, 1) if targets],
            'waiting': [{'source_id': ident, 'missing': ['[FAKE] 可引用的状态变化根或实际目标实体'],
                'reason': '[FAKE] 前置设计尚未提供本次传播所需的变化根或目标'} for ident in ids]
                if not changes or not targets else []}
    if stage == 'anchor_design':
        actual_scenes = _input(inputs, 'scene_design')['members']
        selected={r['scene']:r['action'] for r in _input(inputs,'scene_design')['selected_actions']}
        return {'beats': [{'scene': row['key'], 'observer': row['body']['pov'], 'object': '[FAKE] 封条',
            'action': '[FAKE] 举灯查看', 'observable': '[FAKE] 举灯查看封条边缘', 'check': '[FAKE] 观察先于接触'}
            |{'action_ref':selected[row['key']],'step_index':0,'timing':'before',
              'trigger_basis':'[FAKE] 本场人物借灯观察纸角与可见铜丝后才伸入木片'}
            for row in actual_scenes], 'selected_propagations': []}
    if stage == 'expression_design':
        return {'guidance': [{'scene': row['key'], 'observable': '[FAKE] 借灯观察封条后才伸手',
            'check': '[FAKE] 动作遵循观察和应对的先后'} for row in _input(inputs, 'scene_design')['members']]}
    from nw.materials.phase_lifecycle import writing_sources
    used = sorted(writing_sources(inputs, []) | set(ids))
    actual_scenes = _input(inputs, 'scene_design').get('members', [])
    return {'material_bindings': candidate.get('material_bindings', {}),
        'process_bindings': _process_bindings(candidate, inputs, scope),
        'method_guidance': [{'scene': row['key'], 'source_ids': used,
            'observable': '[FAKE] 沈砚借灯观察封条边角后采取行动',
            'check': '[FAKE] 核对资料要求的目标、行动、应对及实际后果'} for row in actual_scenes] if used else []}


def phase_output(provider: Any, messages: list[dict]) -> GenResult:
    data=json.loads(messages[-1]['content']);stage=data['stage'];scope=data['scope']
    # Preserve the specialized binding/POV/procedure fixtures, without pretending
    # that their local fixture construction is a production model invocation.
    sources=data.get('binding_sources') or [{'source':s['source'], 'profile':s['source']['profile'],
        'review':{'contract':{'obligations':[]}}} for s in data['sources']]
    if not sources:sources=[{'source':{'id':'fixture','fragment_id':'fixture'},'profile':'character',
                            'review':{'contract':{'obligations':[]}}}]
    fixture_scope=scope if scope!='book' or stage in ('type_selection','plot_design','bind_scope') else 'chapter'
    payload={'scope':fixture_scope,'materials':sources}
    before=list(provider.calls)
    fixture=provider.generate([{'role':'system','content':'candidate_cards fixture'},
                               {'role':'user','content':json.dumps(payload,ensure_ascii=False)}])
    provider.calls[:]=before
    provider.calls.append(messages)
    candidates=json.loads(fixture.text)['candidate_cards']
    products=project_products(stage,candidates,data['inputs'],data['sources'],scope)
    if stage == 'bind_scope' and (required := data.get('required_scene_sources')):
        independent = set(data['scene_independent_sources'])
        guides = products['method_guidance']
        for guide in guides:
            guide['source_ids'] = [ident for ident in guide['source_ids']
                                   if ident in independent or ident not in required or guide['scene'] in required[ident]]
        products['method_guidance'] = [guide for guide in guides if guide['source_ids']]
    refs=sorted(output_refs(stage,products))
    products['_uses']=[{'source_id':s['source']['id'],'operation':'[FAKE] 根据原义执行当前测试步骤并形成实际场景产物',
                       'output_refs':([next(ref for ref in refs if ref.startswith('focus:'))]
                                      if s['source']['key'].startswith('TDR_TEMPLATE_002') else
                                      ['reader_plan'] if stage=='plot_design' and ('读者情绪' in s['source']['key'] or s['source']['key'].startswith('64.1_')) else
                                      ['promise_plan'] if stage=='plot_design' and (s['source']['key'].startswith('45.1_') or s['source']['profile']=='promise_process') else refs[:1])}
                       for s in data['sources'] if refs]
    products['_excluded']=[{'source_id':s['source']['id'],'reason':'[FAKE] 当前隔离场景没有对应的状态变化或静态关系'}
                           for s in data['sources'] if not refs]
    from fake_semantic_clauses import criteria_for
    products['_criteria']=criteria_for(data,products)
    return GenResult(json.dumps({'stage':stage,'products':products},ensure_ascii=False),'complete',{},'test',{'isolated_test':True})


def assembly_output(provider: Any, messages: list[dict]) -> GenResult:
    provider.calls.append(messages)
    return GenResult(json.dumps(json.loads(messages[-1]['content'])['output_contract'],ensure_ascii=False),
                     'complete',{},'test',{'isolated_test':True})
