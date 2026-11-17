"""Locate original semantic fields without certifying their literary meaning."""
import json
import re

from nw.materials.units import chapter_checklist

_META = {'id', 'stable_id', 'effect_id', 'adaptation_id', 'object_kind', 'schema_version',
         'status', 'score', 'scores', 'confidence', 'weight', 'priority', 'evidence_type',
         'name', 'title', 'label', 'canonical_name', 'sha256', 'file_sha256', 'source_id',
         'created_at', 'updated_at', '运行层升级', 'runtime_calling_layer', 'use_authorization',
         'tail_upgrade_evidence', 'model_metadata', 'validation_status', 'review_reason'}
_META |= {'field_source', 'derivation_contract', 'normalized_source', 'normalized_target',
          'original_source', 'original_target', 'source_layer', 'target_layer',
          'needs_review', 'rule_kind'}
_KINDS = {
    'purpose': {'purpose', 'function', 'use', 'use_case', 'goal'},
    'definition': {'definition', 'description', 'scope', 'rule_scope', 'original_meaning',
                   'meaning', 'content', 'summary'},
    'condition': {'condition', 'conditions', 'preconditions', 'applies_when',
                  'selection_constraints', 'required_context', 'activation_condition', 'valid_types'},
    'operation': {'rule', 'rules', 'operation', 'operations', 'instruction', 'instructions',
                  'action', 'actions', 'candidate_actions', 'steps', 'procedure'},
    'prohibition': {'prohibition', 'prohibitions', 'exclusions', 'not_guaranteed',
                    'forbidden_assumptions', 'forbidden_changes', 'forbidden_expressions'},
    'exception': {'exception', 'exceptions', 'excludes_when', 'failure_branches',
                  'alternative_branches', 'interruption_conditions'},
    'effect': {'effect', 'effects', 'candidate_effects', 'candidate_reactions',
               'delayed_effects', 'result', 'outcome'},
    'check': {'check', 'checks', 'validation_rules', 'validation', 'verification',
              'test', 'tests', 'acceptance', 'constraint', 'constraints'},
    'dependency': {'dependency', 'dependencies', 'depends_on', 'requires_rules',
                   'excludes_rules', 'source_refs', 'rule_id', 'upstream'},
    'parameter': {'parameters', 'parameter', 'type', 'type_id', 'type_ids', 'subtype_ids',
                   'hybrid_ids', 'mechanism_ids', 'structure_ids', 'style_ids',
                   'propagation_limits', 'allowed_fields', 'source', 'target', 'relation',
                   'direction', 'generated_from_static', 'effect_kind', 'effect_type',
                   'density', 'visibility', 'payoff_pace', 'violence_tendency',
                   'preferred_conflicts', 'preferred_expressions', 'preferred_parameters',
                   'strength', 'repeat_policy', 'cooldown'},
}
_LABELS = {'定义': 'definition', '目的': 'purpose', '用途': 'purpose', '功能': 'purpose',
           '调用条件': 'condition', '适用条件': 'condition', '触发条件': 'condition',
           '指令': 'operation', '设计指令': 'operation', '写作指令': 'operation',
           '分级标准': 'parameter', '场景变体': 'parameter', '判定标准': 'check',
           '检查方法': 'check', '检查内容': 'check', '修正指南': 'operation',
           '例外处理': 'exception', '禁止': 'prohibition', '禁用': 'prohibition',
           '关联板块': 'dependency', '关联路径': 'dependency', '依赖': 'dependency',
           '示例': 'definition', '反面案例': 'definition', '调用标签': None, '优先级': None}
_EMPTY = {'', '无', '无。', '暂无', '略', '不适用', '待补', '未提供', 'N/A'}
_LABEL = re.compile(r'^\s*(?:【([^】\]）)]+)[】\]）)]|\*\*([^*\r\n]+)\*\*[:：]?)\s*(.*)$')
_BULLET = re.compile(r'^\s*(?:\\?[-*]\s+|\d+[.、]\s*|[①②③④⑤⑥⑦⑧⑨]\s*)')
_ORDER = ('type_selection', 'type_adaptation', 'world_design', 'character_design',
          'static_relations', 'plot_design', 'event_design', 'action_design',
          'scene_design', 'state_transition', 'state_propagation', 'anchor_design',
          'expression_design', 'bind_scope', 'writer', 'review', 'acceptance', 'governance')
_RULE_STAGES = {'TYPE_STATE_PROPAGATION': 'state_propagation',
                'TYPE_CONCEPT_TRIGGER': 'type_adaptation',
                'TYPE_ENTITY_STATE_CHANGE': 'state_transition',
                'TYPE_EVENT_CANDIDATE': 'event_design',
                'TYPE_ACTION_CANDIDATE': 'action_design'}
_EFFECT_STAGES = {'attention_shift': 'type_adaptation', 'state_change': 'state_transition',
                  'event_candidate': 'event_design', 'candidate_action': 'action_design',
                  'action_candidate': 'action_design', 'state_propagation': 'state_propagation'}


