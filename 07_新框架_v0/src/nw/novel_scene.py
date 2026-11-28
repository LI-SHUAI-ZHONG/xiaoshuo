
"""Build, draft, review, and extract one scene within a pinned novel job."""
from dataclasses import asdict, replace
import json
from typing import Callable

from nw.call_budget import BudgetExceeded, prepare_call, read_budget
from nw.call_control import model_settings
from nw.cards import eligible_rule_refs
from nw.context.story import WRITE_PROMPT, StoryScope, build_story_context, scene_scope
from nw.llm.base import GenResult
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
from nw.store import now
from nw.story_delta import (candidate_projection_digest, check_delta, draft_ref, manifest_refs, read_delta)
from nw.story_extract import freeze_delta_input, prepare_delta
from nw.story_models import CardRef, StateDelta
from nw.studio.craft_materials import design_genre_ids
from nw.task_models import InputManifest, TaskRequest, TaskResult, canonical, content_sha256
from nw.tasks import freeze_manifest

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
        write_calls = calls.for_stage('write')
        from nw.context.briefing_compiler import compile_writer_briefing, should_use_natural_briefing
        use_natural = should_use_natural_briefing(write_calls.provider.name, write_calls.config, store=j.store)
        user_content = compile_writer_briefing(work.package, char_limit=limit) if use_natural else canonical(work.package)
        messages = [{'role': 'system', 'content': work.prompt}, {'role': 'user', 'content': user_content}]
        manifest = InputManifest(
            f'{j.id}:{key}', 'write', _settings(write_calls, 'story-write-v1', messages), content_sha256(work.package),
            brief_ref=work.brief_ref, card_refs=work.card_refs, source_refs=work.source_refs,
            branch_id=scope.branch_id, state_revision=scope.revision, story_order=scope.story_order,
            disclosure_order=work.disclosure, predecessor_drafts=work.predecessor_drafts,
            dependency_refs=work.dependency_refs, candidate_delta_refs=chain, candidate_projection_sha256=digest,
            selection=work.selection, novel_job_id=j.id, material_design_sha256=work.material_design_sha256)
        genre_ids = design_genre_ids(scene_materials(j.store, scene))
        row = j.reserve(key, {'package': work.package, 'manifest': asdict(manifest), 'messages': messages,
                              'natural_briefing': use_natural,
                              'writing_material': WRITING_MATERIAL, 'review_material': REVIEW_MATERIAL,
                              'writing_source_keys': list(work.writing_source_keys), 'capacity_preflight': capacity_report,
                              **({'genre_ids': genre_ids} if genre_ids else {})})
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
                 *, contract: dict | None = None, length_feedback: list[str] | None = None,
                 pre_review_note: str = '', revision_diff_note: str = '') -> dict:
    from nw.craft_specs import load_all_craft_specs

    package = frozen['package']
    material = frozen.get('review_material' if purpose == 'review' else 'writing_material', '')
    live_specs = load_all_craft_specs(calls.journal.store)
    messages, version = draft_messages(package, purpose, draft, review, contract, material,
                                       frozen.get('writing_source_keys', ()), length_feedback,
                                       genre_ids=frozen.get('genre_ids'),
                                       craft_specs=live_specs,
                                       pre_review_note=pre_review_note,
                                       revision_diff_note=revision_diff_note)
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


