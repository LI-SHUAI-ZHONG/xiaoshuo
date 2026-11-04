"""Draft evidence validation and independent model review of candidate changes."""
from dataclasses import asdict, replace
from hashlib import sha256
import json
import re

from nw.call_budget import create_budget, prepare_call, read_budget
from nw.call_control import model_settings
from nw.config import Config
from nw.llm.base import LLMProvider
from nw.models import Draft
from nw.store import Store
from nw.story_dependencies import add_dependency, check_inputs_current, verify_legacy_ref
from nw.story_models import Evidence, StateDelta, StateHead
from nw.story_state import ACTIONS, baseline_for, parse_fact, position, replay, revision_state, selected_operations
from nw.task_models import Budget, Finding, InputManifest, Ref, TaskRequest, canonical, content_sha256
from nw.tasks import freeze_manifest, read_input_manifest, run_task


def draft_digest(draft: Draft) -> str:
    return sha256(draft.text.encode('utf-8')).hexdigest()


def draft_ref(draft: Draft) -> Ref:
    return Ref('draft', draft.id, draft.version, draft_digest(draft))


def delta_ref(delta: StateDelta) -> Ref:
    return Ref('delta', delta.id, 1, delta.sha256)


def _evidence(raw: dict, draft: Draft) -> Evidence:
    try:
        evidence = Evidence(**raw)
    except TypeError:
        raise ValueError('Malformed draft evidence') from None
    if (evidence.draft_id != draft.id or evidence.text_sha256 != draft_digest(draft)
            or type(evidence.start) is not int or type(evidence.end) is not int
            or not 0 <= evidence.start < evidence.end <= len(draft.text)
            or not draft.text[evidence.start:evidence.end].strip()):
        raise ValueError('Invalid evidence range, draft or text hash')
    return evidence


def _manifest(store: Store, draft: Draft, ident: str) -> tuple[dict, dict]:
    manifest, package = read_input_manifest(store, ident)
    if manifest['purpose'] != 'state_extract' or package.get('draft_id') != draft.id:
        raise ValueError('Delta manifest does not freeze this draft')
    if package.get('draft_sha256', draft_digest(draft)) != draft_digest(draft):
        raise ValueError('Delta manifest draft hash mismatch')
    revision_state(store, StateHead(manifest['branch_id'], manifest['state_revision']))
    scene = store.get('scene', draft.scene_id)
    chapter = store.get('chapter', scene.chapter_id)
    if position(manifest['disclosure_order'])[:2] != (chapter.index, scene.index):
        raise ValueError('Delta manifest disclosure does not match the draft scene')
    baseline = baseline_for(store, manifest['branch_id'])
    if (manifest['story_order'] < baseline['as_of_story_order'] or
            position(manifest['disclosure_order']) < position(baseline['disclosure_order'])):
        raise ValueError('HISTORY_INCOMPLETE')
    return manifest, package


_PARAGRAPH_BREAK = re.compile(r'\r?\n[ \t]*\r?\n(?:[ \t]*\r?\n)*')


def _evidence_paragraph(draft: Draft, evidence: list[dict]) -> int:
    last = max(item['start'] + len(draft.text[item['start']:item['end']].rstrip()) for item in evidence)
    return sum(1 for match in _PARAGRAPH_BREAK.finditer(draft.text, 0, last)
               if match.end() < last)


def _operations(raw: list[dict], draft: Draft, manifest: dict) -> list[dict]:
    required = {'op','entity_id','predicate','holder','claim','story_order',
                'disclosure_order','expected_old','new_value','evidence'}
    if not isinstance(raw, list):
        raise ValueError('Delta operations must be a list')
    result = []
    for op in raw:
        if not isinstance(op, dict) or set(op) != required or op['op'] not in ACTIONS:
            raise ValueError('Invalid state operation')
        removing = op['op'] in ('unset', 'remove_relation')
        if removing != (op['new_value'] is None) or (removing and op['expected_old'] is None):
            raise ValueError('State operation must declare its old and new values')
        if op['op'] in ('add_relation', 'introduce_promise') and op['expected_old'] is not None:
            raise ValueError('New relations and promises require an empty precondition')
        if op['op'] == 'advance_promise' and op['expected_old'] is None:
            raise ValueError('Promise advancement requires an existing value')
        evidence = [op['evidence']] if isinstance(op['evidence'], dict) else op['evidence']
        if not isinstance(evidence, list) or not evidence:
            raise ValueError('State operation requires evidence')
        refs = [asdict(_evidence(item, draft)) for item in evidence]
        fact = parse_fact({**op, 'value': op['expected_old'] if removing else op['new_value']}, tuple(refs))
        if (fact.story_order < manifest['story_order'] or
                fact.disclosure_order < position(manifest['disclosure_order']) or
                fact.disclosure_order[:2] != position(manifest['disclosure_order'])[:2]):
            raise ValueError('State operation is outside the frozen scene order')
        if fact.holder == 'READER' and fact.disclosure_order[2] < _evidence_paragraph(draft, refs):
            raise ValueError('Reader disclosure precedes its draft evidence')
        result.append({**op, 'disclosure_order': list(fact.disclosure_order), 'evidence': refs})
    return result


