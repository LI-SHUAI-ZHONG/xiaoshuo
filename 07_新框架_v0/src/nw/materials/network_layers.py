"""Bind a network source's current-project use to frozen inputs and exact outputs."""

POLICY = 'network-layer-fields-v1'
FILES = {'静态网络.txt', '动态网络.txt', '锚点网络.txt'}
FIELDS = {'clause_id', 'trigger_ref', 'result_ref'}
_SCENE_OUTPUTS = {'patches', 'transitions', 'beats', 'guidance', 'selected_propagations'}

INSTRUCTION = (
    '\n标为 network_layer_fields 的资料若被本步采用，layer_application 改用 '
    '{bindings:[{clause_id,trigger_ref,result_ref}]}。每条适用原义条款的每个 output_ref 各登记一次。'
    'trigger_ref 从同一条款的 input_refs 选择实际条件，result_ref 指向同一条款交付的具体产物行或字段。'
    '例如动作引用真实前置关系或事实，并指向本候选的动作步骤或结果；'
    '锚点引用已选行动的对应步骤，并指向本节拍的可见表现；静态关系引用真实对象或前置，并指向本项目关系或成立条件。'
    '产物须属于同一来源的 _uses 所登记的候选、关系或场景。禁止用整组候选、整组节拍或整组关系代替具体引用。'
    '实际操作、可见效果、审稿判据填写于同条原义条款。'
    '按本项目现场条件设计，已隔离的旧统一代价、动作和正文策略不能作为执行依据。'
)
REVIEW_INSTRUCTION = (
    '各条 work:layer 分别核对原义及冻结的触发与结果字段。result.path 定位产物，result.value 是项目设计，'
    '以当前稿的独立引文判断该产物的可见效果是否实现。即使两个字段来自同一条款，也分别给出 layer_check。'
    '引文须处于当前视角的披露范围，不能依靠旧运行层模板或阶段产物本身证明正文效果。'
)


def uses_fields(source: dict, contract: dict, context: dict) -> bool:
    path = source['source'].get('path', '').replace('\\', '/').rsplit('/', 1)[-1]
    return (context.get('network_layer_policy') == POLICY and path in FILES
            and bool(contract.get('application_guidance')))


def _output_owner(stage: str, tokens: list[str], products: dict) -> str | None:
    from nw.materials.phase_lifecycle import CANDIDATE_SELECTION

    if len(tokens) < 2 or not tokens[1].isdigit() or not isinstance(products[tokens[0]], list):
        return None
    field, index = tokens[:2]
    row = products[field][int(index)]
    if field in _SCENE_OUTPUTS:
        return 'scene:' + row['scene']
    if field == 'method_guidance':
        return 'guidance:' + row['scene']
    if field in ('relations', 'static_bindings'):
        return 'relation:' + row['id']
    if field == 'candidates' and stage in CANDIDATE_SELECTION:
        return CANDIDATE_SELECTION[stage][3] + ':' + row['id']
    if field == 'directions':
        return 'direction:' + index
    if field == 'members':
        prefix = 'scene' if stage == 'scene_design' else 'member'
        return prefix + ':' + row['key']
    return None


def _check_anchor_trigger(tokens: list[str], trigger: str, value: dict, products: dict) -> None:
    from nw.materials.semantic_application import pointer_tokens, require

    if tokens[0] != 'beats' or not trigger.startswith('input:action_design:'):
        return
    beat = value['beats'][int(tokens[1])]
    parts = pointer_tokens(trigger.removeprefix('input:action_design:'))
    if parts[0] == 'products':
        parts = parts[1:]
    require(len(parts) >= 2 and parts[0] == 'candidates' and parts[1].isdigit(),
            'network layer anchor trigger must identify its own action')
    action = products['action_design']['products']['candidates'][int(parts[1])]
    require(action['id'] == beat.get('action_ref'), 'network layer anchor trigger must identify its own action')
    if parts[2:3] == ['steps']:
        require(parts[3:4] == [str(beat['step_index'])], 'network layer anchor trigger must identify its own action step')


def validate_bindings(criterion: dict, value: dict, stage: str, products: dict,
                      context: dict, rejected: list[str], used_outputs: list[str]) -> None:
    from nw.materials.semantic_application import has_content, input_value, output_value, pointer_tokens, require
    from nw.task_models import canonical

    application = criterion['layer_application']
    require(isinstance(application, dict) and set(application) == {'bindings'}
            and isinstance(application['bindings'], list), 'network layer needs exact project field bindings')
    clauses = {clause['id']: clause for clause in criterion['clauses'] if clause['applicability'] == 'applies'}
    missing = {(ident, ref) for ident, clause in clauses.items() for ref in clause['output_refs']}
    rejected_text = [canonical(raw)[1:-1] for raw in rejected]
    for row in application['bindings']:
        require(isinstance(row, dict) and set(row) == FIELDS and all(isinstance(v, str) for v in row.values()),
                'network layer binding needs a clause ID, trigger input and result output')
        ident, trigger, result = row['clause_id'], row['trigger_ref'], row['result_ref']
        require((ident, result) in missing, 'network layer result must cover one applied clause output once')
        clause = clauses[ident]
        require(trigger in clause['input_refs'], 'network layer trigger must be a frozen input of the same clause')
        inputs = input_value(trigger, stage, products, context)
        outputs = output_value(result, value)
        tokens = pointer_tokens(result)
        # A whole collection could bind several candidates or let an unchosen action leak into writing.
        require(len(tokens) > 1 or not isinstance(outputs, (list, dict)),
                'network layer result must identify a concrete product or field')
        owner = _output_owner(stage, tokens, value)
        member = stage == 'scene_design' and owner and owner.startswith('scene:') and 'member:' + owner[6:] in used_outputs
        require(owner is None or owner in used_outputs or member,
                'network layer result belongs to a different product than its recorded use')
        _check_anchor_trigger(tokens, trigger, value, products)
        require(has_content(inputs), 'network layer trigger needs a substantive frozen value')
        refs = (clause['operation'], clause['observable'], clause['check'], outputs)
        translated = canonical(refs)
        require(not any(raw in translated for raw in rejected_text),
                'rejected runtime field returned as an execution instruction')
        missing.remove((ident, result))
    require(not missing, 'every applied clause output needs its network layer field binding')