def _spot_fix_revise(calls: JobCalls, step_key: str, scene: str, frozen: dict, draft: Draft,
                     plan: dict, instruction: str, verify: Callable[[], None]) -> tuple[Draft, dict] | None:
    """Execute host-bounded Spot-Fix local revision and persist a first-class revised Draft.

    Returns `(new_draft, splice_meta)` on success, or `None` if model JSON fails so caller
    cleanly falls back to full-scene revise without breaking the job.
    """
    from nw.call_control import send_model
    from nw.craft_specs import build_review_craft_guards, load_all_craft_specs
    from nw.spot_fix import apply_spot_fix_edits, build_spot_fix_messages

    j = calls.journal
    step = j.latest(step_key)
    if step and step['status'] == 'DONE' and step['output'].get('draft_id'):
        return j.store.get('draft', step['output']['draft_id']), step['output'].get('spot_fix') or {}

    revise_calls = calls.for_stage('revise')
    live_specs = load_all_craft_specs(j.store)
    voice_guard = build_review_craft_guards(frozen['package'], specs=live_specs, max_chars=360)
    spot_messages = build_spot_fix_messages(
        draft.text,
        plan,
        instruction=instruction,
        mode='spot-fix',
        voice_guidance=voice_guard,
    )
    verify()
    params = dict(revise_calls.config.params)
    live = revise_calls.provider.name != 'fake'
    gen = send_model(
        revise_calls.provider,
        spot_messages,
        revise_calls.config.model,
        params,
        allow_continuation=False,
        max_empty_retries=(2 if live else 0),
    )
    if gen.finish_reason != 'complete' or not gen.text.strip():
        return None
    try:
        spliced = apply_spot_fix_edits(draft.text, plan, gen.text)
    except (ValueError, RuntimeError):
        return None

    if step is None:
        step = j.reserve(step_key, {'source_draft_id': draft.id, 'mode': 'spot-fix', 'ranges': plan['ranges']})
    ident = call_id(j.id, step_key, step['attempt'])
    dependencies = [*frozen['manifest']['dependency_refs'], asdict(draft_ref(draft))]
    settings = _settings(revise_calls, 'novel-revise-v1', spot_messages)
    manifest = replace(
        InputManifest(**frozen['manifest']),
        id=f'run:{ident}',
        purpose='revise',
        settings=settings,
        dependency_refs=tuple(dependencies),
    )
    if manifest.selection is not None:
        manifest = replace(manifest, selection={**manifest.selection, 'manifest_id': manifest.id})
    if not j.store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (manifest.id,)).fetchone():
        freeze_manifest(j.store, manifest, frozen['package'])
    if j.store.connection.execute('SELECT id FROM runs WHERE id=?', (ident,)).fetchone() is None:
        j.store.add_run(Run(
            ident, scene, 'revise', revise_calls.provider.name, revise_calls.config.model,
            canonical(settings['params']),
            canonical({
                **settings,
                'messages': spot_messages,
                'manifest_id': manifest.id,
                'spot_fix': {
                    'source_draft_id': draft.id,
                    'applied_ranges': spliced['applied_ranges'],
                    'protected_intact': spliced['protected_intact'],
                },
            }),
            canonical(frozen['package']), '', 'error', '{}', now(), '',
        ))
        _, new_draft = j.store.finish_run(ident, GenResult(
            text=spliced['text'],
            finish_reason='complete',
            usage=gen.usage,
            request_id=gen.request_id,
            raw={**(gen.raw if isinstance(gen.raw, dict) else {}), 'spot_fix': spliced},
        ))
    else:
        row = j.store.connection.execute('SELECT id FROM drafts WHERE run_id=?', (ident,)).fetchone()
        new_draft = j.store.get('draft', row['id']) if row else None
    if new_draft is None:
        return None
    j.result(step_key, 'DONE', {
        'run_id': ident,
        'draft_id': new_draft.id,
        'manifest_id': manifest.id,
        'spot_fix': {
            'applied_ranges': spliced['applied_ranges'],
            'protected_intact': spliced['protected_intact'],
            'delta_chars': spliced['delta_chars'],
        },
    })
    return new_draft, spliced


def _extract(calls: JobCalls, scene: str, draft: Draft, frozen: dict,
             material_review_run: str | None, hypotheses: list[dict], reader_only: list[dict],
             *, reconciliation_feedback: str = '', attempt_suffix: str = '') -> StateDelta:
    j = calls.journal
    suffix = f':{attempt_suffix}' if attempt_suffix else ''
    key = f'scene:{scene}:delta{suffix}'
    row = j.latest(key)
    if row and row['status'] == 'DONE':
        return read_delta(j.store, row['output']['delta_id'])
    written = frozen['manifest']
    base_ident = f'{j.id}:scene:{scene}:delta'
    scope = {'id': base_ident, 'branch_id': j.head.branch_id, 'base_revision': j.head.revision,
             'story_order': written['story_order'], 'candidate_delta_refs': written['candidate_delta_refs']}
    if row is None:
        row = j.reserve(key, {'draft_id': draft.id, 'scope': scope, 'reconciliation': bool(reconciliation_feedback)})
    elif row['input']['draft_id'] != draft.id:
        raise JobPaused('STALE', key, 'STALE_DRAFT', scene_id=scene)
    scope = row['input']['scope']
    extract_calls = calls.for_stage('state_extract')
    fact_calls = calls.for_stage('fact_review')
    if not j.store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (base_ident,)).fetchone():
        settings = _settings(extract_calls, 'state-extract-v1', [])
        freeze_delta_input(j.store, draft.id, scope, settings, material_review_run=material_review_run,
                           material_hypotheses=hypotheses, reader_only_spans=reader_only,
                           genre_ids=frozen.get('genre_ids'))

    def invoke(kind: str, request: TaskRequest, validate: Callable[[dict], None]) -> TaskResult:
        task_key = f'{key}:{kind}'
        target_calls = fact_calls if kind == 'fact-review' else extract_calls
        return target_calls.task(task_key, lambda: request, validate,
                                 verify=lambda: _verify_context(calls, task_key, scene, frozen['manifest']))

    delta = prepare_delta(
        j.store, draft.id, base_ident, calls.provider, calls.config, j.id,
        invoke=invoke,
        reconciliation_feedback=reconciliation_feedback,
        attempt_suffix=attempt_suffix,
    )
    j.result(key, 'DONE', {'delta_id': delta.id, 'sha256': delta.sha256, 'manifest_id': base_ident})
    return delta