def _findings(items: list[dict], draft: Draft) -> list[dict]:
    if not isinstance(items, list):
        raise ValueError('Review findings must be a list')
    for item in items:
        if (not isinstance(item, dict) or set(item) != set(Finding.__dataclass_fields__) or
                item['status'] not in ('OPEN', 'NOT_CHECKED') or
                item['severity'] not in ('hard', 'soft', 'info') or
                item['target_ref'] != asdict(draft_ref(draft)) or
                not isinstance(item['evidence'], list) or not item['evidence'] or
                any(not isinstance(item[k], str) or not item[k].strip()
                    for k in ('code', 'explanation', 'suggested_action'))):
            raise ValueError('Review finding must refer to this draft and evidence')
        for evidence in item['evidence']:
            _evidence(evidence, draft)
    return items


def read_delta(store: Store, ident: str) -> StateDelta:
    row = store.connection.execute('SELECT * FROM state_deltas WHERE id=?', (ident,)).fetchone()
    if row is None:
        raise ValueError('State delta not found')
    validation = json.loads(row['validation_json'])
    manifest = json.loads(row['manifest_json'])
    return StateDelta(row['id'], row['branch_id'], row['base_revision'], row['draft_id'], row['manifest_id'],
                      json.loads(row['operations_json']), validation['findings'], row['sha256'],
                      validation.get('extraction_task_id'), validation.get('review_task_id'),
                      tuple(tuple(pair) for pair in manifest['candidate_delta_refs']))


def _scene_position(store: Store, scene_id: str) -> tuple[int, int]:
    scene = store.get('scene', scene_id)
    return store.get('chapter', scene.chapter_id).index, scene.index


def candidate_snapshot(store: Store, head: StateHead, refs: list | tuple, scene_id: str) -> dict:
    snapshot = revision_state(store, head)
    cutoff = _scene_position(store, scene_id)
    snapshot['slots'] = {key: slot for key, slot in snapshot['slots'].items()
                         if _scene_position(store, key) < cutoff}
    seen: set[str] = set()
    scenes = {scene_id}
    for pair in refs:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2 or
                not all(isinstance(value, str) and value for value in pair)):
            raise ValueError('Invalid candidate delta reference')
        ident, digest = pair
        delta = read_delta(store, ident)
        if (ident in seen or delta.sha256 != digest or
                (delta.branch_id, delta.base_revision) != (head.branch_id, head.revision)):
            raise ValueError('Candidate dependency has a different base, hash, or repeated delta')
        if any(dep_id not in seen for dep_id, _ in delta.candidate_delta_refs):
            raise ValueError('Candidate dependency list is not closed and ordered')
        seen.add(ident)
        draft = store.get('draft', delta.draft_id)
        if draft.scene_id in scenes or _scene_position(store, draft.scene_id) >= cutoff:
            raise ValueError('Candidate dependency must name a distinct earlier scene')
        scenes.add(draft.scene_id)
        snapshot['slots'][draft.scene_id] = {'draft_id': draft.id, 'delta_id': ident}
    return snapshot


def candidate_projection_digest(store: Store, head: StateHead, refs: list | tuple, scene_id: str) -> str:
    snapshot = candidate_snapshot(store, head, refs, scene_id)
    facts = replay(baseline_for(store, head.branch_id), selected_operations(store, snapshot))
    return content_sha256({'snapshot': snapshot, 'facts': [asdict(f) for f in facts]})


