"""Graph/coverage integrity checks; author review decides literary interpretations."""
from nw.studio.corpus_catalog import DETAILS, DOMAINS, OVERVIEW
from nw.studio.corpus_index import range_coverage


def graph_issues(body: dict, length: int, coverage: dict | None = None) -> list[dict]:
    issues=[]

    def check(ok: bool, field: str, message: str, severity: str = 'error') -> None:
        if not ok: issues.append({'field':field,'message':message,'severity':severity})

    maps={}
    for section in ('units','characters','events','threads','links','evidence'):
        maps[section]={r['id']:r for r in body[section]}
        check(len(maps[section])==len(body[section]),section,'记录标识重复：'+section)
    units,people,events,threads,links,evidence=(maps[s] for s in ('units','characters','events','threads','links','evidence'))
    roots=[u for u in units.values() if u['level']=='book']
    check(len(roots)==1 and roots[0]['parent_id'] is None and roots[0]['start']==0 and roots[0]['end']==length,
          'units','必须有一项覆盖已导入文本的全书根目录')
    parents={'volume':{'book'},'chapter':{'book','volume'},'scene':{'chapter'}}
    for unit in units.values():
        if unit['level']=='book': continue
        parent=units.get(unit['parent_id'])
        check(bool(parent) and parent['level'] in parents[unit['level']],'units','卷章场缺少正确的上级：'+unit['id'])
        if parent:check(parent['start']<=unit['start']<unit['end']<=parent['end'],'units','子范围超出上级：'+unit['id'])
    grouped={}
    for unit in units.values():grouped.setdefault(unit['parent_id'],[]).append(unit)
    for siblings in grouped.values():
        children=sorted(siblings,key=lambda r:r['start'])
        for previous,current in zip(children,children[1:]):
            check(previous['end']<=current['start'],'units','同层范围重叠：'+previous['id']+' / '+current['id'])
    chapters=[u for u in units.values() if u['level']=='chapter']
    check(bool(chapters) and range_coverage(chapters,length)['complete_imported_text'],'units','章节目录没有覆盖全部已导入文本')
    check(bool(body['source_extent']['note']),'source_extent','请记录参考文本完整性判断依据')
    for key,label in OVERVIEW.items():check(bool(body['overview'][key]),'overview','全书总览待填写：'+label)
    for section in ('characters','events','threads','links','domains'):
        for row in body[section]:
            refs=row['evidence_ids']
            check(bool(refs) and set(refs)<=evidence.keys(),section,'记录缺少可定位原作证据：'+str(row.get('id',row.get('domain'))))
    for person in people.values():
        check(bool(person['name']),'characters','人物名称为空')
        target=person['canonical_id'];seen={person['id']}
        while target:
            if target in seen or target not in people:
                check(False,'characters','人物归并引用不存在或形成循环');break
            seen.add(target);target=people[target]['canonical_id']
    for event in events.values():
        unit=units.get(event['unit_id'])
        check(bool(unit),'events','事件没有真实卷章场：'+event['id'])
        check(set(event['characters'])<=people.keys(),'events','事件引用未知人物：'+event['id'])
        check(bool(event['summary']),'events','事件缺少实际内容：'+event['id'])
        check(bool(event['result']),'events','事件结果尚不明确：'+event['id'],'warning')
        check(set(event['parent_event_ids'])<=events.keys() and event['id'] not in event['parent_event_ids'],
              'events','细节事件引用了不存在或自身的总览节点：'+event['id'])
        if event['granularity']=='detail':
            check(bool(event['parent_event_ids']),'events','细节事件未对应全书总览节点：'+event['id'])
            check(all(events[k]['granularity']=='overview' for k in event['parent_event_ids'] if k in events),
                  'events','细节的父事件必须是总览节点')
        if unit:
            check(all(unit['start']<=evidence[k]['start']<evidence[k]['end']<=unit['end'] for k in event['evidence_ids'] if k in evidence),
                  'events','事件证据超出所属卷章场：'+event['id'])
    for link in links.values():
        a,b=events.get(link['source']),events.get(link['target'])
        check(bool(a) and bool(b) and a['id']!=b['id'],'links','关系端点无效：'+link['id'])
        check(link['thread_id'] is None or link['thread_id'] in threads,'links','关系引用未知线索/弧光')
        check(bool(link['explanation']),'links','关系缺少成立依据：'+link['id'])
        if a and b:
            if link['kind'] in ('causes','enables') and a['story_order'] is not None and b['story_order'] is not None:
                check(a['story_order']<=b['story_order'],'links','因果关系的故事时间逆向，请复核或说明非线性/时间环：'+link['id'],'warning')
            refs=set(link['evidence_ids'])
            check(bool(refs&set(a['evidence_ids'])) and bool(refs&set(b['evidence_ids'])),
                  'links','关系须保留前后事件各自证据：'+link['id'])
            ua,ub=units.get(a['unit_id']),units.get(b['unit_id'])
            ca=ua['parent_id'] if ua and ua['level']=='scene' else a['unit_id']
            cb=ub['parent_id'] if ub and ub['level']=='scene' else b['unit_id']
            check(ca==cb or len({(evidence[k]['start'],evidence[k]['end']) for k in refs if k in evidence})>=2,
                  'links','跨章关系需要多处原文证据：'+link['id'])
            if link['kind'] in ('responds','escalates','foreshadows','hints','pays_off','reveals'):
                sa=min((evidence[k]['start'] for k in a['evidence_ids'] if k in evidence),default=0)
                sb=min((evidence[k]['start'] for k in b['evidence_ids'] if k in evidence),default=0)
                check(sa<=sb,'links','信息/埋收关系与文本出现顺序相反：'+link['id'])
    for thread in threads.values():
        check(bool(thread['node_ids']) and set(thread['node_ids'])<=events.keys(),'threads','线索/弧光没有完整实际事件链：'+thread['id'])
        check(set(thread['characters'])<=people.keys(),'threads','线索/弧光引用未知人物')
        check(bool(thread['title']) and bool(thread['explanation']),'threads','线索/弧光缺少名称与解释')
        for key,label in DETAILS[thread['domain']].items():
            check(bool(thread['details'][key]),'threads','具体分析待填写：'+label,'warning')
        if thread['domain']=='character_arc':check(bool(thread['characters']),'threads','人物弧光必须指定人物')
        if thread['status']=='resolved' and thread['domain'] in ('hook','foreshadow'):
            kind='responds' if thread['domain']=='hook' else 'pays_off'
            matching=[l for l in links.values() if l['thread_id']==thread['id'] and l['kind']==kind
                      and l['source'] in thread['node_ids'] and l['target'] in thread['node_ids']]
            check(bool(matching),'threads','声称已回应/回收但缺少前后事件及证据关系：'+thread['id'])
    causal={key:[] for key in events};indegree={key:0 for key in events}
    for link in links.values():
        if link['kind'] in ('causes','enables') and link['source'] in events and link['target'] in events:
            causal[link['source']].append(link['target']);indegree[link['target']]+=1
    queue=[key for key,n in indegree.items() if n==0];processed=0
    while queue:
        key=queue.pop();processed+=1
        for target in causal[key]:
            indegree[target]-=1
            if indegree[target]==0:queue.append(target)
    check(processed==len(events),'links','因果图存在环；请核对实际因果或明确时间环等特殊结构依据','warning')
    dispositions={d['domain']:d for d in body['domains']}
    check(len(dispositions)==len(body['domains']),'domains','制作职责分析状态重复')
    for domain,label in DOMAINS.items():
        row=dispositions.get(domain)
        check(bool(row),'domains','尚未检查：'+label)
        if row:
            check(bool(row['explanation']),'domains','请说明该职责的判断依据：'+label)
            found=any(t['domain']==domain for t in threads.values())
            check(row['status']!='observed' or found,'domains','标为已观察但没有实际线索/事件链：'+label)
            check(row['status']!='not_observed' or not found,'domains','已有线索却标为未观察：'+label)
    check(bool(events),'events','尚无有证据的事件节点')
    if coverage is not None:
        reviewed=set(coverage.get('reviewed_units',[]))
        manual=bool(chapters) and {u['id'] for u in chapters}<=reviewed
        read=range_coverage(coverage.get('survey_ranges',[]),length)['complete_imported_text']
        detail=range_coverage(coverage.get('detail_ranges',[]),length)['complete_imported_text']
        check(manual or read and detail,'coverage','仍有范围未通读/细拆；不能批准全范围分析')
    return issues
