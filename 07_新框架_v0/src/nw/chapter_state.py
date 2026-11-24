"""Reconstruct chapter-end changes from the branch's accepted scene versions."""
from dataclasses import asdict

from nw.cards import read_card
from nw.materials.chapter_progress import CHANGE_PROJECTION
from nw.materials.identity_evidence import accepted_scene_checks
from nw.models import Chapter
from nw.store import Store
from nw.story_delta import draft_ref, paragraph_evidence, read_delta
from nw.story_models import CardRef, StateHead
from nw.story_state import IDENTITY_STATUS_PREFIX, approved_scene_positions, revision_state
from nw.task_models import canonical


def _chapter_state(store: Store, head: StateHead, snapshot: dict, chapter: Chapter,
                   approved: dict[str, tuple[int, int]], *, include_anchor_checks: bool = False) -> dict:
    slots = snapshot['slots']
    approved_ids = {scene_id for scene_id, place in approved.items() if place[0] == chapter.index}
    known = [scene for scene in store.list('scene')
             if scene.chapter_id == chapter.id and (scene.id in approved_ids or scene.id in slots)]
    drafts = []
    changes = []
    identity_disclosures = []
    character_changes = []
    reviewed_progress = []
    reviewed_cast_work = []
    identity_anchor_checks = []
    pending = []
    missing_deltas = []
    for scene in sorted(known, key=lambda row: row.index):
        slot = slots.get(scene.id)
        if slot is None:
            pending.append(scene.id)
            continue
        draft = store.get('draft', slot['draft_id'])
        if draft.scene_id != scene.id:
            raise ValueError('Chapter state draft does not belong to the accepted scene')
        delta_id = slot['delta_id']
        delta = read_delta(store, delta_id) if delta_id is not None else None
        if delta is not None and delta.draft_id != draft.id:
            raise ValueError('Chapter state delta does not match the accepted draft')
        drafts.append({'scene_id': scene.id, 'scene_index': scene.index, 'draft_ref': asdict(draft_ref(draft)),
                       'delta_id': delta_id, 'delta_sha256': delta.sha256 if delta else None})
        if delta is None:
            missing_deltas.append(scene.id)
            continue
        anchors, progress = accepted_scene_checks(store, draft, delta, identity=include_anchor_checks,
                                                 cast_work=reviewed_cast_work)
        identity_anchor_checks.extend(anchors)
        reviewed_progress.extend(progress)
        for operation in sorted(delta.operations, key=lambda op: (op['disclosure_order'], op['story_order'])):
            change = {**operation, 'scene_id': scene.id, 'delta_id': delta_id}
            if canonical(operation['expected_old']) == canonical(operation['new_value']):
                change['value_unchanged'] = True
            identity_status = operation['predicate'].startswith(IDENTITY_STATUS_PREFIX)
            if identity_status:
                change['paragraph_evidence'] = paragraph_evidence(draft, operation['evidence'])
            if operation['holder'] == 'WORLD' and operation['claim'] == 'fact':
                changes.append(change)
            elif identity_status and operation['claim'] in ('fact', 'belief', 'suspicion'):
                identity_disclosures.append(change)
            elif operation['holder'] not in ('WORLD', 'READER'):
                character_changes.append(change)
    affected_ids = {change['entity_id'] for change in changes}
    affected_characters = []
    for setting in snapshot['settings']:
        if setting['card_id'] not in affected_ids:
            continue
        ref = CardRef(setting['card_id'], setting['version'])
        card = read_card(store, ref)
        if card['kind'] == 'character':
            affected_characters.append({'card_ref': asdict(ref), 'name': card['body']['name'],
                                        'role': card['body']['role']})
    scope_complete = bool(approved_ids) and not pending
    return {'head': asdict(head), 'chapter': asdict(chapter), 'scope_complete': scope_complete,
            'change_projection': CHANGE_PROJECTION,
            'drafts': drafts, 'pending_scene_ids': pending, 'missing_delta_scene_ids': missing_deltas,
            'affected_characters': affected_characters, 'changes': changes,
            **({'character_changes': character_changes} if character_changes else {}),
            **({'reviewed_progress': reviewed_progress} if reviewed_progress else {}),
            **({'reviewed_cast_work': reviewed_cast_work} if reviewed_cast_work else {}),
            **({'identity_disclosures': identity_disclosures} if identity_disclosures else {}),
            **({'identity_anchor_checks': identity_anchor_checks} if identity_anchor_checks else {})}


def chapter_state(store: Store, head: StateHead, chapter_index: int) -> dict:
    """Inspect the accepted evidence for an explicit chapter and branch revision."""
    chapter = next((row for row in store.list('chapter') if row.index == chapter_index), None)
    if chapter is None:
        raise ValueError('Chapter index not found')
    snapshot = revision_state(store, head)
    return _chapter_state(store, head, snapshot, chapter, approved_scene_positions(store, snapshot),
                          include_anchor_checks=True)


def continuation_chapter_state(store: Store, head: StateHead, snapshot: dict) -> dict | None:
    """Offer the latest completed approved chapter as author-facing planning evidence."""
    if not snapshot['slots']:
        return None
    chapters = {row.id: row for row in store.list('chapter')}
    latest = max((chapters[scene.chapter_id] for scene in store.list('scene')
                  if scene.id in snapshot['slots']), key=lambda row: row.index, default=None)
    if latest is None:
        return None
    approved = approved_scene_positions(store, snapshot)
    summary = _chapter_state(store, head, snapshot, latest, approved)
    return summary if summary['scope_complete'] else None
