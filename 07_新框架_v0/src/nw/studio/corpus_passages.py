"""Optional, source-ordered narration observations within the v5 corpus."""
from nw.studio.corpus_story_observations import event_chapter


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


def sequence_issue(thread: dict, events: dict, evidence: dict, units: dict, content: str | None = None) -> str:
    sequence=thread['details'].get('passage_sequence')
    if sequence is None:
        return ''
    chapter=None
    previous_end=None
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
            if content is not None:
                gap=content[previous_end-1:quote['start']+1].splitlines()
                if any(line.strip() for line in gap[1:-1]):
                    return '段落链跨过了未举证的完整自然段，请补中间承接原句或缩小观察范围'
        chapter=current
        previous_end=quote['end']
    return ''


def method_sequence(thread: dict) -> dict:
    sequence=thread['details']['passage_sequence']
    return {'thread_id':thread['id'], 'kind':sequence['kind'], 'condition':sequence['condition'],
            'boundary':sequence['boundary'], 'beats':[
                {k:v for k,v in b.items() if k not in ('event_id','evidence_id')} for b in sequence['beats']]}
