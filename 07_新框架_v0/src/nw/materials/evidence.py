"""Prose and state evidence for the materials adopted by an approved scene."""
from dataclasses import asdict
import json
import re

from nw.cards import card_input_ref, read_card
from nw.materials.binding import scene_routes, verify_materials
from nw.materials.layer_workflow import PROMPT as LAYER_PROMPT, has_layers, validate_layer_check
from nw.materials.process_workflow import validate_processes
from nw.materials.stage_workflow import stage_checks
from nw.models import Draft, Run
from nw.store import Store
from nw.story_delta import _evidence, candidate_snapshot, draft_ref
from nw.story_models import CardRef, Fact, StateDelta, StateHead
from nw.story_state import revision_state
from nw.task_models import _text, canonical, content_sha256
from nw.tasks import read_input_manifest

PROMPT = (
    'profile=method_work 时，以method_sources原义、method_artifact和method_operation为依据，'
    '核对模型是否实际执行方法并产生所需效果；只说知道方法、只写一个动作词或复述用途不能通过。'
    '逐条审查 material_review.checks。另回 material_checks 数组，每项只有 id、status、reason、evidence。'
    'status 为 pass、failed 或 unverified。逐项判断指定动作、表达或效果是否实际成立。'
    '引用原文时 evidence 每项含 kind、id、version、sha256（来自 draft 或 comparison.ref）、'
    'start、end（正文 Unicode 半开区间）、quote（精确原文）。每处取一个段落内的足够语句。'
    '每条 pass 需要当前正文证据与解释。跨章语体还须引用 comparison.text 中的前章叙述，'
    '对照句式、用词和叙述距离。名称、关键词、计划或资料号不足以通过。'
    '含 source_contract.obligations 的条目须另含 source_checks 数组，逐项返回其中真实来源字段 ID、'
    'status（pass、failed、unverified 或 not_applicable）、reason 和 evidence。'
    '每个来源条件、例外、限制和检查点均须回传。not_applicable 只用于条件未触发的例外或边界，须说明原因。'
) + LAYER_PROMPT
_PARAGRAPH = re.compile(r'\r?\n[ \t]*\r?\n')
_EXCERPT_LIMIT = 1600
_VISIBLE = {
    'static_binding': ('restriction', 'cost'),
    'dynamic_binding': ('trigger', 'choice', 'cost'),
    'anchor': ('object', 'beat', 'timing', 'condition'),
    'static_relation': ('mechanism', 'restriction', 'cost', 'excludes'),
    'dynamic_relation': ('trigger', 'choice', 'cost', 'failure', 'knowledge_boundary'),
    'type_transition': ('trigger', 'choice', 'cost', 'failure', 'knowledge_boundary'),
}


def scene_materials(store: Store, scene_id: str, scene_ref: dict | None = None) -> dict:
    card = json.loads(store.get('scene', scene_id).card_json)
    pointer = card.get('_nw_material_plan')
    if pointer is None:
        binding = card.get('story')
        ref = scene_ref or (binding.get('scene_ref') if isinstance(binding, dict) else None)
        if isinstance(ref, dict) and store.connection.execute("""
                SELECT 1 FROM plan_applications AS plan, json_each(plan.mapping_json, '$.chapters') AS chapter,
                json_each(chapter.value, '$.scenes') AS scene
                WHERE json_type(scene.value,'$.material_key')='text'
                  AND json_extract(scene.value,'$.scene_ref.card_id')=?
                  AND json_extract(scene.value,'$.scene_ref.version')=? LIMIT 1
                """, (ref.get('card_id'), ref.get('version'))).fetchone():
            raise ValueError('MATERIAL_DESIGN: use the original materialized scene for this scene card')
        return {}
    if not _text(pointer):
        raise ValueError('MATERIAL_DESIGN: invalid applied plan reference')
    row = store.connection.execute('SELECT mapping_json FROM plan_applications WHERE proposal_id=?',
                                   (pointer,)).fetchone()
    if row is None:
        raise ValueError('MATERIAL_DESIGN: applied plan is missing')
    application = json.loads(row[0])
    match = next((entry for chapter in application['chapters'] for entry in chapter['scenes']
                  if entry['scene_id'] == scene_id), {})
    design = application.get('material_design')
    if not design or 'material_key' not in match or scene_ref is not None and scene_ref != match['scene_ref']:
        raise ValueError('MATERIAL_DESIGN: scene does not belong to this approved material plan')
    from nw.materials.work_application import validate_saved_work
    validate_saved_work(store,pointer,design,application['root'])
    process_artifacts = {'process_bindings': design['process_bindings']} if design.get('process_bindings') else {}
    context = design.get('process_context', {})
    validate_processes({**context, 'material_bindings': design.get('scene_bindings', {}), **process_artifacts},
                       'chapter', design['materials'], design.get('material_deferrals'), existing=context.get('existing'))
    return {'materials': design['materials'], 'book_bindings': design['book_bindings'],
            **({key:design[key] for key in ('work_session','work_application')} if design.get('work_session') else {}),
            'material_deferrals': design.get('material_deferrals', {}),
            'bindings': design.get('scene_bindings', {}).get(match['material_key'], {}),
            'process_bindings': design.get('process_bindings', {}), 'material_key': match['material_key'],
            'scene_card_id': match['scene_ref']['card_id'],
            'chapter_index': store.get('chapter', store.get('scene', scene_id).chapter_id).index,
            'scene_members': context.get('members', []), 'process_ids': context.get('ids', {})}


