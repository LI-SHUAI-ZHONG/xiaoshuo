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
    '{"recommendation":"pass或revise","notes":"具体意见","core_changes":[]}；'
    '需要修订时可附带可选字段 "repair_scope":"local或structural" 及 "target_paragraphs":[0基段落号] 以便精准局部手术修订。'
    '只有影响核心人物目标、世界规则、重要生死、视角形式或终局承诺的变化才填入 core_changes。'
)
REVISE_PROMPT = (
    '根据冻结的工作包、旧稿和审稿意见修订本场。保持作者已确认的设定与披露边界，只输出完整修订正文。'
    '叙述节拍需要修订时，对照同号工作包和旧稿定位调整知情者、讲述次序或实际效果。'
)


def draft_messages(package: dict, purpose: str, draft: Draft, review: dict | None, contract: dict | None,
                   material: str, writing_keys: Iterable[str], length_feedback: list[str] | None = None,
                   *, genre_ids: list[str] | tuple[str, ...] | None = None,
                   craft_specs: dict | None = None,
                   pre_review_note: str = '',
                   revision_diff_note: str = '') -> tuple[list[dict], str]:
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
                if status != 'pass' and check['id'].startswith('work:cast-presence:'):
                    visible['fix'] = '按本场批准的角色与任务写出他们实际在场的言语或动作。仅被谈起的人仍保留在转述中。'
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
        if any(check.get('profile') == 'cast_presence_review' for check in contract['checks']):
            from nw.materials.cast_appearances import PROMPT as CAST_REVIEW
            appended += ' ' + CAST_REVIEW
        if any('action_order' in check for check in contract['checks']):
            appended += ' ' + ACTION_REVIEW_PROMPT
        if any(check['id'].startswith(narration_review.PREFIX) for check in contract['checks']):
            current = any('narrative_person' in check for check in contract['checks'])
            appended += ' ' + (narration_review.PROMPT if current else narration_review.LEGACY_PROMPT)
        from nw.materials.passage_review import review_prompt as passage_prompt
        if passage := passage_prompt(contract['checks']):
            appended += ' ' + passage
        from nw.materials.passage_craft import review_prompt as craft_prompt
        if craft := craft_prompt(contract['checks']):
            appended += ' ' + craft
        if any(check.get('layer_contract', {}).get('policy') == NETWORK_LAYER_POLICY for check in contract['checks']):
            appended += ' ' + NETWORK_LAYER_REVIEW
    from nw.chapter_break import REVIEW as BREAK_REVIEW, WRITING as BREAK_WRITING, chapter_end
    if chapter_end(package):
        appended += ' ' + (BREAK_REVIEW if purpose == 'review' else BREAK_WRITING)
        if purpose == 'revise' and review and review.get('chapter_break'):
            data['chapter_break_revision'] = '补完末段动作或对话，在自然节拍换章。'
    if genre_ids:
        from nw.studio.craft_materials import review_genre_guidance, writing_genre_guidance
        note = review_genre_guidance(genre_ids) if purpose == 'review' else writing_genre_guidance(genre_ids)
        if note:
            appended += ' ' + note
    from nw.craft_specs import build_review_craft_guards
    from nw.writing_craft import ANTI_AI_REVIEW_GUIDE, ANTI_AI_REVISE_GUIDE, package_uses_craft_layers
    if contract is not None or bool(genre_ids) or package_uses_craft_layers(package):
        appended += ' ' + (ANTI_AI_REVIEW_GUIDE if purpose == 'review' else ANTI_AI_REVISE_GUIDE)
    if craft_guard := build_review_craft_guards(package, specs=craft_specs, max_chars=450):
        appended += ' ' + craft_guard
    if purpose == 'review' and pre_review_note:
        appended += ' ' + pre_review_note + ' 只依据正文证据、机检线索与已确认规范核验，不自由主观评价“文笔好坏”。'
    if purpose == 'review':
        appended += ' 核查本场核心冲突与关键节拍是否当场展开演出（scene），而非仅用一两句旁白概述带过（summary）或遗漏（missing）。'
    if purpose == 'review' and revision_diff_note:
        appended += '\n' + revision_diff_note + ' 请结合上述改前/改后差异核验是否已修复原问题，并检查是否存在未授权段落的越界破坏。'
    keys = check_source_keys(contract['checks']) if contract else writing_keys
    body = canonical(data)
    prompt = step_material_prompt(prompt, material, keys)
    messages = [{'role': 'system', 'content': prompt+appended}, {'role': 'user', 'content': body}]
    return messages, version
