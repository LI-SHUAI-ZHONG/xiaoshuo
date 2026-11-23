"""Deliver frozen, approved corpus examples without changing source adjudication."""
from copy import deepcopy

from nw.materials.step_guard import PRIORITY_HIERARCHY


def author_stage_input(package: dict, stage: str) -> dict:
    """Build a bounded stage packet; approval is checked again at delivery.

    The Studio freezes the selected library rows when creating a novel. These
    are examples of methods, never facts about the current story, signatures
    of author approval, or replacements for the original material contracts.
    """
    raw = (package.get('governance_inputs') or {}).get(stage, {})
    if not isinstance(raw, dict):
        raise ValueError('AUTHOR_REFERENCES: stage input must be an object')
    packet = {}
    for field in ('author_preferences', 'project_config', 'creation_plan'):
        if field in raw:
            if not isinstance(raw[field], dict):
                raise ValueError(f'AUTHOR_REFERENCES: {field} must be an object')
            packet[field] = deepcopy(raw[field])
    for field in ('author_references', 'upgrade_references'):
        rows = raw.get(field, [])
        if not isinstance(rows, list):
            raise ValueError(f'AUTHOR_REFERENCES: {field} must be a list')
        selected = []
        for row in rows:
            if not isinstance(row, dict) or row.get('status') != 'approved':
                raise ValueError('AUTHOR_REFERENCES: only approved examples may enter a stage')
            if not isinstance(row.get('stages'), list) or stage not in row['stages']:
                raise ValueError('AUTHOR_REFERENCES: example is outside its approved stages')
            evidence = row.get('evidence')
            if (not row.get('id') or not row.get('book_id') or
                    not isinstance(row.get('usage_text'), str) or not row['usage_text'].strip() or
                    not isinstance(evidence, dict) or not isinstance(evidence.get('quote'), str) or
                    not evidence['quote'].strip()):
                raise ValueError('AUTHOR_REFERENCES: a method needs its source and evidence')
            if field == 'upgrade_references' and not row.get('version'):
                raise ValueError('AUTHOR_REFERENCES: upgrade must be pinned to a version')
            # Pass only method text and a brief, located excerpt, never an
            # imported chapter, arbitrary metadata or authority-like fields.
            clean = {k: deepcopy(row[k]) for k in
                     ('id', 'book_id', 'slot', 'option_key', 'version', 'stages') if k in row}
            clean.update(usage_text=row['usage_text'][:2000], status='approved',
                         evidence={k: deepcopy(evidence[k]) for k in
                                   ('start', 'end', 'chapter', 'locator') if k in evidence})
            clean['evidence']['quote'] = evidence['quote'][:400]
            selected.append(clean)
        if selected:
            packet[field] = selected
    if packet:
        packet['authority'] = 'author_preferences_and_approved_method_examples'
        packet['method_priority'] = 'design_ready'
        packet['priority_hierarchy'] = PRIORITY_HIERARCHY
        packet['instruction'] = (
            '作者偏好仅为本步设计输入，须与Brief及冻结产物核对；project_config是偏好而非裁定结果。'
            '拆解和升级条目是已批准的参考用法，优先级等同design_ready，低于已接受事实、Brief和冻结产物。'
            '只借鉴用法，不抄写证据，不把来源书情节当成本书事实，不得代替步骤前置、原件核验或作者确认。'
        )
        if plan := packet.get('creation_plan'):
            packet.pop('author_preferences', None)  # The detailed rows supersede bare IDs.
            packet['instruction'] += (
                'creation_plan只交付当前步骤负责的立项选项。Brief的constraints是作者硬约束。'
                'preferences提供原义和现有步骤用法，结合本步需求采用。'
                'types是立项冻结的类型知识，按立项顺序保留已选ID及其主次关系，用定义、纳入项和排除项细化本书适配。'
                '编辑知识补充类型口径，类型表和已批准事实仍由正式规则核验。'
                'excerpt_limits标出摘要省略范围，完整对应版本保存在立项档案。')
            if plan.get('preference_interactions'):
                packet['instruction'] += (
                    '每条可能相互拉扯的偏好都在preference_resolutions逐项绑定到真实guidance项。'
                    '给出适用条件的理由和写法所在JSON路径，例如/guidance/0/observable。'
                    '同组偏好须有各自的场景指导或同一场的独立叙述节拍。'
                    '当前场不适用时给出理由，以deferred标识并将output_ref留空。')
    return packet