def scene_checks(design: dict, *, scoped: bool = False) -> list[dict]:
    rows = scene_routes(design.get('materials', ()), design.get('material_deferrals'))
    bindings = design.get('bindings', {})
    if rows.keys() != bindings.keys():
        raise ValueError('MATERIAL_DESIGN: approved scene bindings do not match the required sources')
    from nw.materials.work_application import work_checks
    methods=(work_checks(design['work_session'],design['work_application'],design['material_key'],design.get('process_ids'))
             if design.get('work_session') and not scoped else [])
    return [
        {'id': ident, 'profile': row['profile'], 'binding': bindings[ident],
         **({'source_contract': row['review']['contract'], 'source_refs': row['review']['source_refs']}
            if row['review'].get('adjudication_policy') else {}),
         **({'layer_contract': row['review']['layer_contract']} if has_layers(row) else {}),
         'evidence_required': row['review']['evidence_required']}
        for ident, row in rows.items() if bindings[ident].get('disposition', 'selected') == 'selected'
        and (row['profile'] == 'scope_review') == scoped
    ] + stage_checks(design, scoped=scoped) + methods


def writer_checks(design: dict) -> list[dict]:
    return [
        {'id': row['id'], **{key: row['binding'][key]
                            for key in ('observable', 'check', *_VISIBLE.get(row['profile'], ()))}}
        for row in scene_checks(design) if row['profile'] not in ('editor', 'character_editor', 'prose_review', 'pov_process')
    ]


def state_hypotheses(design: dict, checks: list[dict], draft_id: str) -> list[dict]:
    bindings = {r['id']: r['binding'] for r in scene_checks(design)}
    return [
        {'id': check['id'], 'transitions': bindings[check['id']]['state'],
         'review_spans': [span for span in check['evidence'] if span['id'] == draft_id]}
        for check in checks if bindings[check['id']].get('state')
    ]


def verify_preconditions(design: dict, facts: list[Fact], active_ids: set[str]) -> None:
    before = {(fact.entity_id, fact.predicate, fact.holder): fact.value
              for fact in facts if fact.claim == 'fact'}
    for ident, binding in [(row['id'], row['binding']) for row in scene_checks(design)]:
        for field in ('source_card', 'target_card', 'observer', 'character'):
            if field in binding and binding[field] not in active_ids:
                raise ValueError(f'MATERIAL_DESIGN: project entity is unavailable for {ident}')
        for item in binding.get('state', []):
            key = (item['entity_id'], item['predicate'], item['holder'])
            if item['holder'] != 'WORLD' and item['holder'] not in active_ids:
                raise ValueError(f'MATERIAL_DESIGN: knowledge holder is unavailable for {ident}')
            if canonical(before.get(key)) != canonical(item['expected_old']):
                raise ValueError(f'MATERIAL_PRECONDITION: {ident} {key} does not match frozen state')


