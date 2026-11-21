"""Character arrangements and manuscript evidence for the selected workbench scene."""
from nw.store import Store
from nw.studio.corpus_catalog import CAST_ROSTER_OPTIONS


def scene_cast_view(store: Store, design: dict, scene: dict) -> dict:
    if not scene['in_branch_workbench']:
        return {}
    session = design.get('work_session', {})
    stages = {row['stage']: row['products'] for row in session.get('stages', [])}
    scene_plan = stages.get('scene_design', {})
    plan = next((row for row in scene_plan.get('cast_distribution_plan', [])
                 if row['chapter'] == scene['chapter_index']), None)
    people = session.get('context', {}).get('approved_cards', [])
    names = {p['card_id']: p['body']['name'] for p in people if p['kind'] == 'character'}
    for person in stages.get('character_design', {}).get('members', []):
        if person['kind'] == 'character':
            key = person['key']
            names[key] = person['body']['name']
            names[design.get('process_ids', {}).get(key, key)] = names[key]
    view = {}
    if plan:
        view['plan'] = {**plan, 'people': [{**person, 'name': names.get(person['actor'], person['actor'])}
                                          for person in plan['people']]}
        view['labels'] = {'positions': CAST_ROSTER_OPTIONS['standing'],
                          'functions': CAST_ROSTER_OPTIONS['function_kind']}
    if scene['accepted_draft_id']:
        from nw.materials.cast_appearances import accepted_scene
        slot = {'draft_id': scene['accepted_draft_id'], 'delta_id': scene['accepted_delta_id']}
        actual = accepted_scene(store, scene['id'], slot)
        view['accepted'] = {**actual, 'people': [{**person, 'name': person.get('name') or names.get(person['actor'], person['actor'])}
                                                for person in actual['people']]}
    return view
