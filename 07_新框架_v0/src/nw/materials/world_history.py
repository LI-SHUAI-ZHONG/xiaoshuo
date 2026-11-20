"""Select compatible approved histories and verify their use on actual receiving products."""
from collections.abc import Iterable, Iterator
import re

from nw.materials.semantic_application import output_value, pointer_tokens, require
from nw.materials.world_resources import approved_text


POLICY = 'world-history-prerequisites-v1'


def history_families() -> tuple:
    from nw.materials import world_history_periods as periods, world_history_impacts as impacts

    return ((periods.RULES, periods.approved_period), (impacts.RULES, impacts.approved_history_impact))


def consistent_history_cards(key: str, cards: list[dict], approved: list[dict]) -> list[dict]:
    from nw.materials import world_history_periods as periods, world_history_impacts as impacts

    if key in periods.RULES:
        if len(approved) < 2:
            return cards
        # A later phase cannot have started earlier in the same local calendar.
        all_dates = [proof['evidence'] for card in approved for other in periods.RULES
                     if (proof := periods.approved_period(card, other))]

        def conflicts(evidence: dict, other: dict) -> bool:
            if evidence['world'] != other['world']:
                return False
            order = periods.PERIODS.index(evidence['after']) - periods.PERIODS.index(other['after'])
            measures = []
            if evidence['calendar'] and evidence['calendar'] == other['calendar']:
                measures.append((evidence['year'], other['year']))
            if evidence.get('time_anchor') and evidence['time_anchor'] == other.get('time_anchor'):
                a, b = evidence.get('offset'), other.get('offset')
                measures.append((a, b))
                directions = periods.relative_direction(evidence['time_text'], a), periods.relative_direction(other['time_text'], b)
                if directions[0] * directions[1] < 0:
                    measures.append(directions)
            return any(left is not None and right is not None and
                       (left != right if order == 0 else order * (left - right) < 0)
                       for left, right in measures)

        return [card for card in cards if not any(conflicts(card['evidence'], other) for other in all_dates)]

    return impacts.consistent_impact_cards(key, cards)


_CONFIRMED = re.compile(r'(?:但|然而|经查|随后|最终|其实|事实上|实际|却)[^，。；！？]{0,12}?(?:证实|确认|载明|记载|查明|核实)|'
                        r'(?:原始档案|原始记录|同期实录|原始卷宗)(?:证实|确认|载明)')
_NONFACT = re.compile(r'据说|传闻|传言|谣言|据传|相传|听说|听闻|假如|假设|如果|假使|倘若|声称|谎称|伪称|伪造|'
                      r'本想|打算|计划|设想|推测|猜测|怀疑|怀疑是否|能否|是否|质疑|询问|待查|查证是否|调查是否|'
                      r'查证|试图|宣称|假称|否认|误以为|误记为|误传|原以为|错误记作|待证|并非|不是')
_CITED_RECORD = re.compile(r'(?:原始档案|原始卷宗|同期实录|同期档案|原始记录|档案|卷宗)(?:证实|载明|确认|记载)[：:，,]?\s*$')
_RETRACTED = re.compile(r'^.{0,4}?(?:的传闻|的传言|的谣言|的假消息|之说未经证实|的说法(?:待证|未经证实))|^[，,]?(?:这|此说|此事)?(?:只是|仅是|系|是)(?:未经证实的)?(?:传闻|传言|谣言|推测|假设)')


def factual_history_claim(statement: str, start: int, end: int) -> bool:
    """Scope hearsay and investigation to the assertion, including a later factual correction."""
    prefix = _CONFIRMED.split(statement[:start])[-1]
    if statement.rstrip().endswith(('?', '？')) or _NONFACT.search(prefix):
        return False
    original = statement[:start]
    for left, right in (('“', '”'), ('「', '」'), ('『', '』')):
        pos = original.rfind(left)
        if pos > original.rfind(right) and not _CITED_RECORD.search(original[:pos]):
            return False
    return not _RETRACTED.search(statement[end:].lstrip())


