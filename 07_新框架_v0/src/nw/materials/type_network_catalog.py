"""Verify the authored static source behind each type-adaptation derivation."""
from nw.materials.network_workflow import DYNAMIC_PROFILES, STATIC_PROFILES
from nw.materials.semantic_products import original
from nw.materials.work_catalog import SourceDesk


def edge_proof(source: dict, basis: dict) -> dict | None:
    derived, static = original(source), original(basis)
    if (source['source']['profile'] not in DYNAMIC_PROFILES or basis['source']['profile'] not in STATIC_PROFILES
            or not isinstance(derived, dict) or not isinstance(static, dict)
            or derived.get('generated_from_static') is not True or static.get('generated_from_static') or static.get('effect')
            or any(not isinstance(static.get(key), str) or not static[key] for key in ('source', 'target', 'type', 'condition'))
            or any(derived.get(key) != static[key] for key in ('source', 'target', 'type'))
            or not isinstance(derived.get('condition'), str)
            or derived['condition'] != static['condition'] + '；且当前故事明确采用该静态关系'):
        return None
    static_id = basis['source']['id']
    if source.get('related_sources') != [static_id]:
        return None
    if any(item.get('source_state') != 'design_ready' or item.get('use_mode') != 'project_method'
           or any(item.get('source_issues', {}).values()) for item in (source, basis)):
        return None
    return {'static_id': static_id, 'source': basis['source'],
            'edge': {key: static[key] for key in ('source', 'target', 'type', 'condition')}}


def load_type_network_bases(desk: SourceDesk, authored: dict, rules: dict) -> dict[str, dict]:
    from nw.materials.type_network import RULES

    step = authored.get('type_adaptation', {})
    result = {}
    for ident in step:
        rule = rules.get(ident)
        if (not rule or not rule['derived'] or rule['key'] not in RULES or rule['static_id'] not in step
                or desk.by_id[ident]['state'] != 'design_ready' or desk.by_id[rule['static_id']]['state'] != 'design_ready'):
            continue
        proof = edge_proof(desk.read(ident), desk.read(rule['static_id']))
        if proof:
            result[ident] = proof
    return result