def comparison_draft(store: Store, scene_id: str, snapshot: dict) -> Draft | None:
    chapter = store.get('scene', scene_id).chapter_id
    index = store.get('chapter', chapter).index
    drafts = []
    for other_id, slot in snapshot['slots'].items():
        scene = store.get('scene', other_id)
        chapter_index = store.get('chapter', scene.chapter_id).index
        if chapter_index < index:
            drafts.append((chapter_index, scene.index, slot['draft_id']))
    return store.get('draft', max(drafts)[2]) if drafts else None


def review_contract(store: Store, draft: Draft, manifest: dict) -> tuple[dict | None, Draft | None]:
    checks = scene_checks(scene_materials(store, draft.scene_id))
    if not checks:
        return None, None
    contract = {'draft': asdict(draft_ref(draft)), 'checks': checks}
    comparison = None
    head = StateHead(manifest['branch_id'], manifest['state_revision'])
    for check in checks:
        if check['profile'] == 'cast_presence_review':
            from nw.materials.cast_appearances import other_named_characters
            check['other_named'] = other_named_characters(store, head, draft, check['roster'])
    if any(check['profile'] == 'character_editor' for check in checks):
        versions = {row['card_id']: row['version'] for row in revision_state(store, head)['settings']}
        for check in checks:
            if check['profile'] != 'character_editor':
                continue
            ident = check['binding']['character']
            if ident not in versions:
                raise ValueError('MATERIAL_PRECONDITION: the character review needs an active character card')
            card = read_card(store, CardRef(ident, versions[ident]))
            if card['kind'] != 'character':
                raise ValueError('MATERIAL_PRECONDITION: the material target is not a character card')
            check['character_card'] = {'ref': asdict(card_input_ref(card)), 'body': card['body']}
    if any(check['profile'] == 'editor' for check in checks):
        chain = manifest['candidate_delta_refs']
        snapshot = (candidate_snapshot(store, head, chain, draft.scene_id) if chain else revision_state(store, head))
        comparison = comparison_draft(store, draft.scene_id, snapshot)
        if comparison is None:
            raise ValueError('MATERIAL_PRECONDITION: cross-chapter review requires a prior chapter draft')
        contract['comparison'] = {'ref': asdict(draft_ref(comparison)), 'text': comparison.text[:_EXCERPT_LIMIT]}
    return contract, comparison


def _span(raw: dict, drafts: dict[str, Draft], current: Draft) -> dict:
    if not isinstance(raw, dict) or set(raw) != {'kind', 'id', 'version', 'sha256', 'start', 'end', 'quote'}:
        raise ValueError('MATERIAL_EVIDENCE: expected a pinned draft span and exact quote')
    target = drafts.get(raw['id']) if _text(raw['id']) else None
    if target is None or {key: raw[key] for key in ('kind', 'id', 'version', 'sha256')} != asdict(draft_ref(target)):
        raise ValueError('MATERIAL_EVIDENCE: wrong draft, version or hash')
    if type(raw['version']) is not int:
        raise ValueError('MATERIAL_EVIDENCE: draft version must be an integer')
    _evidence({'draft_id': target.id, 'text_sha256': raw['sha256'], 'start': raw['start'], 'end': raw['end']}, target)
    if (raw['quote'] != target.text[raw['start']:raw['end']] or _PARAGRAPH.search(raw['quote'])
            or target != current and raw['end'] > _EXCERPT_LIMIT):
        raise ValueError('MATERIAL_EVIDENCE: quote must match a visible paragraph span')
    return raw