def _core_gate(calls: JobCalls, decide: Callable, key: str, target: dict) -> None:
    choice = calls.journal.gate(key, target, decide, {'approve': 'novel_core', 'reject': 'novel_reject'})
    if choice['action'] == 'reject':
        raise JobPaused('REJECTED', key, 'CORE_CHANGE_REJECTED')


def _is_manual_author_draft(calls: JobCalls, draft: Draft | None) -> bool:
    if draft is None:
        return False
    run = calls.journal.store.get('run', draft.run_id)
    if run.provider != 'author':
        return False
    try:
        snap = json.loads(run.input_snapshot_json)
    except ValueError:
        return False
    return isinstance(snap, dict) and snap.get('source') == 'studio_manual_author'


def _pin_manual_draft(calls: JobCalls, scene: str, source_draft: Draft, frozen: dict) -> Draft:
    """Bind an author's manual prose to this job's frozen writing manifest before independent 16 review."""
    j = calls.journal
    key = f'scene:{scene}:manual-pin'
    step = j.latest(key)
    if step and step['status'] == 'DONE':
        return j.store.get('draft', step['output']['draft_id'])
    if step is None:
        step = j.reserve(key, {'source_draft_id': source_draft.id})
    ident = call_id(j.id, key, step['attempt'])
    manifest = replace(InputManifest(**frozen['manifest']), id=f'run:{ident}')
    if manifest.selection is not None:
        manifest = replace(manifest, selection={**manifest.selection, 'manifest_id': manifest.id})
    if not j.store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (manifest.id,)).fetchone():
        freeze_manifest(j.store, manifest, frozen['package'])
    existing_run = j.store.connection.execute('SELECT id FROM runs WHERE id=?', (ident,)).fetchone()
    if existing_run is None:
        j.store.add_run(Run(
            ident, scene, 'write', 'author', 'manual-studio', '{}',
            canonical({
                'manifest_id': manifest.id,
                'messages': frozen['messages'],
                'source': 'studio_manual_author',
                'source_draft_id': source_draft.id,
                'branch_id': j.head.branch_id,
            }),
            canonical(frozen['package']), '', 'error', '{}', now(), '',
        ))
        _, draft = j.store.finish_run(ident, GenResult(
            text=source_draft.text, finish_reason='complete',
            usage={'source': 'author'}, request_id=f'manual-pin:{ident}',
            raw={'author': True, 'source_draft_id': source_draft.id},
        ))
    else:
        draft_row = j.store.connection.execute('SELECT id FROM drafts WHERE run_id=?', (ident,)).fetchone()
        draft = j.store.get('draft', draft_row['id']) if draft_row else None
    if draft is None:
        raise JobPaused('BLOCKED', key, '无法为手动草稿绑定冻结写作清单')
    j.result(key, 'DONE', {'run_id': ident, 'draft_id': draft.id, 'manifest_id': manifest.id,
                           'source_draft_id': source_draft.id})
    return draft


