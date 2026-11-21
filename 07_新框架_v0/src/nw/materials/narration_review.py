"""Evidence and POV-safe feedback for the scene's ordered narration beats."""
from nw.models import Draft


PREFIX = 'work:narration:'
FIXES = {
    'viewpoint': '分清谁亲历、听见或推测；把他人未说出口的判断还给有权限的视角。',
    'time': '使读者认得讲述的时间和回到当下的位置。',
    'causality': '对照本场依据区分已发生的事实、猜测和未决原因。',
    'expression': '按本场安排调整概述、重演、想法、对话或可见反应的呈现。',
    'effect': '补出本节拍怎样改变理解、语气、交流、选择或读者所知。',
    'missing': '按冻结工作包补出当前稿尚无依据的叙述节拍。',
    'order': '依本场批准的讲述顺序安排相关句段。',
}
PROMPT = (
    'work:narration: 检查沿用 id、status、reason、evidence 四个字段。通过时在 reason 解释读者由哪处措辞或变化'
    '看出谁知道或推测什么。发现问题时给 failed 或 unverified，并在 reason 开头以方括号标明问题，如 [viewpoint]，可选 '
    + '、'.join(FIXES) + '；后面说明与本稿的关系。'
    '按 narration_order 核对文本中的讲述次序，允许多个效果落在同一句。'
    '人物回忆和叙述者向读者交代的既定往事须分清；未证因果、他人内心的归属或从过去返回当下有误，给相应问题和原句。'
    '缺写可用 [missing]、failed 和空 evidence；其余判断尽可能指出当前稿的相关句段。'
)


def issue(row: dict) -> str:
    """Keep the durable review in its established four-field format."""
    reason = row['reason'].strip()
    code, separator, explanation = reason.partition(']')
    if separator and code.startswith('[') and code[1:] in FIXES:
        return code[1:]
    if separator and code == '[as_designed]':
        reason = explanation.strip()
    if row['status'] == 'unverified':
        return 'missing'
    if row['status'] != 'pass' or not reason or any(reason == span['quote'].strip() for span in row['evidence']):
        return 'effect'
    return 'as_designed'


def assess_beats(checks: list[dict], rows: list[dict], draft: Draft) -> None:
    """A later planned tell may share a sentence, but cannot occur only before its predecessor."""
    beats = sorted((check for check in checks if check['id'].startswith(PREFIX)),
                   key=lambda check: check['narration_order'])
    by_id = {row['id']: row for row in rows}
    start = 0
    for beat in beats:
        row = by_id[beat['id']]
        row['narration_issue'] = issue(row)
        if row['status'] != 'pass':
            continue
        if row['narration_issue'] != 'as_designed':
            row['status'] = 'failed'
            continue
        starts = [span['start'] for span in row['evidence'] if span['id'] == draft.id
                  and span['start'] >= start and len(''.join(span['quote'].split())) >= 8]
        if not starts:
            row.update(status='failed', narration_issue='order', reason=FIXES['order'])
            continue
        start = min(starts)


def revision_feedback(check: dict, draft: Draft) -> dict:
    """Only forward an enumerated correction and positions from the reviser's own draft."""
    locations = [{'start': span['start'], 'end': span['end']} for span in check['evidence']
                 if span['id'] == draft.id and span['version'] == draft.version]
    return {'fix': FIXES[check['narration_issue']], 'draft_locations': locations}


def reader_spans(checks: list[dict], rows: list[dict], draft: Draft) -> list[dict]:
    """Take the review's current-draft evidence only for actual narrator-owned beats."""
    reader_beats = {c['id']: c['method_artifact']['narration']['time'] for c in checks if c['id'].startswith(PREFIX)
                    and c['method_artifact']['narration']['owner'] is None}
    return [{'start': span['start'], 'end': span['end'], 'time': reader_beats[row['id']]} for row in rows
            if row['id'] in reader_beats and row['status'] == 'pass'
            for span in row['evidence'] if span['id'] == draft.id]


def check_state_audience(operations: list[dict], reader_only: list[dict]) -> None:
    if not reader_only:
        return
    for op in operations:
        if op['holder'] == 'READER':
            continue
        restricted = [r for r in reader_only if op['holder'] != 'WORLD' or r.get('time') == 'past']
        if restricted and not any(all(e['end'] <= r['start'] or e['start'] >= r['end'] for r in restricted)
                                  for e in op['evidence']):
            raise ValueError('MATERIAL_EVIDENCE: 仅向读者讲述的段落不能单独证明人物获知；回述往事也不能单独证明当下世界变化')
