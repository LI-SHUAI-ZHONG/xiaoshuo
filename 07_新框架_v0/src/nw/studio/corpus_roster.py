"""Check the original passage and subject behind each chapter's cast observation."""
from nw.studio.corpus_story_observations import event_chapter


def canonical_person(key: str, people: dict) -> str:
    seen = set()
    while key not in seen and (parent := people.get(key, {}).get('canonical_id')):
        seen.add(key)
        key = parent
    return key


def subject_evidence(people: dict, events: dict) -> dict:
    result = {}
    named = {}
    for person in people.values():
        who = canonical_person(person['id'],people)
        record = result.setdefault(who, {'citations':set(), 'names':set()})
        record['citations'].update(person['evidence_ids'])
        name = person['name'].strip()
        if name:
            named.setdefault(name,set()).add(who)
    for name, identities in named.items():
        if len(identities)==1 and name not in {'我','你','他','她','它','他们','她们','对方','那人','此人'}:
            result[next(iter(identities))]['names'].add(name)
    for event in events.values():
        for person in event['characters']:
            who = canonical_person(person,people)
            if who in result:
                result[who]['citations'].update(event['evidence_ids'])
    return result


def roster_issue(row: dict, events: dict, units: dict, people: dict, evidence: dict, personal: dict) -> str:
    if len(row['characters']) != 1 or len(row['node_ids']) != 1:
        return '每条阵容观察须对应一个人物或群体和一个具体事件'
    subject = row['characters'][0]
    event = events.get(row['node_ids'][0], {})
    if subject not in people or event.get('granularity') != 'detail' or not event_chapter(event, units):
        return '阵容观察须指向已登记对象及有真实章节位置的细拆事件'
    detail = row['details']
    cite = detail['appearance_evidence']
    span = evidence.get(cite)
    unit = units[event['unit_id']]
    if not span or cite not in event['evidence_ids'] or cite not in row['evidence_ids'] or not (
            unit['start'] <= span['start'] < span['end'] <= unit['end']):
        return '实际出场或提及须有同一章场事件和本条观察共同引用的原句'
    who = canonical_person(subject,people)
    grounding = personal[who]
    if detail['presence'] == 'onstage' and who not in {
            canonical_person(p, people) for p in event['characters']}:
        return '认定实际出场须指向该细拆事件中的人物'
    if (detail['presence']=='mentioned' and row['status']!='uncertain' and cite not in grounding['citations']
            and not any(name in span['quote'] for name in grounding['names'])):
        return '仅提及也须由该人可区分的名字、别称或已关联到该人的同一处原句证明；归属未明时记为存疑'
    proof = detail['standing_evidence']
    if detail['standing'] != 'unknown' and (not proof or proof not in row['evidence_ids'] or proof not in evidence):
        return '全书地位须有可追溯的原文依据，不能判断时可保留未知'
    if proof and (proof not in row['evidence_ids'] or proof not in evidence):
        return '角色地位证据编号未出现在本条观察的原文依据中'
    if proof and proof != cite and proof not in grounding['citations']:
        return '全书地位的依据须来自同一个人物或其参与的事件'
    if detail['function_kind'] != 'unknown' and not detail['chapter_function'].strip():
        return '本章职责须说明此人具体起了什么作用'
    return ''


def coverage_issue(rows: list, events: dict, people: dict, units: dict, status: str) -> str:
    if status == 'uncertain':
        return ''
    chapters={u['id'] for u in units.values() if u['level']=='chapter'}
    checked={event_chapter(e,units) for e in events.values() if e['granularity']=='detail'}
    if chapters-checked:
        return '有章节尚无可定位的细拆事件，不能将未核对的章节登记为零人；请补证或将阵容范围标为存疑'
    expected = {(e['id'], canonical_person(p, people)) for e in events.values()
                if e['granularity'] == 'detail' for p in e['characters']}
    covered = {(r['node_ids'][0], canonical_person(r['characters'][0], people)) for r in rows
               if len(r['node_ids']) == len(r['characters']) == 1}
    missing = expected - covered
    if missing:
        example = '、'.join(f'{event}/{person}' for event, person in sorted(missing)[:4])
        return f'有细拆事件人物尚未逐项核对阵容（{example}），补充观察或标明当前范围存疑'
    return ''
