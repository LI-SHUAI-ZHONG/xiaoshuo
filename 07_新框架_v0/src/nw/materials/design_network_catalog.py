"""Pair the reviewed step methods with their exact authored static and dynamic originals."""
from nw.materials import character_prerequisites, world_prerequisites
from nw.materials.network_workflow import type_matches
from nw.materials.type_network_catalog import edge_proof

POLICY = 'frozen-design-prerequisites-v1'
OWNERS = {'world_design': world_prerequisites, 'character_design': character_prerequisites}
ACTION_BASES = {'C00025', 'C00032'}


def load_catalog(desk, authored: dict, rules: dict) -> dict:
    result = {}
    for stage, methods in OWNERS.items():
        for ident in authored.get(stage, {}):
            rule = rules.get(ident)
            if not rule or not rule['derived'] or (key := rule['key']) not in methods.SPECS:
                continue
            spec = methods.SPECS[key]
            basis_stage = 'action_design' if key in ACTION_BASES else stage
            static_id = rule['static_id']
            # Book scope has no action step. Keep the audited reason, but never offer its rule.
            if basis_stage in authored and static_id not in authored[basis_stage]:
                continue
            if static_id not in desk.by_id or any(desk.by_id[i]['state'] != 'design_ready' for i in (ident, static_id)):
                continue
            source = desk.read(ident)
            proof = edge_proof(source, desk.read(static_id))
            expected = {'source': spec['source'], 'target': spec['target'], 'type': spec['relation'], 'condition': spec['condition']}
            if proof and proof['edge'] == expected:
                result[key] = {'owner': stage, 'source': source['source'], 'static': proof['source'],
                               'valid_types': rule['valid_types'], 'basis_stage': basis_stage}
    return result


def audit(stage: str, context: dict) -> list[dict]:
    if context.get('design_network_policy') != POLICY or stage not in OWNERS:
        return []
    return [dict(key=key, **OWNERS[stage].SPECS[key], basis_stage=row['basis_stage'])
            for key, row in sorted(context['design_network_catalog'].items()) if row['owner'] == stage
            and type_matches(row['valid_types'], context.get('network_type_scope', {}))]


def verify_pins(session: dict, desk) -> None:
    from nw.materials.semantic_application import require
    from nw.materials.semantic_products import original
    context = session['context']
    catalog = context.get('design_network_catalog', {})
    for key in {c['key'] for stage in session['stages'] for c in stage.get('network_design_candidates', [])}:
        record = catalog[key]
        source = desk.read(record['source']['id'])
        proof = edge_proof(source, desk.read(record['static']['id']))
        spec = OWNERS[record['owner']].SPECS[key]
        require(source['source'] == record['source'] and source['source']['key'] == key and proof
                and proof['source'] == record['static'] and proof['edge'] == {
                    'source': spec['source'], 'target': spec['target'], 'type': spec['relation'], 'condition': spec['condition']}
                and original(source).get('valid_types') == record['valid_types'], '世界或人物步骤资料的来源版本或适用条件已变化')
