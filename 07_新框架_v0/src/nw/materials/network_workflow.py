"""Prepare actual static relationships before admitting derived dynamic methods."""
from collections import Counter, defaultdict
from pathlib import Path
import unicodedata

from nw.materials.template_support import product


POLICY = 'network-prerequisites-v1'
EARLY_POLICY = 'network-early-prerequisites-v1'
DYNAMIC_PROFILES = {'dynamic_relation', 'dynamic_binding'}
STATIC_PROFILES = {'static_relation', 'static_binding'}
EARLY_STAGES = ('type_adaptation', 'world_design', 'character_design', 'static_relations', 'plot_design')


def _name(value: str) -> str:
    return unicodedata.normalize('NFKC', value).strip().casefold()


def resolve_type_scope(workspace: Path, selection: dict, *, families: dict[str, str] | None = None) -> dict[str, list[str]]:
    """Use agreed original names and parent IDs for the actual type selections."""
    from nw.materials.type_adjudication import TYPE_TABLE
    from nw.materials.type_sources import MAIN_TYPES, SUBTYPES, original_type_records

    by_id = defaultdict(set)
    for rows in original_type_records(workspace, (TYPE_TABLE, MAIN_TYPES, SUBTYPES)).values():
        for _, value, duplicates in rows:
            ident, label = value.get('type_id'), value.get('canonical_name')
            kind, parent = value.get('type_kind'), value.get('parent_id')
            if (not duplicates and isinstance(ident, str) and isinstance(label, str) and label.strip()
                    and isinstance(kind, str) and (parent is None or isinstance(parent, str))):
                by_id[ident].add((kind, label, parent))
    agreed = {ident: next(iter(rows)) for ident, rows in by_id.items() if len(rows) == 1}
    result = {}
    for choice in selection.get('selection', []):
        ident = choice['id']
        if ident not in agreed:
            continue
        kind, label, parent = agreed[ident]
        if kind not in ('GENRE', 'SUBGENRE'):
            continue
        labels = {label}
        if kind == 'SUBGENRE' and parent in agreed and agreed[parent][0] == 'GENRE':
            labels.add(agreed[parent][1])
            if families is not None:
                families[ident] = parent
        elif kind == 'GENRE' and families is not None:
            families[ident] = ident
        result[ident] = sorted(labels)
    return result


def type_matches(valid_types: object, scope: dict[str, list[str]]) -> bool:
    if valid_types is None or valid_types == []:
        return True
    if not isinstance(valid_types, list) or not all(isinstance(v, str) and v.strip() for v in valid_types):
        return False
    allowed = {_name(v) for v in valid_types}
    return any(_name(name) in allowed for names in scope.values() for name in names)


def bound_relations(products: dict) -> dict[str, dict[str, dict]]:
    """Only relations with a corresponding recorded source use can serve as inputs."""
    result = defaultdict(dict)
    for stage, field in (('static_relations', 'relations'), ('static_relations_basis', 'relations'),
                         ('plot_design', 'static_bindings')):
        value = product(products, stage)
        uses = defaultdict(set)
        for use in value.get('_uses', []):
            for ref in use['output_refs']:
                uses[ref].add(use['source_id'])
        for index, row in enumerate(value.get(field, [])):
            for ident in uses['relation:' + row['id']]:
                if field == 'relations' or row.get('source_id') == ident:
                    result[ident][f'input:{stage}:/{field}/{index}'] = row
    return dict(result)


def prepared_plot_source(source: dict, context: dict) -> bool:
    ref = source['source']
    return (context.get('network_prerequisite_policy') == POLICY and ref['profile'] in STATIC_PROFILES
            and ref['id'] in context.get('prepared_static_sources', []))


def prepared_static_source(source: dict, stage: str, context: dict) -> bool:
    if stage == 'plot_design':
        return prepared_plot_source(source, context)
    ref = source['source']
    return (stage == 'static_relations' and context.get('early_network_policy') == EARLY_POLICY
            and context.get('network_prerequisite_policy') == POLICY and ref['profile'] in STATIC_PROFILES
            and ref['id'] in context.get('early_static_sources', []))


