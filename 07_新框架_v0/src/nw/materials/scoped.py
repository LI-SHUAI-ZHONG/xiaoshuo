"""Independent material review over complete, version-pinned chapter scopes."""
from dataclasses import asdict, replace
import json

from nw.call_budget import prepare_call
from nw.call_control import model_settings
from nw.materials.binding import verify_materials
from nw.materials.evidence import _span, scene_checks, scene_materials
from nw.materials.layer_workflow import PROMPT as LAYER_PROMPT, validate_layer_check
from nw.materials.stage_effects import enrich_scope, metric_failure
from nw.materials.stage_input import check_source_keys, step_material_prompt
from nw.materials.steps.review_scope import MATERIAL as SCOPE_MATERIAL
from nw.store import Store
from nw.story_delta import draft_ref
from nw.story_models import StateDelta, StateHead
from nw.story_state import approved_scene_positions, revision_state
from nw.task_models import InputManifest, _object, _text, canonical, content_sha256
from nw.tasks import read_input_manifest

KEY = 'batch:material-scope-review'
_SELECTED_PROMPT_VERSION = 'material-scope-review-v2'
PROMPT = (
    '按 material_scope_review 中的完整稿件范围独立审查原始资料合同。只输出 JSON '
    '{"recommendation":"pass或revise","notes":"具体结论","material_checks":[]}。'
    '每个检查返回 id、status（pass/failed/unverified）、reason、evidence、source_checks。'
    'source_checks 必须逐项覆盖 source_contract.obligations 的原始字段ID，每项含 id、status、reason、evidence。'
    '字段status另可为not_applicable，但仅用于已批准source_scope标记不适用的项。'
    'evidence 每项含稿件ref的kind、id、version、sha256及start、end、quote，引用单段内足够完整的精确句段。'
    '检查整体通过须引用该范围每章的实际稿件；每个通过的来源字段也须有真实段落和解释。'
    '完整阅读所有场景后再判断整章数量、因果、语体、节奏或全书要求。不能用单场表现替代整章或全书。'
    '不修改小说事实，不生成替代正文；不足时返回unverified或failed。'
) + LAYER_PROMPT


def _pov_previous(active: dict, scenes: set) -> set:
    ordered = sorted(active, key=active.get)
    return {ordered[index-1] for index, scene in enumerate(ordered) if index and scene in scenes}


def _scope_positions(check: dict, active: dict) -> dict:
    scope = check['binding']['review_scope']
    chapters = set(scope['chapters'])
    indices = check.get('source_contract', {}).get('evidence_scope', {}).get('scene_indices')
    needed = {scene: pos for scene, pos in active.items() if pos[0] in chapters}
    if {pos[0] for pos in needed.values()} != chapters or scope['kind'] == 'book' and (
            {pos[0] for pos in active.values()} != chapters):
        raise ValueError('MATERIAL_SCOPE_INCOMPLETE: the approved chapter range must match the source scope')
    if indices:
        expected = {(chapter, index) for chapter in chapters for index in indices}
        needed = {scene: pos for scene, pos in needed.items() if pos in expected}
        if set(needed.values()) != expected or len(needed) != len(expected):
            raise ValueError('MATERIAL_SCOPE_INCOMPLETE: each source-required scene position needs an approved scene')
    return needed


