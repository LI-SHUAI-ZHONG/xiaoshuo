
"""Build, draft, review, and extract one scene within a pinned novel job."""
from dataclasses import asdict
from typing import Callable

from nw.call_budget import BudgetExceeded, prepare_call, read_budget
from nw.call_control import model_settings
from nw.cards import eligible_rule_refs
from nw.context.story import WRITE_PROMPT, StoryScope, build_story_context, scene_scope
from nw.materials.action_review import check_material_acceptance, review_result
from nw.materials.binding import verify_materials
from nw.materials.evidence import review_contract, scene_materials, state_hypotheses
from nw.materials.narration_review import reader_spans
from nw.materials.steps.review import MATERIAL as REVIEW_MATERIAL
from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
from nw.length_plan import scene_length_feedback
from nw.models import Draft, Run
from nw.scene_messages import REVIEW_PROMPT, REVISE_PROMPT, draft_messages
from nw.scene_capacity import SceneCapacity
from nw.novel_calls import JobCalls, call_id
from nw.novel_store import JobPaused
from nw.story_delta import (candidate_projection_digest, check_delta, draft_ref, manifest_refs, read_delta)
from nw.story_extract import freeze_delta_input, prepare_delta
from nw.story_models import CardRef, StateDelta
from nw.task_models import InputManifest, TaskRequest, TaskResult, canonical, content_sha256

CORE_PREDICATES = frozenset({'core_goal', 'protagonist_goal', 'world_rule', 'pov', 'ending', 'ending_promise',
                            'alive', 'death', 'life_status', '生死', '核心目标', '世界规则', '终局承诺', '视角'})


def _settings(calls: JobCalls, prompt_version: str, messages: list[dict]) -> dict:
    try:
        params, _ = prepare_call(calls.journal.store, calls.journal.id, calls.provider.name, calls.config.params, messages,
                                 context_window_tokens=getattr(calls.config, 'context_window_tokens', None))
    except BudgetExceeded as exc:
        stage = {'novel-review-v1': '审稿', 'novel-revise-v1': '修订', 'story-write-v1': '写作'}.get(
            prompt_version, prompt_version)
        chars = sum(len(message['content']) for message in messages)
        limit = read_budget(calls.journal.store, calls.journal.id).context_char_limit
        raise BudgetExceeded(f'{exc}。{stage}实际输入 {chars} 字符，任务上限 {limit}，模型 {calls.config.model}。'
                             '请拆分场景或在核对窗口后调整预算。') from exc
    return model_settings(calls.provider, calls.config.model, params, prompt_version)


def _inputs(calls: JobCalls, scene: str, chain: tuple[tuple[str, str], ...]) -> dict:
    j = calls.journal
    key = f'scene:{scene}:select'
    j.check_active(key)
    row = j.latest(key)
    if row is None:
        explicit = j.request['scene_scopes'].get(scene)
        scope = (StoryScope(j.head.branch_id, j.head.revision, **explicit) if explicit
                 else scene_scope(j.store, scene, j.head.branch_id))
        limit = read_budget(j.store, j.id).context_char_limit
        capacity = SceneCapacity(calls, scene, chain)
        work = build_story_context(j.store, scene, scope, limit, candidate_refs=chain, base_prompt=WRITE_PROMPT,
                                   validate_capacity=capacity.check)
        capacity_report = capacity.check(work.prompt, work.package, set(work.writing_source_keys))
        capacity_report['omitted_optional_groups'] = list(work.omitted_optional_groups)
        digest = candidate_projection_digest(j.store, j.head, chain, scene) if chain else None
        messages = [{'role': 'system', 'content': work.prompt}, {'role': 'user', 'content': canonical(work.package)}]
        write_calls = calls.for_stage('write')
        manifest = InputManifest(
            f'{j.id}:{key}', 'write', _settings(write_calls, 'story-write-v1', messages), content_sha256(work.package),
            brief_ref=work.brief_ref, card_refs=work.card_refs, source_refs=work.source_refs,
            branch_id=scope.branch_id, state_revision=scope.revision, story_order=scope.story_order,
            disclosure_order=work.disclosure, predecessor_drafts=work.predecessor_drafts,
            dependency_refs=work.dependency_refs, candidate_delta_refs=chain, candidate_projection_sha256=digest,
            selection=work.selection, novel_job_id=j.id, material_design_sha256=work.material_design_sha256)
        row = j.reserve(key, {'package': work.package, 'manifest': asdict(manifest), 'messages': messages,
                              'writing_material': WRITING_MATERIAL, 'review_material': REVIEW_MATERIAL,
                              'writing_source_keys': list(work.writing_source_keys), 'capacity_preflight': capacity_report})
    frozen = row['input']
    manifest = frozen['manifest']
    if manifest['candidate_delta_refs'] != [list(ref) for ref in chain] or (
            chain and candidate_projection_digest(j.store, j.head, chain, scene) != manifest['candidate_projection_sha256']):
        raise JobPaused('STALE', key, 'STALE_CANDIDATE_PROJECTION', scene_id=scene)
    _verify_context(calls, key, scene, manifest)
    if row['status'] != 'DONE':
        j.result(key, 'DONE', {'selection': manifest['selection'], 'candidate_delta_refs': manifest['candidate_delta_refs'],
                               'context_sha256': manifest['context_sha256']})
    return frozen