def _adopted(rule: dict, bound: dict) -> bool:
    return any(row['relation'] == rule['relation'] for row in bound.get(rule['static_id'], {}).values())


def _prepare_for_plot(authored: dict, rules: dict, context: dict, rows: dict) -> dict[str, str]:
    usages = {ident: text for pool in authored.values() for ident, text in pool.items()}
    usages.update(authored.get('plot_design', {}))
    usages.update(authored.get('static_relations', {}))
    linked = defaultdict(list)
    for ident in authored.get('plot_design', {}):
        rule = rules.get(ident)
        if not rule or not rule['derived'] or rows[ident]['state'] != 'design_ready':
            continue
        basis = rule['static_id']
        if (basis in usages and rows[basis]['state'] == 'design_ready'
                and rows[basis].get('profile') in STATIC_PROFILES
                and type_matches(rule['valid_types'], context.get('network_type_scope', {}))):
            linked[basis].append(rule['key'])
    return {basis: ('为剧情规则' + '、'.join(sorted(keys)) + '核对关系是否能在本步先落实。'
                    '仅在已有世界或人物卡确能分别支撑两个端点及成立条件时建立关系；'
                    '需要剧情产物时留待补设计。原步用法：' + usages[basis]) for basis, keys in linked.items()}


def same_stage_rules(authored: dict, rules: dict, context: dict, rows: dict) -> dict[str, dict]:
    from nw.materials.network_followup import POLICY as FOLLOWUP_POLICY

    if context.get('same_stage_network_policy') != FOLLOWUP_POLICY:
        return {}
    step = authored.get('static_relations', {})
    return {ident: rule for ident in step if (rule := rules.get(ident)) and rule['derived']
            and rows[ident]['state'] == 'design_ready' and rule['static_id'] in step
            and rows[rule['static_id']]['state'] == 'design_ready'
            and rows[rule['static_id']].get('profile') in STATIC_PROFILES
            and type_matches(rule['valid_types'], context.get('network_type_scope', {}))}


def _prepare_for_followup(authored: dict, rules: dict, context: dict, rows: dict) -> dict[str, str]:
    keys = defaultdict(list)
    for rule in same_stage_rules(authored, rules, context, rows).values():
        keys[rule['static_id']].append(rule['key'])
    step = authored.get('static_relations', {})
    return {basis: ('当项目内关系已成立时，为本步后半的' + '、'.join(sorted(names)) + '保存真实双方及成立条件。'
                    '若缺少真实端点或条件，不登记此关系。原步用法：' + step[basis]) for basis, names in keys.items()}


def early_waiting(stage: str, authored: dict, rules: dict, products: dict, context: dict, rows: dict) -> dict:
    if context.get('early_network_policy') != EARLY_POLICY or stage not in EARLY_STAGES:
        return {}
    bound = bound_relations(products)
    counts = Counter()
    examples = []
    for ident in authored.get(stage, {}):
        rule = rules.get(ident)
        if (not rule or not rule['derived'] or rows[ident]['state'] != 'design_ready'
                or not type_matches(rule['valid_types'], context.get('network_type_scope', {})) or _adopted(rule, bound)):
            continue
        basis = rows.get(rule['static_id'])
        if stage == 'type_adaptation' and _type_network_active(context):
            decision, missing = _type_network_decision(ident, rule, products, context)
            if decision is not None:
                continue
            reason = '等待' + '、'.join(missing)
        elif stage == 'world_design' and _world_network_active(context):
            decision, missing = world_network_decision(ident, rule['key'], rule['valid_types'], products, context)
            if decision is not None:
                continue
            reason = '等待' + '、'.join(missing)
        elif not basis or basis['state'] != 'design_ready':
            reason = '缺少具有制作资格的唯一静网依据'
        elif stage == 'static_relations':
            reason = '等待独立保存的静网关系，本轮产物不能自证'
        elif stage == 'plot_design':
            reason = '上游未落实本项目的对应静网关系'
        else:
            reason = '本步早于静网关系阶段，等待可验证的实际前置'
        counts[reason] += 1
        if len(examples) < 6:
            examples.append({'key': rule['key'], 'static_key': basis['key'] if basis else None, 'reason': reason})
    return {'counts': dict(counts), 'examples': examples} if counts else {}


