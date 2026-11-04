"""Construct the versioned input shared by standalone and scheduled extraction."""
from dataclasses import asdict, replace
from typing import Callable

from nw.call_budget import create_budget, prepare_call, read_budget
from nw.call_control import model_settings
from nw.config import Config
from nw.llm.base import LLMProvider

from nw.store import Store
from nw.story_delta import (_findings, _manifest, _operations, candidate_projection_digest, candidate_snapshot,
                            draft_digest, draft_ref, save_delta, story_write_manifest)
from nw.story_models import StateDelta, StateHead
from nw.story_state import baseline_for, position, replay, selected_operations, state_at
from nw.task_models import Budget, InputManifest, TaskRequest, TaskResult, canonical, content_sha256
from nw.tasks import freeze_manifest, run_task


def freeze_delta_input(store: Store, draft_id: str, scope: dict, settings: dict) -> str:
    required = {'id', 'branch_id', 'base_revision', 'story_order'}
    if not isinstance(scope, dict) or not required <= scope.keys() or scope.keys() - required - {
            'candidate_delta_refs', 'predecessor_drafts', 'brief_ref', 'dependency_refs'}:
        raise ValueError('Invalid delta manifest fields')
    for field in ('candidate_delta_refs', 'predecessor_drafts', 'dependency_refs'):
        if not isinstance(scope.get(field, []), list):
            raise ValueError(f'{field} must be a list')
    if any(not isinstance(raw, dict) or not isinstance(raw.get('id'), str)
           for raw in scope.get('predecessor_drafts', [])):
        raise ValueError('Invalid predecessor draft reference')
    head = StateHead(scope['branch_id'], scope['base_revision'])
    draft = store.get('draft', draft_id)
    scene = store.get('scene', draft.scene_id)
    chapter = store.get('chapter', scene.chapter_id)
    disclosure = (chapter.index, scene.index, 0)
    view = state_at(store, head.branch_id, head.revision, scope['story_order'], 'AUTHOR', disclosure)
    deps = scope.get('candidate_delta_refs', [])
    digest = candidate_projection_digest(store, head, deps, scene.id) if deps else None
    snapshot = candidate_snapshot(store, head, deps, scene.id)
    facts = replay(baseline_for(store, head.branch_id), selected_operations(store, snapshot),
                   story_order=scope['story_order'], disclosure=disclosure)
    changed_ids = {ident for ident, _ in deps}
    written = story_write_manifest(store, draft)
    same_scope = written is not None and (written['branch_id'], written['state_revision']) == (
        head.branch_id, head.revision)
    job_id = written.get('novel_job_id') if same_scope else None
    if job_id:
        projected = candidate_snapshot(store, head, deps, scene.id, include_later=True)
        view = state_at(store, head.branch_id, head.revision, scope['story_order'], 'AUTHOR', disclosure,
                        before_scene=scene.id, snapshot=projected)
        facts = view.facts
    if written is not None and written['story_order'] != scope['story_order']:
        raise ValueError('Delta story time must match the frozen work package')
    predecessors = {raw['id']: raw for raw in scope.get('predecessor_drafts', [])}
    for slot in snapshot['slots'].values():
        if slot['delta_id'] not in changed_ids:
            ref = draft_ref(store.get('draft', slot['draft_id']))
            predecessors.setdefault(ref.id, asdict(ref))
    brief_ref = scope.get('brief_ref')
    dependency_refs = scope.get('dependency_refs', []).copy()
    if same_scope:
        if brief_ref is not None and brief_ref != written['brief_ref']:
            raise ValueError('Delta Brief must match the frozen work package')
        brief_ref = written['brief_ref']
        for ref in written['predecessor_drafts']:
            predecessors.setdefault(ref['id'], ref)
        dependency_refs.extend(ref for ref in written['dependency_refs'] if ref not in dependency_refs and
                               (ref['kind'] != 'draft' or store.get('draft', ref['id']).scene_id != draft.scene_id))
    if job_id:
        known_drafts = {*predecessors, *(ref['id'] for ref in dependency_refs if ref['kind'] == 'draft')}
        evidence_ids = {evidence['draft_id'] for fact in facts for evidence in fact.evidence if 'draft_id' in evidence}
        for evidence_id in sorted(evidence_ids - known_drafts):
            source = store.get('draft', evidence_id)
            if source.scene_id != scene.id:
                dependency_refs.append(asdict(draft_ref(source)))
    package = {'draft_id': draft.id, 'draft_sha256': draft_digest(draft),
               'facts': [asdict(fact) for fact in facts], 'settings': view.settings}
    return freeze_manifest(store, InputManifest(
        scope['id'], 'state_extract', settings, content_sha256(package),
        brief_ref=brief_ref,
        card_refs=tuple({'card_id': card['card_id'], 'version': card['version']} for card in view.settings),
        branch_id=head.branch_id, state_revision=head.revision, story_order=scope['story_order'],
        disclosure_order=disclosure, predecessor_drafts=tuple(predecessors.values()),
        candidate_delta_refs=tuple(deps), candidate_projection_sha256=digest,
        dependency_refs=tuple(dependency_refs), novel_job_id=job_id), package)


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
                  config: Config, budget: Budget | str, *, invoke: Callable[[str, TaskRequest, Callable[[dict], None]], TaskResult] | None = None) -> StateDelta:
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
    def dispatch(kind: str, request: TaskRequest, validate: Callable[[dict], None]) -> TaskResult:
        if invoke:
            return invoke(kind, request, validate)
        return run_task(store, request, provider, config, validate=validate)

    result = dispatch('extract', TaskRequest(extraction_id, project_id, 'state_extract', manifest_id,
                                            {'messages': messages}, budget_id),
                      lambda output: _operations(output['operations'], draft, manifest))
    if result.validation != 'VALID':
        raise ValueError(f'State extraction {result.status}/{result.validation}: {result.id}')
    operations = _operations(result.parsed['operations'], draft, manifest)
    review_package = {**frozen_input, 'candidate_operations': operations, 'extraction_task_id': result.id}
    review_messages = [{'role': 'system', 'content': (
        '独立核对正文与候选变更。只输出 JSON {"findings":[]}。问题需含 code、severity（hard/soft/info）、'
        'target_ref、evidence、explanation、suggested_action、status。问题用 OPEN，正文未支持的事实用 hard。')},
        {'role': 'user', 'content': canonical(review_package)}]
    review_manifest_id = f'delta-review-manifest:{manifest_id}'
    if invoke is None or not store.connection.execute(
            'SELECT 1 FROM input_manifests WHERE id=?', (review_manifest_id,)).fetchone():
        params, _ = prepare_call(store, budget_id, provider.name, config.params, review_messages)
        freeze_manifest(store, InputManifest(review_manifest_id, 'fact_review',
            model_settings(provider, config.model, params, 'fact-review-v1'), content_sha256(review_package),
            branch_id=manifest['branch_id'], state_revision=manifest['state_revision'],
            story_order=manifest['story_order'], disclosure_order=position(manifest['disclosure_order'])), review_package)
    review_id = f'delta-review:{manifest_id}'
    review = dispatch('fact-review', TaskRequest(review_id, project_id, 'fact_review', review_manifest_id,
                                                  {'messages': review_messages}, budget_id),
                      lambda output: _findings(output['findings'], draft))
    if review.validation != 'VALID':
        raise ValueError(f'Fact review {review.status}/{review.validation}: {review.id}')
    return save_delta(store, f'delta:{manifest_id}', draft.id, manifest_id, operations,
                      findings=review.parsed['findings'], extraction_task_id=result.id, review_task_id=review.id)
