"""Rebuild usable creative contracts while retaining invalid scoring metadata."""
from hashlib import sha256
import json
import re
import sqlite3
from nw.materials.type_adjudication import _REF_FIELDS, _TYPE_FIELDS, _original, _values

_SCORE_ONLY = re.compile(r'(?:[^\n]+ )?confidence=[^\s，]+[， ](?:超出|超出原始Schema规定的).*')
_ADAPTATION_NOTE = '表达适配只限定所选类型的候选参数；'
_PINNED_TYPE_FILES = frozenset({
    'aa0ac0359d8fb51d35a95f76cc29a652bab7dbfdbdf283a3fcf7acedefb4e582',
    'e7b7f8f2d1bb7f1af3007ed24da1d3531f767a08c14db94e79346264eafed7b0',
})
_SYNTHETIC_SCORE_FIELDS = (
    'compatibility_score', 'diversity_score', 'novelty_score', 'similarity_score',
    'risk_score', 'quality_score', 'source_support_score', 'hierarchy_validity_score',
    'static_connection_score', 'dynamic_rule_validity_score', 'expression_completeness_score',
    'scene_usefulness_score', 'information_diversity_score', 'resource_diversity_score',
    'relationship_diversity_score', 'foreshadowing_diversity_score', 'continuity_safety_score',
    'final_score',
)
_ITEM_MISLABELED_ADAPTATIONS = frozenset({'ADAPT_B_00022', 'ADAPT_B_00023', 'ADAPT_B_00024', 'ADAPT_B_00025'})
_ADAPTATION_LIST_CARRIERS = (
    'preferred_expressions', 'alternative_expressions', 'candidate_actions', 'candidate_reactions',
    'candidate_scene_uses', 'candidate_plot_uses', 'candidate_information_patterns',
    'candidate_resource_patterns', 'candidate_relationship_patterns', 'candidate_foreshadowing_patterns',
    'character_modifiers', 'identity_modifiers',
)


def original_record(db: sqlite3.Connection, row: dict) -> dict:
    data = db.execute('SELECT substr(payload,?-byte_start+1,?) FROM fragments WHERE id=?',
                      (row['byte_start'], row['byte_end']-row['byte_start'], row['fragment_id'])).fetchone()[0]
    if sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Functional reconstruction source hash mismatch')
    value = json.loads(data)
    return _original(value, [])


def _without_score(value: dict, source_ref: dict, *, strip_synthetic: bool = False) -> tuple[dict, list]:
    result = dict(value)
    quarantined = []
    score = result.get('confidence')
    invalid = isinstance(score, (int, float)) and not isinstance(score, bool) and not 0 <= score <= 1
    if invalid:
        del result['confidence']
        quarantined.append({'field': 'confidence', 'original_value': score, 'source_ref': source_ref,
                            'reason': '超范围评分不能作置信度、权重或选用依据；未填写替代值，保留其余原义及约束。'})
    if strip_synthetic:
        removed_scores = {k: result.pop(k) for k in _SYNTHETIC_SCORE_FIELDS if k in result}
        if removed_scores:
            quarantined.append({'field': 'synthetic_scores', 'original_value': removed_scores, 'source_ref': source_ref,
                                'reason': '剥离模板批量生成的合成评分浮点字段，不作为文学质量或选用权重依据。'})
    return result, quarantined


def _unit_row(db: sqlite3.Connection, cache: dict, ident: str) -> dict | None:
    key = ('unit_row', ident)
    if key not in cache:
        from nw.materials.route_catalog import _UNITS
        found = db.execute(_UNITS + ' WHERE u.id=?', (ident,)).fetchone()
        cache[key] = dict(found) if found is not None else None
    return cache[key]