def _type_network_active(context: dict) -> bool:
    from nw.materials.type_network import POLICY as TYPE_NETWORK_POLICY

    return context.get('type_network_policy') == TYPE_NETWORK_POLICY


def _type_network_decision(ident: str, rule: dict, products: dict, context: dict) -> tuple[dict | None, list[str]]:
    from nw.materials.type_network import availability

    if ident not in context.get('type_network_bases', {}):
        return None, ['具有制作资格且可核对的本步静网原条']
    return availability(rule['key'], rule['valid_types'], products, context)


def _world_network_active(context: dict) -> bool:
    from nw.materials.world_network import POLICY as WORLD_NETWORK_POLICY

    return context.get('world_network_policy') == WORLD_NETWORK_POLICY


def world_network_decision(ident: str, key: str, valid_types: object,
                           products: dict, context: dict) -> tuple[dict | None, list[str]]:
    from nw.materials.world_network import RULES, availability

    if key not in RULES:
        return None, ['逐条核对的世界设计前置']
    if ident not in context.get('world_network_bases', {}):
        return None, ['具有制作资格且可核对的本步静网原条']
    return availability(key, valid_types, products, context)


def _static_inputs(rules: dict, authored: dict, scope: dict, bound: dict, rows: dict) -> dict[str, str]:
    uses = {ident: text for pool in authored.values() for ident, text in pool.items()}
    linked = defaultdict(list)
    same_step_uses = {}
    after_plot = False
    for stage, pool in authored.items():
        if after_plot:
            for ident in pool.keys() & rules.keys():
                rule = rules[ident]
                ref = rule['static_id']
                if (ref in uses and rows[ref]['state'] == 'design_ready' and rows[ident]['state'] == 'design_ready'
                        and type_matches(rule['valid_types'], scope)
                        and not _adopted(rule, bound)):
                    link = rule['key']
                    if link not in linked[ref]:
                        linked[ref].append(link)
                    if ref in pool:
                        same_step_uses.setdefault(ref, pool[ref])
        after_plot = after_plot or stage == 'plot_design'
    return {ref: ('为后续规则' + '、'.join(sorted(keys)) + '准备实际静态关系。'
                  '仅在人物、对象和剧情条件确有对应时，在static_bindings记录真实双方、原关系类型和成立条件。'
                  '原步已写的适用情境：' + same_step_uses.get(ref, uses[ref])) for ref, keys in linked.items()}


def step_sources(stage: str, authored: dict, rules: dict, products: dict, context: dict,
                 rows: dict) -> tuple[dict[str, str], dict[str, str]]:
    scope = context.get('network_type_scope', {})
    bound = bound_relations(products)
    pool = {}
    for ident, use in authored[stage].items():
        rule = rules.get(ident)
        if rule is None or (type_matches(rule['valid_types'], scope) and
                (not rule['derived'] or _adopted(rule, bound))):
            pool[ident] = use
        elif stage == 'type_adaptation' and _type_network_active(context):
            decision, _ = _type_network_decision(ident, rule, products, context)
            if decision is not None:
                pool[ident] = use
        elif stage == 'world_design' and _world_network_active(context):
            decision, _ = world_network_decision(ident, rule['key'], rule['valid_types'], products, context)
            if decision is not None:
                pool[ident] = use
    if stage == 'static_relations' and context.get('early_network_policy') == EARLY_POLICY:
        prepared = _prepare_for_plot(authored, rules, context, rows)
        for basis, hint in _prepare_for_followup(authored, rules, context, rows).items():
            prepared[basis] = '\n'.join(text for text in (prepared.get(basis), hint) if text)
    else:
        prepared = _static_inputs(rules, authored, scope, bound, rows) if stage == 'plot_design' else {}
    return pool, prepared
