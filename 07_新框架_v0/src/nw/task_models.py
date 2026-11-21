"""Frozen model-call inputs and the project task result contract."""
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any

TASK_KINDS = frozenset({'plan', 'rule_extract', 'select', 'state_extract', 'fact_review', 'material_work'})
CARD_KINDS = frozenset({'world', 'character', 'style', 'taboo', 'plot', 'scene', 'promise',
                        'rule', 'brief', 'volume', 'chapter'})


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':'))


def response_json(value: Any) -> str:
    # Escaping preserves malformed provider Unicode without binding surrogates as SQLite TEXT.
    return json.dumps(value, ensure_ascii=True, allow_nan=False)


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Ref:
    kind: str
    id: str
    version: int
    sha256: str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    target_ref: dict
    evidence: list[dict]
    explanation: str
    suggested_action: str
    status: str


@dataclass(frozen=True)
class Budget:
    max_calls: int
    context_char_limit: int
    output_limit: int
    max_revisions: int = 2
    price_snapshot: dict | None = None
    max_cost: str | None = None
    used_calls: int = 0
    reserved_calls: int = 0


@dataclass(frozen=True)
class InputManifest:
    id: str
    purpose: str
    settings: dict
    context_sha256: str
    schema_version: int = 1
    brief_ref: Ref | None = None
    card_refs: tuple[dict, ...] = ()
    source_refs: tuple[dict, ...] = ()
    branch_id: str | None = None
    state_revision: int | None = None
    story_order: int | None = None
    disclosure_order: int | tuple[int, int, int] | None = None
    predecessor_drafts: tuple[Ref, ...] = ()
    candidate_delta_refs: tuple[tuple[str, str], ...] = ()
    candidate_projection_sha256: str | None = None
    dependency_refs: tuple[Ref, ...] = ()
    selection: dict | None = None
    novel_job_id: str | None = None
    material_design_sha256: str | None = None


@dataclass(frozen=True)
class TaskRequest:
    id: str
    project_id: str
    kind: str
    manifest_id: str
    payload: dict
    budget_id: str
    attempt: int = 1
    retry_of: str | None = None


@dataclass(frozen=True)
class TaskResult:
    id: str
    status: str
    finish_reason: str | None = None
    validation: str = 'UNREVIEWED'
    parsed: dict | None = None
    output_text: str = ''
    raw: dict | None = None
    request_id: str | None = None
    usage: dict = field(default_factory=dict)
    reason: str | None = None


def _object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _records(value: Any, field_name: str) -> list[dict]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f'{field_name} must be a list of objects')
    return value


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _range(start: Any, end: Any, minimum: int) -> bool:
    return type(start) is int and type(end) is int and minimum <= start <= end


def _source_ref(ref: dict) -> bool:
    return (_text(ref.get('source_id')) and _sha256(ref.get('span_sha256'))
            and _range(ref.get('start_line'), ref.get('end_line'), 1))


def _ref(ref: Any) -> bool:
    return (isinstance(ref, dict) and _text(ref.get('kind')) and _text(ref.get('id'))
            and type(ref.get('version')) is int and ref['version'] >= 1 and _sha256(ref.get('sha256')))


def _evidence(ref: dict) -> bool:
    return (_text(ref.get('draft_id')) and _sha256(ref.get('text_sha256'))
            and _range(ref.get('start'), ref.get('end'), 0) and ref['start'] < ref['end'])


def validate_task_output(kind: str, text: str) -> dict:
    """Check the transport envelope. Source and story checks belong to its consumers."""
    fields = {'plan': {'scope', 'candidate_cards'}, 'rule_extract': {'rules'},
              'select': {'selected_refs'}, 'state_extract': {'operations'}, 'fact_review': {'findings'},
              'material_work': {'status','tasks','requests','understanding','work_plan'}}
    if kind not in fields:
        raise ValueError('Unknown task kind')
    data = json.loads(text, object_pairs_hook=_object)
    # Reject nonfinite values, overflowing exponents and unpaired surrogates.
    canonical(data).encode('utf-8')
    if kind == 'material_work' and isinstance(data, dict) and set(data) in ({'judgments'}, {'cast_demands'}):
        _records(next(iter(data.values())), 'casting records')
        return data
    if kind=='material_work' and isinstance(data,dict) and 'stage' in data:
        if (not _text(data['stage']) or not (
                set(data)=={'stage','products'} and isinstance(data['products'],dict)
                or set(data)=={'stage','requests'} and isinstance(data['requests'],list)
                or data['stage']=='world_design' and set(data)=={'stage','world_method_gap'} and isinstance(data['world_method_gap'],dict)
                or data['stage']=='plot_design' and set(data)=={'stage','cast_gap'} and isinstance(data['cast_gap'],dict))):
            raise ValueError('Invalid method stage envelope')
        return data
    if not isinstance(data, dict) or set(data) != fields[kind]:
        raise ValueError(f'Unexpected fields for {kind}')
    if kind == 'plan':
        cards = _records(data['candidate_cards'], 'candidate_cards')
        if (data['scope'] not in ('book', 'volume', 'chapter', 'scene', 'replan') or not cards or
                any(not _text(c.get('kind')) or c['kind'] not in CARD_KINDS or
                    not isinstance(c.get('body'), dict) or not c['body'] for c in cards)):
            raise ValueError('Invalid scope or candidate card')
    elif kind == 'rule_extract':
        for rule in _records(data['rules'], 'rules'):
            sources = _records(rule.get('source_refs'), 'source_refs')
            if not _text(rule.get('original_meaning')) or not sources or not all(map(_source_ref, sources)):
                raise ValueError('Extracted rules require meaning and source references')
    elif kind == 'select':
        refs = data['selected_refs']
        if (not isinstance(refs, list) or len(refs) > 5 or not all(_text(ref) for ref in refs)
                or len(refs) != len(set(refs))):
            raise ValueError('Invalid selected rule IDs')
    elif kind == 'state_extract':
        for op in _records(data['operations'], 'operations'):
            evidence = op.get('evidence')
            evidence = [evidence] if isinstance(evidence, dict) else _records(evidence, 'evidence')
            if (op.get('op') not in ('set', 'unset', 'add_relation', 'remove_relation',
                                    'introduce_promise', 'advance_promise')
                    or not evidence or not all(map(_evidence, evidence))):
                raise ValueError('State changes require an operation and evidence')
    elif kind == 'material_work':
        if data['status'] not in ('retrieve','ready') or any(not isinstance(data[k],list) for k in
                ('tasks','requests','understanding','work_plan')):
            raise ValueError('Invalid method study response')
    else:
        for finding in _records(data['findings'], 'findings'):
            if (set(finding) != set(Finding.__dataclass_fields__) or
                    not all(_text(finding.get(k)) for k in ('code', 'severity', 'explanation', 'suggested_action')) or
                    finding['status'] not in ('OPEN', 'RESOLVED', 'WAIVED', 'NOT_CHECKED') or
                    not _ref(finding['target_ref'])):
                raise ValueError('Invalid finding')
            evidence = _records(finding['evidence'], 'evidence')
            if not all(map(_evidence, evidence)):
                raise ValueError('Invalid finding evidence')
    return data
