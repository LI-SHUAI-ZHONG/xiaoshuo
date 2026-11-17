"""Compile pinned original clauses for later project design and independent review.

Compilation is structural: it does not prove applicability or literary effects,
promote source qualification, create project facts, or repair missing originals.
"""
from copy import deepcopy
from hashlib import sha256
import json
import re

from nw.materials.semantic_fields import infer_stages, json_fields, text_fields
from nw.task_models import content_sha256

POLICY = 'source-semantics-v2'
READABLE_POLICIES = {'source-semantics-v1', POLICY}


def _layer_json(text: str) -> object:
    match = re.search(r'(?m)^```json[^\n]*\n', text)
    start = match.end() if match else text.find('{')
    if start < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(text[start:].lstrip())[0]
    except ValueError:
        return None


def _rejected(field: dict, rejected: list[dict]) -> bool:
    path = str(field.get('field', '')).strip('/')
    for row in rejected:
        other = str(row.get('field', '')).strip('/')
        if row.get('binding') is not None and field.get('binding') is not None and field['binding'] != row['binding']:
            continue
        if other and (path == other or path.startswith(other + '/') or other.startswith(path + '/')):
            return True
    return False


def _aligned_span(raw: str, text: str, expected: str | None) -> tuple[int, int] | None:
    """Recover a stripped field's exact hash span, extending only adjacent space."""
    start = raw.find(text)
    while start >= 0:
        end = start + len(text); low = start; high = end
        while low and raw[low-1].isspace():
            low -= 1
        while high < len(raw) and raw[high].isspace():
            high += 1
        for left in range(start, low-1, -1):
            for right in range(end, high+1):
                if expected is None or sha256(raw[left:right].encode('utf-8')).hexdigest() == expected:
                    return left, right
        if expected == content_sha256(text):
            return start, end
        start = raw.find(text, start+1)
    return None


def _application_guidance(source: dict, context: dict, issues: list[dict]) -> list[dict]:
    """Only retain explicitly aligned, located fields as subordinate guidance."""
    result: list[dict] = []
    review = context.get('adjudication_contract', {})
    references = {r.get('id'): r for r in review.get('source_refs', []) if isinstance(r, dict)}
    for layer in source.get('application_layers', []):
        pin = deepcopy(layer.get('source_ref', {})); raw = layer.get('text', '')
        expected = pin.get('sha256')
        if isinstance(expected, str) and re.fullmatch(r'[a-f0-9]{64}', expected) and sha256(raw.encode('utf-8')).hexdigest() != expected:
            raise ValueError('MATERIAL_SEMANTICS: application layer hash mismatch')
        rejected = deepcopy(layer.get('rejected_fields', [])); aligned = []
        parsed = _layer_json(raw)
        for field in layer.get('aligned_fields', []):
            if not isinstance(field, dict) or _rejected(field, rejected):
                continue
            text = field.get('text')
            if not isinstance(text, str) or not text.strip():
                issues.append({'kind': 'unresolved_aligned_application_field', 'severity': 'review',
                               'locator': field.get('field'), 'source_ref': pin,
                               'reason': '已对齐字段没有可定位原文；未加入执行指导。'})
                continue
            actual_hash = sha256(text.encode('utf-8')).hexdigest()
            expected = field.get('sha256')
            span = _aligned_span(raw, text, expected)
            field_pin = deepcopy(field.get('ref') or references.get(field.get('source_id')) or pin)
            if span is None:
                if expected and expected not in (actual_hash, content_sha256(text)):
                    raise ValueError('MATERIAL_SEMANTICS: aligned application field hash mismatch')
                # JSON guidance can contain the exact value as an escaped string.
                if isinstance(parsed, dict) and parsed.get(field.get('field')) == text:
                    field_pin['locator'] = str(pin.get('locator', '')).rstrip('/') + '/' + field['field']
                elif field.get('source_id') not in references:
                    issues.append({'kind': 'unlocated_aligned_application_field', 'severity': 'review',
                                   'locator': field.get('field'), 'source_ref': pin,
                                   'reason': '不能由已对齐标签代替真实字段定位；未加入执行指导。'})
                    continue
            else:
                start, end = span
                field_pin.update(id=field.get('source_id', field_pin.get('id')),
                    sha256=sha256(raw[start:end].encode('utf-8')).hexdigest(),
                    application_layer_sha256=pin.get('sha256'), text_start=start, text_end=end,
                    text_basis='application_layer_text')
                if type(pin.get('byte_start')) is int:
                    field_pin.update(byte_start=pin['byte_start']+len(raw[:start].encode('utf-8')),
                                     byte_end=pin['byte_start']+len(raw[:end].encode('utf-8')))
                if type(pin.get('line_start')) is int:
                    field_pin.update(line_start=pin['line_start']+raw[:start].count('\n'),
                        line_end=pin['line_start']+raw[:end].count('\n')-(1 if raw[:end].endswith('\n') else 0))
            aligned.append({'field': field.get('field'), 'value': text,
                            'sha256': expected or field_pin.get('sha256', actual_hash), 'value_sha256': actual_hash,
                            'source_ref': field_pin, 'authority': 'aligned_guidance_requires_project_translation'})
        result.append({'source_ref': pin, 'text_sha256': content_sha256(raw),
                       'aligned_fields': aligned, 'rejected_fields': rejected,
                       'authority': 'application_guidance_not_original_rule_or_project_fact'})
    return result