def validate_review(rows: object, contract: dict, draft: Draft, comparison: Draft | None) -> list[dict]:
    required = {row['id']: row for row in contract['checks']}
    if not isinstance(rows, list) or len(rows) != len(required):
        raise ValueError('MATERIAL_EVIDENCE: missing required review checks')
    drafts = {draft.id: draft}
    if comparison is not None:
        drafts[comparison.id] = comparison
    for row in rows:
        optional = {'source_checks'} if isinstance(row, dict) and _text(row.get('id')) and row['id'] in required and (
            'source_contract' in required[row['id']]) else set()
        if isinstance(row, dict) and _text(row.get('id')) and row['id'] in required and 'layer_contract' in required[row['id']]:
            optional |= {'layer_check'}
        if isinstance(row, dict) and _text(row.get('id')) and row['id'] in required and required[row['id']]['profile'] == 'cast_presence_review':
            optional |= {'people'}
        if (not isinstance(row, dict) or set(row) != {'id', 'status', 'reason', 'evidence'} | optional
                or not _text(row['id']) or row['id'] not in required
                or row['status'] not in ('pass', 'failed', 'unverified') or not _text(row['reason'])
                or not isinstance(row['evidence'], list)):
            raise ValueError('MATERIAL_EVIDENCE: duplicate, invalid or unrequested review check')
        rule = required.pop(row['id'])
        if 'source_checks' in optional:
            _source_checks(row['source_checks'], rule['source_contract'].get('obligations', []),
                           rule['binding']['source_scope'], drafts, draft)
        if 'layer_check' in optional:
            layer = validate_layer_check(row['layer_check'])
            layer_spans = [_span(item, drafts, draft) for item in layer['evidence']]
            needed = drafts.keys() if rule['profile'] == 'editor' else {draft.id}
            if layer['status'] == 'pass' and (not needed <= {
                    span['id'] for span in layer_spans if len(''.join(span['quote'].split())) >= 8}
                    or any(layer['reason'].strip() == span['quote'].strip() for span in layer_spans)):
                raise ValueError('MATERIAL_TRANSLATION_EVIDENCE: explain the actual effect with the required draft passages')
        spans = [_span(item, drafts, draft) for item in row['evidence']]
        if 'people' in optional:
            from nw.materials.cast_appearances import check_people
            check_people(rule, row, draft)
        ids = {span['id'] for span in spans}
        if row['status'] == 'pass':
            if draft.id not in ids or (rule['profile'] == 'editor' and ids != drafts.keys()):
                raise ValueError('MATERIAL_EVIDENCE: pass requires the draft spans for this rule')
            if any(row['reason'].strip() == item['quote'].strip() for item in spans):
                raise ValueError('MATERIAL_EVIDENCE: explain the judgment beyond quoting the draft')
            meaningful = {span['id'] for span in spans if len(''.join(span['quote'].split())) >= 8
                          and span['quote'] != row['id']}
            if draft.id not in meaningful or rule['profile'] == 'editor' and meaningful != drafts.keys():
                raise ValueError('MATERIAL_EVIDENCE: cite a meaningful passage, not a keyword')
    return rows


def _source_checks(rows: object, obligations: list[dict], scope: dict,
                    drafts: dict[str, Draft], draft: Draft) -> None:
    expected = {item['id']: item for item in obligations}
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError('MATERIAL_EVIDENCE: every original source obligation needs a result')
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'id','status','reason','evidence'}
                or not _text(row['id']) or row['id'] not in expected
                or row['status'] not in ('pass','failed','unverified','not_applicable')
                or not _text(row['reason']) or not isinstance(row['evidence'], list)):
            raise ValueError('MATERIAL_EVIDENCE: invalid or duplicate source obligation result')
        source = expected.pop(row['id'])
        spans = [_span(item, drafts, draft) for item in row['evidence']]
        if row['status'] == 'not_applicable':
            if scope[row['id']]['disposition'] != 'not_applicable':
                raise ValueError('MATERIAL_EVIDENCE: the adopted source condition requires verification')
        elif row['status'] == 'pass' and not any(
                span['id'] == draft.id and len(''.join(span['quote'].split())) >= 8 for span in spans):
            raise ValueError('MATERIAL_EVIDENCE: source obligation pass requires a meaningful current passage')


def review_result(run: Run, contract: dict | None, draft: Draft, comparison: Draft | None) -> dict:
    from nw.task_models import _object

    raw = json.loads(run.output_text, object_pairs_hook=_object)
    canonical(raw).encode('utf-8')
    fields = {'recommendation', 'notes', 'core_changes'}
    if contract:
        fields.add('material_checks')
    if (not isinstance(raw, dict) or set(raw) != fields or raw['recommendation'] not in ('pass', 'revise')
            or not isinstance(raw['notes'], str) or not isinstance(raw['core_changes'], list)
            or not all(_text(line) for line in raw['core_changes'])):
        message = 'review requires recommendation, notes and core changes'
        raise ValueError(f'MATERIAL_EVIDENCE: {message} and all required checks' if contract else message)
    if contract:
        checks = validate_review(raw['material_checks'], contract, draft, comparison)
        if any(check['status'] != 'pass' or check.get('layer_check', {}).get('status', 'pass') != 'pass' or any(
                result['status'] in ('failed','unverified') for result in check.get('source_checks', []))
               for check in checks):
            raw['recommendation'] = 'revise'
    return raw


