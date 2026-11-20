"""Natural chapter breaks are reviewed against the actual final paragraph of a pinned draft."""
from dataclasses import asdict
import json

from nw.models import Draft
from nw.store import Store


WRITING = ('本章在 2000–2500 个非空白字符之间都可。场景字数只是分配建议，按事件、人物动作与对话的自然段落写，'
           '给后续待写场留出展开空间，最后一场在完整段落或叙事节拍收束处换章，悬念可以留到下一章。')
REVIEW_CONTRACT = '[CHAPTER_END_REVIEW_V1]'
REVIEW = (REVIEW_CONTRACT + ' 审读本章实际末段，在 notes 字符串自由意见后另起三行依次填写“章末状态：natural 或 revise”、'
          '“章末引句：实际引文”、“章末理由：具体理由”。章末引句逐字引用最后一段的结尾，'
          '覆盖末句或足以辨认其收束的最后一段语句（至多200字符）。章末理由说明人物行动、对话或信息在哪个节拍停下。'
          '完整自然的段落结尾填 natural；机械截字、半句或被切断的段落填 revise 并指出应在哪里收束。')


def chapter_end(package: dict) -> bool:
    for row in package.get('items', ()):
        if row.get('source') == 'chapter:length':
            progress = json.loads(row['text'])
            return progress.get('length_mode') == 'tiered' and progress.get('chapter_end') is True
    return False


def chapter_break_from_notes(notes: str) -> dict:
    rows = notes.rstrip().splitlines()[-3:] if isinstance(notes, str) else []
    markers = ('章末状态：', '章末引句：', '章末理由：')
    if len(rows) != len(markers) or any(not row.startswith(mark) for row, mark in zip(rows, markers)):
        raise ValueError('章末审稿须在 notes 末尾记录状态、实际末段引句和理由')
    status, quote, reason = (row.removeprefix(mark).strip() for row, mark in zip(rows, markers))
    return {'status': status, 'quote': quote, 'reason': reason}


def break_is_natural(check: object, draft: Draft) -> bool:
    if not isinstance(check, dict) or set(check) != {'status', 'quote', 'reason'}:
        raise ValueError('章末审稿缺少 chapter_break 的状态、末段引句或理由')
    quote, reason = check['quote'], check['reason']
    lines = draft.text.rstrip().splitlines()
    last = lines[-1].strip() if lines else ''
    if (check['status'] not in ('natural', 'revise') or not isinstance(reason, str) or not reason.strip()
            or not isinstance(quote, str) or not last or not min(8, len(last)) <= len(quote) <= 200
            or not last.endswith(quote)):
        raise ValueError('章末审读须逐字引用本版最后一段的结尾并说明断章理由')
    closing_marks = "”’」』）》】）" + "'\""
    ending = last.rstrip(closing_marks).rstrip()
    return check['status'] == 'natural' and not ending.endswith(('，', ',', '、', '：', ':'))


def require_break_review(store: Store, draft: Draft, manifest_id: str) -> None:
    from nw.story_delta import draft_ref
    from nw.tasks import read_input_manifest
    manifest, delta_package = read_input_manifest(store, manifest_id)
    if not (run_id := delta_package.get('material_review_run')):
        raise ValueError('章末缺少与本版正文对应的自然断章审稿')
    run = store.get('run', run_id)
    snapshot = json.loads(run.input_snapshot_json)
    if (run.kind != 'review' or run.finish_reason != 'complete' or not run.ended_at or run.scene_id != draft.scene_id
            or not isinstance(snapshot, dict) or not snapshot.get('manifest_id')):
        raise ValueError('章末缺少对应本场本版的独立审稿')
    reviewed, context = read_input_manifest(store, snapshot['manifest_id'])
    messages = snapshot['messages']
    payload = json.loads(messages[-1]['content'])
    if (reviewed['purpose'] != 'review' or asdict(draft_ref(draft)) not in reviewed['dependency_refs']
            or any(manifest[key] != reviewed[key] for key in
                   ('branch_id', 'state_revision', 'story_order', 'disclosure_order', 'candidate_delta_refs'))
            or payload.get('draft') != asdict(draft) or payload.get('context') != context
            or not chapter_end(context) or REVIEW_CONTRACT not in messages[0]['content']):
        raise ValueError('章末审稿未对应本场、当前版本和分支输入')
    output = json.loads(run.output_text)
    if output.get('recommendation') != 'pass' or not break_is_natural(chapter_break_from_notes(output.get('notes', '')), draft):
        raise ValueError('章末需在完成的自然段或叙事节拍处换章')
