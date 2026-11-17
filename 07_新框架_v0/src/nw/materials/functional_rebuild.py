"""Rebuild usable creative contracts while retaining invalid scoring metadata."""
from hashlib import sha256
import json
import re
import sqlite3
from nw.materials.type_adjudication import _original

_SCORE_ONLY = re.compile(r'(?:[^\n]+ )?confidence=[^\s，]+[， ](?:超出|超出原始Schema规定的).*')
_ADAPTATION_NOTE = '表达适配只限定所选类型的候选参数；'


def original_record(db: sqlite3.Connection, row: dict) -> dict:
    data = db.execute('SELECT substr(payload,?-byte_start+1,?) FROM fragments WHERE id=?',
                      (row['byte_start'], row['byte_end']-row['byte_start'], row['fragment_id'])).fetchone()[0]
    if sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Functional reconstruction source hash mismatch')
    value = json.loads(data)
    return _original(value, [])


def _without_score(value: dict, source_ref: dict) -> tuple[dict, list]:
    result = dict(value)
    score = result.get('confidence')
    invalid = isinstance(score, (int, float)) and not isinstance(score, bool) and not 0 <= score <= 1
    if not invalid:
        return result, []
    del result['confidence']
    return result, [{'field': 'confidence', 'original_value': score, 'source_ref': source_ref,
                     'reason': '超范围评分不能作置信度、权重或选用依据；未填写替代值，保留其余原义及约束。'}]


def rebuild_function(db: sqlite3.Connection, row: dict, result: dict, cache: dict | None = None,
                     *, engine=None, stack: frozenset = frozenset()) -> dict:
    if (row['family'] not in {'types', 'type_links'} or row['kind'] != 'record'
            or row['layer'] != 'baseline' or result.get('owner_id') != row['id']
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
    from nw.materials.route_catalog import _UNITS
    pin = {k: row[k] for k in ('id', 'key', 'file_sha256', 'sha256')}
    effective, quarantined = _without_score(original, pin)
    dependencies = []
    dependency_issues = []
    positive = {i for group in result['contract'].get('constituents', [])
                if group['field'] != 'excludes_rules' for i in group['root_ids']}
    for ident in sorted({i for group in result['contract'].get('constituents', []) for i in group['root_ids']}):
        found = db.execute(_UNITS + ' WHERE u.id=?', (ident,)).fetchone()
        if found is None:
            return result
        dependency = dict(found)
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