def manifest_refs(store: Store, manifest: dict, scene_id: str, *, current: bool = True) -> list[Ref]:
    refs = []
    try:
        if manifest.get('brief_ref'):
            ref = Ref(**manifest['brief_ref'])
            if ref.kind != 'brief':
                raise ValueError('Brief reference must target a brief')
            refs.append(verify_legacy_ref(store, ref))
        for raw in manifest.get('dependency_refs', []):
            refs.append(verify_legacy_ref(store, Ref(**raw)))
    except TypeError:
        raise ValueError('Invalid frozen input reference') from None
    for raw in manifest['predecessor_drafts']:
        try:
            ref = Ref(**raw)
        except TypeError:
            raise ValueError('Invalid frozen draft reference') from None
        draft = store.get('draft', ref.id)
        if ref != draft_ref(draft):
            raise ValueError('Frozen draft dependency hash mismatch')
        if _scene_position(store, draft.scene_id) >= _scene_position(store, scene_id):
            raise ValueError('Frozen draft dependency must be an earlier scene')
        refs.append(ref)
    for ident, digest in manifest['candidate_delta_refs']:
        ref = delta_ref(read_delta(store, ident))
        if ref.sha256 != digest:
            raise ValueError('Frozen candidate dependency hash mismatch')
        refs.append(ref)
    if current:
        check_inputs_current(store, refs)
    return refs


def _validated_task(store: Store, task_id: str, kind: str) -> tuple[str, dict]:
    row = store.connection.execute(
        "SELECT manifest_id,result_json FROM task_calls WHERE id=? AND kind=? AND status='FINISHED' "
        "AND finish_reason='complete' AND validation='VALID'", (task_id, kind)).fetchone()
    if row is None:
        raise ValueError(f'Invalid {kind} task evidence')
    return row['manifest_id'], json.loads(row['result_json'])


def _check_review_provenance(store: Store, draft: Draft, manifest: dict, operations: list[dict],
                             findings: list[dict], extraction_id: str | None, review_id: str | None) -> None:
    if manifest['settings']['provider'] == 'author':
        if extraction_id or review_id or findings:
            raise ValueError('Manual author deltas cannot claim a model review')
        return
    if not extraction_id or not review_id or extraction_id == review_id:
        raise ValueError('Model state extraction requires independent fact review')
    ident, extraction = _validated_task(store, extraction_id, 'state_extract')
    if ident != manifest['id'] or _operations(extraction['operations'], draft, manifest) != operations:
        raise ValueError('Extraction task does not match the frozen operations')
    review_manifest_id, review = _validated_task(store, review_id, 'fact_review')
    review_manifest, package = read_input_manifest(store, review_manifest_id)
    if (any(review_manifest[key] != manifest[key] for key in
            ('branch_id', 'state_revision', 'story_order', 'disclosure_order')) or
            package.get('draft') != asdict(draft) or package.get('extraction_task_id') != extraction_id or
            package.get('candidate_operations') != operations or _findings(review['findings'], draft) != findings):
        raise ValueError('Fact review does not match the frozen draft, operations or findings')


def save_delta(store: Store, ident: str, draft_id: str, manifest_id: str, operations: list[dict],
               *, findings: list[dict] | None = None, extraction_task_id: str | None = None,
               review_task_id: str | None = None) -> StateDelta:
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError('Delta ID is required')
    draft = store.get('draft', draft_id)
    manifest, _ = _manifest(store, draft, manifest_id)
    ops = _operations(operations, draft, manifest)
    checks = _findings(findings if findings is not None else [], draft)
    _check_review_provenance(store, draft, manifest, ops, checks, extraction_task_id, review_task_id)
    candidates = manifest['candidate_delta_refs']
    if candidates and manifest['candidate_projection_sha256'] != candidate_projection_digest(
            store, StateHead(manifest['branch_id'], manifest['state_revision']), candidates, draft.scene_id):
        raise ValueError('Frozen candidate projection hash mismatch')
    body = {'draft': asdict(draft_ref(draft)), 'manifest': manifest, 'operations': ops, 'findings': checks,
            'extraction_task_id': extraction_task_id, 'review_task_id': review_task_id}
    digest = content_sha256(body)
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        row = store.connection.execute('SELECT sha256 FROM state_deltas WHERE id=?', (ident,)).fetchone()
        if row is not None and row['sha256'] != digest:
            raise ValueError('Delta ID already freezes different content')
        if row is None:
            store.connection.execute('INSERT INTO state_deltas VALUES (?,?,?,?,?,?,?,?,?)',
                                     (ident, manifest['branch_id'], manifest['state_revision'], draft.id,
                                      manifest_id, canonical(manifest), canonical(ops),
                                      canonical({'findings': checks, 'extraction_task_id': extraction_task_id,
                                                 'review_task_id': review_task_id}), digest))
        delta = read_delta(store, ident)
        for ref in [draft_ref(draft), *manifest_refs(store, manifest, draft.scene_id)]:
            add_dependency(store, delta_ref(delta), ref)
    return delta


