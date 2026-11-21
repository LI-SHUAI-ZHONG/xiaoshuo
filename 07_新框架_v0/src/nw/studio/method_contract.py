"""Versioned method documents and completeness checks, never literary scoring."""
from copy import deepcopy
import re

from nw.materials.phase_routes import ORDER, phase_order
from nw.studio.catalog import canonical_types
from nw.studio.method_catalog import ARTIFACTS, CONSUMERS, INPUTS, METHOD_FIELDS, SCOPES, TASKS, output_artifacts

SECTIONS = ('applicability', 'prerequisites', 'operations', 'outputs', 'downstream',
            'acceptance', 'evidence', 'non_applicability')
LABELS = dict(zip(SECTIONS, ('适用条件', '所需前置', '具体操作', '预期产物',
    '下游用途', '验收方法', '原作证据', '不适用情况')))
KEY = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,63}$')
ROW_FIELDS = {
    'prerequisites': ('key', 'input_kind', 'artifact', 'requirement'),
    'operations': ('key', 'instruction', 'input_keys', 'output_keys'),
    'outputs': ('key', 'stage', 'field', 'artifact_kind', 'description'),
    'downstream': ('output_key', 'consumer', 'usage'),
    'acceptance': ('output_key', 'check', 'evidence_required'),
    'evidence': ('book_id', 'start', 'end', 'quote', 'explanation'),
}


def text(value: object, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f'{label}须为不超过 {maximum} 字的文本')
    return value.strip()


def names(value: object, label: str, allowed: object = None) -> list[str]:
    if not isinstance(value, list) or len(value) > 64 or any(not isinstance(v, str) for v in value):
        raise ValueError(f'{label}须为不超过 64 项的列表')
    if len(set(value)) != len(value) or allowed is not None and any(v not in allowed for v in value):
        raise ValueError(f'{label}包含重复或未知项目')
    return list(value)


def normalize(body: dict) -> dict:
    if not isinstance(body, dict):
        raise ValueError('方法须为对象')
    extra = set(body) - {'title', 'tasks', 'scopes', 'type_tags', *SECTIONS}
    if extra:
        raise ValueError('方法含未知字段：' + ','.join(sorted(extra)))
    tags = names(body.get('type_tags', []), '类型范围')
    canonical = list(dict.fromkeys(tag for value in tags for tag in canonical_types([value])))
    result = {'title': text(body.get('title', ''), '名称', 120),
        'tasks': names(body.get('tasks', []), '生产任务', TASKS),
        'scopes': names(body.get('scopes', []), '制作层级', SCOPES),
        'type_tags': canonical}
    if len(result['type_tags']) > 64:
        raise ValueError('类型范围含自动补齐的父类型最多 64 项')
    for section in ('applicability', 'non_applicability'):
        rows = body.get(section, [])
        if not isinstance(rows, list) or len(rows) > 64:
            raise ValueError(f'{section}须为列表，最多 64 项')
        result[section] = [text(row, section) for row in rows]
    for section, fields in ROW_FIELDS.items():
        rows = body.get(section, [])
        if not isinstance(rows, list) or len(rows) > 64:
            raise ValueError(f'{section}须为列表，最多 64 项')
        result[section] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError(f'{section}条目字段不完整或包含未知字段')
            clean = {}
            for key, value in row.items():
                if key in ('start', 'end'):
                    if type(value) is not int or value < 0:
                        raise ValueError('证据位置须为非负整数')
                    clean[key] = value
                elif key in ('input_keys', 'output_keys'):
                    clean[key] = names(value, key)
                else:
                    clean[key] = text(value, key, 1500 if key == 'quote' else 4000)
                    if key == 'quote':
                        clean[key] = value  # Exact whitespace belongs to the located evidence.
            for key in ('key', 'output_key'):
                if key in clean and not KEY.fullmatch(clean[key]):
                    raise ValueError('前置/操作/产物标识须为字母开头的字母、数字和下划线')
            for key, allowed in (('input_kind', INPUTS), ('stage', ORDER),
                                  ('consumer', CONSUMERS), ('artifact_kind', ARTIFACTS)):
                if key in clean and clean[key] not in allowed:
                    raise ValueError(f'{section}含未知{key}')
            if section == 'outputs' and clean['field'] not in METHOD_FIELDS[clean['stage']]:
                raise ValueError('预期产物字段不属于真实设计步骤')
            if section == 'outputs' and clean['artifact_kind'] not in output_artifacts(clean['stage'], clean['field']):
                raise ValueError('产物种类与真实步骤字段不符，设计卡须对应本步具体设计卡字段')
            result[section].append(clean)
    return result


