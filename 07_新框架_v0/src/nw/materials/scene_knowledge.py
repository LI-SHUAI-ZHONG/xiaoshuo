"""Freeze accepted character knowledge at the clock of each proposed scene."""
from dataclasses import asdict

from nw.store import Store
from nw.story_models import StateHead
from nw.story_state import revision_state, state_at
from nw.task_models import canonical


POLICY = 'scene-clock-knowledge-v1'


def freeze(store: Store, branch_head: dict, scene_product: dict) -> dict:
    head = StateHead(**branch_head)
    snapshot = revision_state(store, head)
    slots = {}
    for ident in snapshot['slots']:
        scene = store.get('scene', ident)
        slots[store.get('chapter', scene.chapter_id).index, scene.index] = ident
    bodies = {row['key']: row['body'] for row in scene_product['members']}
    facts = {}
    for chapter in scene_product['chapters']:
        for scene in chapter['scenes']:
            key = scene['card']
            pos = (chapter['index'], scene['index'], 0)
            # A replacement cannot inherit its own draft. New slots still need the before-scene cutoff.
            view = state_at(store, head.branch_id, head.revision, scene['story_order'], 'AUTHOR', pos,
                            before_scene=slots.get(pos[:2], ''), snapshot=snapshot)
            body = bodies[key]
            holders = {body['pov'], *body.get('characters', []), 'READER'}
            facts[key] = [asdict(fact) for fact in view.facts if fact.holder in holders]
    return facts


def scoped(scene_product: dict, context: dict) -> dict | None:
    if context.get('scene_knowledge_policy') != POLICY:
        return None
    if project := context.get('_project_scene_knowledge'):
        return project(scene_product)
    exact = context.get('narration_scene_facts')
    expected = {scene['card'] for chapter in scene_product['chapters'] for scene in chapter['scenes']}
    if not isinstance(exact, dict) or exact.keys() != expected or any(not isinstance(v, list) for v in exact.values()):
        raise ValueError('MATERIAL_STAGE: missing accepted scene knowledge for the frozen scene clocks')
    return exact


def verify_archive(store: Store, plan: dict, session: dict) -> None:
    if plan.get('scene_knowledge_policy') != POLICY:
        return
    scene_product = next((row['products'] for row in session['stages'] if row['stage'] == 'scene_design'), None)
    if scene_product is None or canonical(session['context'].get('narration_scene_facts')) != canonical(
            freeze(store, plan['branch_head'], scene_product)):
        raise ValueError('MATERIAL_STAGE: accepted scene knowledge differs from the frozen branch revision')
