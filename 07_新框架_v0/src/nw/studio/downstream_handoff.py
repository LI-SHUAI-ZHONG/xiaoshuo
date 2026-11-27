"""Real workflow receivability audit from corpus decomposition into downstream stages.

Evaluates approved/draft corpus structures, derived production methods, cast
distribution samples, length statistics, and passage techniques through the
EXACT workflow rules used by novel design and writing (`MethodReader`,
`binding`, `enabled_outputs`, `incompatible_method`, `world_source`,
`automatic_requirements`, `genre_cast_samples`, `passage_sources`), and reports
originality / single-source concentration advisories aligned to the original
workflow's TYPE_F / H0D work-case rules.
"""
from __future__ import annotations

from collections import defaultdict
import json
from typing import Any

from nw.materials.phase_routes import ORDER, phase_order
from nw.materials.planning_hierarchy import incompatible_method
from nw.materials.story_policies import current as current_story_policies
from nw.production_methods.inputs import binding
from nw.production_methods.matching import type_match
from nw.production_methods.passage_sources import recommendations as passage_recommendations
from nw.production_methods.sources import MethodReader, enabled_outputs, stage_tasks
from nw.studio.cast_samples import design_reference, genre_cast_samples
from nw.studio.catalog import SLOT_LABELS, canonical_types, type_map
from nw.studio.corpus_catalog import DOMAINS
from nw.studio.corpus_story_observations import STORY_TASKS
from nw.studio.method_catalog import INPUTS, OUTPUT_LABELS, SCOPES, STAGES, TASKS
from nw.studio.method_recommendations import (
    AUTO_BASE_TASKS,
    AUTO_SLOT_TASKS,
    SLOT_OBSERVATIONS,
    _anticipated_inputs,
    _launch_candidates,
    _schedule,
    same_reference_type,
)
from nw.studio.step_material_blueprint import build_step_blueprint
from nw.studio.world_materials import classify_world_method, world_profile_for_types
from nw.studio.character_materials import character_profile_for_types, classify_character_method
from nw.studio.plot_materials import classify_plot_event_method, plot_profile_for_types
from nw.studio.execution_materials import classify_execution_method, execution_profile_for_types
from nw.studio.craft_materials import classify_craft_method, craft_profile_for_types


_SLOT_DOMAINS: dict[str, tuple[str, ...]] = {
    'world': ('world_rules',),
    'character': ('character_arc', 'cast_entry', 'cast_roster'),
    'structure': ('main_plot', 'subplot', 'chapter_progress'),
    'hook': ('hook', 'foreshadow', 'information'),
    'tone': ('pacing',),
    'style': ('narration', 'pacing'),
    'narration': ('narration',),
}