def _proofs(handoff: dict, key: str, products: dict, context: dict) -> list[dict]:
    if handoff['origin']['stage'] != 'world_design' or handoff['source_id'] not in context.get('world_network_bases', {}):
        return []
    matcher = next((match for rules, match in history_families() if key in rules), None)
    if matcher is None:
        return []
    indices = {int(tokens[1]) for row in handoff['actual_inputs'] if len(tokens := pointer_tokens(row['path'])) == 4
               and tokens[0] == 'members' and tokens[1].isdecimal() and tokens[2] == 'body' and tokens[3] in ('rule', 'limits')}
    require(bool(indices), key + ' 历史交接缺少实际世界产物')
    refs = set(handoff['requirement']['input_refs'])
    result = []
    for index in sorted(indices):
        body = products['world_design']['products']['members'][index]['body']
        candidates = [card for card in context.get('approved_cards', []) if approved_text(card) == (body['rule'], body['limits'])
                      and {f"approved:{card['card_id']}:/body/{field}" for field in ('rule', 'limits')} <= refs]
        require(len(candidates) == 1 and (proof := matcher(candidates[0], key)) is not None,
                key + ' 历史交接须保留原批准卡和实际世界产物')
        result.append(proof['evidence'])
    return result


def receipt_guidance(handoffs: list[dict], products: dict, context: dict, keys: dict) -> dict:
    result = {}
    for handoff in handoffs:
        key = keys.get(handoff['source_id'])
        if key and (proofs := _proofs(handoff, key, products, context)):
            result[handoff['id']] = {'key': key, 'evidence': proofs}
    return result


_NON_STORY_FIELDS = {'id', 'key', 'kind', 'label', 'title', 'tags', 'status', 'source_id', 'source_ids', 'profile',
                     'sha256', 'contract_sha256', 'task_id', 'ref', 'source_refs'}


def _texts(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)
    elif isinstance(value, dict):
        for name, item in value.items():
            if name not in _NON_STORY_FIELDS and not name.startswith('_'):
                yield from _texts(item)


def _receiving_fields(value: dict, refs: list[str]) -> Iterator[tuple[list[str], list[str]]]:
    """Keep cited fields together only if they belong to the same actual story product."""
    groups: dict[str, list[str]] = {}
    for ref in refs:
        tokens = pointer_tokens(ref)
        target = output_value(ref, value)
        owner = value
        path = ''
        owner_path = ref
        for raw, token in zip(ref[1:].split('/'), tokens):
            path += '/' + raw
            if isinstance(owner, list):
                owner = owner[int(token)]
                if isinstance(owner, dict):
                    owner_path = path
            else:
                owner = owner[token]
        cited = groups.setdefault(owner_path, [])
        if not (_NON_STORY_FIELDS.intersection(tokens)
                or isinstance(target, list) and any(isinstance(r, dict) for r in target)):
            cited.extend(_texts(target))
    for owner_path, cited in groups.items():
        yield cited, list(_texts(output_value(owner_path, value)))


def check_history_receipt(handoff: dict, refs: list[str], value: dict, products: dict, context: dict, key: str) -> None:
    if context.get('world_history_policy') != POLICY:
        return
    proofs = _proofs(handoff, key, products, context)
    if not proofs:
        return
    from nw.materials.world_history_dates import check_dates, mentions_transition
    from nw.materials.world_history_impacts import check_impact_claims
    from nw.materials.world_history_periods import RULES as PERIOD_RULES

    for cited, surrounding in _receiving_fields(value, refs):
        for proof in proofs:
            mentions_anchor = any(anchor in text for text in cited for anchor in proof['anchors'] if anchor)
            mentions_period = key in PERIOD_RULES and any(mentions_transition(proof, text) for text in cited)
            require(mentions_anchor or mentions_period, key + ' 历史回执指向的实际设计缺少本项目的历史依据')
            if key in PERIOD_RULES:
                check_dates(key, proof, surrounding)
            else:
                check_impact_claims(key, proof, surrounding)
