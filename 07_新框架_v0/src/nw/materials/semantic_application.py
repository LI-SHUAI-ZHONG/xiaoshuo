"""Validate source clauses against real frozen stage inputs and output paths.

These checks establish traceability and coverage, never literary success. Legacy
stages are unchanged unless they supply _criteria or explicitly require semantics.
"""
from copy import deepcopy
import re

from nw.materials.phase_routes import ORDER, product_ref
from nw.materials.source_semantics import compile_semantics, _layer_json,READABLE_POLICIES
from nw.task_models import canonical, content_sha256

CRITERIA_FIELDS = {'source_id', 'contract_sha256', 'clauses', 'layer_application'}
CLAUSE_FIELDS = {'id', 'applicability', 'reason', 'input_refs', 'output_refs',
                 'operation', 'observable', 'check', 'consumer'}
_META = {'id', 'key', 'status', 'label', 'tags', 'profile', 'sha256', 'source_id',
         'source_ids', 'rule_id', 'contract_sha256', 'policy', 'task_id', 'ref'}
_GENERIC = {'pass', 'done', 'ready', 'completed', 'candidate', 'planned', 'selected',
            '已应用', '已使用', '已完成', '按原文要求逐条执行', '按流程执行'}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError('MATERIAL_STAGE: semantic ' + reason)


def pointer_tokens(pointer: str) -> list[str]:
    require(isinstance(pointer, str) and pointer.startswith('/'), 'expected an absolute JSON pointer')
    raw = pointer[1:].split('/')
    require(all(not re.search(r'~(?![01])', token) for token in raw), 'invalid JSON pointer escape')
    return [token.replace('~1', '/').replace('~0', '~') for token in raw]


def resolve_pointer(value: object, pointer: str) -> object:
    current = value
    for token in pointer_tokens(pointer):
        if isinstance(current, dict):
            require(token in current, 'absent JSON pointer ' + pointer)
            current = current[token]
        elif isinstance(current, list):
            require(bool(re.fullmatch(r'0|[1-9]\d*', token)) and int(token) < len(current),
                    'absent array pointer ' + pointer)
            current = current[int(token)]
        else:
            require(False, 'pointer traverses a scalar ' + pointer)
    return current


def has_content(value: object) -> bool:
    if isinstance(value, dict):
        return any(has_content(item) for key, item in value.items()
                   if key not in _META and not key.startswith('_'))
    if isinstance(value, list):
        return any(has_content(item) for item in value)
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().casefold() not in _GENERIC
    return value is not None


def concrete(text: object) -> bool:
    if not isinstance(text, str):
        return False
    value = re.sub(r'^(?:\[FAKE[^\]]*\]\s*)+', '', text.strip())
    compact = ''.join(value.split()); lower = compact.casefold()
    if len(compact) < 8 or lower in _GENERIC or '<填写' in value:
        return False
    if lower.startswith(('read_', 'readout_', 'readsource', 'readoriginal', 'source_sha', 'source_state')):
        return False
    if re.match(r'^(?:读取|回读|记录|检查|核对).*(?:哈希|元数据|来源状态|资料状态)', value):
        return False
    return bool(compact.replace('已应用', '').replace('已使用', '').replace('已完成', '').strip('，。:：;； '))


def contracts_for(sources: list[dict], context: dict) -> dict[str, dict]:
    supplied = context.get('semantic_contracts')
    if supplied is None:
        contracts = [compile_semantics(source) for source in sources]
    else:
        contracts = list(supplied.values()) if isinstance(supplied, dict) else supplied
        require(isinstance(contracts, list), 'frozen contracts must be a list or source-id map')
    result = {}
    for contract in contracts:
        require(isinstance(contract, dict) and contract.get('policy') in READABLE_POLICIES
                and isinstance(contract.get('source_id'), str), 'invalid frozen source contract')
        if context.get('semantic_policy'):
            require(contract['policy']==context['semantic_policy'],'frozen semantic policy version differs from this session')
        require(content_sha256({k: v for k, v in contract.items() if k != 'sha256'}) == contract.get('sha256'),
                'frozen source contract hash mismatch')
        require(contract['source_id'] not in result, 'duplicate frozen source contract')
        result[contract['source_id']] = contract
    for source in sources:
        ref = source['source']; contract = result.get(ref['id'])
        require(contract is not None, 'missing frozen source contract')
        for key in ('sha256', 'file_sha256'):
            pinned = contract.get('source_ref', {}).get(key)
            require(pinned is None or key not in ref or pinned == ref[key], 'source pin differs from frozen contract')
    return result


