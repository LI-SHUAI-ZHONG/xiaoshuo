"""Chapter progress and the work a character performs at a particular encounter."""
from collections.abc import Iterable

STORY_DETAILS = {
    'chapter_progress': {
        'entry_condition': '章场开始时仍然有效的事情、人物或世界正在做什么',
        'turn': '触发进展的交流、发现、念头、决定或外来事件及其来由',
        'change': '谁的认知、关系、处境、选择或行动从什么变成什么',
        'knowledge_change': '谁经何途径实际得知什么，谁仍不知或误信（有原文才填）',
        'next_pressure': '此次结果留下什么具体问题或机会（有原文才填）',
        'later_use': '后续另一章实际怎样用上这个收获或后果；尚未写到留空',
    },
    'cast_entry': {
        'plot_need': '什么剧情需要或交接把这个人带到此处',
        'position': '原作可判定的人物地位或阵营；仅见一段不能断定主次时留空',
        'function': '此人在本次事件实际提供、阻止、触发或交接了什么',
        'own_reason': '此人自己的目的、压力及参与的理由（缺证留空）',
        'encounter': '在怎样的情境与谁发生交集，行动或交流造成什么作用',
        'identity_access': '谁自报或介绍了什么，谁听见、相信、存疑；真实身份是否已有依据',
        'claim_status': '这次出场时可知的身份依据：原文确证、人物说法、分析推断或未知',
        'later_reveal': '稍后原文确实揭露的身份及对旧交集的影响；只留下疑点时留空',
    },
}

REQUIRED_DETAILS = {
    'chapter_progress': ('entry_condition', 'turn', 'change'),
    'cast_entry': ('plot_need', 'function', 'encounter'),
}

# Each task already has a real production route, output and applicability contract.
STORY_TASKS = {
    'chapter_progress': ('chapter_outline', 'event_chain', 'scene_composition', 'information', 'state_change'),
    'cast_entry': ('character_arc', 'subplot', 'information', 'foreshadow', 'scene_composition'),
}


def event_chapter(event: dict, units: dict) -> str | None:
    unit = units.get(event['unit_id'], {})
    if unit.get('level') == 'scene':
        unit = units.get(unit.get('parent_id'), {})
    return unit.get('id') if unit.get('level') == 'chapter' else None


def _people(ids: list, characters: dict) -> set[str]:
    people=set()
    for person in ids:
        seen=set()
        while person not in seen and (canonical:=characters.get(person,{}).get('canonical_id')):
            seen.add(person)
            person=canonical
        people.add(person)
    return people


def story_observation_issue(thread: dict, events: dict, links: Iterable[dict], units: dict,
                            evidence: dict, characters: dict) -> str:
    domain = thread['domain']
    if domain not in STORY_DETAILS or thread['status'] == 'uncertain':
        return ''
    if not all(thread['details'][key] for key in REQUIRED_DETAILS[domain]):
        return '章场观察须说明本场来由、实际推进或人物作用；未能判断可标存疑'
    nodes = [events[node] for node in thread['node_ids'] if node in events]
    quotes = set(thread['evidence_ids'])
    if not nodes or any(event['granularity'] != 'detail' or not quotes.intersection(event['evidence_ids']) for event in nodes):
        return '章场观察须逐个对应细拆事件及其原作短引'
    if any(not event_chapter(event, units) for event in nodes):
        return '章场观察的细拆事件须定位到原作的具体章节或章内场景'
    if domain == 'cast_entry':
        people = _people([who for event in nodes for who in event['characters']],characters)
        subjects = _people(thread['characters'],characters)
        if not subjects or not subjects <= people:
            return '人物出场观察须指定确实属于所引事件的人物'
        if thread['details']['claim_status'] != 'unknown' and not thread['details']['identity_access']:
            return '声称可以判断出场身份时须说明当时谁怎样得知、转述或推断'
    later_key = 'later_use' if domain == 'chapter_progress' else 'later_reveal'
    if not thread['details'][later_key]:
        return ''
    kinds = {'causes', 'enables', 'changes_character'} if domain == 'chapter_progress' else {'reveals', 'pays_off'}
    node_ids = {e['id'] for e in nodes}
    for link in links:
        if (link['thread_id'] != thread['id'] or link['kind'] not in kinds or link['certainty'] != 'observed'
                or not {link['source'], link['target']} <= node_ids):
            continue
        before, after = events[link['source']], events[link['target']]
        if domain == 'chapter_progress' and event_chapter(before,units) == event_chapter(after,units):
            continue
        if domain == 'cast_entry' and not subjects <= (_people(before['characters'],characters) & _people(after['characters'],characters)):
            continue
        cited = quotes.intersection(link['evidence_ids'], evidence)
        if any(evidence[a]['end'] <= evidence[b]['start'] for a in cited.intersection(before['evidence_ids'])
               for b in cited.intersection(after['evidence_ids'])):
            return ''
    return ('声称跨章用上收获须有前后两章的实际事件、按序原句和已观察的承接关系'
            if domain == 'chapter_progress' else '声称后来揭晓身份须有出场和揭晓两处按序原句及已观察的揭示关系')