def scope_contract(store: Store, deltas: list[StateDelta], head: StateHead) -> dict | None:
    checks, designs = {}, {}
    for delta in deltas:
        draft = store.get('draft', delta.draft_id)
        design = scene_materials(store, draft.scene_id)
        verify_materials(store.directory.parent, design.get('materials', ()))
        designs[draft.scene_id] = content_sha256(design)
        for check in scene_checks(design, scoped=True):
            ident = check['id'] + ':' + content_sha256(check['binding'])[:16]
            checks[ident] = {**check, 'id': ident, 'source_id': check['id']}
    if not checks:
        return None
    snapshot = revision_state(store, head)
    active = approved_scene_positions(store, snapshot)
    slots = {key: value['draft_id'] for key, value in snapshot['slots'].items()}
    for delta in deltas:
        draft = store.get('draft', delta.draft_id)
        slots[draft.scene_id] = draft.id
    needed = {}
    for check in checks.values():
        observed = _scope_positions(check, active)
        needed.update(observed)
        if check['profile'] == 'pov_process':
            previous_scenes = _pov_previous(active, set(observed))
            check['comparison_draft_ids'] = sorted(slots[scene] for scene in previous_scenes if scene in slots
                and active[scene][0] not in check['binding']['review_scope']['chapters'])
            for previous in previous_scenes:
                needed[previous] = active[previous]
    if set(needed) - slots.keys():
        raise ValueError('MATERIAL_SCOPE_INCOMPLETE: each required approved scene needs a current draft')
    drafts = []
    for scene, pos in sorted(needed.items(), key=lambda item: item[1]):
        draft = store.get('draft', slots[scene])
        if draft.scene_id != scene:
            raise ValueError('MATERIAL_SCOPE_INCOMPLETE: draft belongs to another scene')
        drafts.append({'scene_id': scene, 'chapter_index': pos[0], 'scene_index': pos[1],
                       'scene_card_id': json.loads(store.get('scene',scene).card_json)['story']['scene_ref']['card_id'],
                       'ref': asdict(draft_ref(draft)), 'text': draft.text})
    enrich_scope(store, list(checks.values()), drafts, head, deltas)
    return {'head': asdict(head), 'checks': [checks[key] for key in sorted(checks)], 'drafts': drafts,
            'designs': designs, 'batch': [{'delta_id': delta.id, 'delta_sha256': delta.sha256,
                                         'draft_id': delta.draft_id} for delta in deltas]}


def precheck_scope(store: Store, scenes: list[str], head: StateHead) -> None:
    snapshot = revision_state(store, head)
    active = approved_scene_positions(store, snapshot)
    available = set(scenes) | snapshot['slots'].keys()
    for scene in scenes:
        design = scene_materials(store, scene)
        for check in scene_checks(design, scoped=True):
            needed = _scope_positions(check, active)
            if check['profile'] == 'pov_process':
                for previous in _pov_previous(active, set(needed)):
                    needed[previous] = active[previous]
            if set(needed) - available:
                raise ValueError('MATERIAL_SCOPE_INCOMPLETE: write all missing approved scenes in the declared range together')


def _spans(store: Store, values: object, visible: dict) -> list[dict]:
    if not isinstance(values, list):
        raise ValueError('MATERIAL_SCOPE_EVIDENCE: expected exact draft evidence')
    result = []
    for raw in values:
        if not isinstance(raw, dict) or not _text(raw.get('id')) or raw['id'] not in visible:
            raise ValueError('MATERIAL_SCOPE_EVIDENCE: evidence is outside the frozen scope')
        draft = store.get('draft', raw['id'])
        result.append(_span(raw, {draft.id: draft}, draft))
    return result


def _meaningful(spans: list[dict]) -> list[dict]:
    return [span for span in spans if len(''.join(span['quote'].split())) >= 8]


def _covers_scope(spans: list[dict], visible: dict, check: dict) -> bool:
    chapters = check['binding']['review_scope']['chapters']
    scope = check.get('source_contract', {}).get('evidence_scope', {})
    meaningful = _meaningful(spans)
    if scope.get('chapter_boundary_sentences'):
        last = max((draft for draft in visible.values() if draft['chapter_index'] == chapters[0]),
                   key=lambda draft: draft['scene_index'])
        first = min((draft for draft in visible.values() if draft['chapter_index'] == chapters[1]),
                    key=lambda draft: draft['scene_index'])
        return (any(span['id'] == last['ref']['id'] and span['end'] >= len(last['text'].rstrip())
                    for span in meaningful)
                and any(span['id'] == first['ref']['id']
                        and span['start'] <= len(first['text']) - len(first['text'].lstrip())
                        for span in meaningful))
    if indices := scope.get('scene_indices'):
        return set(indices) <= {visible[span['id']]['scene_index'] for span in meaningful}
    return set(chapters) <= {visible[span['id']]['chapter_index'] for span in meaningful}


