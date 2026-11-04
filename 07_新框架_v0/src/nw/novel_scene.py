
"""Build, draft, review, and extract one scene within a pinned novel job."""
from dataclasses import asdict
import json
from typing import Callable

from nw.call_budget import prepare_call, read_budget
from nw.call_control import model_settings
from nw.cards import eligible_rule_refs
from nw.context.story import WRITE_PROMPT, StoryScope, build_story_context, scene_scope
from nw.models import Draft, Run
from nw.novel_calls import JobCalls, call_id
from nw.novel_store import JobPaused
from nw.story_delta import (candidate_projection_digest, check_delta, draft_ref, manifest_refs, read_delta)
from nw.story_extract import freeze_delta_input, prepare_delta
from nw.story_models import CardRef, StateDelta
from nw.task_models import InputManifest, TaskRequest, TaskResult, _object, canonical, content_sha256

REVIEW_PROMPT = (
    '审查本场与约束、场景目标、POV所知和前文的一致性。只输出 JSON '
    '{"recommendation":"pass或revise","notes":"具体意见","core_changes":[]}。'
    '只有影响核心人物目标、世界规则、重要生死、视角形式或终局承诺的变化才填入 core_changes。'
)
REVISE_PROMPT = (
    '根据冻结的工作包、旧稿和审稿意见修订本场。保持作者已确认的设定与披露边界，只输出完整修订正文。'
)
CORE_PREDICATES = frozenset({'core_goal', 'protagonist_goal', 'world_rule', 'pov', 'ending', 'ending_promise',
                            'alive', 'death', 'life_status', '生死', '核心目标', '世界规则', '终局承诺', '视角'})


def _review(run: Run) -> dict:
    raw = json.loads(run.output_text, object_pairs_hook=_object)
    canonical(raw).encode('utf-8')
    if (not isinstance(raw, dict) or set(raw) != {'recommendation', 'notes', 'core_changes'}
            or raw['recommendation'] not in ('pass', 'revise') or not isinstance(raw['notes'], str)
            or not isinstance(raw['core_changes'], list)
            or not all(isinstance(line, str) and line.strip() for line in raw['core_changes'])):
        raise ValueError('review requires a recommendation, notes and a list of core changes')
    return raw


def _messages(prompt: str, payload: dict) -> list[dict]:
    return [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': canonical(payload)}]


def _settings(calls: JobCalls, prompt_version: str, messages: list[dict]) -> dict:
    params, _ = prepare_call(calls.journal.store, calls.journal.id, calls.provider.name, calls.config.params, messages)
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
        work = build_story_context(j.store, scene, scope, read_budget(j.store, j.id).context_char_limit,
                                   candidate_refs=chain)
        digest = candidate_projection_digest(j.store, j.head, chain, scene) if chain else None
        messages = _messages(WRITE_PROMPT, work.package)
        manifest = InputManifest(
            f'{j.id}:{key}', 'write', _settings(calls, 'story-write-v1', messages), content_sha256(work.package),
            brief_ref=work.brief_ref, card_refs=work.card_refs, source_refs=work.source_refs,
            branch_id=scope.branch_id, state_revision=scope.revision, story_order=scope.story_order,
            disclosure_order=work.disclosure, predecessor_drafts=work.predecessor_drafts,
            dependency_refs=work.dependency_refs, candidate_delta_refs=chain, candidate_projection_sha256=digest,
            selection=work.selection, novel_job_id=j.id)
        row = j.reserve(key, {'package': work.package, 'manifest': asdict(manifest), 'messages': messages})
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
    manifest_refs(j.store, manifest, scene)
    selected = {CardRef(**ref) for ref in manifest['selection']['selected_refs']}
    if selected and not selected <= set(eligible_rule_refs(j.store)):
        raise JobPaused('STALE', key, 'STALE_METHOD_VERSION', scene_id=scene)



def _draft_input(calls: JobCalls, frozen: dict, purpose: str, draft: Draft, review: dict | None) -> dict:
    package = frozen['package']
    data = {'context': package, 'draft': asdict(draft)}
    if review is not None:
        data['review'] = review
    prompt, version = (REVIEW_PROMPT, 'novel-review-v1') if purpose == 'review' else (REVISE_PROMPT, 'novel-revise-v1')
    messages = _messages(prompt, data)
    manifest = {**frozen['manifest'], 'purpose': purpose, 'settings': _settings(calls, version, messages),
                'dependency_refs': [*frozen['manifest']['dependency_refs'], asdict(draft_ref(draft))]}
    return {'manifest': manifest, 'messages': messages, 'package': package,
            'target_draft': asdict(draft_ref(draft))}


def _extract(calls: JobCalls, scene: str, draft: Draft, frozen: dict) -> StateDelta:
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
    if not j.store.connection.execute('SELECT 1 FROM input_manifests WHERE id=?', (ident,)).fetchone():
        settings = _settings(calls, 'state-extract-v1', [])
        freeze_delta_input(j.store, draft.id, scope, settings)

    def invoke(kind: str, request: TaskRequest, validate: Callable[[dict], None]) -> TaskResult:
        task_key = f'{key}:{kind}'
        return calls.task(task_key, lambda: request, validate,
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
    max_revisions = read_budget(j.store, j.id).max_revisions
    draft = j.store.get('draft', prior) if prior else None
    def verify() -> None:
        _verify_context(calls, j.current_step or prefix, scene, frozen['manifest'])

    while True:
        if round_no == 0:
            _, draft, _ = calls.run(f'{prefix}:write', scene, lambda: frozen, verify=verify)
        else:
            _, draft, _ = calls.run(f'{prefix}:revise:{round_no}', scene,
                                    lambda: _draft_input(calls, frozen, 'revise', draft, review or {}), verify=verify)
        _, _, review = calls.run(f'{prefix}:review:{round_no}', scene,
                                 lambda: _draft_input(calls, frozen, 'review', draft, None), _review, verify=verify)
        if review['core_changes']:
            _core_gate(calls, decide, f'{prefix}:core:{round_no}',
                       {'scene_id': scene, 'draft': asdict(draft_ref(draft)), 'review': review})
        if review['recommendation'] == 'pass':
            break
        if round_no == max_revisions:
            key = f'{prefix}:review-limit'
            choice = j.gate(key, {'scene_id': scene, 'draft': asdict(draft_ref(draft)), 'review': review},
                            decide, {'keep': 'novel_review', 'reject': 'novel_reject'})
            if choice['action'] == 'reject':
                raise JobPaused('REJECTED', key, 'DRAFT_REJECTED')
            break
        round_no += 1
    delta = _extract(calls, scene, draft, frozen)
    key = f'{prefix}:check'
    j.check_active(key)
    findings = check_delta(j.store, delta)
    if j.latest(key) is None:
        j.reserve(key, {'delta_id': delta.id, 'sha256': delta.sha256})
    j.result(key, 'DONE', {'findings': [asdict(finding) for finding in findings]})
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
