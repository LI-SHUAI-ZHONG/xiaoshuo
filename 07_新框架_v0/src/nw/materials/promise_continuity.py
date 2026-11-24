"""Author-side promise dates and progress from approved, branch-selected records."""
import json

from nw.store import Store
from nw.story_models import Fact
from nw.task_models import content_sha256


_ACCEPTED = ('planted', 'sleeping', 'awake', 'paid_off')
_APPLIED_PLOTS = """SELECT a.proposal_id, a.decision_id,
    json_extract(a.mapping_json, '$.root.card_id') AS root_id,
    json_extract(a.mapping_json, '$.root.version') AS root_version,
    json_extract(a.mapping_json, '$.approvals') AS approvals_json,
    json_extract(a.mapping_json, '$.material_design.process_context.ids') AS ids_json,
    s.value AS plot_json
    FROM plan_applications a JOIN task_calls t ON t.id=a.proposal_id
    JOIN json_each(a.mapping_json, '$.material_design.work_session.stages') s
    WHERE t.kind='plan' AND t.status='FINISHED' AND t.validation='VALID'
    AND json_extract(a.mapping_json, '$.decision_id')=a.decision_id
    AND json_extract(s.value, '$.stage')='plot_design'
    AND json_type(s.value, '$.products.promise_plan')='array'
    ORDER BY a.rowid"""


def _dates(entry: dict) -> dict:
    dates = {key: entry[key] for key in ('plant_chapter', 'payoff_chapter')
             if type(entry.get(key)) is int and entry[key] > 0}
    window = entry.get('payoff_window')
    if isinstance(window, dict):
        if (type(window.get('min_offset')) is int and type(window.get('max_offset')) is int
                and 0 <= window['min_offset'] <= window['max_offset']):
            dates['payoff_window'] = {key: window[key] for key in ('min_offset', 'max_offset')}
    return dates


def _schedule_rows(store: Store, active: dict, promises: dict) -> dict:
    schedules = {}
    for row in store.connection.execute(_APPLIED_PLOTS):
        if active.get((row['root_id'], row['root_version'])) != row['decision_id']:
            continue
        plot = json.loads(row['plot_json'])
        if content_sha256(plot['products']) != plot.get('sha256'):
            continue
        ids = json.loads(row['ids_json'] or '{}')
        approvals = json.loads(row['approvals_json'])
        created = {ref['card_id'] for ref in approvals
                   if active.get((ref['card_id'], ref['version'])) == ref['decision_id']}
        for entry in plot['products']['promise_plan']:
            if not isinstance(entry, dict) or not isinstance(entry.get('promise'), str):
                continue
            ident = ids.get(entry['promise'])
            if ident not in promises or ident not in created or ident in schedules:
                continue
            if dates := _dates(entry):
                schedules[ident] = {**dates, 'source': {'proposal_id': row['proposal_id'],
                    'approval_id': row['decision_id'], 'plot_sha256': plot['sha256']}}
    return schedules


def approved_promise_snapshot(store: Store, settings: list[dict], cards: list[dict],
                              facts: list[Fact], operations: list[dict]) -> list[dict]:
    """Freeze active cards, established lifecycle and original approved chapter schedule."""
    active = {(row['card_id'], row['version']): row['decision_id'] for row in settings}
    promises = {card['card_id']: card for card in cards if card['kind'] == 'promise' and
                (card['card_id'], card['version']) in active}
    if not promises:
        return []
    schedules = _schedule_rows(store, active, promises)
    confirmed = {fact.entity_id: fact for fact in facts if fact.entity_id in promises
                 and fact.predicate == 'promise_stage' and fact.holder == 'WORLD' and fact.claim == 'fact'
                 and fact.evidence and fact.value in _ACCEPTED}
    first_plant = {}
    for op in operations:
        ident = op['entity_id']
        if (ident in confirmed and op['predicate'] == 'promise_stage' and op['holder'] == 'WORLD'
                and op['expected_old'] is None and op['new_value'] == 'planted' and op['evidence']):
            chapter = op['disclosure_order'][0]
            first_plant[ident] = min(chapter, first_plant.get(ident, chapter))

    snapshot = []
    for ident, card in sorted(promises.items()):
        fact = confirmed.get(ident)
        row = {'card_id': ident, 'version': card['version'], 'title': card['body']['title'],
               'accepted_stage': fact.value if fact else None}
        if fact:
            row['state_evidence'] = list(fact.evidence)
            if ident in first_plant:
                row['planted_chapter'] = first_plant[ident]
        if ident in schedules:
            row['schedule'] = schedules[ident]
        snapshot.append(row)
    return snapshot


