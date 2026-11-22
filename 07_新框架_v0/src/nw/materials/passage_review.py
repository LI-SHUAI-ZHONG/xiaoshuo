"""Project only the adopted passage steps and check their actual order in prose."""
import json
import re

from nw.task_models import canonical


METHODS = {
    'procedure_branch': '从一例完整办理转到后一个人的不同选择',
    'focus_relay': '从现场通过可感知的线索逐步移到具体人物或动作',
}
ROLES = {
    'demonstration': '让读者看清第一次办理的要求、实际操作和可见结果。',
    'compression': '略过重复办理，保留经过的时间、顺序或接下来值得看的差异。',
    'different_choice': '在相同规则下写出不同选择及此刻切实发生的后果。',
    'orientation': '用此处正在发生的事确立地点和读者的位置。',
    'attention': '给出把读者带到下一个观察对象的声音、目光、动作或空间联系。',
    'focus': '落到具体的人或物，写出此刻可见的新信息或变化。',
    'handoff': '写清眼下实际交出的物件或得到的信息，为仍待发生的事留出后续。',
}
DETAIL = {'scene': '展开现场', 'summary': '概述经过', 'ellipsis': '省略重复、交代承接', 'pause': '停在有作用的细节'}
STATUS = {'observed': '已呈现的情况', 'inference': '人物的判断待证', 'pending': '尚未兑现的可能'}
FIXES = {
    'passage_link': '补出前一处声音、动作、物件或选择如何引出本拍，让读者跟得上。',
    'passage_order': '依次落下本场选中的叙述动作，使各自的变化有能单独定位的原句；可在一句内承接。',
    'passage_detail': '按本拍安排展开、概述或略过已有过程，把篇幅留给带来变化的选择、动作或细节。',
    'passage_status': '区分读者目前看到的事、人物自己的推断及仍待发生的结果。',
    'passage_evidence': '对照本拍要表达的变化，检查当前稿中读者能具体看见或听见什么。',
}
_REVIEW = (
    '带 passage_step 的叙述检查逐拍对照实际稿件。每个通过项的 reason 用中文引号“”摘出其本稿 evidence 中'
    '明确体现本拍的短语，再解释它怎样改变读者所见、所知或所期待，以及怎样承接上一拍。'
    '不同参与拍分别引用可按顺序独立定位且互不重叠的语句或分句，可以合段、拆段。'
    '如果一句短命令或跳时提示不足八字，已经承担本拍，在 evidence 单独定位这句，另引本稿中有助于读懂它的足八字上下文，'
    'reason 用引号摘出短句的关键字词。顺序和受众均按短句本身定位，无需改长原文。'
    '以原来确定的观察者核对人物已知与读者已知。'
    '若含 passage_source，对照 passage_fit 和 passage_limits 的适用前置与禁用情形，核对其 operation 在这拍具体体现在哪里。'
    'inference/pending 仅引体现推测、选项或待办的文字；若后续真有确认，另引后来实际发生的独立证据。'
    '失败时用 [passage_link]、[passage_order]、[passage_detail]、[passage_status] 或 [passage_evidence] 指明缺陷。'
)
_METHOD_REVIEW = {
    'procedure_branch': '办理分流依据 passage_comparison 的共同关口、两个人与各自实际做法核对原句，交代第二个人具体改选了什么。'
                        '核对示范是否交代了过程与实际所得，略写处有没有重复演全套，后人的不同选择是否仍留有待兑现的结果。',
    'focus_relay': '注意力转移核对切换的可感知依据及具体落点；跟随他人的目光不取得其私下想法，叙述者交代的信息不自动进入人物所知。',
}
_QUOTED = re.compile(r'[“「『"]([^”」』"\n]+)[”」』"]')


def review_prompt(checks: list[dict]) -> str:
    kinds = {check['passage_step']['kind'] for check in checks if 'passage_step' in check}
    return _REVIEW + ''.join(_METHOD_REVIEW[kind] for kind in sorted(kinds)) if kinds else ''


def _anchors(reason: str) -> set[str]:
    reason = reason.removeprefix('[as_designed]').strip()
    if not any(c.isalnum() for c in _QUOTED.sub('', reason)):
        return set()
    anchors = {value for value in _QUOTED.findall(reason) if any(c.isalnum() for c in value)}
    # A reviewer may reproduce a phrase in ordinary prose without quote marks.
    anchors.update(reason[i:i + 4] for i in range(len(reason) - 3) if reason[i:i + 4].isalnum())
    return anchors