def _kind(name: str) -> str | None:
    for kind, names in _KINDS.items():
        if name in names:
            return kind
    if name.startswith(('forbidden_', 'prohibited_')):
        return 'prohibition'
    if name.startswith(('required_', 'trigger_')):
        return 'condition'
    if name.startswith(('preferred_', 'allowed_', 'max_', 'min_')):
        return 'parameter'
    if name.endswith('_changes'):
        return 'effect'
    return None


def _pointer(path: str, key: object) -> str:
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')


def json_fields(text: str, original: object) -> tuple[list[dict], list[dict]]:
    """Walk JSON with lexical spans in original_text, retaining unknown fields."""
    decoder = json.JSONDecoder(); fields: list[dict] = []; issues: list[dict] = []

    def space(pos: int) -> int:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    def walk(value: object, start: int, end: int, path: str,
             inherited: str | None = None, field: str = '') -> None:
        if isinstance(value, dict):
            pos = space(start + 1)
            for name, item in value.items():
                _, pos = decoder.raw_decode(text, pos); pos = space(pos)
                pos = space(pos + 1); left = pos
                _, right = decoder.raw_decode(text, pos)
                if name not in _META:
                    kind = _kind(name)
                    if inherited in {'effect', 'dependency', 'condition', 'operation', 'prohibition', 'exception'} and kind in {None, 'definition', 'parameter'}:
                        kind = inherited
                    walk(item, left, right, _pointer(path, name), kind or inherited, name)
                pos = space(right)
                if pos < len(text) and text[pos] == ',':
                    pos = space(pos + 1)
            return
        if isinstance(value, list):
            pos = space(start + 1)
            for index, item in enumerate(value):
                _, right = decoder.raw_decode(text, pos)
                walk(item, pos, right, _pointer(path, index), inherited, field)
                pos = space(right)
                if pos < len(text) and text[pos] == ',':
                    pos = space(pos + 1)
            return
        if value is None or isinstance(value, str) and value.strip() in _EMPTY:
            return
        kind = inherited or 'definition'
        if inherited is None:
            issues.append({'kind': 'unclassified_original_field', 'locator': path,
                           'severity': 'review', 'reason': '原字段保留，尚未核定创作功能；不影响其他可定位字段。'})
        structural = (kind in {'parameter', 'dependency'} and
                      (not isinstance(value, str) or field in {'type', 'type_id', 'type_ids',
                       'subtype_ids', 'hybrid_ids', 'mechanism_ids', 'structure_ids', 'style_ids',
                       'source', 'target', 'relation', 'direction', 'effect_kind', 'effect_type',
                       'allowed_fields', 'requires_rules', 'excludes_rules', 'rule_id'}))
        fields.append({'kind': kind, 'locator': path, 'value': value, 'start': start, 'end': end,
                       'check_mode': 'deterministic' if structural else 'semantic_review',
                       'role': field})

    start = len(text) - len(text.lstrip()); _, end = decoder.raw_decode(text, start)
    walk(original, start, end, '')
    return fields, issues


def anchor_cells(text: str) -> list[tuple[int, int]]:
    first = text.splitlines()[0] if text.splitlines() else ''
    bars = [m.start() for m in re.finditer(r'(?<!\\)\|', first)]
    if len(bars) != 6 or not re.fullmatch(r'(?:[A-Z]|ID)\d+(?:\.\d+)*', first[bars[0]+1:bars[1]].strip()):
        return []
    return [(bars[i]+1, bars[i+1]) for i in range(5)]