def continuation_reminder(products: dict, context: dict) -> dict | None:
    """Project bounded author-side reminders. Local event names stay local to one plan."""
    prior = {p['card_id']: p for p in context['promise_continuity']}
    plot = products.get('plot_design', {}).get('products', {})
    local = {p['promise']: p for p in plot.get('promise_plan', ()) if isinstance(p, dict) and p.get('promise')}
    if not prior and not local:
        return None

    scene = products.get('scene_design', {}).get('products', {})
    current_scene = context.get('current_scene')
    active_events = set(context.get('current_events', ()))
    active_events.add(context.get('current_event'))
    active_events.update(p['event'] for p in scene.get('selected_events', ())
                         if p.get('event') and (not current_scene or p.get('scene') == current_scene))
    chapters = scene.get('chapters', ())
    current_chapter = context.get('current_chapter', context.get('chapter_target_index'))
    if current_chapter is None and len(chapters) == 1:
        current_chapter = chapters[0].get('index')

    unverified = [ident for ident in local if ident not in prior]
    counts = {'unverified': len(unverified), 'planted': 0, 'hinted': 0, 'paid_off': 0}
    due, overdue, still_open, pending = [], [], [], []
    resolved = []
    # Definitions mentioned by this plan must come first in bounded status lists.
    for ident in sorted(prior, key=lambda key: key not in local):
        row = prior[ident]
        accepted = row['accepted_stage']
        status = {'planted': 'planted', 'sleeping': 'hinted', 'awake': 'hinted',
                  'paid_off': 'paid_off'}.get(accepted, 'unverified')
        counts[status] += 1
        if status == 'paid_off':
            resolved.append(ident)
            continue
        if status == 'unverified':
            unverified.append(ident)
            continue

        schedule = row.get('schedule', {})
        payoff_chapter = schedule.get('payoff_chapter')
        planted = row.get('planted_chapter')
        window = schedule.get('payoff_window', {})
        current = local.get(ident, {})
        detail = {'promise': ident, 'title': row['title'][:96], 'status': status, 'accepted_stage': accepted}
        if payoff_chapter is not None:
            detail['payoff_chapter'] = payoff_chapter
        if window:
            detail['payoff_window'] = window
        if planted is not None:
            detail['planted_chapter'] = planted
        if row.get('state_evidence'):
            detail['state_evidence'] = row['state_evidence'][0]
        local_event = current.get('payoff_event')
        local_scene = current.get('payoff_scene')
        if ((local_event and local_event in active_events) or (local_scene and local_scene == current_scene)
                or (type(current_chapter) is int and payoff_chapter == current_chapter)):
            due.append(detail)
        else:
            still_open.append(ident)
            pending.append(detail)

        if type(current_chapter) is not int:
            continue
        if type(payoff_chapter) is int and current_chapter > payoff_chapter:
            overdue.append({**detail, 'reason': f'超过批准方案的回收章（第{payoff_chapter}章）'})
        elif type(planted) is int and type(window.get('max_offset')) is int:
            if current_chapter - planted > window['max_offset']:
                overdue.append({**detail, 'reason': f'超过实际埋设后{window["max_offset"]}章的回收窗口'})

    return {'lifecycle_counts': counts, 'due_this_scene': due[:6], 'overdue_warnings': overdue[:6],
            'still_open': still_open[:8], 'pending': pending[:8],
            'resolved': resolved[:8], 'unverified': unverified[:8],
            'rule': ('未核实的条目仍是作者计划。只有已接受正文或批准底稿中的状态证据能确认埋设与回收。'
                     '为本步到期的伏笔安排可见兑现或说明延期。人物只能通过当前获准的途径获知线索。')}
