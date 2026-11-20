"""Prepare actual static relationships before admitting derived dynamic methods."""
from collections import defaultdict
from pathlib import Path
import unicodedata

from nw.materials.template_support import product


POLICY = 'network-prerequisites-v1'
DYNAMIC_PROFILES = {'dynamic_relation', 'dynamic_binding'}
STATIC_PROFILES = {'static_relation', 'static_binding'}


def _name(value: str) -> str:
    return unicodedata.normalize('NFKC', value).strip().casefold()


def resolve_type_scope(workspace: Path, selection: dict) -> dict[str, list[str]]:
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
    for stage, field in (('static_relations', 'relations'), ('plot_design', 'static_bindings')):
        value = product(products, stage)
        uses = defaultdict(set)
        for use in value.get('_uses', []):
            for ref in use['output_refs']:
                uses[ref].add(use['source_id'])
        for index, row in enumerate(value.get(field, [])):
            for ident in uses['relation:' + row['id']]:
                if stage == 'static_relations' or row.get('source_id') == ident:
                    result[ident][f'input:{stage}:/{field}/{index}'] = row
    return dict(result)


def prepared_plot_source(source: dict, context: dict) -> bool:
    ref = source['source']
    return (context.get('network_prerequisite_policy') == POLICY and ref['profile'] in STATIC_PROFILES
            and ref['id'] in context.get('prepared_static_sources', []))


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
                        and not any(r['relation'] == rule['relation'] for r in bound.get(ref, {}).values())):
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
                (not rule['derived'] or any(row['relation'] == rule['relation']
                    for row in bound.get(rule['static_id'], {}).values()))):
            pool[ident] = use
    prepared = _static_inputs(rules, authored, scope, bound, rows) if stage == 'plot_design' else {}
    return pool, prepared
