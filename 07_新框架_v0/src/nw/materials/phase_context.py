"""Recreate only the project facts actually sent to an individual design step."""

ACTION_STATE_POLICY = 'action-state-input-v1'


def new_character_keys(products: dict, context: dict) -> set[str]:
    """Local keys for new cards are distinct from project identities in prior state."""
    approved = {row['card_id'] for row in context.get('approved_cards', ()) if row['kind'] == 'character'}
    return {row['key'] for row in products.get('character_design', {}).get('products', {}).get('members', ())
            if row['kind'] == 'character'} - approved


def visible_facts(stage: str,products: dict,context: dict) -> list[dict]:
    if stage=='state_propagation':return context.get('accepted_state',[])
    action_state = stage == 'action_design' and context.get('action_state_policy') == ACTION_STATE_POLICY
    if not action_state and stage not in ('character_design','scene_design','state_transition'):return []
    from nw.materials.phase_contract import entity_ids
    known=entity_ids(products,context)
    return [r for r in context.get('accepted_state',[]) if r.get('entity_id') in known
            and (not action_state or r.get('holder') == 'WORLD' and r.get('claim') == 'fact')]
