"""Interpret type methods and auxiliary contracts without promoting placeholders."""


def review_auxiliary(engine, row: dict, value: dict) -> dict:
    block = row['fragment_key']
    transition = block in {'类型动态规则总表.json', '类型状态变化适配.json'}
    profile = 'type_transition' if transition else 'type_expression' if 'adaptation_id' in value else 'metadata'
    result = engine._base(row, value, profile)
    result['meaning'] = (value.get('description') or value.get('rule') or value.get('rule_scope')
                         or value.get('constraint') or value.get('action') or value.get('name')
                         or f'{block} 的来源字段、选型或核验合同')
    result['contract']['guidance'] = value
    result['boundary'] += (' 原文为候选、推导或模板的身份保留；旧source_refs只提供引用线索，'
                           '不得将旧编号当作现行网络边或从空对象、字段和数值推定故事事实。')
    if transition:
        result['contract']['method_fields'] = value
        result['contract']['applicable_type_ids'] = sorted({
            ident for field in ('type_ids', 'subtype_ids', 'hybrid_ids', 'mechanism_ids', 'structure_ids', 'style_ids')
            for ident in value.get(field, []) if isinstance(ident, str)})
        for field in ('type_ids', 'subtype_ids', 'hybrid_ids', 'mechanism_ids', 'structure_ids', 'style_ids'):
            engine._references(result, value, (field,), engine.definition_blocks)
        if block == '类型动态规则总表.json':
            effects = value.get('candidate_effects', [])
            if not isinstance(effects, list) or not effects or any(
                    not isinstance(item, dict) or not isinstance(item.get('description'), str)
                    or not item['description'].strip() for item in effects):
                result['missing'].append('原始候选效果缺少具体说明，不能只凭效果编号补成行动或状态结果')
            if not any(value.get(field) for field in ('trigger_concepts', 'trigger_entities', 'trigger_event_types',
                   'trigger_information_types', 'trigger_resource_types', 'trigger_relationship_types',
                   'trigger_foreshadowing_types', 'preconditions', 'required_context')):
                result['missing'].append('原始动态方法缺少触发对象与前置条件')
            if not value.get('selection_constraints') or not value.get('not_guaranteed'):
                result['missing'].append('原始动态方法缺少外部选择约束或非保证边界')
            engine._references(result, value, ('requires_rules', 'excludes_rules'), ('类型动态规则总表.json',))
        else:
            allowed = value.get('allowed_fields')
            if not isinstance(allowed, list) or not allowed or not all(isinstance(field, str) and field for field in allowed):
                result['missing'].append('状态适配原文未给出允许改变的字段')
            if not value.get('preconditions') or not value.get('validation_rules') or not value.get('forbidden_changes'):
                result['missing'].append('状态适配缺少前置条件、原始判据或禁止改动边界')
            result['contract']['allowed_fields'] = allowed or []
        result['contract']['requires_rules'] = value.get('requires_rules', [])
        result['contract']['excludes_rules'] = value.get('excludes_rules', [])
        result['contract']['project_completion_required'] = [
            '作者采用类型来源和具体目标对象', '前状态、原触发、人物选择、代价及失败分支',
            '同稿中的状态变化、知情边界和连续性验证']
        result['evidence_required'] = '原始条件及限制、具体目标、前后状态、行动选择和同稿证据；没有状态提取与独立核验不得接受。'
        result['state'] = 'design_ready' if value.get('status') == 'active' and not result['missing'] else 'reference'
    elif block == '类型动态候选效果.json':
        engine._references(result, value, ('rule_id',), ('类型动态规则总表.json',))
        fields = [field for field in ('target_id', 'change_field', 'candidate_value') if value.get(field) is None]
        result['missing'].append('候选效果须随所属规则选用；原文未给定：' + '、'.join(fields))
    elif block == '类型动态触发条件.json':
        engine._references(result, value, ('rule_id',), ('类型动态规则总表.json',))
        result['missing'].append('此项只定义父规则的条件，不单独产生人物行为或状态结果')
    elif 'adaptation_id' in value:
        engine._references(result, value, ('type_id',), engine.definition_blocks)
        result['missing'].append('表达适配只限定所选类型的候选参数；保留原始对象、优选、禁用及非保证边界供来源修复')
    else:
        result['contract']['use'] = ('选型、传播、去重或检查的辅助合同；不作为独立的正文事实来源。'
                                     '具体规则字段已完整保留于guidance，可与当前实现逐项比较。')
    return result