def check_delta(store: Store, delta: StateDelta, *, project: bool = True) -> list[Finding]:
    checks = [Finding(**finding) for finding in delta.findings]
    draft = store.get('draft', delta.draft_id)
    try:
        manifest, _ = _manifest(store, draft, delta.manifest_id)
        _operations(delta.operations, draft, manifest)
        manifest_refs(store, manifest, draft.scene_id)
        _check_review_provenance(store, draft, manifest, delta.operations, delta.findings,
                                 delta.extraction_task_id, delta.review_task_id)
        if not project:
            return checks
        snapshot = candidate_snapshot(store, StateHead(delta.branch_id, delta.base_revision),
                                      manifest['candidate_delta_refs'], draft.scene_id)
        replay(baseline_for(store, delta.branch_id), [*selected_operations(store, snapshot), *delta.operations])
    except ValueError as exc:
        checks.append(Finding('INVALID_DELTA', 'hard', asdict(draft_ref(draft)), [], str(exc),
                              '核对稿件、证据和旧值后新建候选变更', 'OPEN'))
    return checks


def _budget(store: Store, manifest_id: str, budget: Budget | str) -> str:
    if isinstance(budget, str):
        return budget
    ident = f'delta-budget:{manifest_id}'
    row = store.connection.execute('SELECT 1 FROM budgets WHERE id=?', (ident,)).fetchone()
    if row is None:
        create_budget(store, ident, budget)
    else:
        previous = replace(read_budget(store, ident), used_calls=0, reserved_calls=0)
        if previous != budget:
            raise ValueError('Delta retry must use its original budget')
    return ident


def prepare_delta(store: Store, draft_id: str, manifest_id: str, provider: LLMProvider,
                  config: Config, budget: Budget | str) -> StateDelta:
    draft = store.get('draft', draft_id)
    if draft.status != 'complete':
        raise ValueError('State extraction requires a complete draft')
    manifest, package = _manifest(store, draft, manifest_id)
    budget_id = _budget(store, manifest_id, budget)
    project_id = store.project().id
    evidence_format = {'draft_id': draft.id, 'text_sha256': draft_digest(draft), 'start': 0, 'end': len(draft.text)}
    frozen_input = {'draft': asdict(draft), 'target_ref': asdict(draft_ref(draft)), 'context': package,
                    'evidence_format': evidence_format,
                    'story_order': manifest['story_order'], 'disclosure_order': manifest['disclosure_order']}
    messages = [{'role': 'system', 'content': (
        '只输出 JSON {"operations":[]}。逐项提供 op、entity_id、predicate、holder、claim、story_order、'
        'disclosure_order、expected_old、new_value、evidence。证据用正文 Unicode 半开区间。'
        '未发生的计划、人物说辞和误信不得写成 WORLD 事实。')},
        {'role': 'user', 'content': canonical(frozen_input)}]
    extraction_id = f'delta-extract:{manifest_id}'
    result = run_task(store, TaskRequest(extraction_id, project_id, 'state_extract', manifest_id,
                                       {'messages': messages}, budget_id), provider, config,
                      validate=lambda output: _operations(output['operations'], draft, manifest))
    if result.validation != 'VALID':
        raise ValueError(f'State extraction {result.status}/{result.validation}: {result.id}')
    operations = _operations(result.parsed['operations'], draft, manifest)
    review_package = {**frozen_input, 'candidate_operations': operations, 'extraction_task_id': result.id}
    review_messages = [{'role': 'system', 'content': (
        '独立核对正文与候选变更。只输出 JSON {"findings":[]}。问题需含 code、severity（hard/soft/info）、'
        'target_ref、evidence、explanation、suggested_action、status。问题用 OPEN，正文未支持的事实用 hard。')},
        {'role': 'user', 'content': canonical(review_package)}]
    params, _ = prepare_call(store, budget_id, provider.name, config.params, review_messages)
    review_manifest_id = f'delta-review-manifest:{manifest_id}'
    freeze_manifest(store, InputManifest(review_manifest_id, 'fact_review',
        model_settings(provider, config.model, params, 'fact-review-v1'), content_sha256(review_package),
        branch_id=manifest['branch_id'], state_revision=manifest['state_revision'],
        story_order=manifest['story_order'], disclosure_order=position(manifest['disclosure_order'])), review_package)
    review_id = f'delta-review:{manifest_id}'
    review = run_task(store, TaskRequest(review_id, project_id, 'fact_review', review_manifest_id,
                                        {'messages': review_messages}, budget_id), provider, config,
                      validate=lambda output: _findings(output['findings'], draft))
    if review.validation != 'VALID':
        raise ValueError(f'Fact review {review.status}/{review.validation}: {review.id}')
    return save_delta(store, f'delta:{manifest_id}', draft.id, manifest_id, operations,
                      findings=review.parsed['findings'], extraction_task_id=result.id, review_task_id=review.id)
