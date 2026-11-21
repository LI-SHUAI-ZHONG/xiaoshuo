"""Evidence and POV-safe feedback for the scene's ordered narration beats."""
import json

from nw.models import Draft


PREFIX = 'work:narration:'
FIXES = {
    'viewpoint': '分清谁亲历、听见或推测；把他人未说出口的判断还给有权限的视角。',
    'person': '按场卡人称写叙述句，区分对白里的我与真正承担本场视角的人。',
    'witness': '补出本场人物实际听到、看到或后来获知的途径，使他的回应有依据。',
    'time': '使读者认得讲述的时间和回到当下的位置。',
    'causality': '对照本场依据区分已发生的事实、猜测和未决原因。',
    'expression': '按本场安排调整概述、重演、想法、对话或可见反应的呈现。',
    'effect': '补出本节拍怎样改变理解、语气、交流、选择或读者所知。',
    'missing': '按冻结工作包补出当前稿尚无依据的叙述节拍。',
    'order': '依本场批准的讲述顺序安排相关句段。',
}
_PROMPT_START = (
    'work:narration: 检查沿用 id、status、reason、evidence 四个字段。通过时在 reason 解释读者由哪处措辞或变化'
    '看出谁知道或推测什么。发现问题时给 failed 或 unverified，并在 reason 开头以方括号标明问题，如 [viewpoint]，可选 '
)
_PROMPT_END = (
    '；后面说明与本稿的关系。'
    '按 narration_order 核对文本中的讲述次序，允许多个效果落在同一句。'
    '人物回忆和叙述者向读者交代的既定往事须分清；未证因果、他人内心的归属或从过去返回当下有误，给相应问题和原句。'
    '缺写可用 [missing]、failed 和空 evidence；其余判断尽可能指出当前稿的相关句段。'
)
LEGACY_PROMPT = _PROMPT_START + '、'.join(k for k in FIXES if k not in ('witness','person')) + _PROMPT_END
PROMPT = (_PROMPT_START + '、'.join(FIXES) + _PROMPT_END +
          '若步骤版本 product_ref 为 @ 短引用，在本组检查的 stage_product_refs 读取相应完整版本。'
          '核对叙述句的人称及亲历感；人物台词中的“我”不能证明整场采用第一人称。'
          '按 witnesses 核对谁真正接收到消息，留意人物如何从所见所闻形成自己的判断、情绪和接下来的做法。')


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
    from nw.materials.cast_design import assess_hidden
    assess_hidden(checks, rows, draft)


def revision_feedback(check: dict, draft: Draft) -> dict:
    """Only forward an enumerated correction and positions from the reviser's own draft."""
    locations = [{'start': span['start'], 'end': span['end']} for span in check['evidence']
                 if span['id'] == draft.id and span['version'] == draft.version]
    return {'fix': FIXES[check['narration_issue']], 'draft_locations': locations}


def reader_spans(checks: list[dict], rows: list[dict], draft: Draft) -> list[dict]:
    """Pin the recipients of reviewed passages to the actual project character IDs."""
    limits = {}
    for check in checks:
        if not check['id'].startswith(PREFIX):
            continue
        beat = check['method_artifact']['narration']
        observable = json.loads(check['binding']['observable']) if 'binding' in check else {}
        if beat['owner'] is None:
            limits[check['id']] = {'time': beat['time']}
        else:
            if 'witnesses' in observable:
                limits[check['id']] = {'time': beat['time'], 'mode': beat['mode'],
                    'holders': [observable['owner'], *observable['witnesses']]}
        if 'cast_subject' in observable and check['id'] in limits:
            limits[check['id']].update(cast_subject=observable['cast_subject'], cast_basis=observable['basis_claim'],
                                       mode=beat['mode'])
    return [{'start': s['start'], 'end': s['end'], **limits[row['id']]} for row in rows
            if row['id'] in limits and row['status'] == 'pass' for s in row['evidence'] if s['id'] == draft.id]


def check_state_audience(operations: list[dict], reader_only: list[dict]) -> None:
    if not reader_only:
        return
    for op in operations:
        holder = op['holder']
        identity_fact = op.get('claim') == 'fact' and op.get('predicate', '').startswith('identity_status:')
        if identity_fact:
            introductions = [r for r in reader_only if 'cast_subject' in r and (
                r['cast_subject'] != op['entity_id'] or r['mode'] == 'speech' and r['cast_basis'] == 'cast_entry')]
            if introductions and not any(all(e['end'] <= r['start'] or e['start'] >= r['end'] for r in introductions)
                                         for e in op['evidence']):
                raise ValueError('MATERIAL_EVIDENCE: 他人的身份披露、自报或转述，不能单独证实此人的真实身份')
        if holder == 'READER':
            continue
        if holder == 'WORLD':
            restricted = [r for r in reader_only if r['time'] == 'past' or
                          r.get('mode') in ('perception', 'thought', 'inference')]
        else:
            restricted = [r for r in reader_only if holder not in r.get('holders', ())]
        if restricted and not any(all(e['end'] <= r['start'] or e['start'] >= r['end'] for r in restricted)
                                  for e in op['evidence']):
            raise ValueError('MATERIAL_EVIDENCE: 仅向读者讲述或本人未见证的段落不能单独证明人物获知；人物心声与回述往事也不能单独证明当下世界变化')
