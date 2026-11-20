"""Counts refer to registered observations, never universal genre targets."""
from nw.studio.corpus_catalog import domains_for
from nw.studio.corpus_index import range_coverage


def corpus_statistics(document: dict,coverage: dict) -> dict:
    units={u['id']:u for u in document['units']};events={e['id']:e for e in document['events']}
    evidence={e['id']:e for e in document['evidence']}
    chapters=sorted([u for u in units.values() if u['level']=='chapter'],key=lambda u:u['start'])
    rows={u['id']:{'unit_id':u['id'],'title':u['title'],'start':u['start'],'end':u['end'],
        'overview_events':[],'detail_events':[],'hook_opens':[],'hook_responses':[],
        'foreshadow_plants':[],'foreshadow_hints':[],'foreshadow_payoffs':[],'emotional_transitions':[]} for u in chapters}
    def chapter(event_id: str) -> str | None:
        event=events.get(event_id);unit=units.get(event['unit_id']) if event else None
        return unit['parent_id'] if unit and unit['level']=='scene' else unit['id'] if unit and unit['level']=='chapter' else None
    for event in events.values():
        cid=chapter(event['id'])
        if cid in rows:
            rows[cid]['overview_events' if event['granularity']=='overview' else 'detail_events'].append(event['id'])
            if event['granularity']=='detail' and (event['emotion_before'] or event['emotion_after']):
                rows[cid]['emotional_transitions'].append({'event_id':event['id'],'before':event['emotion_before'],'after':event['emotion_after']})
    for thread in document['threads']:
        if thread['domain'] not in ('hook','foreshadow') or not thread['node_ids']:continue
        ordered=sorted((events[k] for k in thread['node_ids'] if k in events),
            key=lambda e:min((evidence[k]['start'] for k in e['evidence_ids'] if k in evidence),default=0))
        if not ordered:continue
        cid=chapter(ordered[0]['id'])
        if cid in rows:rows[cid]['hook_opens' if thread['domain']=='hook' else 'foreshadow_plants'].append(thread['id'])
        for link in document['links']:
            if link['thread_id']!=thread['id']:continue
            key={'responds':'hook_responses','hints':'foreshadow_hints','pays_off':'foreshadow_payoffs'}.get(link['kind'])
            target=chapter(link['target'])
            if key and target in rows and thread['id'] not in rows[target][key]:rows[target][key].append(thread['id'])
    length=max((u['end'] for u in units.values()),default=0)
    return {'chapter_ranges':list(rows.values()),'thread_counts':{domain:sum(t['domain']==domain for t in document['threads'])
        for domain in domains_for(document.get('schema_version',1))},
        'open_thread_ids':[t['id'] for t in document['threads'] if t['status']!='resolved'],
        'survey':range_coverage(coverage.get('survey_ranges',[]),length),
        'detail':range_coverage(coverage.get('detail_ranges',[]),length),
        'manual_reviewed_units':coverage.get('reviewed_units',[]),
        'counting_basis':'按已登记线索标识与当前目录范围计数；不是原作实例已找全的证明，不是类型配额。'}