def scope_result(store: Store, run, contract: dict) -> dict:
    result = json.loads(run.output_text, object_pairs_hook=_object)
    canonical(result).encode('utf-8')
    if (not isinstance(result, dict) or set(result) != {'recommendation', 'notes', 'material_checks'}
            or result['recommendation'] not in ('pass', 'revise') or not _text(result['notes'])
            or not isinstance(result['material_checks'], list)):
        raise ValueError('MATERIAL_SCOPE_EVIDENCE: invalid independent review envelope')
    expected = {row['id']: row for row in contract['checks']}
    visible = {row['ref']['id']: row for row in contract['drafts']}
    if len(result['material_checks']) != len(expected):
        raise ValueError('MATERIAL_SCOPE_EVIDENCE: every scoped rule needs its own result')
    for row in result['material_checks']:
        layer_fields = {'layer_check'} if isinstance(row, dict) and _text(row.get('id')) and row['id'] in expected and 'layer_contract' in expected[row['id']] else set()
        if (not isinstance(row, dict) or set(row) != {'id', 'status', 'reason', 'evidence', 'source_checks'} | layer_fields
                or not _text(row['id']) or row['id'] not in expected or not _text(row['reason'])
                or row['status'] not in ('pass', 'failed', 'unverified')):
            raise ValueError('MATERIAL_SCOPE_EVIDENCE: invalid or duplicate scope check')
        check = expected.pop(row['id'])
        chapters = set(check['binding']['review_scope']['chapters'])
        indices = check.get('source_contract', {}).get('evidence_scope', {}).get('scene_indices')
        rule_visible = {ident: value for ident, value in visible.items()
                        if (value['chapter_index'] in chapters and (not indices or value['scene_index'] in indices))
                        or ident in check.get('comparison_draft_ids', [])}
        spans = _spans(store, row['evidence'], rule_visible)
        if layer_fields:
            layer = validate_layer_check(row['layer_check'])
            layer_spans = _spans(store, layer['evidence'], rule_visible)
            if layer['status'] == 'pass' and (not _covers_scope(layer_spans, rule_visible, check)
                    or any(layer['reason'].strip() == span['quote'].strip() for span in layer_spans)):
                raise ValueError('MATERIAL_TRANSLATION_EVIDENCE: effect review requires evidence at the source-required positions')
            if layer['status'] != 'pass':
                result['recommendation'] = 'revise'
        if row['status'] == 'pass' and not _covers_scope(spans, rule_visible, check):
            raise ValueError('MATERIAL_SCOPE_EVIDENCE: pass requires meaningful evidence at the source-required positions')
        fields = {field['id']: field for field in check['source_contract']['obligations']}
        if not isinstance(row['source_checks'], list) or len(row['source_checks']) != len(fields):
            raise ValueError('MATERIAL_SCOPE_EVIDENCE: every original source obligation needs a result')
        for field in row['source_checks']:
            if (not isinstance(field, dict) or set(field) != {'id', 'status', 'reason', 'evidence'}
                    or not _text(field['id']) or field['id'] not in fields or not _text(field['reason'])
                    or field['status'] not in ('pass', 'failed', 'unverified', 'not_applicable')):
                raise ValueError('MATERIAL_SCOPE_EVIDENCE: invalid source obligation result')
            fields.pop(field['id'])
            evidence = _spans(store, field['evidence'], rule_visible)
            if field['status'] == 'not_applicable':
                if check['binding']['source_scope'][field['id']]['disposition'] != 'not_applicable':
                    raise ValueError('MATERIAL_SCOPE_EVIDENCE: required source field cannot be skipped')
            elif field['status'] == 'pass' and (not any(rule_visible[span['id']]['chapter_index'] in chapters
                    for span in _meaningful(evidence)) or any(
                    field['reason'].strip() == span['quote'].strip() for span in evidence)):
                raise ValueError('MATERIAL_SCOPE_EVIDENCE: explain each original field using real prose')
        failure = metric_failure(check, check.get('stage_metrics', {}))
        if failure:
            row['status'] = 'failed'
            row['reason'] += '；程序核验：' + failure
        if row['status'] != 'pass' or any(field['status'] in ('failed', 'unverified') for field in row['source_checks']):
            result['recommendation'] = 'revise'
    return result


