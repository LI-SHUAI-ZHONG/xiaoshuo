"""Execute selection and conversion rules against the actual proposed design."""
from nw.materials.layer_workflow import has_layers, validate_application
from nw.task_models import _text, canonical
from nw.materials.stage_workflow import PROFILES as STAGES, COMMON, FIELDS, stage_prompt, validate_stage

PROFILES = {'material_selection', 'material_conversion'} | STAGES


def _processes(materials: list[dict]) -> dict:
    return {row['source']['id']: row for row in materials
            if row['request']['disposition'] == 'required' and row['profile'] in PROFILES}


def process_prompt(materials: list[dict], *, book: bool) -> str:
    processes = _processes(materials)
    if book:
        processes = {ident: row for ident,row in processes.items() if row['profile'] == 'preflight_process'}
    if not processes:
        return ''
    return (' 每个方案另加 process_bindings，按以下流程来源ID返回阶段产物：' +
            canonical({ident: row['profile'] for ident, row in processes.items()}) +
            '。material_selection 返回 task_function、selections、exclusions；task_function 说明当前功能。'
            'selections 逐一列出所有非流程必用来源，每项含 id、block_id（source.fragment_id）、具体 reason。'
            'exclusions 逐一列出延后或不适用来源的 id、reason。不能用板块名称代替确切子项。'
            '按 material_deferrals 范围延后的来源也列入 exclusions，并照录作者给出的延后理由。'
            'material_conversion 返回 mappings，逐一引用 material_bindings 中实际采用的每个 scene 与来源id，'
            '每项含 scene、id、parameter、observable、check；后三项必须与该场的实际绑定相同。'
            '按设计范围延后的来源无映射。两类流程项如有 adjudication_policy，另附 source_scope 逐原字段处置；'
            '如有 layer_contract.execution，另附 layer_application（trigger、operation、result、verification），'
            '说明该流程对当前设计的真实作用，不把流程变成角色事件。' +
            ''.join(' ' + ident + '：' + stage_prompt(row['profile']) for ident,row in processes.items() if row['profile'] in STAGES))


def validate_processes(candidate: dict, scope: str, materials: list[dict],
                       deferrals: dict | None = None, *, existing: dict | None = None) -> None:
    processes = _processes(materials)
    if scope == 'book':
        processes = {ident: row for ident,row in processes.items() if row['profile'] == 'preflight_process'}
    if not processes:
        if 'process_bindings' in candidate:
            raise ValueError('MATERIAL_PROCESS: no process artifact was requested at this stage')
        return
    outputs = candidate.get('process_bindings')
    if not isinstance(outputs, dict) or set(outputs) != set(processes):
        raise ValueError('MATERIAL_PROCESS: every selected process requires its actual design artifact')
    for ident, process in processes.items():
        output = outputs[ident]
        profile = process['profile']
        fields = (COMMON | FIELDS[profile] if profile in STAGES else
                  {'task_function', 'selections', 'exclusions'} if profile == 'material_selection' else {'mappings'})
        if process['review'].get('adjudication_policy'):
            fields |= {'source_scope'}
        if has_layers(process):
            fields |= {'layer_application'}
        if not isinstance(output, dict) or set(output) != fields:
            raise ValueError('MATERIAL_PROCESS: invalid process artifact fields')
        if has_layers(process):
            validate_application(output, process)
        if 'source_scope' in fields:
            from nw.materials.binding import _validate_source_scope
            _validate_source_scope(output, process['review']['contract'].get('obligations', []))
        if profile in STAGES:
            validate_stage(output, candidate, profile,
                           [r for r in materials if r['source']['id'] not in (deferrals or {})], existing)
        elif profile == 'material_selection':
            _selection(output, materials, deferrals or {})
        else:
            _conversion(output, candidate, materials, deferrals or {})


def _selection(output: dict, materials: list[dict], deferrals: dict) -> None:
    wanted = {row['source']['id']: row for row in materials if row['profile'] not in PROFILES}
    if not _text(output['task_function']):
        raise ValueError('MATERIAL_PROCESS: selection begins with the concrete task function')
    for field in ('selections', 'exclusions'):
        rows = output[field]
        if not isinstance(rows, list):
            raise ValueError('MATERIAL_PROCESS: source selections and exclusions must be explicit lists')
        for choice in rows:
            fields = {'id', 'reason', 'block_id'} if field == 'selections' else {'id', 'reason'}
            if (not isinstance(choice, dict) or set(choice) != fields or not _text(choice['id'])
                    or choice['id'] not in wanted or not _text(choice['reason'])):
                raise ValueError('MATERIAL_PROCESS: duplicate or unrequested source selection')
            material = wanted.pop(choice['id'])
            selected = material['request']['disposition'] == 'required' and choice['id'] not in deferrals
            if selected != (field == 'selections') or selected and choice['block_id'] != material['source']['fragment_id']:
                raise ValueError('MATERIAL_PROCESS: selection must match its source block and current disposition')
            if choice['id'] in deferrals and choice['reason'] != deferrals[choice['id']]:
                raise ValueError('MATERIAL_PROCESS: preserve the actual author deferral reason')
    if wanted:
        raise ValueError('MATERIAL_PROCESS: every requested source needs a selection or exclusion reason')


def _conversion(output: dict, candidate: dict, materials: list[dict], deferrals: dict) -> None:
    selected = {row['source']['id'] for row in materials
                if row['request']['disposition'] == 'required' and row['profile'] not in PROFILES} - deferrals.keys()
    bindings = candidate.get('material_bindings')
    if (not isinstance(bindings, dict) or any(not isinstance(m, dict) or any(
            not isinstance(b, dict) for b in m.values()) for m in bindings.values())):
        raise ValueError('MATERIAL_PROCESS: conversion requires structured scene material bindings')
    expected = {(scene, ident): binding for scene, mappings in bindings.items()
                for ident, binding in mappings.items() if ident in selected
                and binding.get('disposition', 'selected') == 'selected'}
    rows = output['mappings']
    if not isinstance(rows, list) or len(rows) != len(expected) or not expected:
        raise ValueError('MATERIAL_PROCESS: every used scene parameter needs a concrete expression mapping')
    for mapping in rows:
        if (not isinstance(mapping, dict) or set(mapping) != {'scene', 'id', 'parameter', 'observable', 'check'}
                or not _text(mapping['scene']) or not _text(mapping['id'])):
            raise ValueError('MATERIAL_PROCESS: invalid parameter mapping')
        binding = expected.pop((mapping['scene'], mapping['id']), None)
        if binding is None or any(mapping[key] != binding[key] for key in ('parameter', 'observable', 'check')):
            raise ValueError('MATERIAL_PROCESS: mapping differs from the actual approved scene parameter and expression')
