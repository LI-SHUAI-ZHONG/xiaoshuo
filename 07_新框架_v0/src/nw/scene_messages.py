"""Compose the same reviewer and reviser messages for capacity checks and execution."""
from collections.abc import Iterable
from dataclasses import asdict

from nw.materials.action_review import ACTION_ORDER_REASON, ACTION_REVIEW_PROMPT
from nw.materials.evidence import PROMPT as MATERIAL_REVIEW_PROMPT
from nw.materials.network_layers import POLICY as NETWORK_LAYER_POLICY, REVIEW_INSTRUCTION as NETWORK_LAYER_REVIEW
from nw.materials import narration_review
from nw.materials.stage_input import check_source_keys, step_material_prompt
from nw.models import Draft
from nw.task_models import canonical


REVIEW_PROMPT = (
    '审查本场与约束、场景目标、POV所知和前文的一致性。只输出 JSON '
    '{"recommendation":"pass或revise","notes":"具体意见","core_changes":[]}。'
    '只有影响核心人物目标、世界规则、重要生死、视角形式或终局承诺的变化才填入 core_changes。'
)
REVISE_PROMPT = (
    '根据冻结的工作包、旧稿和审稿意见修订本场。保持作者已确认的设定与披露边界，只输出完整修订正文。'
    '叙述节拍需要修订时，对照同号工作包和旧稿定位调整知情者、讲述次序或实际效果。'
)


def draft_messages(package: dict, purpose: str, draft: Draft, review: dict | None, contract: dict | None,
                   material: str, writing_keys: Iterable[str], length_feedback: list[str] | None = None) -> tuple[list[dict], str]:
    data = {'context': package, 'draft': asdict(draft)}
    if review is not None:
        checks = review.get('material_checks', ())
        # The independent reviewer can see author-only design and earlier chapter prose.
        if checks:
            ordered_actions_failed = any(check.get('reason') == ACTION_ORDER_REASON for check in checks)
            visible_checks = []
            for check in checks:
                status = check['status']
                if status == 'pass' and check['id'].startswith('work:layer:'):
                    status = check['layer_check']['status']
                visible = {'id': check['id'], 'status': status}
                if status != 'pass' and check['id'].startswith(narration_review.PREFIX):
                    visible.update(narration_review.revision_feedback(check, draft))
                visible_checks.append(visible)
            data['review'] = {
                'recommendation': review.get('recommendation'),
                'notes': (ACTION_ORDER_REASON if ordered_actions_failed else
                          '在现有披露范围内，复核写作包中的检查点和场景叙述。'),
                'material_checks': visible_checks,
            }
        else:
            data['review'] = {key: value for key, value in review.items() if key != 'length_feedback'}
    if length_feedback:
        data['length_feedback'] = length_feedback
    prompt, version = (REVIEW_PROMPT, 'novel-review-v1') if purpose == 'review' else (REVISE_PROMPT, 'novel-revise-v1')
    appended = ''
    if contract is not None:
        data['material_review'] = contract
        appended = ' ' + MATERIAL_REVIEW_PROMPT
        if any('action_order' in check for check in contract['checks']):
            appended += ' ' + ACTION_REVIEW_PROMPT
        if any(check['id'].startswith(narration_review.PREFIX) for check in contract['checks']):
            current = any('narrative_person' in check for check in contract['checks'])
            appended += ' ' + (narration_review.PROMPT if current else narration_review.LEGACY_PROMPT)
        if any(check.get('layer_contract', {}).get('policy') == NETWORK_LAYER_POLICY for check in contract['checks']):
            appended += ' ' + NETWORK_LAYER_REVIEW
    from nw.chapter_break import REVIEW as BREAK_REVIEW, WRITING as BREAK_WRITING, chapter_end
    if chapter_end(package):
        appended += ' ' + (BREAK_REVIEW if purpose == 'review' else BREAK_WRITING)
        if purpose == 'revise' and review and review.get('chapter_break'):
            data['chapter_break_revision'] = '补完末段动作或对话，在自然节拍换章。'
    keys = check_source_keys(contract['checks']) if contract else writing_keys
    body = canonical(data)
    prompt = step_material_prompt(prompt, material, keys)
    messages = [{'role': 'system', 'content': prompt+appended}, {'role': 'user', 'content': body}]
    return messages, version