def completeness(body: dict) -> list[dict]:
    issues = []

    def require(condition: bool, field: str, message: str) -> None:
        if not condition:
            issues.append({'field': field, 'message': message})

    require(bool(body['title']), 'title', '请填写方法名称')
    require(bool(body['tasks']), 'tasks', '请明确帮助完成的生产任务')
    require(bool(body['scopes']), 'scopes', '请明确全书/卷/章/场景范围')
    for section in SECTIONS:
        require(bool(body[section]), section, '请补齐' + LABELS[section])
        for row in body[section]:
            require(bool(row) and (not isinstance(row, dict) or all(value not in ('', []) for value in row.values())),
                    section, '条目内容不能为空')
    selected = [TASKS[key] for key in body['tasks']]
    allowed_stages = {stage for task in selected for stage in task['stages']}
    for task in selected:
        require(bool(set(task['scopes']) & set(body['scopes'])), 'scopes', task['name'] + '与所选层级不符')
    for scope in body['scopes']:
        require(any(scope in task['scopes'] for task in selected), 'scopes', '制作层级没有对应生产任务')
    for section in ('prerequisites', 'operations', 'outputs'):
        keys = [row['key'] for row in body[section]]
        require(len(keys) == len(set(keys)), section, '条目标识不能重复')
    inputs = {row['key'] for row in body['prerequisites']}
    outputs = {row['key']: row for row in body['outputs']}
    used_inputs, made_outputs = set(), set()
    for row in body['operations']:
        require(set(row['input_keys']) <= inputs, 'operations', '操作引用了不存在的前置')
        require(set(row['output_keys']) <= outputs.keys(), 'operations', '操作引用了不存在的产物')
        used_inputs.update(row['input_keys'])
        made_outputs.update(row['output_keys'])
    require(inputs <= used_inputs, 'prerequisites', '存在未被操作使用的前置')
    require(outputs.keys() <= made_outputs, 'outputs', '存在未由操作产生的预期产物')
    for row in body['outputs']:
        require(row['stage'] in allowed_stages, 'outputs', '产物所属步骤不服务于所选生产任务')
        for scope in body['scopes']:
            require(row['stage'] in phase_order(scope), 'outputs',
                    SCOPES[scope] + '范围不执行该产出步骤，请缩小层级或按层级拆分方法')
        require(any(d['output_key'] == row['key'] for d in body['downstream']), 'downstream', '每个产物须有指定下游')
        require(any(a['output_key'] == row['key'] for a in body['acceptance']), 'acceptance', '每个产物须有验收方法')
    for row in [*body['downstream'], *body['acceptance']]:
        require(row['output_key'] in outputs, 'outputs', '下游或验收引用了不存在的产物')
    for row in body['downstream']:
        output = outputs.get(row['output_key'])
        if output and row['consumer'] in ORDER:
            require(ORDER.index(row['consumer']) > ORDER.index(output['stage']), 'downstream', '下游必须在产物步骤之后')
    if 'narration' in body['tasks']:
        beats = {key for key, row in outputs.items()
                 if row['stage'] == 'expression_design' and row['field'] == 'guidance'}
        require(bool(beats), 'outputs', '叙述方法须把讲述安排落在表达设计的具体场景节拍')
        for key in beats:
            consumers = {row['consumer'] for row in body['downstream'] if row['output_key'] == key}
            require({'writer', 'review'} <= consumers, 'downstream', '叙述节拍须交给正文写作和独立审稿')
        for key, output in outputs.items():
            if output['stage'] == 'scene_design':
                require(any(d['output_key'] == key and d['consumer'] == 'expression_design' for d in body['downstream']),
                        'downstream', '叙述方法的场景安排须交给表达设计，才能从本场实际节拍写审')
    for row in body['evidence']:
        require(row['end'] > row['start'], 'evidence', '原作证据位置范围无效')
    return issues


def draft(body: dict) -> tuple[dict, list[dict]]:
    result = normalize(deepcopy(body))
    return result, completeness(result)
