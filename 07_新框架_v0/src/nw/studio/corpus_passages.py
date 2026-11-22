"""Optional, source-ordered narration observations within the v5 corpus."""
from nw.studio.corpus_story_observations import event_chapter
from nw.passage_catalog import OBSERVATIONS
from bisect import bisect_right


KINDS = {
    'procedure_branch': {'label': '先示范一次办理，再对照不同选择',
                         'required_roles':['demonstration','different_choice'],
                         'roles': {'demonstration':'示范办理', 'compression':'略过重复', 'different_choice':'分叉到新选择',
                                   'handoff':'交出结果或留下下一步问题'}},
    'focus_relay': {'label': '从空间或群体逐步聚焦具体人物',
                    'required_roles':['orientation','attention','focus'],
                    'roles': {'orientation':'交代现场', 'attention':'转接注意', 'focus':'落到具体对象',
                              'handoff':'以新细节或问题接向下文'}},
}
CRAFT_KINDS = {key: {'label':label, 'required_roles':list(roles), 'roles':roles}
               for key, (label, roles) in OBSERVATIONS.items()}
CRAFT_KINDS['place_function']['role_order_flexible'] = True
JUDGMENT_KINDS = {'qualified_claim', 'interpreted_motive'}


def judgment_issue(sequence: dict, claim_status: str | None = None) -> str:
    if sequence.get('kind') not in JUDGMENT_KINDS:
        return ''
    if claim_status == 'stated' or any(
        beat['claim_status'] == 'stated' or beat['story_change'] or not beat['reader_change']
        for beat in sequence['beats']
    ):
        return '估计或对他人动机的解释须保留为人物说法、推断或未知，只能记录读者所得；实际言行与后续证实另引事件'
    return ''


def paratext_evidence(evidence: dict) -> set[str]:
    """Match offsets as well as IDs so a second citation cannot relabel the same words."""
    spans = sorted((e['start'], e['end']) for e in evidence.values()
                   if e.get('text_role') in ('heading','reader_address'))
    if not spans:
        return set()
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    ends = [end for _, end in merged]
    result = set()
    for key, row in evidence.items():
        i = bisect_right(ends, row['start'])
        if i < len(merged) and merged[i][0] < row['end']:
            result.add(key)
    return result


def sequence_issue(thread: dict, events: dict, evidence: dict, units: dict, content: str | None = None) -> str:
    sequence=thread['details'].get('passage_sequence')
    if sequence is None:
        return ''
    if issue := judgment_issue(sequence, thread['details'].get('claim_status')):
        return issue
    chapter=None
    previous_end=None
    previous_event=None
    independent = sequence.get('kind') in CRAFT_KINDS and sequence['kind'] != 'paragraph_turn'
    for beat in sequence['beats']:
        event=events.get(beat['event_id'])
        quote=evidence.get(beat['evidence_id'])
        if (not event or event['granularity']!='detail' or not quote or event['id'] not in thread['node_ids']
                or quote['id'] not in event['evidence_ids'] or quote['id'] not in thread['evidence_ids']):
            return '段落链各落点须同时引用本观察、本章细拆事件和该事件的实际原句'
        current=event_chapter(event,units)
        if not current or chapter and current!=chapter:
            return '连续段落的证据须来自同一章'
        if content is not None and units[current].get('boundary_basis')=='source_heading':
            chapter_unit=units[current]
            line_end=content.find('\n',chapter_unit['start'],chapter_unit['end'])
            body_start=line_end+1 if line_end!=-1 else chapter_unit['end']
            if quote['start']<body_start and not content[body_start:quote['end']].strip():
                return '章名只能定位章节，段落链的现场落点须引用故事正文'
        if previous_end is not None:
            if quote['start']<previous_end:
                return '段落链须按原文实际位置递进，不能倒排或重用同一处引文'
            if content is not None and not (independent and previous_event == event['id']):
                gap=content[previous_end-1:quote['start']+1].splitlines()
                if any(line.strip() for line in gap[1:-1]):
                    return '段落链跨过了未举证的完整自然段，请补中间承接原句或缩小观察范围'
        chapter=current
        previous_end=quote['end']
        previous_event=event['id']
    return ''


def method_sequence(thread: dict) -> dict:
    sequence=thread['details']['passage_sequence']
    return {'thread_id':thread['id'], 'kind':sequence['kind'], 'condition':sequence['condition'],
            'boundary':sequence['boundary'], 'beats':[
                {k:v for k,v in b.items() if k not in ('event_id','evidence_id')} for b in sequence['beats']]}
