"""Count the people attested by roster observations, keeping chapter evidence attached."""
from collections import defaultdict

from nw.studio.corpus_roster import roster_issue, subject_evidence
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
    for chapter in chapters:
        observations = by_chapter[chapter['id']]
        present, named = set(), set()
        local_positions, local_functions = defaultdict(set), defaultdict(set)
        included = []
        for t in observations:
            detail = t['details']
            if (status != 'observed' or t['status'] == 'uncertain' or not t['characters']
                    or detail.get('subject_kind') != 'individual' or detail.get('presence') not in ('onstage','mentioned')
                    or roster_issue(t, events, units, characters, evidence, personal)):
                continue
            who = identities.get(t['characters'][0])
            if not who:
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
        first = present - seen
        measured = bool(included)
        rows.append({'unit_id': chapter['id'], 'title': chapter['title'], 'observed': measured,
                     'appearing_count': len(present) if measured else None, 'first_count': len(first) if measured else None,
                     'returning_count': len(present & seen) if measured else None,
                     'mentioned_only_count': len(named - present) if measured else None,
                     'appearing_ids': sorted(present), 'first_ids': sorted(first), 'mentioned_only_ids': sorted(named-present),
                     'positions': _counts(local_positions), 'functions': _counts(local_functions),
                     'observation_ids': included})
        seen.update(present)
        mentioned.update(named)
    measured = any(r['observed'] for r in rows)
    return {'status': status, 'unique_count': len(seen) if measured else None,
            'mentioned_only_count': len(mentioned - seen) if measured else None,
            'positions': _counts(positions), 'functions': _counts(functions), 'chapters': rows}
