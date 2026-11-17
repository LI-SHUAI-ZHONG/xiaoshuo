"""Author chapter summaries and periodic reviews tied to accepted versions."""
from dataclasses import asdict
import json
from uuid import uuid4

from nw.cards import card_input_ref, read_card
from nw.chapter_state import _chapter_state
from nw.models import Chapter
from nw.store import Store, now
from nw.story_delta import story_write_manifest
from nw.story_models import CardRef, StateHead
from nw.story_state import approved_scene_positions, baseline_for, revision_state, selected_operations
from nw.task_models import canonical, content_sha256


def _chapters(store: Store, snapshot: dict, approved: dict[str, tuple[int, int]]) -> dict[int, Chapter]:
    scenes = set(approved) | snapshot['slots'].keys()
    chapter_ids = {scene.chapter_id for scene in store.list('scene') if scene.id in scenes}
    return {chapter.index: chapter for chapter in store.list('chapter') if chapter.id in chapter_ids}


def _preview(store: Store, chapter: Chapter, snapshot: dict, with_scenes: set[str]) -> dict | None:
    """Find the chapter card from an applied plan with a scene in this branch."""
    approved = {(row['card_id'], row['version']) for row in snapshot['settings']}
    previews = {}
    for row in store.connection.execute('''
        SELECT mapping_json, result_json FROM plan_applications JOIN task_calls ON task_calls.id=proposal_id
        WHERE EXISTS(SELECT 1 FROM json_each(mapping_json,'$.chapters')
                     WHERE json_extract(value,'$.chapter_id')=?)''', (chapter.id,)):
        applied = json.loads(row['mapping_json'])
        root = CardRef(**applied['root'])
        if (root.card_id, root.version) not in approved:
            continue
        if not any(entry['chapter_id'] == chapter.id and any(scene['scene_id'] in with_scenes for scene in entry['scenes'])
                   for entry in applied['chapters']):
            continue
        saved = json.loads(row['result_json']).get('plan_proposal', {})
        chosen = next((candidate for candidate in saved.get('materialization', ())
                       if candidate['root'] == applied['root']), None)
        if chosen is None:
            continue
        for section in chosen['chapters']:
            if section['index'] == chapter.index and section['card'] is not None:
                ref = CardRef(**chosen['members'][section['card']])
                card = read_card(store, ref)
                if card['kind'] != 'chapter':
                    raise ValueError('CHAPTER_RECORD: the approved preview does not reference a chapter card')
                previews[ref] = {'ref': asdict(card_input_ref(card)), 'body': card['body']}
    return next(iter(previews.values())) if len(previews) == 1 else None


def _input_hash(branch_id: str, kind: str, inputs: dict) -> str:
    return content_sha256({'branch_id': branch_id, 'kind': kind, 'inputs': inputs})


def _latest(store: Store, head: StateHead, chapter: Chapter, kind: str, digest: str) -> dict | None:
    row = store.connection.execute('''
        SELECT id, report_json, report_sha256 FROM chapter_records
        WHERE branch_id=? AND chapter_id=? AND kind=? AND input_sha256=? ORDER BY rowid DESC LIMIT 1''',
        (head.branch_id, chapter.id, kind, digest)).fetchone()
    if row is None:
        return None
    report = json.loads(row['report_json'])
    if (content_sha256(report) != row['report_sha256'] or report['recorded_head']['branch_id'] != head.branch_id
            or _input_hash(head.branch_id, kind, report['inputs']) != digest):
        raise ValueError('CHAPTER_RECORD: saved evidence or author record changed')
    return {'id': row['id'], 'sha256': row['report_sha256'], **report}


def _report(store: Store, head: StateHead, chapter: Chapter, kind: str, inputs: dict,
            value: dict | None = None, expected: str | None = None) -> dict:
    digest = _input_hash(head.branch_id, kind, inputs)
    if value is not None:
        if expected != digest:
            raise ValueError('CHAPTER_RECORD_STALE: read the current chapter inputs before recording')
        with store.connection:
            store.connection.execute('BEGIN IMMEDIATE')
            latest = _latest(store, head, chapter, kind, digest)
            if latest is None or latest['author_record'] != value:
                report = {'recorded_head': asdict(head), 'inputs': inputs, 'author_record': value}
                store.connection.execute('INSERT INTO chapter_records VALUES (?,?,?,?,?,?,?,?)', (
                    uuid4().hex, head.branch_id, chapter.id, kind, digest, canonical(report), content_sha256(report), now()))
    record = _latest(store, head, chapter, kind, digest)
    return {'status': 'recorded' if record else 'ready', 'head': asdict(head),
            'input_sha256': digest, 'inputs': inputs, 'record': record}