def _state_evidence(design: dict, delta: StateDelta, checks: list[dict]) -> None:
    bindings = {r['id']: r['binding'] for r in scene_checks(design)}
    for check in checks:
        for expected in bindings[check['id']].get('state', []):
            if not any(op['claim'] == 'fact' and all(canonical(op[key]) == canonical(value)
                       for key, value in expected.items()) and any(
                           span['id'] == delta.draft_id and span['start'] <= evidence['start']
                           and evidence['end'] <= span['end']
                           for span in check['evidence'] for evidence in op['evidence'])
                       for op in delta.operations):
                raise ValueError(f"MATERIAL_STATE_EVIDENCE: {check['id']} lacks a reviewed transition for "
                                 f"{expected['holder']} / {expected['predicate']}")


def check_material_acceptance(store: Store, draft: Draft, delta: StateDelta) -> list[dict]:
    design = scene_materials(store, draft.scene_id)
    verify_materials(store.directory.parent, design.get('materials', ()))
    checks = scene_checks(design)
    if not checks:
        return []
    manifest, package = read_input_manifest(store, delta.manifest_id)
    run_id = package.get('material_review_run')
    if not _text(run_id):
        raise ValueError('MATERIAL_EVIDENCE: this draft needs an independent material review')
    run = store.get('run', run_id)
    snapshot = json.loads(run.input_snapshot_json)
    if not _text(snapshot.get('manifest_id')):
        raise ValueError('MATERIAL_EVIDENCE: review has no frozen input')
    reviewed, context = read_input_manifest(store, snapshot['manifest_id'])
    contract, comparison = review_contract(store, draft, manifest)
    messages = snapshot['messages']
    expected = {'context': context, 'draft': asdict(draft), 'material_review': contract}
    expected_items = {f"material:{row['id']}": canonical(row) for row in writer_checks(design)}
    recorded_items = {row['source']: row['text'] for row in context['items']
                      if row['source'].startswith('material:')}
    written = store.get('run', draft.run_id)
    write_snapshot = json.loads(written.input_snapshot_json)
    if not _text(write_snapshot.get('manifest_id')):
        raise ValueError('MATERIAL_EVIDENCE: draft has no frozen writing input')
    write_manifest, write_context = read_input_manifest(store, write_snapshot['manifest_id'])
    fields = ('branch_id', 'state_revision', 'story_order', 'disclosure_order', 'candidate_delta_refs', 'novel_job_id')
    if (run.kind != 'review' or reviewed['purpose'] != 'review' or run.finish_reason != 'complete'
            or not run.ended_at or run.id == draft.run_id or asdict(draft_ref(draft)) not in reviewed['dependency_refs']
            or run.scene_id != draft.scene_id or not manifest.get('novel_job_id')
            or any(reviewed[key] != manifest[key] or write_manifest[key] != manifest[key] for key in fields)
            or any(item.get('material_design_sha256') != content_sha256(design)
                   for item in (reviewed, write_manifest, manifest))
            or messages[-1]['content'] != canonical(expected) or PROMPT not in messages[0]['content']
            or json.loads(run.context_package_json) != context or context != write_context
            or draft.text != written.output_text or recorded_items != expected_items):
        raise ValueError('MATERIAL_EVIDENCE: review did not use the exact draft, inputs and branch')
    result = review_result(run, contract, draft, comparison)
    if result['recommendation'] != 'pass':
        raise ValueError('MATERIAL_EVIDENCE: all required checks must pass on the accepted draft')
    if package.get('material_hypotheses', []) != state_hypotheses(design, result['material_checks'], draft.id):
        raise ValueError('MATERIAL_STATE_EVIDENCE: extraction did not freeze the approved hypotheses and review spans')
    _state_evidence(design, delta, result['material_checks'])
    bindings = {r['id']: r['binding'] for r in scene_checks(design)}
    return [{**check, 'verification': ('state_verified' if bindings[check['id']].get('state')
                                       else 'prose_verified')} for check in result['material_checks']]

