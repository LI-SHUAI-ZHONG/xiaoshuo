"""Bounded windows retain global basis, unresolved threads and endpoint evidence."""
from nw.studio.corpus_prompts import messages
from nw.studio.corpus_story_observations import STORY_DETAILS, event_chapter


def event_position(event: dict, evidence: dict) -> int:
    return min((evidence[k]['start'] for k in event['evidence_ids'] if k in evidence),default=0)


def relation_events(document: dict) -> list[dict]:
    units={u['id']:u for u in document['units']};evidence={e['id']:e for e in document['evidence']}
    def chapter(event: dict) -> str:
        unit=units[event['unit_id']]
        return unit['parent_id'] if unit['level']=='scene' else unit['id']
    detailed={chapter(e) for e in document['events'] if e['granularity']=='detail'}
    selected=[e for e in document['events'] if e['granularity']=='detail' or chapter(e) not in detailed]
    return sorted(selected,key=lambda e:(event_position(e,evidence),e['id']))


def window_payload(document: dict, selected: list[dict], *, domain: str | None, prefix: str,
                   last: bool, global_basis: dict | None = None) -> dict:
    threads=[t for t in document['threads'] if domain is None or t['domain']==domain]
    if domain=='cast_roster':
        window={e['id'] for e in selected}
        # Each observation belongs to one event. Previous chapters need only a witnessed
        # example for the cumulative disposition; do not resend the entire cast register.
        local=[t for t in threads if window.intersection(t['node_ids'])]
        prior=next((t for t in threads if t['status']!='uncertain' and not window.intersection(t['node_ids'])),None)
        threads=local+([prior] if prior else [])
    open_threads=[t for t in threads if t['status']!='resolved']
    frontier={node for t in threads for node in ([t['node_ids'][0],t['node_ids'][-1]] if t['node_ids'] else [])}
    # Causal continuation across windows also keeps the last processed event.
    all_events={e['id']:e for e in document['events']}
    frontier.update(parent for e in selected for parent in e['parent_event_ids'])
    endpoint_events=[all_events[k] for k in sorted(frontier) if k in all_events]
    evidence_ids={eid for event in [*selected,*endpoint_events] for eid in event['evidence_ids']}
    evidence_ids.update(eid for thread in open_threads for eid in thread['evidence_ids'])
    observations=[]
    if domain in ('narration','cast_roster') or domain in STORY_DETAILS:
        window={event['id'] for event in selected}
        observations=[t for t in threads if t['status']=='resolved' and window.intersection(t['node_ids'])]
        evidence_ids.update(eid for t in observations for eid in t['evidence_ids'])
    people_ids={p for e in [*selected,*endpoint_events] for p in e['characters']}
    if domain=='cast_roster':
        people_ids.update(p for t in threads for p in t['characters'])
        evidence_ids.update(k for t in threads for k in t['evidence_ids'])
        roster_people={p['id']:p for p in document['characters']}
        pending=list(people_ids)
        while pending:
            target=roster_people.get(pending.pop(),{}).get('canonical_id')
            if target and target not in people_ids:
                people_ids.add(target)
                pending.append(target)
        evidence_ids.update(k for p in people_ids if p in roster_people for k in roster_people[p]['evidence_ids'])
    return {'prefix':prefix,'source_extent':document['source_extent'],'domain':domain,'last_window':last,
        'overview':global_basis['overview'] if global_basis else document['overview'],
        'open_threads':open_threads,
        **({'narration_observations':observations} if domain=='narration' else {}),
        **({'local_observations':observations} if domain in STORY_DETAILS or domain=='cast_roster' else {}),
        'closed_thread_index':[{'id':t['id'],'title':t['title'],'domain':t['domain'],'status':t['status'],'node_ids':t['node_ids']}
                               for t in threads if t['status']=='resolved'],
        'events':selected,'frontier_events':endpoint_events,
        'characters':[p for p in document['characters'] if p['id'] in people_ids],
        'evidence':[e for e in document['evidence'] if e['id'] in evidence_ids],
        'units':[u for u in document['units'] if u['id'] in {e['unit_id'] for e in [*selected,*endpoint_events]}]}


def choose_window(document: dict, events: list[dict], cursor: int, *, phase: str, domain: str | None,
                  prefix: str, maximum: int, global_basis: dict | None = None, passages: bool = True) -> tuple[list[str],int]:
    selected=[];next_cursor=cursor
    units={u['id']:u for u in document['units']} if domain=='cast_roster' else {}
    for event in events[cursor:]:
        if domain=='cast_roster' and selected and event_chapter(event,units)!=event_chapter(selected[0],units):
            break
        proposed=[*selected,event]
        payload=window_payload(document,proposed,domain=domain,prefix=prefix,last=cursor+len(proposed)==len(events),global_basis=global_basis)
        size=sum(len(m['content']) for m in messages(phase,payload,version=document['schema_version'],passages=passages))
        if size>maximum and selected:break
        selected=proposed;next_cursor+=1
        if size>maximum:break  # model_call records and rejects; never truncate the mandatory context.
    return [e['id'] for e in selected],next_cursor
