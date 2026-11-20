"""Keep the approved selection order within each scene."""

MULTI_ACTION_POLICY = 'scene-multi-action-v1'


def selected_action_ids(scene_product: dict) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for row in scene_product.get('selected_actions', []):
        groups.setdefault(row['scene'], []).append(row['action'])
    return groups


def action_choice(actions: list[dict]) -> str:
    return '；'.join(row['action'] for row in actions)