def _base_ref(source: dict, context: dict) -> dict:
    pin = deepcopy(source['source'])
    exact = context.get('source_ref', {})
    for name in ('file_sha256', 'sha256'):
        if name in exact and name in pin and exact[name] != pin[name]:
            raise ValueError('MATERIAL_SEMANTICS: source locator hash mismatch')
    pin.update(deepcopy(exact))
    return pin


def compile_semantics(source: dict, context: dict | None = None) -> dict:
    """Return immutable source-derived obligations; no model or storage is used."""
    context = context or {}
    if (not isinstance(source, dict) or not isinstance(source.get('source'), dict)
            or not isinstance(source['source'].get('id'), str)
            or not isinstance(source.get('original_text'), str)):
        raise ValueError('MATERIAL_SEMANTICS: expected a complete original snapshot')
    text = source['original_text']; digest = content_sha256(text)
    if source.get('original_text_sha256', digest) != digest:
        raise ValueError('MATERIAL_SEMANTICS: original text hash mismatch')
    pin = _base_ref(source, context); original: object = text
    compilation: list[dict] = []
    if text.lstrip().startswith(('{', '[')):
        try:
            original = json.loads(text)
        except ValueError:
            compilation.append({'kind': 'invalid_original_json', 'severity': 'repair',
                                'reason': '原始JSON不可解析；保留原文等待核读，不猜补字段。'})
    if isinstance(original, (dict, list)):
        fields, discovered = json_fields(text, original)
    else:
        fields, discovered = text_fields(text)
    compilation.extend(discovered)
    obligations = []
    for field in fields:
        owner_locator = str(pin.get('locator', '')).rstrip('/')
        relative = field['locator']
        locator = owner_locator + relative if relative.startswith('/') else '/'.join(filter(None, (owner_locator, relative)))
        reference = {**deepcopy(pin), 'locator': locator, 'owner_locator': pin.get('locator'),
                     'text_start': field['start'], 'text_end': field['end'],
                     'text_basis': 'original_text', 'source_text_sha256': digest,
                     'clause_sha256': sha256(text[field['start']:field['end']].encode('utf-8')).hexdigest(),
                     'original_role': field['role']}
        item = {'kind': field['kind'], 'source_ref': reference, 'locator': locator,
                'value': deepcopy(field['value']), 'check_mode': field['check_mode']}
        item['id'] = 'semantic:' + content_sha256({'source_id': source['source']['id'], **item})
        obligations.append(item)
    application = _application_guidance(source, context, compilation)
    for issue in compilation:
        if issue.get('kind') == 'incomplete_original_enumeration':
            issue['obligation_ids'] = [o['id'] for o in obligations
                if issue['text_start'] <= o['source_ref']['text_start']
                and o['source_ref']['text_end'] <= issue['text_end']]
        elif issue.get('kind') in {'unclassified_original_field','uninterpreted_original_text'}:
            issue['obligation_ids']=[o['id'] for f,o in zip(fields,obligations)
                                     if f['locator']==issue['locator']]
        elif issue.get('kind')=='unclassified_original_section':
            issue['obligation_ids']=[o['id'] for f,o in zip(fields,obligations)
                                     if f['role']==issue['locator']]
        elif issue.get('kind')=='invalid_original_json':
            issue['obligation_ids']=[o['id'] for o in obligations]
    issues = deepcopy(source.get('source_issues', {}))
    if not isinstance(issues, dict):
        issues = {'original': issues}
    issues['compilation'] = compilation
    damaged = {ident for i in compilation if i.get('severity') == 'repair' for ident in i.get('obligation_ids', [])}
    blocked = any(i.get('kind') == 'invalid_original_json' for i in compilation)
    blocked = blocked or bool(obligations) and damaged == {o['id'] for o in obligations}
    disposition = 'navigation_only' if not obligations else 'source_repair_required' if blocked else 'project_method'
    source_context = deepcopy(context.get('source_context', {}))
    if isinstance(original, dict):
        source_context['original_metadata'] = {k: deepcopy(original[k]) for k in
            ('status', 'evidence_type', 'object_kind', 'rule_kind', 'schema_version',
             'field_source', 'derivation_contract', 'normalized_source', 'normalized_target',
             'original_source', 'original_target', 'source_layer', 'target_layer', 'needs_review') if k in original}
    source_context['source_state'] = source.get('source_state')
    source_context['authority'] = 'original_source_method_not_project_fact_or_semantic_verification'
    result = {'policy': POLICY, 'source_id': source['source']['id'], 'source_text_sha256': digest,
              'source_ref': pin, 'source_context': source_context,
              'stages': infer_stages(original, source['source'].get('profile', ''),
                                     source['source'].get('key', ''), context),
              'disposition': disposition, 'obligations': obligations,
              'dependencies': sorted(set(i for i in source.get('related_sources', []) if isinstance(i, str))),
              'source_issues': issues, 'application_guidance': application}
    result['sha256'] = content_sha256(result)
    return result