def _verify_context(calls: JobCalls, key: str, scene: str, manifest: dict) -> None:
    j = calls.journal
    j.check_active(key)
    design = scene_materials(j.store, scene)
    if design.get('work_session'):
        from nw.production_methods.selection import verify_sources
        verify_sources(j.store,design['work_session'])
    if manifest.get('material_design_sha256') != (content_sha256(design) if design else None):
        raise ValueError('STALE_MATERIAL: approved scene design changed')
    verify_materials(j.store.directory.parent, design.get('materials', ()))
    manifest_refs(j.store, manifest, scene)
    selected = {CardRef(**ref) for ref in manifest['selection']['selected_refs']}
    if selected and not selected <= set(eligible_rule_refs(j.store)):
        raise JobPaused('STALE', key, 'STALE_METHOD_VERSION', scene_id=scene)



def _draft_input(calls: JobCalls, frozen: dict, purpose: str, draft: Draft, review: dict | None,
                 *, contract: dict | None = None, length_feedback: list[str] | None = None) -> dict:
    package = frozen['package']
    material = frozen.get('review_material' if purpose == 'review' else 'writing_material', '')
    messages, version = draft_messages(package, purpose, draft, review, contract, material,
                                       frozen.get('writing_source_keys', ()), length_feedback)
    dependencies = [*frozen['manifest']['dependency_refs'], asdict(draft_ref(draft))]
    if contract and 'comparison' in contract and contract['comparison']['ref'] not in dependencies:
        dependencies.append(contract['comparison']['ref'])
    for check in contract['checks'] if contract else ():
        if 'character_card' in check and check['character_card']['ref'] not in dependencies:
            dependencies.append(check['character_card']['ref'])
    stage_calls = calls.for_stage(purpose)
    manifest = {**frozen['manifest'], 'purpose': purpose, 'settings': _settings(stage_calls, version, messages),
                'dependency_refs': dependencies}
    return {'manifest': manifest, 'messages': messages, 'package': package,
            'target_draft': asdict(draft_ref(draft))}


def _extract(calls: JobCalls, scene: str, draft: Draft, frozen: dict,
             material_review_run: str | None, hypotheses: list[dict], reader_only: list[dict]) -> StateDelta:
    j = calls.journal
    key = f'scene:{scene}:delta'
    row = j.latest(key)
    if row and row['status'] == 'DONE':
        return read_delta(j.store, row['output']['delta_id'])
    written = frozen['manifest']
    ident = f'{j.id}:{key}'
    scope = {'id': ident, 'branch_id': j.head.branch_id, 'base_revision': j.head.revision,
             'story_order': written['story_order'], 'candidate_delta_refs': written['candidate_delta_refs']}
    if row is None:
        row = j.reserve(key, {'draft_id': draft.id, 'scope': scope})
    elif row['input']['draft_id'] != draft.id:
        raise JobPaused('STALE', key, 'STALE_DRAFT', scene_id=scene)
    scope = row['input']['scope']
    extract_calls = calls.for_stage('state_extract')
    fact_calls = calls.for_stage('fact_review')
    if not j.store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (ident,)).fetchone():
        settings = _settings(extract_calls, 'state-extract-v1', [])
        freeze_delta_input(j.store, draft.id, scope, settings, material_review_run=material_review_run,
                           material_hypotheses=hypotheses, reader_only_spans=reader_only)

    def invoke(kind: str, request: TaskRequest, validate: Callable[[dict], None]) -> TaskResult:
        task_key = f'{key}:{kind}'
        target_calls = fact_calls if kind == 'fact-review' else extract_calls
        return target_calls.task(task_key, lambda: request, validate,
                                 verify=lambda: _verify_context(calls, task_key, scene, frozen['manifest']))

    delta = prepare_delta(j.store, draft.id, ident, calls.provider, calls.config, j.id, invoke=invoke)
    j.result(key, 'DONE', {'delta_id': delta.id, 'sha256': delta.sha256, 'manifest_id': ident})
    return delta