def _all_methods(library: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        listed = library.list_methods(limit=100, offset=offset)
        batch = listed.get('methods', ())
        rows.extend(batch)
        total = int(listed.get('total', len(rows)))
        if not batch or len(rows) >= total:
            break
        offset += len(batch)
    return rows


def _book_types_map(library: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with library.connect() as conn:
        for row in conn.execute('SELECT id, title, status, confirmed_types_json FROM staging_books'):
            result[row['id']] = {
                'id': row['id'],
                'title': row['title'],
                'status': row['status'],
                'confirmed_types': json.loads(row['confirmed_types_json'] or '[]'),
            }
    return result


def _method_receivability(
    row: dict[str, Any],
    reader: MethodReader,
    books_meta: dict[str, dict[str, Any]],
    *,
    types: list[str],
    planning_hierarchy: bool,
    policies: dict[str, Any],
    active_tasks: set[str] | None,
    passage_method_ids: set[str],
) -> dict[str, Any]:
    body = row.get('body') or {}
    origin = row.get('structure_origin')
    book_id = origin.get('book_id') if isinstance(origin, dict) else None
    book_info = books_meta.get(book_id, {}) if book_id else {}
    output_stages = sorted({o['stage'] for o in body.get('outputs', ()) if o.get('stage') in ORDER}, key=ORDER.index)
    downstream_exec = sorted({
        d['consumer'] for d in body.get('downstream', ()) if d.get('consumer') in ('writer', 'review', 'acceptance')
    })
    match = type_match(types, body.get('type_tags', ())) if types else None
    scopes = ('book', 'volume', 'chapter') if planning_hierarchy else ('book', 'chapter')

    global_blockers: list[str] = []
    if not row.get('current_for_production'):
        rt = row.get('runtime_integration', '')
        if row.get('status') != 'approved':
            global_blockers.append('方法尚未审核批准（仍为草稿或已退回），不会进入下游制作步骤')
        elif rt == 'requires_approved_structure':
            global_blockers.append('未绑定已批准的 v5 参考作品结构，仅在资料库可读、不能进入制作选材')
        elif rt == 'requires_current_structure':
            global_blockers.append('绑定的参考作品结构不是当前最新已批准 v5 版本，须重新绑定或修订')
        else:
            global_blockers.append('当前版本不是可供制作选用的有效批准版本')
    if types and match is None:
        global_blockers.append('方法适用类型与所查小说类型不匹配')

    placements: list[dict[str, Any]] = []
    stage_blockers: list[str] = []
    if not global_blockers:
        for scope in scopes:
            scope_policy = {**policies, 'scope': scope, 'planning_hierarchy': planning_hierarchy}
            for stage in phase_order(scope, planning_hierarchy=planning_hierarchy):
                matched_tasks = stage_tasks(body, stage, scope)
                if not matched_tasks:
                    continue
                reasons: list[str] = []
                if incompatible_method(body, stage, scope_policy):
                    reasons.append(f'{SCOPES[scope]}·{STAGES[stage]} 要求建立超出当前规划层级职责的卡片')
                if not enabled_outputs(body, stage, scope_policy):
                    if any(o['stage'] == stage and o['field'] == 'continuations' for o in body.get('outputs', ())):
                        reasons.append(f'{SCOPES[scope]}·{STAGES[stage]} 仅在存在前章已核验遗留事项时启用（第 1 章自动跳过）')
                    else:
                        reasons.append(f'{SCOPES[scope]}·{STAGES[stage]} 需要启用对应分步产物规则')
                if 'world_rules' in matched_tasks and stage == 'world_design':
                    check_types = types or list(body.get('type_tags', ()))
                    if check_types:
                        if match and match['level'] == 'cross_type':
                            reasons.append('全书世界规则方法不接受跨类型匹配，须与本书同类型')
                        elif reader.db_path.is_file() and reader.world_source(row, check_types) is None:
                            reasons.append('世界规则方法缺少同类型参考书的世界规则线索与受影响事件证据')
                available_inputs = _anticipated_inputs(scope, stage, planning_hierarchy=planning_hierarchy)
                missing = binding({'body': body}, stage, available_inputs)['missing']
                if missing:
                    labels = '、'.join(dict.fromkeys(INPUTS.get(item['input_kind'], item['input_kind']) for item in missing))
                    reasons.append(f'{SCOPES[scope]}·{STAGES[stage]} 缺少该步可达前置：{labels}')

                policy_active = active_tasks is None or bool(matched_tasks & active_tasks)
                if reasons:
                    stage_blockers.extend(reasons)
                placements.append({
                    'scope': scope,
                    'scope_name': SCOPES[scope],
                    'stage': stage,
                    'stage_name': STAGES[stage],
                    'tasks': sorted(matched_tasks),
                    'task_names': [TASKS[t]['name'] for t in sorted(matched_tasks) if t in TASKS],
                    'fields': sorted({o['field'] for o in body.get('outputs', ()) if o['stage'] == stage}),
                    'field_labels': [
                        OUTPUT_LABELS.get(f, f)
                        for f in sorted({o['field'] for o in body.get('outputs', ()) if o['stage'] == stage})
                    ],
                    'receivable': not reasons,
                    'policy_active': policy_active,
                    'block_reasons': reasons,
                })
        if not placements:
            stage_blockers.append('方法声明的制作层级（scopes）与预期产物步骤（outputs.stage）或任务不重叠，下游无步骤可接收')

    receivable_placements = [p for p in placements if p['receivable']]
    active_receivable = [p for p in receivable_placements if p['policy_active']]
    if global_blockers:
        status = 'draft' if row.get('status') == 'draft' else 'blocked'
    elif receivable_placements:
        status = 'receivable' if active_receivable else 'inactive_by_policy'
    else:
        status = 'blocked'

    all_reasons = [*global_blockers, *(r for r in stage_blockers if r not in global_blockers)]
    if status == 'inactive_by_policy':
        needed_task_names = '、'.join(TASKS[t]['name'] for t in body.get('tasks', ()) if t in TASKS)
        all_reasons.append(f'当前项目制作配置尚未勾选对应职责（{needed_task_names}），可在制作方法配置中开启或立项时选为偏好')

    return {
        'id': row['id'],
        'version': row['version'],
        'approved_version': row.get('approved_version'),
        'title': body.get('title') or '未命名方法',
        'status': status,
        'review_status': row.get('status'),
        'current_for_production': bool(row.get('current_for_production')),
        'tasks': list(body.get('tasks', ())),
        'task_names': [TASKS[t]['name'] for t in body.get('tasks', ()) if t in TASKS],
        'scopes': list(body.get('scopes', ())),
        'type_tags': list(body.get('type_tags', ())),
        'type_match': match,
        'book_id': book_id,
        'book_title': book_info.get('title', ''),
        'book_confirmed_types': book_info.get('confirmed_types', []),
        'output_stages': output_stages,
        'downstream_execution': downstream_exec,
        'placements': placements,
        'receivable_stages': sorted({p['stage'] for p in receivable_placements}, key=ORDER.index),
        'world_categories': classify_world_method(body),
        'character_categories': classify_character_method(body),
        'plot_categories': classify_plot_event_method(body),
        'execution_categories': classify_execution_method(body),
        'craft_categories': classify_craft_method(body),
        'block_reasons': all_reasons,
        'feeds_passage_references': row['id'] in passage_method_ids,
    }


def _auto_mode_readiness(
    reader: MethodReader,
    types: list[str],
    *,
    planning_hierarchy: bool,
) -> dict[str, Any]:
    if not types:
        return {'checked': False, 'ready': False, 'boards': [], 'missing_boards': []}
    sources: dict[str, list[str]] = {}
    matches: list[dict[str, Any]] = []
    if reader.db_path.is_file():
        from nw.production_methods.sources import matching_methods

        for row, match in matching_methods(reader, types):
            if match['level'] == 'cross_type':
                continue
            book_id = row['structure_origin']['book_id']
            if book_id not in sources:
                sources[book_id] = json.loads(reader._staging_row(book_id)['confirmed_types_json'])
            if same_reference_type(types, row['body']['type_tags'], sources[book_id]):
                matches.append(row)

    blocked: dict[str, dict[str, None]] = {}
    candidates = _launch_candidates(reader, types, matches, blocked, planning_hierarchy=planning_hierarchy)
    covered, assignments = _schedule(candidates, capacity=3)

    assigned_by_slot: dict[str, dict[str, Any]] = {}
    titles = {row['id']: row['body']['title'] for row in matches}
    for (scope, stage), slots, selected in assignments:
        offers = candidates[(scope, stage)]
        for slot in slots:
            matched_ids = [
                {'id': ident, 'version': version, 'title': titles.get(ident, ident)}
                for ident, version in selected
                if slot in offers.get((ident, version), frozenset())
            ]
            assigned_by_slot[slot] = {
                'scope': scope,
                'scope_name': SCOPES[scope],
                'stage': stage,
                'stage_name': STAGES[stage],
                'methods': matched_ids,
            }

    boards: list[dict[str, Any]] = []
    missing_boards: list[str] = []
    for slot in AUTO_SLOT_TASKS:
        ready = slot in covered and slot in assigned_by_slot
        if not ready:
            missing_boards.append(slot)
        boards.append({
            'slot': slot,
            'label': SLOT_LABELS.get(slot, slot),
            'ready': ready,
            'route': assigned_by_slot.get(slot),
            'blocked_reasons': list(blocked.get(slot, ()))[:4],
            'suggested_domains': [
                {'id': d, 'name': DOMAINS[d]} for d in _SLOT_DOMAINS.get(slot, ()) if d in DOMAINS
            ],
            'required_tasks': [
                {'id': t, 'name': TASKS[t]['name']}
                for t in sorted(AUTO_BASE_TASKS.get(slot, set()))
                if t in TASKS
            ],
        })
    return {
        'checked': True,
        'ready': not missing_boards,
        'ready_count': len(boards) - len(missing_boards),
        'total_boards': len(boards),
        'missing_boards': missing_boards,
        'boards': boards,
    }


def _originality_advisory(audited_methods: list[dict[str, Any]]) -> dict[str, Any]:
    """Check TYPE_F / H0D single-source convergence risk across receivable methods."""
    receivable = [m for m in audited_methods if m['status'] in ('receivable', 'inactive_by_policy') and m['book_id']]
    by_book: dict[str, dict[str, Any]] = {}
    for row in receivable:
        bid = row['book_id']
        entry = by_book.setdefault(bid, {
            'book_id': bid,
            'book_title': row['book_title'] or bid,
            'method_count': 0,
            'stages': set(),
        })
        entry['method_count'] += 1
        entry['stages'].update(row['receivable_stages'])
    sources = [
        {
            'book_id': item['book_id'],
            'book_title': item['book_title'],
            'method_count': item['method_count'],
            'stages': sorted(item['stages'], key=ORDER.index),
        }
        for item in sorted(by_book.values(), key=lambda x: (-x['method_count'], x['book_id']))
    ]
    warnings: list[dict[str, Any]] = []
    if len(receivable) >= 3 and len(sources) == 1:
        only = sources[0]
        warnings.append({
            'code': 'TYPE_F_SINGLE_SOURCE_CONCENTRATION',
            'severity': 'warning',
            'rule_ref': 'TYPE_F 案例重复惩罚规则 / H0D OR-01..OR-05',
            'message': (
                f"当前可接收的 {len(receivable)} 条拆解方法全部来自单一参考作品《{only['book_title']}》，"
                f"覆盖 {len(only['stages'])} 个制作步骤。按原工作流类型适配原创性规则，建议补充拆解第 2 本同类型作品以分散结构来源，避免多步骤组合贴近单本原作结构。"
            ),
        })
    return {
        'distinct_source_books': len(sources),
        'receivable_method_count': len(receivable),
        'sources': sources,
        'warnings': warnings,
    }


def audit_downstream_handoff(
    library: Any,
    *,
    types: list[str] | tuple[str, ...] = (),
    book_id: str = '',
    planning_hierarchy: bool = True,
    active_tasks: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Audit how decomposition assets connect to every downstream workflow step."""
    normalized_types = canonical_types(list(types)) if types else []
    book_id = str(book_id or '').strip()
    books_meta = _book_types_map(library)
    book_record: dict[str, Any] | None = None
    if book_id:
        if book_id not in books_meta:
            raise FileNotFoundError('参考作品不存在')
        book_record = books_meta[book_id]
        if not normalized_types and book_record['confirmed_types']:
            normalized_types = canonical_types(book_record['confirmed_types'])

    reader = MethodReader(library.workspace)
    policies = current_story_policies() if (library.workspace / 'materials/catalog.db').is_file() else {}
    task_filter = set(active_tasks) if active_tasks is not None else None

    passage_refs = passage_recommendations(library, normalized_types) if normalized_types else []
    if book_id:
        book_passage_refs = [r for r in passage_refs if r['book_id'] == book_id]
    else:
        book_passage_refs = passage_refs
    passage_method_ids = {r['method_id'] for r in passage_refs}

    raw_methods = _all_methods(library)
    if book_id:
        scoped_methods = [
            row for row in raw_methods
            if (row.get('structure_origin') or {}).get('book_id') == book_id
            or any(ev.get('book_id') == book_id for ev in (row.get('body') or {}).get('evidence', ()))
        ]
    else:
        scoped_methods = raw_methods

    audited_methods = [
        _method_receivability(
            row,
            reader,
            books_meta,
            types=normalized_types,
            planning_hierarchy=planning_hierarchy,
            policies=policies,
            active_tasks=task_filter,
            passage_method_ids=passage_method_ids,
        )
        for row in scoped_methods
    ]
    if normalized_types and not book_id:
        audited_methods = [
            m for m in audited_methods
            if m['type_match'] is not None or not m['type_tags'] or m['status'] == 'draft'
        ]

    # Extra non-method decomposition assets consumed by downstream stages
    cast_raw = genre_cast_samples(library, normalized_types) if normalized_types else None
    cast_ref = design_reference(cast_raw) if cast_raw else None
    book_cast_status = None
    if book_id and cast_raw:
        book_cast_status = next((s for s in cast_raw.get('sources', ()) if s['book_id'] == book_id), None)

    length_rec = library.recommend_length(normalized_types) if normalized_types else None

    # Build 17-step downstream receiving matrix grounded in step_material_blueprint
    blueprint = build_step_blueprint(library)
    by_stage_receivable: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_stage_inactive: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_stage_blocked: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_stage_draft: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for m in audited_methods:
        target_steps = list(dict.fromkeys([*m['output_stages'], *m['downstream_execution']]))
        if m['status'] == 'draft':
            for st in target_steps:
                by_stage_draft[st].append({'id': m['id'], 'version': m['version'], 'title': m['title']})
            continue
        if m['status'] == 'blocked':
            for st in target_steps:
                by_stage_blocked[st].append({
                    'id': m['id'], 'version': m['version'], 'title': m['title'],
                    'reasons': m['block_reasons'][:3],
                })
            continue
        # receivable or inactive_by_policy
        placed_stages = set()
        for pl in m['placements']:
            st = pl['stage']
            placed_stages.add(st)
            entry = {
                'id': m['id'], 'version': m['version'], 'title': m['title'],
                'scope': pl['scope'], 'scope_name': pl['scope_name'],
                'fields': pl['fields'], 'field_labels': pl['field_labels'],
                'task_names': pl['task_names'], 'book_title': m['book_title'],
            }
            if not pl['receivable']:
                by_stage_blocked[st].append({**entry, 'reasons': pl['block_reasons'][:3]})
            elif pl['policy_active']:
                by_stage_receivable[st].append(entry)
            else:
                by_stage_inactive[st].append({**entry, 'reasons': m['block_reasons'][-1:]})
        for exec_step in m['downstream_execution']:
            if exec_step not in placed_stages:
                entry = {
                    'id': m['id'], 'version': m['version'], 'title': m['title'],
                    'scope': '/'.join(m['scopes']), 'scope_name': '/'.join(SCOPES.get(s, s) for s in m['scopes']),
                    'fields': [], 'field_labels': [], 'task_names': m['task_names'], 'book_title': m['book_title'],
                }
                if m['status'] == 'receivable':
                    by_stage_receivable[exec_step].append(entry)
                else:
                    by_stage_inactive[exec_step].append(entry)

    steps_audit: list[dict[str, Any]] = []
    for step in blueprint['steps']:
        sid = step['step_id']
        rec_rows = by_stage_receivable[sid]
        inact_rows = by_stage_inactive[sid]
        blk_rows = by_stage_blocked[sid]
        drf_rows = by_stage_draft[sid]
        extra_assets: list[str] = []
        if sid in ('world_design', 'character_design', 'plot_design', 'scene_design') and cast_ref:
            br = cast_ref.get('book_range')
            extra_assets.append(
                f"同类型人物分布样本已就绪（{cast_ref.get('complete_count', 0)} 本完整样本"
                + (f"，全书人数 {br['min']}–{br['max']}" if br else '')
                + '）'
            )
        if sid == 'plot_design' and length_rec and length_rec.get('recommended_tier'):
            extra_assets.append(
                f"同类型篇幅统计样本已就绪（{length_rec.get('sample_count', 0)} 本，建议档位 {length_rec['recommended_tier']}）"
            )
        if sid in ('scene_design', 'expression_design') and book_passage_refs:
            kinds = sorted({r['kind'] for r in book_passage_refs})
            extra_assets.append(f"段落技法候选已就绪（{len(book_passage_refs)} 条，覆盖 {'/'.join(kinds)}）")

        if rec_rows:
            step_status = 'ready'
        elif inact_rows:
            step_status = 'inactive_by_policy'
        elif extra_assets:
            step_status = 'asset_only'
        elif blk_rows:
            step_status = 'blocked'
        elif drf_rows:
            step_status = 'draft_only'
        else:
            step_status = 'gap'

        steps_audit.append({
            'order': step['order'],
            'step_id': sid,
            'name': step['name'],
            'short_name': step['short_name'],
            'phase_group': step['phase_group'],
            'status': step_status,
            'receivable_count': len({r['id'] for r in rec_rows}),
            'inactive_count': len({r['id'] for r in inact_rows}),
            'blocked_count': len({r['id'] for r in blk_rows}),
            'draft_count': len({r['id'] for r in drf_rows}),
            'receivable_methods': rec_rows,
            'inactive_methods': inact_rows,
            'blocked_methods': blk_rows,
            'draft_methods': drf_rows,
            'extra_assets': extra_assets,
            'corpus_domains': step['corpus_domains'],
        })

    type_lookup = type_map()
    world_profile = world_profile_for_types(normalized_types)
    world_cat_counts: dict[str, int] = {c['id']: 0 for c in world_profile['categories']}
    character_profile = character_profile_for_types(normalized_types)
    char_cat_counts: dict[str, int] = {c['id']: 0 for c in character_profile['categories']}
    plot_profile = plot_profile_for_types(normalized_types)
    plot_cat_counts: dict[str, int] = {c['id']: 0 for c in plot_profile['categories']}
    execution_profile = execution_profile_for_types(normalized_types)
    exec_cat_counts: dict[str, int] = {c['id']: 0 for c in execution_profile['categories']}
    craft_profile = craft_profile_for_types(normalized_types)
    craft_cat_counts: dict[str, int] = {c['id']: 0 for c in craft_profile['categories']}
    for m in audited_methods:
        if m['status'] in ('receivable', 'inactive_by_policy'):
            for cid in m.get('world_categories', ()):
                if cid in world_cat_counts:
                    world_cat_counts[cid] += 1
            for cid in m.get('character_categories', ()):
                if cid in char_cat_counts:
                    char_cat_counts[cid] += 1
            for cid in m.get('plot_categories', ()):
                if cid in plot_cat_counts:
                    plot_cat_counts[cid] += 1
            for cid in m.get('execution_categories', ()):
                if cid in exec_cat_counts:
                    exec_cat_counts[cid] += 1
            for cid in m.get('craft_categories', ()):
                if cid in craft_cat_counts:
                    craft_cat_counts[cid] += 1
    for cat in world_profile['categories']:
        cat['receivable_count'] = world_cat_counts.get(cat['id'], 0)
    for cat in character_profile['categories']:
        cat['receivable_count'] = char_cat_counts.get(cat['id'], 0)
    character_profile['character_categories'] = [c for c in character_profile['categories'] if c['target_stage'] == 'character_design']
    character_profile['relation_categories'] = [c for c in character_profile['categories'] if c['target_stage'] == 'static_relations']
    for cat in plot_profile['categories']:
        cat['receivable_count'] = plot_cat_counts.get(cat['id'], 0)
    plot_profile['structure_categories'] = [c for c in plot_profile['categories'] if c['slot'] == 'structure']
    plot_profile['hook_categories'] = [c for c in plot_profile['categories'] if c['slot'] == 'hook']
    plot_profile['plot_categories'] = [c for c in plot_profile['categories'] if c['target_stage'] == 'plot_design']
    plot_profile['event_categories'] = [c for c in plot_profile['categories'] if c['target_stage'] == 'event_design']
    for cat in execution_profile['categories']:
        cat['receivable_count'] = exec_cat_counts.get(cat['id'], 0)
    execution_profile['action_categories'] = [c for c in execution_profile['categories'] if c['target_stage'] == 'action_design']
    execution_profile['scene_categories'] = [c for c in execution_profile['categories'] if c['target_stage'] == 'scene_design']
    execution_profile['transition_categories'] = [c for c in execution_profile['categories'] if c['target_stage'] == 'state_transition']
    execution_profile['propagation_categories'] = [c for c in execution_profile['categories'] if c['target_stage'] == 'state_propagation']
    for cat in craft_profile['categories']:
        cat['receivable_count'] = craft_cat_counts.get(cat['id'], 0)
    craft_profile['narration_categories'] = [c for c in craft_profile['categories'] if c['slot'] == 'narration']
    craft_profile['anchor_categories'] = [c for c in craft_profile['categories'] if c['target_stage'] == 'anchor_design']
    craft_profile['expression_categories'] = [c for c in craft_profile['categories'] if c['target_stage'] == 'expression_design']
    craft_profile['bind_scope_categories'] = [c for c in craft_profile['categories'] if c['target_stage'] == 'bind_scope']
    craft_profile['writer_categories'] = [c for c in craft_profile['categories'] if c['target_stage'] == 'writer']
    craft_profile['review_categories'] = [c for c in craft_profile['categories'] if c['target_stage'] == 'review']
    craft_profile['acceptance_categories'] = [c for c in craft_profile['categories'] if c['target_stage'] == 'acceptance']
    return {
        'types': [{'id': tid, 'name': type_lookup[tid]['name']} for tid in normalized_types if tid in type_lookup],
        'type_ids': normalized_types,
        'book': book_record,
        'planning_hierarchy': planning_hierarchy,
        'world_profile': world_profile,
        'character_profile': character_profile,
        'plot_profile': plot_profile,
        'execution_profile': execution_profile,
        'craft_profile': craft_profile,
        'summary': {
            'total_methods': len(audited_methods),
            'receivable_methods': sum(1 for m in audited_methods if m['status'] == 'receivable'),
            'inactive_methods': sum(1 for m in audited_methods if m['status'] == 'inactive_by_policy'),
            'blocked_methods': sum(1 for m in audited_methods if m['status'] == 'blocked'),
            'draft_methods': sum(1 for m in audited_methods if m['status'] == 'draft'),
            'ready_steps': sum(1 for s in steps_audit if s['status'] == 'ready'),
            'total_steps': len(steps_audit),
            'book_world_ready': any(
                any(p['scope'] == 'book' and p['stage'] == 'world_design' and p['receivable'] for p in m['placements'])
                for m in audited_methods
            ),
            'cast_sample_ready': bool(cast_ref),
            'passage_reference_count': len(book_passage_refs),
        },
        'auto_readiness': _auto_mode_readiness(reader, normalized_types, planning_hierarchy=planning_hierarchy),
        'originality_audit': _originality_advisory(audited_methods),
        'cast_samples': {
            'ready': bool(cast_ref),
            'complete_count': cast_raw.get('complete_count', 0) if cast_raw else 0,
            'book_range': cast_raw.get('book_range') if cast_raw else None,
            'book_status': book_cast_status,
        },
        'length_recommendation': {
            'ready': bool(length_rec and length_rec.get('recommended_tier')),
            'recommended_tier': length_rec.get('recommended_tier') if length_rec else None,
            'sample_count': length_rec.get('sample_count', 0) if length_rec else 0,
        },
        'passage_references': [
            {
                'ref': r['ref'], 'method_id': r['method_id'], 'version': r['version'],
                'book_id': r['book_id'], 'kind': r['kind'], 'scopes': r['scopes'],
                'condition': r['condition'], 'boundary': r['boundary'],
            }
            for r in book_passage_refs
        ],
        'methods': audited_methods,
        'steps': steps_audit,
    }