def _author_text(value: object, name: str, limit: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ValueError(f'CHAPTER_RECORD: expected non-empty {name}')
    value = value.strip()
    if limit is not None and len(value) > limit:
        raise ValueError(f'CHAPTER_RECORD: {name} must be at most {limit} characters')
    return value


def _summary(store: Store, head: StateHead, chapter: Chapter, snapshot: dict,
             approved: dict[str, tuple[int, int]], payload: dict | None = None) -> dict:
    state = _chapter_state(store, head, snapshot, chapter, approved)
    if not state['scope_complete']:
        if payload is not None:
            raise ValueError('CHAPTER_SCOPE_INCOMPLETE: accept every approved scene first')
        return {'status': 'drafts_pending', 'chapter': asdict(chapter),
                'pending_scene_ids': state['pending_scene_ids'], 'record': None}
    preview = _preview(store, chapter, snapshot, {draft['scene_id'] for draft in state['drafts']})
    inputs = {'chapter': asdict(chapter), 'drafts': state['drafts'], 'preview': preview}
    if payload is None:
        return _report(store, head, chapter, 'summary', inputs)
    if not {'input_sha256', 'summary'} <= payload.keys() or payload.keys() - {'input_sha256', 'summary', 'comparison'}:
        raise ValueError('CHAPTER_RECORD: summary file needs input_sha256, summary and optional comparison')
    value = {'summary': _author_text(payload['summary'], 'summary', 100)}
    if 'comparison' in payload:
        if preview is None:
            raise ValueError('CHAPTER_RECORD: no approved preview is available for comparison')
        value['comparison'] = _author_text(payload['comparison'], 'comparison')
    return _report(store, head, chapter, 'summary', inputs, value, payload['input_sha256'])


def chapter_summary(store: Store, head: StateHead, index: int, payload: dict | None = None) -> dict:
    if type(index) is not int or index < 1:
        raise ValueError('CHAPTER_RECORD: invalid chapter index')
    snapshot = revision_state(store, head)
    approved = approved_scene_positions(store, snapshot)
    chapter = _chapters(store, snapshot, approved).get(index)
    if chapter is None:
        raise ValueError('CHAPTER_RECORD: chapter is not in this branch revision')
    return _summary(store, head, chapter, snapshot, approved, payload)


def chapter_index(store: Store, head: StateHead) -> dict:
    snapshot = revision_state(store, head)
    approved = approved_scene_positions(store, snapshot)
    entries = []
    lines = ['# 章节摘要索引']
    for chapter in sorted(_chapters(store, snapshot, approved).values(), key=lambda row: row.index):
        result = _summary(store, head, chapter, snapshot, approved)
        record = result['record']
        summary = record['author_record']['summary'] if record else None
        entries.append({'chapter': chapter.index, 'title': chapter.title, 'status': result['status'],
                        'summary': summary, 'record_id': record['id'] if record else None})
        text = ' '.join(summary.splitlines()) if summary else {'drafts_pending': '章稿待接受', 'ready': '摘要待填写'}[result['status']]
        lines.append(f'- 第{chapter.index}章 {" ".join(chapter.title.splitlines())}。{text}')
    return {'head': asdict(head), 'chapters': entries, 'markdown': '\n'.join(lines)}


def continuation_summary(store: Store, head: StateHead, chapter: int) -> dict | None:
    record = chapter_summary(store, head, chapter)['record']
    if record is None:
        return None
    return {'id': record['id'], 'sha256': record['sha256'], **record['author_record']}


def continuation_reviews(store: Store, head: StateHead, chapter: Chapter) -> list[dict]:
    kinds = [row[0] for row in store.connection.execute('''SELECT DISTINCT kind FROM chapter_records
        WHERE branch_id=? AND chapter_id=? AND kind NOT IN ('summary','commitment-ending') ORDER BY kind''',
        (head.branch_id, chapter.id))]
    result = []
    for kind in kinds:
        record = chapter_review(store, head, chapter.index, kind).get('record')
        if record is not None:
            result.append({'id': record['id'], 'sha256': record['sha256'],
                           'rule': record['inputs']['rule'], 'finding': record['author_record']['finding']})
    return result


def _character_inputs(store: Store, head: StateHead, snapshot: dict, states: list[dict]) -> dict:
    active = [read_card(store, CardRef(row['card_id'], row['version'])) for row in snapshot['settings']]
    characters = {card['card_id']: card for card in active if card['kind'] == 'character'}
    initial = {}
    for row in store.connection.execute('''SELECT state_json FROM story_commits
            WHERE branch_id=? AND revision<=? ORDER BY revision''', (head.branch_id, head.revision)):
        for ref in json.loads(row[0])['settings']:
            if ref['card_id'] in characters and ref['card_id'] not in initial:
                initial[ref['card_id']] = read_card(store, CardRef(ref['card_id'], ref['version']))
        if initial.keys() == characters.keys():
            break
    planned = {}
    unmatched = []
    for state in states:
        for draft in state['drafts']:
            ident = draft['draft_ref']['id']
            manifest = story_write_manifest(store, store.get('draft', ident))
            if manifest is None:
                unmatched.append(ident)
                continue
            for raw in manifest['card_refs']:
                ref = CardRef(**raw)
                row = read_card(store, ref)
                if row['kind'] == 'character':
                    item = planned.setdefault(ref, {'ref': asdict(card_input_ref(row)), 'body': row['body'], 'draft_ids': []})
                    item['draft_ids'].append(ident)
    return {'initial_character_cards': [{'ref': asdict(card_input_ref(row)), 'body': row['body']} for row in initial.values()],
            'checkpoint_character_cards': [{'ref': asdict(card_input_ref(row)), 'body': row['body']} for row in characters.values()],
            'write_time_character_cards': list(planned.values()), 'drafts_without_write_manifest': unmatched}


def _promise_inputs(store: Store, head: StateHead, snapshot: dict, through: int, promise_ids: set[str]) -> dict:
    def is_promise(item: dict) -> bool:
        return (item['entity_id'] in promise_ids and item['predicate'] == 'promise_stage'
                and item['holder'] == 'WORLD' and item['claim'] == 'fact')

    baseline = baseline_for(store, head.branch_id)
    return {'promise_baseline': {'disclosure_order': baseline['disclosure_order'],
                                 'facts': [fact for fact in baseline['facts'] if is_promise(fact)]}
            if baseline['disclosure_order'][0] <= through else None,
            'promise_evidence': sorted((op for op in selected_operations(store, snapshot)
                                        if op['disclosure_order'][0] <= through and is_promise(op)),
                                       key=lambda op: (op['disclosure_order'], op['story_order']))}


def chapter_review(store: Store, head: StateHead, through: int, kind: str, payload: dict | None = None) -> dict:
    from nw.materials.steps.review_scope_book_quality import CHARACTER_CHECKPOINT
    from nw.materials.steps.review_scope_costs import COST_CHECKPOINT
    from nw.materials.steps.review_scope_reader_engagement import COMMITMENT_CHECKPOINT, COMMITMENT_ENDING
    from nw.materials.steps.review_scope_resources import RESOURCE_CHECKPOINTS

    instructions = {'character': CHARACTER_CHECKPOINT, 'cost': COST_CHECKPOINT,
                    'commitment': COMMITMENT_CHECKPOINT, 'commitment-ending': COMMITMENT_ENDING,
                    **RESOURCE_CHECKPOINTS}
    if kind not in instructions or type(through) is not int or through < 1:
        raise ValueError('CHAPTER_RECORD: invalid checkpoint chapter or rule')
    snapshot = revision_state(store, head)
    approved = approved_scene_positions(store, snapshot)
    chapters = _chapters(store, snapshot, approved)
    if through not in chapters:
        raise ValueError('CHAPTER_RECORD: chapter is not in this branch revision')
    rule = instructions[kind]
    if kind == 'commitment-ending' and through != max(chapters):
        raise ValueError('CHAPTER_REVIEW_NOT_DUE: the closing chapter must be the last approved chapter')
    interval = rule['interval']
    if interval and through % interval:
        if payload is not None:
            raise ValueError('CHAPTER_REVIEW_NOT_DUE: use the checkpoint for the selected rule')
        return {'status': 'not_due', 'through_chapter': through, 'rule': rule}
    scope = range(through - interval + 1 if interval else 1, through + 1)
    states = {index: _chapter_state(store, head, snapshot, chapters[index], approved)
              for index in scope if index in chapters}
    missing = [index for index in scope if index not in states or not states[index]['scope_complete']]
    missing_deltas = [scene for state in states.values() for scene in state['missing_delta_scene_ids']]
    track_changes = kind == 'cost' or kind.startswith('resource-')
    if missing or track_changes and missing_deltas:
        if payload is not None:
            raise ValueError('CHAPTER_SCOPE_INCOMPLETE: review requires the full chapter window and applicable state evidence')
        return {'status': 'drafts_pending' if missing else 'state_evidence_pending', 'through_chapter': through,
                'rule': rule, 'missing_chapters': missing, 'missing_delta_scene_ids': missing_deltas}

    inputs = {'rule': rule, 'chapters': [{key: state[key] for key in ('chapter', 'drafts', 'changes')}
                                        for state in states.values()]}
    if track_changes:
        preceding = [_chapter_state(store, head, snapshot, chapters[index], approved)
                     for index in sorted(chapters) if index < scope.start]
        inputs['earlier_changes'] = [change for state in preceding for change in state['changes']]
        inputs['earlier_missing_delta_scene_ids'] = [scene for state in preceding for scene in state['missing_delta_scene_ids']]
    if kind == 'character':
        inputs.update(_character_inputs(store, head, snapshot, list(states.values())))
    elif kind != 'cost':
        cards = [read_card(store, CardRef(row['card_id'], row['version'])) for row in snapshot['settings']]
        kinds = {'world'} if track_changes else {'plot', 'promise'}
        inputs['approved_cards'] = [{'ref': asdict(card_input_ref(card)), 'body': card['body']}
                                    for card in cards if card['kind'] in kinds]
        if not track_changes:
            promise_ids = {card['card_id'] for card in cards if card['kind'] == 'promise'}
            inputs.update(_promise_inputs(store, head, snapshot, through, promise_ids))
    if payload is None:
        return _report(store, head, chapters[through], kind, inputs)
    if set(payload) != {'input_sha256', 'finding'}:
        raise ValueError('CHAPTER_RECORD: review file needs input_sha256 and finding')
    return _report(store, head, chapters[through], kind, inputs,
                   {'finding': _author_text(payload['finding'], 'finding')}, payload['input_sha256'])
