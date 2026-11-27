"""Count the people attested by roster observations, keeping chapter evidence attached."""
from collections import defaultdict

from nw.studio.corpus_roster import _is_nonstory_chapter, roster_issue, subject_evidence
from nw.studio.corpus_story_observations import event_chapter


def _counts(groups: dict) -> dict:
    return {key: len(people) for key, people in sorted(groups.items())}


def _canonical_id(who: str, characters: dict) -> str | None:
    visited = set()
    while who in characters and who not in visited:
        visited.add(who)
        target = characters[who].get('canonical_id')
        if not target or target == who:
            return who
        who = target
    return None


def cast_distribution(document: dict) -> dict | None:
    if document.get('schema_version', 1) < 5:
        return None
    units = {u['id']: u for u in document['units']}
    chapters = sorted((u for u in units.values() if u['level'] == 'chapter'), key=lambda u: u['start'])
    characters = {p['id']: p for p in document['characters']}
    identities = {key: _canonical_id(key, characters) for key in characters}
    events = {e['id']: e for e in document['events']}
    personal = subject_evidence(characters, events)
    evidence = {e['id']: e for e in document['evidence']}
    domain = next((d for d in document['domains'] if d['domain'] == 'cast_roster'), {})
    by_chapter = defaultdict(list)
    event_people = defaultdict(set)
    for event in events.values():
        if event['granularity'] == 'detail' and (chapter := event_chapter(event, units)):
            event_people[chapter].update((event['id'], identities.get(who)) for who in event['characters'])
    for thread in document['threads']:
        if thread['domain'] != 'cast_roster' or not thread['node_ids']:
            continue
        event = events.get(thread['node_ids'][0])
        if event and (chapter := event_chapter(event, units)):
            by_chapter[chapter].append(thread)

    status = domain.get('status', 'unassessed')
    seen, mentioned = set(), set()
    positions, functions = defaultdict(set), defaultdict(set)
    rows = []
    prior_pending = set()
    prior_uncovered = False
    for index, chapter in enumerate(chapters, 1):
        observations = by_chapter[chapter['id']]
        present, named = set(), set()
        local_positions, local_functions = defaultdict(set), defaultdict(set)
        included, pending = [], []
        pending_people, checked = set(), set()
        unidentified = 0
        for t in observations:
            detail = t['details']
            who = identities.get(t['characters'][0]) if len(t['characters']) == 1 else None
            if who:
                checked.add((t['node_ids'][0], who))
            if detail.get('subject_kind') == 'group' and t['status'] != 'uncertain' and status == 'observed':
                continue  # Explicitly undifferentiated crowds are outside the individual headcount.
            if (status != 'observed' or t['status'] == 'uncertain' or not who
                    or detail.get('subject_kind') != 'individual' or detail.get('presence') not in ('onstage','mentioned')
                    or roster_issue(t, events, units, characters, evidence, personal)):
                pending.append(t['id'])
                if who and detail.get('subject_kind') == 'individual':
                    pending_people.add(who)
                else:
                    unidentified += 1
                continue
            included.append(t['id'])
            if detail['presence'] == 'mentioned':
                named.add(who)
                continue
            present.add(who)
            standing, function = detail['standing'], detail['function_kind']
            local_positions[standing].add(who)
            local_functions[function].add(who)
            positions[standing].add(who)
            functions[function].add(who)
        missing = event_people[chapter['id']] - checked
        pending_people.update(who for _, who in missing if who)
        non_story = (status == 'observed' and not observations and not missing
                     and _is_nonstory_chapter(chapter['id'], events, units, evidence))
        first = present - seen
        ambiguous = first if prior_uncovered else first & prior_pending
        measured = bool(included)
        coverage = 'non_story' if non_story else 'pending' if pending or missing else 'verified' if measured else 'unassessed'
        rows.append({'unit_id': chapter['id'], 'chapter_index': index, 'title': chapter['title'], 'observed': measured,
                     'coverage': coverage, 'pending_observation_ids': pending,
                     'pending_person_ids': sorted(pending_people - present),
                     'unidentified_observation_count': unidentified,
                     'uncovered_event_ids': sorted({node for node, _ in missing}),
                     'appearing_count': len(present) if measured else None,
                     'first_count': len(first) if measured and not ambiguous else None,
                     'returning_count': len(present & seen) if measured and not ambiguous else None,
                     'mentioned_only_count': len(named - present) if measured else None,
                     'appearing_ids': sorted(present), 'first_ids': sorted(first - ambiguous),
                     'prior_appearance_unresolved_ids': sorted(ambiguous), 'mentioned_only_ids': sorted(named-present),
                     'positions': _counts(local_positions), 'functions': _counts(local_functions),
                     'observation_ids': included})
        seen.update(present)
        mentioned.update(named)
        prior_pending.update(pending_people)
        prior_uncovered = prior_uncovered or (not non_story and not observations) or bool(unidentified) or status != 'observed'
    measured = any(r['observed'] for r in rows)
    return {'status': status, 'unique_count': len(seen) if measured else None,
            'mentioned_only_count': len(mentioned - seen) if measured else None,
            'positions': _counts(positions), 'functions': _counts(functions), 'chapters': rows}