def review_scope(calls, deltas: list[StateDelta]) -> dict | None:
    from nw.novel_store import JobPaused

    j = calls.journal
    contract = scope_contract(j.store, deltas, j.head)
    if contract is None:
        return None
    j.current_step = KEY
    package = {'material_scope_review': contract}

    def verify() -> None:
        j.check_active(KEY)
        if scope_contract(j.store, deltas, j.head) != contract:
            raise ValueError('STALE_MATERIAL: complete scope drafts or adoption changed')

    def prepare() -> dict:
        verify()
        body = canonical(package)
        prompt = step_material_prompt(PROMPT, SCOPE_MATERIAL, check_source_keys(contract['checks']))
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': body}]
        original, _ = read_input_manifest(j.store, deltas[-1].manifest_id)
        params, _ = prepare_call(j.store, j.id, calls.provider.name, calls.config.params, messages)
        manifest = replace(InputManifest(**original), id=f'{j.id}:{KEY}', purpose='review',
            context_sha256=content_sha256(package), material_design_sha256=content_sha256(contract), selection=None,
            settings=model_settings(calls.provider, calls.config.model, params, _SELECTED_PROMPT_VERSION),
            dependency_refs=tuple(draft_ref(j.store.get('draft', row['ref']['id'])) for row in contract['drafts']))
        return {'package': package, 'messages': messages, 'manifest': asdict(manifest),
                'scope_material': SCOPE_MATERIAL}

    scene = j.store.get('draft', deltas[-1].draft_id).scene_id
    run, _, result = calls.run(KEY, scene, prepare, lambda item: scope_result(j.store, item, contract), verify=verify)
    if result['recommendation'] != 'pass':
        raise JobPaused('BLOCKED', KEY, 'MATERIAL_SCOPE_REVIEW: required scope needs revision', run_id=run.id,
                        material_checks=result['material_checks'])
    return result


def check_scope_acceptance(store: Store, deltas: list[StateDelta], head: StateHead) -> list[dict]:
    contract = scope_contract(store, deltas, head)
    if contract is None:
        return []
    manifests = [read_input_manifest(store, delta.manifest_id)[0] for delta in deltas]
    jobs = {manifest.get('novel_job_id') for manifest in manifests}
    if len(jobs) != 1 or None in jobs:
        raise ValueError('MATERIAL_SCOPE_EVIDENCE: scope acceptance requires its originating novel job')
    job = next(iter(jobs))
    step = store.connection.execute('''SELECT * FROM novel_steps WHERE job_id=? AND step_key=?
                                      ORDER BY attempt DESC LIMIT 1''', (job, KEY)).fetchone()
    if step is None or step['status'] != 'DONE':
        raise ValueError('MATERIAL_SCOPE_EVIDENCE: independent complete-scope review is missing')
    output = json.loads(step['output_json'])
    run = store.get('run', output['run_id'])
    snapshot = json.loads(run.input_snapshot_json)
    manifest, package = read_input_manifest(store, snapshot['manifest_id'])
    expected = {'material_scope_review': contract}
    refs = [row['ref'] for row in contract['drafts']]
    frozen = json.loads(step['input_json'])
    material = frozen.get('scope_material', '')
    if manifest['settings']['prompt_version'] == _SELECTED_PROMPT_VERSION:
        prompt = step_material_prompt(PROMPT, material, check_source_keys(contract['checks']))
    else:
        prompt = PROMPT + '\n\n' + material if material else PROMPT
    messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': canonical(expected)}]
    if (run.kind != 'review' or run.finish_reason != 'complete' or not run.ended_at
            or run.id in {store.get('draft', delta.draft_id).run_id for delta in deltas}
            or manifest['purpose'] != 'review' or manifest.get('novel_job_id') != job
            or manifest['branch_id'] != head.branch_id or manifest['state_revision'] != head.revision
            or manifest.get('material_design_sha256') != content_sha256(contract)
            or manifest['dependency_refs'] != refs or package != expected
            or json.loads(run.context_package_json) != expected
            or snapshot['messages'] != messages):
        raise ValueError('MATERIAL_SCOPE_EVIDENCE: scope review does not match these exact drafts and branch')
    result = scope_result(store, run, contract)
    if result['recommendation'] != 'pass':
        raise ValueError('MATERIAL_SCOPE_EVIDENCE: every required scope check must pass')
    return [{**row, 'verification': 'scope_verified'} for row in result['material_checks']]