def text_fields(text: str) -> tuple[list[dict], list[dict]]:
    checklist = chapter_checklist(text)
    if checklist:
        return [{'kind': unit.kind, 'locator': f'text/{unit.start}:{unit.end}',
                 'value': text[unit.start:unit.end], 'start': unit.start, 'end': unit.end,
                 'check_mode': 'semantic_review', 'role': unit.label} for unit in checklist], []
    fields: list[dict] = []; issues: list[dict] = []
    cells = anchor_cells(text)
    if cells:
        for index, kind in ((1, 'definition'), (2, 'operation'), (3, 'condition')):
            left, right = cells[index]; raw = text[left:right]
            left += len(raw) - len(raw.lstrip()); right -= len(raw) - len(raw.rstrip())
            if text[left:right] not in _EMPTY:
                fields.append({'kind': kind, 'locator': f'cell/{index}', 'value': text[left:right],
                               'start': left, 'end': right, 'check_mode': 'semantic_review',
                               'role': ('编号', '锚点名称', '具体内容', '触发条件', '类别')[index]})
        return fields, issues
    current: str | None = None; label = ''; pos = 0
    for line in text.splitlines(keepends=True):
        raw = line.rstrip('\r\n'); left = pos; pos += len(line)
        if not raw.strip() or re.match(r'^\s*#{1,6}\s', raw):
            continue
        if match := _LABEL.match(raw):
            label = match[1] or match[2]; current = _LABELS.get(label)
            left += match.start(3); raw = match[3]
            if label not in _LABELS:
                issues.append({'kind': 'unclassified_original_section', 'locator': label,
                               'severity': 'review', 'reason': '原小节保留，尚未解释其功能。'})
        if label in _LABELS and current is None:
            continue
        if bullet := _BULLET.match(raw):
            left += bullet.end(); raw = raw[bullet.end():]
            if not raw.strip():
                issues.append({'kind':'empty_original_bullet','locator':f'text/{left}',
                    'severity':'repair','reason':'原文项目符号后没有内容；只登记缺项，不推测缺失规则。'})
        trim = len(raw) - len(raw.lstrip()); left += trim; raw = raw.strip()
        if raw in _EMPTY:
            continue
        normal = raw.replace('\\', '').replace('*', '')
        if re.fullmatch(r'[^。！？:：\r\n]{0,16}规则[:：]', normal):
            continue
        if re.search(r'(?:三种核心特征|四种强度|三项原则|以下维度)[:：。]?$', normal):
            issues.append({'kind': 'incomplete_original_enumeration', 'locator': f'text/{left}',
                           'text_start': left, 'text_end': left+len(raw),
                           'severity': 'repair', 'reason': '原文宣称列举但未在该句给出成员；不能猜补。'})
        for part in re.finditer(r'[^。！？]+[。！？]?', raw):
            value = part[0].strip()
            if value in _EMPTY:
                continue
            start = left + part.start() + len(part[0]) - len(part[0].lstrip())
            end = start + len(value)
            fields.append({'kind': current or 'definition', 'locator': f'text/{start}:{end}',
                           'value': value, 'start': start, 'end': end,
                           'check_mode': 'semantic_review', 'role': label or 'unlabelled_original'})
            if current is None:
                issues.append({'kind': 'uninterpreted_original_text', 'locator': f'text/{start}:{end}',
                               'severity': 'review', 'reason': '无已确认语义角色；原句待解释，不据profile宣布理解。'})
    return fields, issues


def infer_stages(original: object, profile: str, key: str = '', context: dict | None = None) -> list[str]:
    """Recognize original shapes; [] asks the caller to keep its existing fallback."""
    if isinstance(original, str):
        try:
            original = json.loads(original)
        except ValueError:
            pass
    selected: set[str] = set()
    if isinstance(original, dict):
        rule_kind = original.get('rule_kind')
        rule_stage = _RULE_STAGES.get(rule_kind) if isinstance(rule_kind, str) else None
        if rule_stage:
            return [rule_stage]
        if all(isinstance(original.get(k), str) and original[k].strip() for k in ('source', 'target', 'type')):
            if original.get('generated_from_static'):
                return ['state_propagation']
            return ['state_transition'] if original.get('effect') else ['static_relations', 'plot_design']
        shape = str(original.get('object_kind', ''))
        adapter = ('adapter' in shape.casefold() and '适配' in shape or
                   original.get('adaptation_id') and original.get('type_id'))
        if adapter and any(original.get(k) for k in ('rule', 'parameters', 'preferred_expressions',
                                                    'preferred_conflicts', 'density', 'payoff_pace')):
            selected.add('type_adaptation')
            if any(k in shape for k in ('冲突', '伏笔', '读者期待', '信息差')):
                selected.add('plot_design')
            if '表达' in shape or original.get('preferred_expressions'):
                selected.add('expression_design')
        effect_kinds = [original.get('effect_kind'), original.get('effect_type')]
        for effect in original.get('candidate_effects', []) if isinstance(original.get('candidate_effects'), list) else []:
            if isinstance(effect, dict):
                effect_kinds.extend((effect.get('effect_kind'), effect.get('effect_type')))
        selected.update(_EFFECT_STAGES[k] for k in effect_kinds if isinstance(k, str) and k in _EFFECT_STAGES)
    elif isinstance(original, str):
        if anchor_cells(original):
            return ['anchor_design']
        fields, _ = text_fields(original)
        body = ' '.join(str(field['value']) for field in fields)
        # These are explicit source operations, not numbering/title heuristics.
        conversion = all(word in body for word in ('参数', '正文')) and any(word in body for word in ('检验', '验证', '核验'))
        selection = all(word in body for word in ('第一层', '第二层', '第三层', '功能定位', '板块', '子项'))
        if conversion or selection:
            return ['bind_scope']
        if '读者' in body and '情绪' in body:
            selected.add('plot_design')
        if '伏笔' in body and any(word in body for word in ('埋设', '回收', '揭示')):
            selected.add('plot_design')
        if '动作序列' in body or '主要动作前' in body:
            selected.update(('action_design', 'scene_design', 'expression_design'))
        if all(word in body for word in ('句式', '用词', '叙述距离')):
            selected.update(('expression_design', 'review'))
        if all(word in body for word in ('任务', '板块', '子项')):
            selected.add('bind_scope')
    return [stage for stage in _ORDER if stage in selected]
