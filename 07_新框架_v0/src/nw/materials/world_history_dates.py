"""Compare dates only when the assertion actually dates this world's historic transition."""
import re
from collections.abc import Iterable

from nw.materials.semantic_application import require
from nw.materials.world_history_periods import PERIODS, YEAR_NUMBER, year_value, relative_direction


_PHASE = '|'.join(PERIODS)
_START = re.compile(r'(?:^|[\s，,：:。“「『的在于与和按]|促使|导致|使|当年|年|证实|确认|查明|载明|记载|发现|显示|见证|记下|意味着)$')
_STATE = {'已处于', '仍处于', '尚处于', '处于'}
_LINK = r'(?:[，,]\s*)?(?:(?:正是|恰是|发生在|发生于|始于|时间为|时间是|时间在|是在|是于|始自于|始自|定于|为|在|于|是)\s*)?'
_UNDATED_YEAR = r'(?:(?:[一-龥A-Za-z]{0,6}历|公元|纪元|西元)\s*' + YEAR_NUMBER + r'年)'


def _transition(world: str) -> re.Pattern:
    return re.compile(re.escape(world) + r'(?:(?:于|在)\s*(?P<inline>[^，,。；;]{1,24}?(?:年|之后|以后|之前)))?[，,]?\s*'
                      + rf'(?:(?:由|从|自)(?P<before>{_PHASE}))?(?:正式|开始|终于|已经)?'
                      + rf'(?P<verb>转入|进入|步入|迈入|转为|过渡到|已处于|仍处于|尚处于|处于)(?P<after>{_PHASE})')


def mentions_transition(evidence: dict, text: str) -> bool:
    return any(_START.search(text[:m.start()]) and m['after'] in (evidence['before'], evidence['after'])
               for m in _transition(evidence['world']).finditer(text))


def _attached_time(pattern: str, lead: str, tail: str, inline: str, event: str) -> re.Match | None:
    if inline and (match := re.fullmatch(pattern, inline)):
        return match
    # Require an adjacent subject or the exact application event between the time and the subject.
    for match in re.finditer(pattern, lead):
        if (not _START.search(lead[:match.start()]) and not lead[:match.start()].endswith(('于', '在', '《', '“'))):
            continue
        remaining = lead[match.end():]
        if re.fullmatch(r'(?:[，,]\s*)?(?:(?:' + re.escape(event) + r')[，,]?\s*(?:促使|使|导致))?', remaining):
            return match
    return re.match(r'(?:的(?:时点|年份|时间|年代|转折))?' + _LINK + pattern, tail)


def _compare(key: str, proof: dict, claim: re.Match, stated: int, approved: int) -> None:
    source, target = proof['before'], proof['after']
    before, after = claim['before'], claim['after']
    if claim['verb'] in _STATE:
        earlier = PERIODS.index(after) < PERIODS.index(target)
        require(not (stated < approved and not earlier or stated > approved and earlier),
                key + ' 剧情所述当年时期与已批准时间线不符')
        return
    if stated < approved and PERIODS.index(after) > PERIODS.index(target):
        require(False, key + ' 剧情将后续历史转折提前到了已批准时期之前')
    if stated > approved and PERIODS.index(after) < PERIODS.index(target):
        require(False, key + ' 剧情将早期历史转折延后到了已批准时期之后')
    if before and stated == approved and (after == target or before == source or (after, before) == (source, target)):
        require((before, after) == (source, target), key + ' 剧情颠倒或改写了已批准的时期变化')
    if after == target and (before is None or before == source):
        require(stated == approved, key + ' 剧情所述转折年份与已批准纪年不符')


def check_dates(key: str, proof: dict, texts: Iterable[str]) -> None:
    from nw.materials.world_history import factual_history_claim

    absolute = re.escape(proof['calendar']) + rf'\s*(?P<n>{YEAR_NUMBER})\s*年' if proof['calendar'] and proof['year'] is not None else ''
    relative = ''
    if proof.get('time_anchor'):
        from nw.materials.world_history_periods import RELATIVE_OFFSET, relative_offset
        relative = re.escape(proof['time_anchor']) + rf'(?P<offset>{RELATIVE_OFFSET})'
    transitions = _transition(proof['world'])
    event = re.compile(re.escape(proof['event']))
    for text in texts:
        for sentence in re.findall(r'[^。；;！？!?\r\n]+[。；;！？!?]?', text):
            for claim in transitions.finditer(sentence):
                lead, tail = sentence[:claim.start()], sentence[claim.end():]
                if not _START.search(lead) or not factual_history_claim(sentence, claim.start(), claim.end()):
                    continue
                inner = claim['inline'] or ''
                if absolute and (match := _attached_time(absolute, lead, tail, inner, proof['event'])):
                    if (year := year_value(match['n'])) is not None:
                        _compare(key, proof, claim, year, proof['year'])
                if relative and (match := _attached_time(relative, lead, tail, inner, proof['event'])):
                    offset = relative_offset(match['offset'])
                    if proof.get('offset') is not None and offset is not None:
                        _compare(key, proof, claim, offset, proof['offset'])
                    if claim['after'] == proof['after'] and claim['verb'] not in _STATE:
                        require(relative_direction(match['offset'], offset) == relative_direction(proof['time_text'], proof.get('offset')),
                                key + ' 剧情改写了历史转折相对于基准事件的先后')
                    if proof.get('offset') is None and offset is not None and claim['after'] == proof['after']:
                        require(False, key + ' 剧情给仅知先后的历史补写了未经批准的年数')
                if not absolute and claim['after'] == proof['after'] and claim['verb'] not in _STATE:
                    require(not _attached_time(_UNDATED_YEAR, lead, tail, inner, proof['event']),
                            key + ' 相对史时缺少可定位到绝对纪年的作者依据')
            if absolute:
                # Keep the local event date separate from dates of other events in the same sentence.
                for match in re.finditer(re.escape(proof['world']) + r'(?:于|在)' + absolute + r'[，,]?' + event.pattern, sentence):
                    if _START.search(sentence[:match.start()]) and factual_history_claim(sentence, match.start(), match.end()):
                        require(year_value(match['n']) == proof['year'], key + ' 剧情改写了已批准历史事件的年份')