def primary_spans(row: dict, draft_id: str, *, pinpoint=False) -> list[dict]:
    """A separately pinpointed short turn takes precedence over its corroborating context."""
    if pinpoint:
        # On a shared beat, another technique may cite the same paragraph for a
        # completed act. Locate the old sequence's quoted change separately.
        focus = row['reason'].split('【',1)[0]
        pins = {}
        for quote in _QUOTED.findall(focus):
            for span in row['evidence']:
                if span['id']==draft_id and span['quote'].count(quote)==1:
                    start = span['start']+span['quote'].index(quote)
                    pins[start,start+len(quote)] = {**span,'start':start,'end':start+len(quote),'quote':quote}
        if pins:
            return [pins[k] for k in sorted(pins)]
    anchors = _anchors(row['reason'])
    spans = [s for s in row['evidence'] if s['id'] == draft_id and any(a in s['quote'] for a in anchors)]
    short = [s for s in spans if len(''.join(s['quote'].split())) < 8]
    return short or spans


def attach_steps(checks: list[dict], records: dict, scene: str, references: list[dict]) -> None:
    choices = records.get('scene_design', {}).get('products', {}).get('passage_choices', [])
    choice = next((item for item in choices if item['scene'] == scene), None)
    if not choice or choice['kind'] not in METHODS:
        return
    sequences = records.get('expression_design', {}).get('products', {}).get('passage_sequences', [])
    sequence = next((item for item in sequences if item['scene'] == scene), None)
    if not sequence:
        raise ValueError('MATERIAL_DESIGN: 本场采用的连续叙述方法缺少表达步骤产物')
    beats = {check['narration_order']: check for check in checks if 'narration_order' in check}
    previous = None
    for step in sequence['steps']:
        check = beats[step['beat']]
        visible = json.loads(check['binding']['observable'])
        # The reviewer can read the design rationale. The writer sees only words
        # already approved for this scene, with the original recipient boundary.
        focus, bridge = step['focus_quote'], step['bridge_quote']
        if focus not in visible['observable'] or previous and bridge not in previous['observable']:
            raise ValueError('MATERIAL_DESIGN: 本场连续叙述落点和承接必须来自所选拍的可见表达')
        visible['passage_step'] = {'method': METHODS[choice['kind']], 'role': step['role'], 'focus': focus,
                                   'detail': DETAIL[step['detail']], 'status': STATUS[step['status']]}
        if previous:
            visible['passage_step']['from_beat'] = previous['order']
            visible['passage_step']['bridge'] = bridge
            visible['passage_step']['from_audience'] = previous['audience']
        else:
            check['passage_choice'] = choice.copy()
        comparison = sequence.get('comparison', {})
        for side in ('example', 'branch'):
            if comparison.get(side + '_beat') == step['beat']:
                visible['passage_step']['actor'] = comparison[side + '_actor']
                visible['passage_step']['choice'] = comparison[side + '_choice']
                check['passage_comparison'] = comparison.copy()
        if sequence.get('source_beat') == step['beat']:
            check['passage_source'] = {'ref': choice['source_ref'], 'operation': sequence['source_operation']}
            ref = next((row for row in references if row['ref'] == choice['source_ref']), None)
            if ref is None:
                raise ValueError('MATERIAL_DESIGN: 本场实际采用的段落方法缺少冻结来源')
            check['passage_limits'] = {key: ref[key] for key in ('applicability', 'non_applicability', 'prerequisites')}
            if 'fit' in choice:
                check['passage_fit'] = choice['fit'].copy()
        check['binding']['observable'] = canonical(visible)
        check['binding']['check'] += ' ' + ROLES[step['role']]
        if previous and previous['audience'] == 'reader_only':
            check['binding']['check'] += ' 上一拍由叙述者交给读者，人物本拍的反应另据他实际看到、听到或原已知道的事。'
        check['passage_step'] = {'kind': choice['kind'], **step}
        previous = {'order': step['beat'], 'observable': visible['observable'], 'audience': visible['audience']}


def assess(checks: list[dict], rows: dict, draft_id: str) -> None:
    if not any('passage_step' in check for check in checks):
        return
    # Keep feasible pairs of (last narration start, last passage end). The
    # earliest start and earliest end may come from different review citations.
    positions = [(0, 0)]
    for check in checks:  # assess_beats supplies scene-local narration order
        row = rows[check['id']]
        if row['status'] != 'pass':
            continue
        spans = [s for s in row['evidence'] if s['id'] == draft_id and len(''.join(s['quote'].split())) >= 8]
        if 'passage_step' in check:
            spans = primary_spans(row, draft_id)
            earliest = min(max(start, end) for start, end in positions)
            candidates = [(s['start'], s['end']) for s in spans if s['start'] >= earliest]
        else:
            candidates = [(s['start'], end) for start, end in positions for s in spans if s['start'] >= start]
        if not candidates:
            code = 'passage_order' if spans else 'passage_evidence'
            row.update(status='failed', narration_issue=code, reason=FIXES[code])
            continue
        positions = []
        for start, end in sorted(candidates):
            if not positions or end < positions[-1][1]:
                positions.append((start, end))