def unresolved_issues(contract: dict, ident: str,review: dict | None=None) -> list[dict]:
    items=[item for item in contract.get('source_issues', {}).get('compilation', [])
            if isinstance(item, dict) and ident in item.get('obligation_ids', [])
            and (item.get('severity') == 'repair' or any(word in item.get('kind', '')
                 for word in ('missing', 'incomplete', 'uninterpreted', 'unclassified')))]
    if review is not None:
        field=next(o for o in contract['obligations'] if o['id']==ident)['source_ref']
        scope=next((c for c in review['clause_reviews'] if c['text_start']==field['text_start']
            and c['text_end']==field['text_end'] and c['sha256']==field['clause_sha256']),None)
        if scope is not None and scope['status']=='reviewed' and scope.get('semantic_role') in {
                'purpose','definition','condition','operation','prohibition','exception','effect','check','dependency','parameter'}:
            items=[i for i in items if i['kind'] not in {'unclassified_original_field',
                'unclassified_original_section','uninterpreted_original_text'}]
        if scope is None or scope['status']=='needs_review':
            items.append({'kind':'binding_interpretation_needs_review','obligation_ids':[ident],
                'severity':'review','reason':scope['reason'] if scope else '此原句尚无用途审核'})
    return items


def input_value(reference: str, stage: str, products: dict, context: dict) -> object:
    require(isinstance(reference, str), 'input reference must be text')
    if reference.startswith('brief:'):
        return resolve_pointer(context.get('brief', {}), reference[6:])
    match = re.fullmatch(r'(input|approved|fact):(.+):(/.*)', reference)
    require(match is not None, 'invalid input reference ' + reference)
    family, ident, pointer = match.groups(); tokens = pointer_tokens(pointer)
    require(not any(t.startswith('_') for t in tokens) and not any(t in {'sha256', 'file_sha256', 'ref'} for t in tokens),
            'input metadata is not a project method input')
    if family == 'input':
        require(ident in products, 'input stage does not exist')
        allowed = context.get('allowed_input_stages')
        require(allowed is None or ident in allowed, 'input stage was not sent to this step')
        require(stage not in ORDER or ident not in ORDER or ORDER.index(ident) < ORDER.index(stage),
                'input stage is not upstream')
        try:product_ref(products[ident])
        except ValueError as exc:
            raise ValueError('MATERIAL_STAGE: semantic '+str(exc)) from exc
        body = products[ident]['products']
        return resolve_pointer({'products': body}, pointer) if tokens[0] == 'products' else resolve_pointer(body, pointer)
    if family == 'approved':
        card = next((r for r in context.get('approved_cards', []) if r.get('card_id', r.get('id')) == ident), None)
        require(card is not None and tokens[0] == 'body', 'approved input must address a real card body')
        return resolve_pointer(card, pointer)
    require(bool(re.fullmatch(r'0|[1-9]\d*', ident)), 'fact index must be a nonnegative integer')
    facts = context.get('accepted_state', [])
    require(int(ident) < len(facts), 'fact input does not exist in the current view')
    return resolve_pointer(facts[int(ident)], pointer)


def output_value(reference: str, value: dict) -> object:
    tokens = pointer_tokens(reference)
    require(not any(token.startswith('_') for token in tokens) and tokens[-1] not in _META,
            'output reference is identity, status or self proof')
    result = resolve_pointer(value, reference)
    require(has_content(result), 'output reference has no actual design content')
    return result


def _strings(values: object, *, nonempty: bool = False) -> bool:
    return (isinstance(values, list) and (bool(values) or not nonempty)
            and all(isinstance(v, str) and v.strip() for v in values) and len(values) == len(set(values)))


def _rejected_values(source: dict) -> list[str]:
    values = []
    def leaves(value: object) -> None:
        if isinstance(value, str) and len(''.join(value.split())) >= 8:
            values.append(value)
        elif isinstance(value, dict):
            for item in value.values(): leaves(item)
        elif isinstance(value, list):
            for item in value: leaves(item)
    for layer in source.get('application_layers', []):
        raw = _layer_json(layer.get('text', ''))
        for rejected in layer.get('rejected_fields', []):
            target = raw
            if isinstance(raw, dict) and type(rejected.get('binding')) is int:
                bindings = raw.get('runtime_calling_layer', [])
                target = bindings[rejected['binding']] if 0 <= rejected['binding'] < len(bindings) else None
            try: leaves(resolve_pointer(target, '/' + str(rejected.get('field', '')).lstrip('/')))
            except ValueError: continue
    return values


def _validate_layer(application: object, source: dict, contract: dict) -> None:
    layers = contract.get('application_guidance') or source.get('application_layers')
    if not layers:
        require(application == {}, 'a project application cannot invent an absent runtime layer')
        return
    require(isinstance(application, dict) and set(application) == {'trigger', 'operation', 'result', 'verification'}
            and all(concrete(v) for v in application.values()) and len(set(application.values())) == 4,
            'layer application needs distinct actual trigger, operation, result and verification')
    forbidden = _rejected_values(source)
    require(not any(value in text for value in forbidden for text in application.values()),
            'rejected runtime field returned as an execution instruction')


