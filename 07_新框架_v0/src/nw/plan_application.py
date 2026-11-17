
"""Apply exactly the approved candidate, with atomic and repeatable materialization."""
from dataclasses import asdict
import json
from typing import Callable
from uuid import uuid4

from nw import planning
from nw.cards import card_input_ref, decision_history, read_card, read_decision
from nw.materials.binding import verify_materials
from nw.materials.phase_routes import STAGED_POLICIES
from nw.models import Chapter, Scene
from nw.store import Store, now
from nw.story_dependencies import find_impacts, outline_ref
from nw.story_models import CardRef, StateHead
from nw.story_state import current_head, revision_state, write_revision
from nw.task_models import Ref, canonical, content_sha256


def _approved_members(store: Store, root: CardRef, root_card: dict, approval: str) -> list[dict]:
    entries = [{**asdict(root), 'decision_id': approval}]
    for raw in root_card['body']['members']:
        expected = Ref(**raw)
        ref = CardRef(expected.id, expected.version)
        member = read_card(store, ref)
        latest = store.connection.execute('SELECT MAX(version) FROM cards WHERE card_id=?', (ref.card_id,)).fetchone()[0]
        if card_input_ref(member) != expected or latest != ref.version or member['status'] == 'disabled':
            raise ValueError('STALE_PLAN: approved member versions changed')
        ident = uuid4().hex
        store.connection.execute('INSERT INTO card_decisions VALUES (?,?,?,?,?,?)',
                                 (ident, ref.card_id, ref.version, 'approved', f'plan decision {approval}', now()))
        entries.append({**asdict(ref), 'decision_id': ident})
    return entries


def _materialize(store: Store, candidate: dict, proposal_id: str) -> list[dict]:
    chapters = {row.index: row for row in store.list('chapter')}
    existing = {(row.chapter_id, row.index) for row in store.list('scene')}
    project = store.project()
    result = []
    if candidate['chapters']:
        store._invalidate_outline()
    for item in candidate['chapters']:
        chapter = chapters.get(item['index'])
        if (chapter is None) != (item['card'] is not None):
            raise ValueError('PLAN_COORDINATE_CONFLICT: planned chapter creation must match the current outline')
        if chapter is None:
            card = read_card(store, CardRef(**candidate['members'][item['card']]))
            chapter = store._insert('chapter', Chapter(uuid4().hex, project.id, item['index'], card['body']['title']))
        entry = {'chapter_id': chapter.id, 'index': chapter.index, 'scenes': []}
        for spec in item['scenes']:
            if (chapter.id, spec['index']) in existing:
                raise ValueError('PLAN_COORDINATE_CONFLICT: scene already exists')
            binding = {'scene_ref': candidate['members'][spec['card']], 'story_order': spec['story_order']}
            card = {'story': binding}
            material = {}
            if candidate.get('material_design'):
                card['_nw_material_plan'] = proposal_id
                material['material_key'] = spec['card']
            scene = store._insert('scene', Scene(uuid4().hex, chapter.id, spec['index'], canonical(card)))
            entry['scenes'].append({'scene_id': scene.id, 'index': scene.index, **binding, **material})
        result.append(entry)
    return result


def _retire_descendants(store: Store, snapshot: dict, parent: dict) -> list[str]:
    original = card_input_ref(parent)
    impacted = {original, *find_impacts(store, [original])}
    active = {(row['card_id'], row['version']) for row in snapshot['settings']}
    retired = {(ref.id, ref.version) for ref in impacted if ref.kind == 'card' and
               (ref.id, ref.version) in active and read_card(store, CardRef(ref.id, ref.version))['kind']
               in ('plot', 'volume', 'chapter', 'scene', 'promise')}
    snapshot['settings'] = [row for row in snapshot['settings'] if (row['card_id'], row['version']) not in retired]
    scenes = []
    for scene in store.list('scene'):
        ref = json.loads(scene.card_json).get('story', {}).get('scene_ref')
        if ref and (ref['card_id'], ref['version']) in retired:
            scenes.append(scene.id)
    snapshot['stale_plan_scenes'] = sorted(set(snapshot.get('stale_plan_scenes', [])) | set(scenes))
    return sorted(scenes)


