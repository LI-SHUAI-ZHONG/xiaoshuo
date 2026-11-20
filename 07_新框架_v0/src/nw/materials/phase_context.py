"""Recreate only the project facts actually sent to an individual design step."""

ACTION_STATE_POLICY = 'action-state-input-v1'


def visible_facts(stage: str,products: dict,context: dict) -> list[dict]:
    if stage=='state_propagation':return context.get('accepted_state',[])
    action_state = stage == 'action_design' and context.get('action_state_policy') == ACTION_STATE_POLICY
    if not action_state and stage not in ('character_design','scene_design','state_transition'):return []
    from nw.materials.phase_contract import entity_ids
    known=entity_ids(products,context)
    return [r for r in context.get('accepted_state',[]) if r.get('entity_id') in known
            and (not action_state or r.get('holder') == 'WORLD' and r.get('claim') == 'fact')]