def scene_delta(calls: JobCalls, scene: str, chain: tuple[tuple[str, str], ...], decide: Callable) -> StateDelta:
    j = calls.journal
    prefix = f'scene:{scene}'
    frozen = _inputs(calls, scene, chain)
    prior = j.request['original_drafts'].get(scene)
    review = None
    prior_draft = j.store.get('draft', prior) if prior else None
    manual_prior = _is_manual_author_draft(calls, prior_draft)
    round_no = 0 if manual_prior else int(prior is not None)
    from nw.chapter_break import chapter_end
    ending = chapter_end(frozen['package'])
    max_revisions = read_budget(j.store, j.id).max_revisions
    draft = prior_draft
    def verify() -> None:
        _verify_context(calls, j.current_step or prefix, scene, frozen['manifest'])

    from nw.pre_review_gate import format_pre_review_rewrite_feedback, run_pre_review_gate
    from nw.spot_fix import compute_revision_diff, route_repair_scope

    pre_rewrote = False
    episode_baseline_draft: Draft | None = prior_draft if round_no > 0 else None
    last_authorized_paragraphs: list[int] | None = None
    last_pre_report: dict | None = None
    while True:
        if round_no == 0:
            if manual_prior and draft is not None:
                draft = _pin_manual_draft(calls, scene, draft, frozen)
            else:
                _, draft, _ = calls.for_stage('write').run(f'{prefix}:write', scene, lambda: frozen, verify=verify)
            episode_baseline_draft = draft
            last_authorized_paragraphs = None
        else:
            spot_enabled = (
                calls.for_stage('revise').provider.name != 'fake'
                or getattr(calls.config, 'enable_spot_fix', False)
            )
            route = route_repair_scope(
                review,
                draft_text=draft.text,
                pre_report=last_pre_report,
                length_feedback=(review or {}).get('length_feedback'),
            ) if spot_enabled else {'scope': 'structural', 'plan': None}
            spot_result = None
            if route['scope'] == 'local' and route.get('plan'):
                plan = route['plan']
                instruction = str((review or {}).get('notes') or '请修正指定局部区间的问题并保持上下文无缝衔接。')
                spot_result = _spot_fix_revise(
                    calls, f'{prefix}:spot-fix:{round_no}', scene, frozen, draft, plan, instruction, verify,
                )
            if spot_result is not None:
                draft, _ = spot_result
                last_authorized_paragraphs = [
                    idx
                    for r in route['plan']['ranges']
                    for idx in range(r['start_paragraph'], r['end_paragraph'] + 1)
                ]
            else:
                last_authorized_paragraphs = None
                _, draft, _ = calls.for_stage('revise').run(
                    f'{prefix}:revise:{round_no}', scene,
                    lambda: _draft_input(calls, frozen, 'revise', draft, review or {},
                                         length_feedback=(review or {}).get('length_feedback')), verify=verify)
        # Lens 0: 0-Token deterministic pre-review script gate (Scripts < Model < Author)
        pre_report = run_pre_review_gate(
            j.store, scene, draft.text,
            branch=j.head.branch_id,
            revision=frozen['manifest'].get('state_revision'),
            story_order=frozen['manifest'].get('story_order'),
            disclosure=tuple(frozen['manifest']['disclosure_order']) if frozen['manifest'].get('disclosure_order') else None,
            manifest=frozen['manifest'],
        )
        last_pre_report = pre_report
        pre_step_key = f'{prefix}:pre-review:{round_no}'
        if j.latest(pre_step_key) is None:
            j.reserve(pre_step_key, {'draft_id': draft.id})
        j.result(pre_step_key, 'DONE', pre_report)
        allow_auto_rewrite = (
            not pre_rewrote
            and round_no == 0
            and not manual_prior
            and pre_report['action'] == 'auto_rewrite'
            and (calls.for_stage('write').provider.name != 'fake' or getattr(calls.config, 'pre_review_auto_rewrite', False))
        )
        if allow_auto_rewrite:
            pre_rewrote = True
            rewrite_note = format_pre_review_rewrite_feedback(pre_report)
            pre_spot_ok = False
            if calls.for_stage('revise').provider.name != 'fake' or getattr(calls.config, 'enable_spot_fix', False):
                pre_route = route_repair_scope(
                    {'notes': rewrite_note, 'repair_scope': 'local'},
                    draft_text=draft.text,
                    pre_report=pre_report,
                )
                if pre_route['scope'] == 'local' and pre_route.get('plan'):
                    res = _spot_fix_revise(
                        calls, f'{prefix}:pre-spot-fix', scene, frozen, draft, pre_route['plan'], rewrite_note, verify,
                    )
                    if res is not None:
                        draft, _ = res
                        pre_spot_ok = True
                        last_authorized_paragraphs = [
                            idx
                            for r in pre_route['plan']['ranges']
                            for idx in range(r['start_paragraph'], r['end_paragraph'] + 1)
                        ]
            if not pre_spot_ok:
                _, draft, _ = calls.for_stage('revise').run(
                    f'{prefix}:pre-rewrite', scene,
                    lambda: _draft_input(calls, frozen, 'revise', draft, {
                        'recommendation': 'revise',
                        'notes': rewrite_note,
                        'core_changes': [],
                    }), verify=verify)
            pre_report = run_pre_review_gate(
                j.store, scene, draft.text,
                branch=j.head.branch_id,
                revision=frozen['manifest'].get('state_revision'),
                story_order=frozen['manifest'].get('story_order'),
                disclosure=tuple(frozen['manifest']['disclosure_order']) if frozen['manifest'].get('disclosure_order') else None,
                manifest=frozen['manifest'],
            )
            last_pre_report = pre_report
            j.result(pre_step_key, 'DONE', pre_report)
        length_feedback = scene_length_feedback(j.store, scene, frozen['manifest'], draft.text)
        contract, comparison = review_contract(j.store, draft, frozen['manifest'])
        def assess(run: Run) -> dict:
            result = review_result(run, contract, draft, comparison, ending=ending)
            if length_feedback:
                result.update(recommendation='revise', length_feedback=length_feedback)
            return result

        pre_note = pre_report.get('review_handoff_note', '') if calls.for_stage('review').provider.name != 'fake' else ''
        diff_note = ''
        if round_no >= 1 and episode_baseline_draft is not None and episode_baseline_draft.id != draft.id:
            rev_diff = compute_revision_diff(
                episode_baseline_draft.text,
                draft.text,
                authorized_paragraphs=last_authorized_paragraphs,
            )
            diff_step_key = f'{prefix}:revision-diff:{round_no}'
            if j.latest(diff_step_key) is None:
                j.reserve(diff_step_key, {'baseline_draft_id': episode_baseline_draft.id, 'draft_id': draft.id})
            j.result(diff_step_key, 'DONE', rev_diff)
            if calls.for_stage('review').provider.name != 'fake' or getattr(calls.config, 'enable_diff_review', False):
                diff_note = rev_diff['summary_for_review']
        review_run, _, review = calls.for_stage('review').run(
            f'{prefix}:review:{round_no}', scene,
            lambda: _draft_input(calls, frozen, 'review', draft, None, contract=contract,
                                 length_feedback=length_feedback, pre_review_note=pre_note,
                                 revision_diff_note=diff_note),
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
    # Fusion F1: Automatic 1-shot post-settlement state reconciliation (strictly preserves approved prose!)
    can_reconcile = (
        any(finding.severity == 'hard' for finding in findings)
        and (calls.for_stage('state_extract').provider.name != 'fake' or getattr(calls.config, 'auto_reconcile_state', False))
    )
    if can_reconcile:
        rec_key = f'{prefix}:reconcile'
        hard_obs = [
            f'- [{f.code}] {f.explanation}（建议：{f.suggested_action}）'
            for f in findings if f.severity == 'hard'
        ]
        feedback = '\n'.join(hard_obs[:8])
        if j.latest(rec_key) is None:
            j.reserve(rec_key, {'original_delta_id': delta.id, 'hard_count': len(hard_obs)})
        try:
            reconciled_delta = _extract(
                calls, scene, draft, frozen,
                review_run.id if contract or ending else None,
                hypotheses, reader_only,
                reconciliation_feedback=feedback,
                attempt_suffix='reconcile1',
            )
            reconciled_findings = check_delta(j.store, reconciled_delta)
            rec_clean = not any(f.severity == 'hard' for f in reconciled_findings)
            j.result(rec_key, 'DONE', {
                'status': 'reconciled' if rec_clean else 'unresolved',
                'delta_id': reconciled_delta.id,
                'remaining_hard': sum(1 for f in reconciled_findings if f.severity == 'hard'),
            })
            if rec_clean:
                delta = reconciled_delta
                findings = reconciled_findings
        except Exception as exc:
            j.result(rec_key, 'FAILED', {'status': 'error', 'reason': str(exc)[:200]})
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