def _rebuild_pinned_baseline(db: sqlite3.Connection, row: dict, result: dict, original: dict,
                             cache: dict, *, engine, stack: frozenset, proposal: bool, source_value) -> dict | None:
    pin = {k: row[k] for k in ('id', 'key', 'file_sha256', 'sha256')}
    # 1. Pinned HYBRID_GENRE records whose definition merely repeated canonical_name
    if (result['profile'] == 'type_identity' and original.get('status') == 'active'
            and original.get('type_kind') == 'HYBRID_GENRE'
            and isinstance(original.get('component_type_ids'), list)
            and len(original['component_type_ids']) >= 2):
        comp_groups = [g for g in result['contract'].get('constituents', []) if g['field'] == 'component_type_ids']
        if comp_groups and all(g['root_ids'] for g in comp_groups):
            comp_names = []
            deps = []
            for g in comp_groups:
                for cid in g['root_ids']:
                    dep = _unit_row(db, cache, cid)
                    if dep is None:
                        return None
                    rkey = ('functional_review', cid, dep['sha256'])
                    if rkey not in cache:
                        cache[rkey] = rebuild_function(db, dep, engine.review(dep), cache, engine=engine, stack=stack)
                    if not cache[rkey]['can_offer_for_design']:
                        return None
                    cval = source_value(dep)
                    comp_names.append(cval.get('canonical_name') or g['original_id'])
                    dep_pin = {k: dep[k] for k in ('id', 'key', 'fragment_id', 'locator', 'file_sha256', 'sha256')}
                    eff_dep, _ = _without_score(cval, dep_pin)
                    deps.append({'source_ref': dep_pin, 'effective_original': eff_dep, 'role': 'execution_dependency'})
            effective, quarantined = _without_score(original, pin, strip_synthetic=True)
            rebuilt_def = (
                f"复合类型「{original.get('canonical_name') or row['key']}」：融合 "
                f"{' × '.join(dict.fromkeys(comp_names))} 的世界前提与核心叙事期待，采用时须明确主次类型边界与兼容约束。"
            )
            quarantined.append({
                'field': 'definition', 'original_value': original.get('definition'), 'source_ref': pin,
                'reason': '原表定义仅复述混合类型名称；依已核实的活跃组成类型component_type_ids重建复合类型适用定义。',
            })
            effective['definition'] = rebuilt_def
            contract = {**result['contract'], 'definition': rebuilt_def, 'effective_original': effective,
                        'dependency_contracts': list({r['source_ref']['id']: r for r in deps}.values())}
            if 'evidence' in contract:
                contract['evidence'] = {k: v for k, v in contract['evidence'].items() if k != 'confidence'}
            return {
                **result, 'state': 'design_ready', 'can_offer_for_design': True,
                'meaning': rebuilt_def, 'contract': contract, 'missing': [], 'conflicts': [],
                'boundary': result['boundary'] + ' 依据已核实的组成主类型重建混合类型边界，主次权重由项目立项明确。',
                'source_retranslation': {
                    'method': 'field_isolated_functional_reconstruction',
                    'reason': '隔离超范围评分并依据已验证的组成类型恢复混合类型定义契约。',
                    'adoption_scope': 'current_project_design_and_evidence_required',
                    'original_status': original.get('status'),
                    'source_pin': pin, 'quarantined_fields': quarantined,
                    'original_state': result['state'], 'original_missing': result.get('missing', []),
                    'original_conflicts': result.get('conflicts', []),
                },
            }

    # 2. Pinned ADAPT_B_* expression adaptations (parameters dict or list carriers)
    if (result['profile'] == 'type_expression' and original.get('status') == 'active'
            and original.get('adaptation_id') and original.get('type_id') and engine is not None):
        params = original.get('parameters')
        has_carrier = (isinstance(params, dict) and bool(params)) or any(
            isinstance(original.get(k), list) and any(isinstance(v, str) and v.strip() for v in original[k])
            for k in _ADAPTATION_LIST_CARRIERS
        )
        if has_carrier and isinstance(original.get('not_guaranteed'), list):
            effective, quarantined = _without_score(original, pin, strip_synthetic=True)
            if original.get('adaptation_id') in _ITEM_MISLABELED_ADAPTATIONS and original.get('target_id') == 'CHARACTER':
                effective['target_id'] = 'ITEM'
                quarantined.append({
                    'field': 'target_id', 'original_value': 'CHARACTER', 'source_ref': pin,
                    'reason': '原表将器物外观、认主/购买归属及物品非保证项错标为CHARACTER；隔离错标对象并限定为器物/道具适配候选。',
                })
            deps = []
            for g in result['contract'].get('constituents', []):
                for cid in g['root_ids']:
                    dep = _unit_row(db, cache, cid)
                    if dep is None:
                        return None
                    rkey = ('functional_review', cid, dep['sha256'])
                    if rkey not in cache:
                        cache[rkey] = rebuild_function(db, dep, engine.review(dep), cache, engine=engine, stack=stack)
                    if not cache[rkey]['can_offer_for_design']:
                        return None
                    dep_pin = {k: dep[k] for k in ('id', 'key', 'fragment_id', 'locator', 'file_sha256', 'sha256')}
                    eff_dep, issues = _without_score(source_value(dep), dep_pin, strip_synthetic=True)
                    quarantined.extend(issues)
                    deps.append({'source_ref': dep_pin, 'effective_original': eff_dep, 'role': 'execution_dependency'})
            if deps:
                contract = {**result['contract'], 'guidance': effective, 'effective_original': effective,
                            'dependency_contracts': list({r['source_ref']['id']: r for r in deps}.values())}
                if 'evidence' in contract:
                    contract['evidence'] = {k: v for k, v in contract['evidence'].items() if k != 'confidence'}
                return {
                    **result, 'state': 'design_ready', 'can_offer_for_design': True,
                    'profile': 'type_expression', 'contract': contract, 'missing': [], 'conflicts': [],
                    'boundary': result['boundary'] + ' 仅将已核实的类型表达参数与非保证边界作为当前项目可选候选，不自动生成情节事实。',
                    'source_retranslation': {
                        'method': 'field_isolated_functional_reconstruction',
                        'reason': '隔离超范围评分并采纳完整的类型表达参数、候选与非保证边界。',
                        'adoption_scope': 'current_project_design_and_evidence_required',
                        'original_status': original.get('status'),
                        'source_pin': pin, 'quarantined_fields': quarantined,
                        'original_state': result['state'], 'original_missing': result.get('missing', []),
                        'original_conflicts': result.get('conflicts', []),
                    },
                }

    # 3. Pinned type_combination records: keep core type/mechanism/structure/style constituents strict,
    #    and strip generator-injected foreign static edges, template dynamic rules, and orphan effects.
    pinned_combo_proposal = (
        result['profile'] == 'type_combination'
        and original.get('status') == 'candidate'
        and any(isinstance(original.get(k), str) and original[k].strip()
                for k in ('combination_id', 'dynamic_combination_id', 'static_combination_id'))
    )
    proposal = proposal or pinned_combo_proposal
    if result['profile'] == 'type_combination' and (original.get('status') == 'active' or proposal) and engine is not None:
        primary = original.get('primary_type_id')
        selected_types = {primary} if isinstance(primary, str) and primary else set()
        for k in ('type_ids', 'component_type_ids', 'subtype_ids', 'hybrid_ids'):
            selected_types.update(x for x in (original.get(k) or []) if isinstance(x, str) and x)
        if not primary or not any(original.get(k) for k in ('component_type_ids', 'type_ids')):
            return None
        # Standalone GENRE_CHUANYUE without a destination world genre/subgenre violates ontology hierarchy rules.
        if primary == 'GENRE_CHUANYUE' and selected_types <= {'GENRE_CHUANYUE'}:
            return {
                **result, 'state': 'blocked', 'can_offer_for_design': False,
                'boundary': '穿越在类型本体层级规则中属于跨界进入机制，缺少目标世界主类型或子类型时不能单独作为完整世界主类型契约采用。',
            }

        constituents = result['contract'].get('constituents', [])
        type_groups = [g for g in constituents if g['field'] in _TYPE_FIELDS]
        if any(not g['root_ids'] for g in type_groups):
            return None

        effective, quarantined = _without_score(original, pin, strip_synthetic=True)
        kept_constituents = []
        deps = []

        # Verify all core type/mechanism/structure/style constituents strictly
        for g in type_groups:
            group_ok_ids = []
            for cid in g['root_ids']:
                dep = _unit_row(db, cache, cid)
                if dep is None:
                    return None
                rkey = ('functional_review', cid, dep['sha256'])
                if rkey not in cache:
                    cache[rkey] = rebuild_function(db, dep, engine.review(dep), cache, engine=engine, stack=stack)
                qualified = cache[rkey]
                if not qualified['can_offer_for_design']:
                    return None
                group_ok_ids.append(cid)
                dep_pin = {k: dep[k] for k in ('id', 'key', 'fragment_id', 'locator', 'file_sha256', 'sha256')}
                eff_dep, issues = _without_score(source_value(dep), dep_pin, strip_synthetic=True)
                quarantined.extend(issues)
                deps.extend(qualified['contract'].get('dependency_contracts', []))
                deps.append({'source_ref': dep_pin, 'effective_original': eff_dep, 'role': 'execution_dependency'})
            kept_constituents.append({**g, 'root_ids': group_ok_ids})

        # Sanitize auxiliary reference lists: static_connection_ids, dynamic_rule_ids, adaptation_ids, then effects/triggers
        ref_groups_by_field: dict[str, list[dict]] = {}
        for g in constituents:
            if g['field'] in _REF_FIELDS:
                ref_groups_by_field.setdefault(g['field'], []).append(g)

        kept_dynamic_rules: set[str] = set()
        for field in ('static_connection_ids', 'dynamic_rule_ids', 'adaptation_ids'):
            kept_symbols = []
            dropped_symbols = []
            for g in ref_groups_by_field.get(field, []):
                valid_roots = []
                for cid in g['root_ids']:
                    dep = _unit_row(db, cache, cid)
                    if dep is None:
                        continue
                    cval = source_value(dep)
                    if field == 'static_connection_ids' and cval.get('source_id') not in selected_types:
                        continue
                    rkey = ('functional_review', cid, dep['sha256'])
                    if rkey not in cache:
                        cache[rkey] = rebuild_function(db, dep, engine.review(dep), cache, engine=engine, stack=stack)
                    qualified = cache[rkey]
                    if not qualified['can_offer_for_design']:
                        continue
                    valid_roots.append(cid)
                    dep_pin = {k: dep[k] for k in ('id', 'key', 'fragment_id', 'locator', 'file_sha256', 'sha256')}
                    eff_dep, issues = _without_score(cval, dep_pin, strip_synthetic=True)
                    quarantined.extend(issues)
                    deps.extend(qualified['contract'].get('dependency_contracts', []))
                    deps.append({'source_ref': dep_pin, 'effective_original': eff_dep, 'role': 'execution_dependency'})
                if valid_roots:
                    kept_symbols.append(g['original_id'])
                    if field == 'dynamic_rule_ids':
                        kept_dynamic_rules.add(g['original_id'])
                    kept_constituents.append({**g, 'root_ids': valid_roots})
                else:
                    dropped_symbols.append(g['original_id'])
            if field in effective:
                effective[field] = kept_symbols
            if dropped_symbols:
                quarantined.append({
                    'field': field, 'original_value': dropped_symbols, 'source_ref': pin,
                    'reason': '剥离模板批处理混入的跨类型连接、未激活模板规则或无效适配引用，仅保留与本组合类型一致的已验证组成项。',
                })

        for field in ('candidate_effect_ids', 'trigger_condition_ids'):
            kept_symbols = []
            dropped_symbols = []
            for g in ref_groups_by_field.get(field, []):
                valid_roots = []
                for cid in g['root_ids']:
                    dep = _unit_row(db, cache, cid)
                    if dep is None:
                        continue
                    cval = source_value(dep)
                    ok_aux = (
                        cval.get('status') == 'active' and cval.get('rule_id') in kept_dynamic_rules
                        and (
                            dep['fragment_key'] == '类型动态候选效果.json'
                            and all(cval.get(k) not in (None, '') for k in ('target_id', 'change_field', 'candidate_value'))
                            or dep['fragment_key'] == '类型动态触发条件.json'
                            and isinstance(cval.get('field'), str) and bool(cval['field'].strip()) and 'expected_value' in cval
                        )
                    )
                    if ok_aux:
                        aux_rev = engine.review(dep)
                        ok_aux = all(isinstance(c, str) and _SCORE_ONLY.fullmatch(c) for c in aux_rev.get('conflicts', []))
                    if not ok_aux:
                        continue
                    valid_roots.append(cid)
                    dep_pin = {k: dep[k] for k in ('id', 'key', 'fragment_id', 'locator', 'file_sha256', 'sha256')}
                    eff_dep, issues = _without_score(cval, dep_pin, strip_synthetic=True)
                    quarantined.extend(issues)
                    deps.append({'source_ref': dep_pin, 'effective_original': eff_dep, 'role': 'parent_bound_auxiliary'})
                if valid_roots:
                    kept_symbols.append(g['original_id'])
                    kept_constituents.append({**g, 'root_ids': valid_roots})
                else:
                    dropped_symbols.append(g['original_id'])
            if field in effective:
                effective[field] = kept_symbols
            if dropped_symbols:
                quarantined.append({
                    'field': field, 'original_value': dropped_symbols, 'source_ref': pin,
                    'reason': '剥离不属于本组合有效动态规则的孤立候选效果或触发条件引用。',
                })

        deps_dedup = list({r['source_ref']['id']: r for r in deps}.values())
        eff_const_fields = _values(effective, _TYPE_FIELDS + tuple(_REF_FIELDS))
        contract = {
            **result['contract'],
            'constituents': kept_constituents,
            'effective_constituent_fields': eff_const_fields,
            'effective_original': effective,
            'dependency_contracts': deps_dedup,
        }
        if 'evidence' in contract:
            contract['evidence'] = {k: v for k, v in contract['evidence'].items() if k != 'confidence'}
        related_ids = sorted({cid for g in kept_constituents for cid in g['root_ids']} - {row['id']})
        return {
            **result, 'state': 'design_ready', 'can_offer_for_design': True,
            'related': related_ids, 'contract': contract, 'missing': [], 'conflicts': [],
            'boundary': '按本组合已核实的类型、机制、结构、风格与同域有效连接供项目类型适配选用；已隔离生成器混入的跨类型/模板引用与合成评分，具体触发、代价与兑现仍以当前项目设计为准。',
            'source_retranslation': {
                'method': 'field_isolated_functional_reconstruction',
                'reason': (
                    '保留完整组合的candidate身份供当前项目类型适配提案，同时剥离跨类型污染引用与合成评分并锁定同域有效组成项。'
                    if proposal else '剥离跨类型污染引用与超范围评分，保留已验证组成契约。'
                ),
                'adoption_scope': 'proposal_only' if proposal else 'current_project_design_and_evidence_required',
                'original_status': original.get('status'),
                'source_pin': pin, 'quarantined_fields': quarantined,
                'original_state': result['state'], 'original_missing': result.get('missing', []),
                'original_conflicts': result.get('conflicts', []),
            },
        }
    return None


