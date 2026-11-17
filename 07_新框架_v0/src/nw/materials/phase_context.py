"""Recreate only the project facts actually sent to an individual design step."""


def visible_facts(stage: str,products: dict,context: dict) -> list[dict]:
    if stage=='state_propagation':return context.get('accepted_state',[])
    if stage not in ('character_design','scene_design','state_transition'):return []
    from nw.materials.phase_contract import entity_ids
    known=entity_ids(products,context)
    return [r for r in context.get('accepted_state',[]) if r.get('entity_id') in known]