def _checked_snapshot(store: Store, frozen: dict) -> tuple[StateHead | None, dict | None]:
    saved = frozen['branch_head']
    head = StateHead(**saved) if saved else None
    if store.managed_story() != (head is not None):
        raise ValueError('STALE_PLAN: project story mode changed')
    if head is None:
        return None, None
    if current_head(store, head.branch_id) != head:
        raise ValueError('STALE_PLAN: branch advanced since design')
    snapshot = revision_state(store, head)
    if head.branch_id == 'main' and snapshot['slots']:
        raise ValueError('Apply design changes on a candidate branch after prose has been accepted')
    return head, snapshot


def apply_plan(store: Store, proposal_id: str, decision_id: str, *,
               before_apply: Callable[[], None] | None = None) -> list[CardRef]:
    proposal = planning.show_plan(store, proposal_id)
    manifest, frozen = planning.plan_input(store, proposal_id)
    if frozen.get('material_work'):
        from nw.materials.work_catalog import SourceDesk
        SourceDesk(store.directory.parent).verify(frozen['material_work']['sources'])
        if frozen['material_work'].get('policy') in STAGED_POLICIES:
            from nw.materials.binding_reviews import verify_session_bindings
            verify_session_bindings(frozen['material_work'],store.directory.parent,test_mode=store.test_mode)
            from nw.materials.governance_runtime import verify_session_governance
            verify_session_governance(frozen['material_work'],store.directory.parent,adopting=True)
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        previous = planning._application(store, proposal_id)
        if previous:
            if previous['decision_id'] != decision_id:
                raise ValueError('Plan was applied with a different decision')
            return [CardRef(row['card_id'], row['version']) for row in previous['approvals']]
        if before_apply:
            before_apply()
        decision = read_decision(store, decision_id).ref
        if (decision.decision != 'approved' or decision.card_ref not in proposal.candidate_cards or
                decision_history(store, decision.card_ref)[-1] != decision):
            raise ValueError('Apply requires the active approval decision for a candidate in this proposal')
        root = decision.card_ref
        latest = store.connection.execute('SELECT MAX(version) FROM cards WHERE card_id=?', (root.card_id,)).fetchone()[0]
        if latest != root.version or store.briefs()[-1].version != manifest['brief_ref']['version']:
            raise ValueError('STALE_PLAN: direction or Brief changed since design')
        if asdict(outline_ref(store)) != manifest['dependency_refs'][0]:
            raise ValueError('STALE_PLAN: outline changed since design')
        head, snapshot = _checked_snapshot(store, frozen)
        chosen = next(item for item in proposal.materialization if item['root'] == asdict(root))
        verify_materials(store.directory.parent, frozen.get('materials', ()))
        stale = []
        if snapshot is not None and proposal.scope == 'replan':
            stale = _retire_descendants(store, snapshot, frozen['parent'])
            if affected := sorted(set(stale) & snapshot['slots'].keys()):
                raise ValueError('REPLAN_ACCEPTED_DESCENDANTS: ' + ', '.join(affected))
        approvals = _approved_members(store, root, read_card(store, root), decision_id)
        chapters = _materialize(store, chosen, proposal_id)
        if snapshot is not None:
            snapshot['settings'].extend(approvals)
        result = {'root': asdict(root), 'decision_id': decision_id, 'approvals': approvals,
                  'chapters': chapters, 'stale_scenes': stale,
                  'branch_head': asdict(StateHead(head.branch_id, head.revision + 1)) if head else None}
        if 'material_design' in chosen:
            result['material_design'] = chosen['material_design']
        if head is not None:
            write_revision(store, StateHead(**result['branch_head']), head.revision,
                           f'plan-apply:{proposal_id}', content_sha256(result), snapshot)
        store.connection.execute('INSERT INTO plan_applications VALUES (?,?,?)',
                                 (proposal_id, decision_id, canonical(result)))
    return [CardRef(row['card_id'], row['version']) for row in approvals]