def _core_gate(calls: JobCalls, decide: Callable, key: str, target: dict) -> None:
    choice = calls.journal.gate(key, target, decide, {'approve': 'novel_core', 'reject': 'novel_reject'})
    if choice['action'] == 'reject':
        raise JobPaused('REJECTED', key, 'CORE_CHANGE_REJECTED')


def scene_delta(calls: JobCalls, scene: str, chain: tuple[tuple[str, str], ...], decide: Callable) -> StateDelta:
    j = calls.journal
    prefix = f'scene:{scene}'
    frozen = _inputs(calls, scene, chain)
    prior = j.request['original_drafts'].get(scene)
    review = None
    round_no = int(prior is not None)
    from nw.chapter_break import chapter_end
    ending = chapter_end(frozen['package'])
    max_revisions = read_budget(j.store, j.id).max_revisions
    draft = j.store.get('draft', prior) if prior else None
    def verify() -> None:
        _verify_context(calls, j.current_step or prefix, scene, frozen['manifest'])

    while True:
        if round_no == 0:
            _, draft, _ = calls.for_stage('write').run(f'{prefix}:write', scene, lambda: frozen, verify=verify)
        else:
            _, draft, _ = calls.for_stage('revise').run(
                f'{prefix}:revise:{round_no}', scene,
                lambda: _draft_input(calls, frozen, 'revise', draft, review or {},
                                     length_feedback=(review or {}).get('length_feedback')), verify=verify)
        length_feedback = scene_length_feedback(j.store, scene, frozen['manifest'], draft.text)
        contract, comparison = review_contract(j.store, draft, frozen['manifest'])
        def assess(run: Run) -> dict:
            result = review_result(run, contract, draft, comparison, ending=ending)
            if length_feedback:
                result.update(recommendation='revise', length_feedback=length_feedback)
            return result

        review_run, _, review = calls.for_stage('review').run(
            f'{prefix}:review:{round_no}', scene,
            lambda: _draft_input(calls, frozen, 'review', draft, None, contract=contract, length_feedback=length_feedback),
            assess, verify=verify)
        if review['core_changes']:
            _core_gate(calls, decide, f'{prefix}:core:{round_no}',
                       {'scene_id': scene, 'draft': asdict(draft_ref(draft)), 'review': review})
        if review['recommendation'] == 'pass':
            break
        if round_no >= max_revisions:
            key = f'{prefix}:review-limit'
            if length_feedback:
                raise JobPaused('BLOCKED', key, '篇幅偏差：' + '；'.join(length_feedback),
                                draft_id=draft.id, length_feedback=length_feedback)
            if ending:
                raise JobPaused('BLOCKED', key, '章末仍需修订以通过本版末段的独立审稿', draft_id=draft.id)
            if contract:
                raise JobPaused('BLOCKED', key, 'MATERIAL_EVIDENCE: the current draft requires a passing review',
                                draft_id=draft.id, material_checks=review['material_checks'])
            choice = j.gate(key, {'scene_id': scene, 'draft': asdict(draft_ref(draft)), 'review': review},
                            decide, {'keep': 'novel_review', 'reject': 'novel_reject'})
            if choice['action'] == 'reject':
                raise JobPaused('REJECTED', key, 'DRAFT_REJECTED')
            break
        round_no += 1
    hypotheses = state_hypotheses(scene_materials(j.store, scene), review.get('material_checks', []), draft.id)
    reader_only = reader_spans(contract['checks'], review['material_checks'], draft) if contract else []
    delta = _extract(calls, scene, draft, frozen, review_run.id if contract or ending else None, hypotheses, reader_only)
    key = f'{prefix}:check'
    j.check_active(key)
    findings = check_delta(j.store, delta)
    material_checks = check_material_acceptance(j.store, draft, delta)
    if j.latest(key) is None:
        j.reserve(key, {'delta_id': delta.id, 'sha256': delta.sha256})
    output = {'findings': [asdict(finding) for finding in findings]}
    if material_checks:
        output['material_checks'] = material_checks
    j.result(key, 'DONE', output)
    if any(finding.severity == 'hard' for finding in findings):
        raise JobPaused('BLOCKED', key, 'HARD_FACT_FINDINGS', delta_id=delta.id,
                        findings=[asdict(finding) for finding in findings])
    core = [op for op in delta.operations if op['predicate'].casefold() in CORE_PREDICATES
            and op['expected_old'] != op['new_value']]
    core_findings = [asdict(finding) for finding in findings if finding.code.upper().startswith('CORE_')]
    if core or core_findings:
        _core_gate(calls, decide, f'{prefix}:core-state',
                   {'scene_id': scene, 'delta_id': delta.id, 'sha256': delta.sha256,
                    'operations': core, 'findings': core_findings})
    return delta