def rebuild_function(db: sqlite3.Connection, row: dict, result: dict, cache: dict | None = None,
                     *, engine=None, stack: frozenset = frozenset()) -> dict:
    if (row['family'] not in {'types', 'type_links'} or row['kind'] != 'record'
            or row['layer'] != 'baseline' or result.get('owner_id') != row['id']
            or result.get('manual_reviewed')
            or result['profile'] not in {'type_identity','type_expression','type_combination','type_link','type_transition'}):
        return result
    cache = {} if cache is None else cache
    if row['id'] in stack:
        return {**result, 'state':'blocked', 'can_offer_for_design':False,
                'missing': [*result.get('missing', []), 'functional_dependency_cycle:' + row['key']]}
    stack = stack | {row['id']}
    def source_value(owner: dict) -> dict:
        key = owner['id'], owner['sha256']
        if key not in cache:
            cache[key] = original_record(db, owner)
        return cache[key]
    original = source_value(row)
    proposal = (result['profile']=='type_combination' and original.get('status')=='candidate'
                and original.get('selection_status')=='candidate' and isinstance(original.get('description'),str)
                and bool(original['description'].strip()))
    if row.get('file_sha256') in _PINNED_TYPE_FILES:
        rebuilt_pinned = _rebuild_pinned_baseline(
            db, row, result, original, cache, engine=engine, stack=stack, proposal=proposal, source_value=source_value
        )
        if rebuilt_pinned is not None:
            return rebuilt_pinned
    if original.get('status') != 'active' and not proposal:
        return result
    missing = result.get('missing', [])
    def useful_list(value: object, *, empty: bool=False) -> bool:
        return isinstance(value,list) and (bool(value) or empty) and all(isinstance(v,str) and v.strip()
            and v.strip() not in {'无','暂无','待补','未知'} for v in value)
    adaptation = bool(original.get('adaptation_id') and original.get('type_id')
        and useful_list(original.get('preferred_expressions')) and useful_list(original.get('not_guaranteed'))
        and useful_list(original.get('avoid_expressions'),empty=True))
    if (any(not isinstance(c, str) or not _SCORE_ONLY.fullmatch(c) for c in result.get('conflicts', []))
            or any(not adaptation or not m.startswith(_ADAPTATION_NOTE) for m in missing)):
        return result
    pin = {k: row[k] for k in ('id', 'key', 'file_sha256', 'sha256')}
    effective, quarantined = _without_score(original, pin)
    dependencies = []
    dependency_issues = []
    positive = {i for group in result['contract'].get('constituents', [])
                if group['field'] != 'excludes_rules' for i in group['root_ids']}
    for ident in sorted({i for group in result['contract'].get('constituents', []) for i in group['root_ids']}):
        dependency = _unit_row(db, cache, ident)
        if dependency is None:
            return result
        dependency_pin = {k: dependency[k] for k in ('id', 'key', 'fragment_id', 'locator', 'file_sha256', 'sha256')}
        source = source_value(dependency)
        value, issues = _without_score(source, dependency_pin)
        quarantined.extend(issues)
        parent_bound = (source.get('status') == 'active' and source.get('rule_id') in original.get('dynamic_rule_ids', [])
            and (dependency['fragment_key'] == '类型动态候选效果.json' and all(
                source.get(k) is not None and source.get(k) != '' for k in ('target_id','change_field','candidate_value'))
                or dependency['fragment_key'] == '类型动态触发条件.json' and isinstance(source.get('field'),str)
                and bool(source['field'].strip()) and 'expected_value' in source))
        if parent_bound and engine is not None:
            auxiliary = engine.review(dependency)
            parent_bound = all(isinstance(c,str) and _SCORE_ONLY.fullmatch(c) for c in auxiliary.get('conflicts', []))
        if engine is not None and ident in positive and not parent_bound:
            review_key = 'functional_review', ident, dependency['sha256']
            if review_key not in cache:
                cache[review_key] = rebuild_function(db, dependency, engine.review(dependency), cache,
                                                     engine=engine, stack=stack)
            qualified = cache[review_key]
            if not qualified['can_offer_for_design']:
                dependency_issues.append('constituent_not_executable:' + dependency['fragment_key'] + ':' + dependency['key'])
            dependencies.extend(qualified['contract'].get('dependency_contracts', []))
        dependencies.append({'source_ref': dependency_pin, 'effective_original': value,
                             'role':'parent_bound_auxiliary' if parent_bound else
                                    'execution_dependency' if ident in positive else 'exclusion_boundary'})
    dependencies = list({r['source_ref']['id']:r for r in dependencies}.values())
    contract = {**result['contract'], 'dependency_contracts': dependencies}
    if dependency_issues:
        return {**result, 'state':'blocked', 'can_offer_for_design':False, 'contract':contract,
                'missing': [*result.get('missing', []), *dependency_issues]}
    if not quarantined and not adaptation and not proposal:
        return {**result, 'contract': contract}
    if 'evidence' in contract:
        contract['evidence'] = {k: v for k, v in contract['evidence'].items() if k != 'confidence' or 'confidence' in effective}
    if 'guidance' in contract:
        contract['guidance'] = effective
    contract['effective_original'] = effective
    if result.get('source_repair'):
        contract['effective_original'] = {**effective, **contract.get('effective_constituent_fields',{})}
    return {**result, 'state': 'design_ready', 'can_offer_for_design': True,
            'profile': 'type_expression' if adaptation else result['profile'],
            'contract': contract, 'missing': [], 'conflicts': [],
            'boundary': result['boundary'] + ' 无效评分仅留缺陷记录；当前候选须按完整有效字段设计并经作者采用及独立效果核验。',
            'source_retranslation': {'method': 'field_isolated_functional_reconstruction',
                'reason': ('保留完整组合的candidate身份供当前项目提案，不改成active；所有确切依赖和限制继续核验。'
                    if proposal else '隔离非创作语义的错误评分；适配的优选、禁用及非保证要求作为条件化方法保留，不改写原始记录。'),
                'adoption_scope':'proposal_only' if proposal else 'current_project_design_and_evidence_required',
                'original_status':original.get('status'),
                'source_pin': pin, 'quarantined_fields': quarantined,
                'original_state': result['state'], 'original_missing': missing,
                'original_conflicts': result.get('conflicts', [])}}