def validate_semantic_applications(stage: str, value: dict, products: dict,
                                   sources: list[dict], context: dict) -> None:
    """Require exact clause coverage and real bindings when semantics is enabled."""
    if not context.get('require_semantics') and '_criteria' not in value:
        return
    require(isinstance(value, dict) and isinstance(value.get('_uses'), list), 'actual source uses are required')
    uses = [r.get('source_id') for r in value['_uses'] if isinstance(r, dict)]
    require(len(uses) == len(value['_uses']) and all(isinstance(i, str) for i in uses)
            and len(set(uses)) == len(uses), 'actual source uses must be unique')
    uses_by_id = {row['source_id']: row for row in value['_uses']}
    require(isinstance(value.get('_criteria'), list), 'missing per-source criteria')
    by_id = {s['source']['id']: s for s in sources}; contracts = contracts_for(sources, context); seen = set()
    for row in value['_criteria']:
        require(isinstance(row, dict) and set(row) == CRITERIA_FIELDS and row['source_id'] in set(uses)-seen
                and row['source_id'] in by_id, 'criteria source is missing, duplicated or unrequested')
        ident = row['source_id']; seen.add(ident); contract = contracts[ident]
        from nw.materials.binding_reviews import validate_execution_binding
        binding_review=validate_execution_binding(stage,by_id[ident],context)
        require(row['contract_sha256'] == contract['sha256'], 'criteria source contract hash changed')
        obligations = {r['id']: r for r in contract['obligations']}
        require(bool(obligations), 'navigation-only source cannot be counted as an applied method')
        require(isinstance(row['clauses'], list), 'source clauses must be a list'); covered = set()
        for clause in row['clauses']:
            require(isinstance(clause, dict) and set(clause) == CLAUSE_FIELDS and clause['id'] in obligations.keys()-covered,
                    'original clause is missing, duplicated or invented')
            covered.add(clause['id']); mode = clause['applicability']; issues = unresolved_issues(contract, clause['id'],binding_review)
            if binding_review:
                field=obligations[clause['id']]['source_ref']
                scope=next((c for c in binding_review['clause_reviews'] if c['text_start']==field['text_start']
                    and c['text_end']==field['text_end'] and c['sha256']==field['clause_sha256']),None)
                require(scope is not None and scope['status']!='needs_review' or mode=='source_unresolved',
                        'clause meaning needs review; preserve source_unresolved instead of guessing nonapplicability')
                require(not scope or scope['status']!='not_project_instruction' or mode=='not_applicable',
                        'source metadata is not a project instruction or a prose effect')
            require(mode in ('applies', 'not_applicable', 'source_unresolved'), 'invalid clause applicability')
            require(isinstance(clause['reason'], str) and clause['reason'].strip(), 'clause decision needs an actual reason')
            require(_strings(clause['input_refs']) and _strings(clause['output_refs']), 'clause references must be unique text lists')
            consumer = clause['consumer']
            require(consumer in ('writer', 'review', 'acceptance') or consumer in ORDER and stage in ORDER
                    and ORDER.index(consumer) > ORDER.index(stage), 'clause consumer must be a downstream stage')
            for reference in clause['input_refs']: input_value(reference, stage, products, context)
            if mode == 'applies':
                require(not issues, 'unresolved source clause cannot be filled with invented project meaning')
                require(bool(clause['input_refs']) and bool(clause['output_refs']), 'applied clause needs actual inputs and outputs')
                require(all(concrete(clause[k]) for k in ('operation', 'observable', 'check'))
                        and len({clause[k].strip() for k in ('operation', 'observable', 'check')}) == 3,
                        'applied clause needs concrete operation, observable and check')
                for reference in clause['output_refs']: output_value(reference, value)
            else:
                require(not clause['output_refs'], 'unapplied clause cannot claim completed outputs')
                require(all(isinstance(clause[k], str) for k in ('operation', 'observable', 'check')), 'clause explanations must be text')
                if mode == 'source_unresolved':
                    require(bool(issues) and (clause['id'] in clause['reason'] or any(i.get('kind', '') in clause['reason'] for i in issues)),
                            'source_unresolved must cite the compiler issue for this exact clause')
                else:
                    reason = clause['reason']
                    require(concrete(reason) and any(word in reason for word in
                        ('本场', '本项目', '当前任务', '本次任务', '所选', '项目中', '实际输入', '当前场景', '本章')),
                        'nonapplicability needs a current task reason, not source qualification')
                    if any(word in reason for word in ('template', 'blocked', 'reference', '模板身份', '来源资格')):
                        require(any(word in reason for word in ('没有', '无需', '不存在', '未选', '未发生', '不涉及', '不需要', '未触发', '未激活')),
                                'source qualification alone is not task nonapplicability')
        require(covered == obligations.keys(), 'every original source clause needs an applicability decision')
        require(any(c['applicability']=='applies' for c in row['clauses']),
                'used method needs an actual applied clause; unresolved or inapplicable is not execution')
        from nw.materials.network_layers import uses_fields, validate_bindings
        if uses_fields(by_id[ident], contract, context):
            validate_bindings(row, value, stage, products, context, _rejected_values(by_id[ident]),
                              uses_by_id[ident]['output_refs'])
        else:
            _validate_layer(row['layer_application'], by_id[ident], contract)
    require(seen == set(uses), 'every actually used source needs its criteria contract')


def make_semantic_checks(session: dict, scene: str, ids: dict | None = None) -> list[dict]:
    from nw.materials.semantic_checks import make_semantic_checks as make
    return make(session, scene, ids)
