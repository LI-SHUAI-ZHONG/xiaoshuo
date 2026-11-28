"""Post-17 continuation hub: chapter summaries, periodic reviews, promise tracking, and finish preflight."""
from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any

from nw.cards import read_card
from nw.chapter_break import require_break_review
from nw.chapter_records import chapter_index, chapter_review, chapter_summary
from nw.chapter_state import _chapter_state
from nw.materials.promise_continuity import approved_promise_snapshot, continuation_reminder
from nw.novel_store import show_job
from nw.story_delta import read_delta
from nw.story_models import CardRef, StateHead
from nw.story_state import (
    approved_scene_positions,
    baseline_for,
    current_head,
    replay,
    revision_state,
    selected_operations,
)
from nw.studio.production_design import next_design
from nw.studio.production_length import manuscript_length, verify_finish_length

CHAPTER_REVIEW_CATALOG: tuple[dict[str, Any], ...] = (
    {
        'kind': 'resource-update',
        'title': '章末资源更新',
        'interval': 1,
        'source': '125.25_资源库记录频率',
        'instructions': '章末用本章已接受的行动和状态变更更新实际资源记录。',
    },
    {
        'kind': 'character',
        'title': '三章人物核心属性复盘',
        'interval': 3,
        'source': '102.3_检查点',
        'instructions': '对照最早已批准的人物设计、写作所用版本和三章实际行为，核对弧光铺垫与引发变化的事件。',
    },
    {
        'kind': 'cost',
        'title': '三章累积代价盘点',
        'interval': 3,
        'source': '118.1 / 118.8_代价复盘',
        'instructions': '核对肉体、精神、关系、资源、时间五类新增代价、旧代价转化/解除、阈值与遗忘风险。',
    },
    {
        'kind': 'commitment',
        'title': '三章创作承诺一致性复盘',
        'interval': 3,
        'source': '板块132_创作意图与承诺',
        'instructions': '按已采用的方向与承诺核对每三章的一致性，检查类型、情感与主题承诺是否延续或偏离。',
    },
    {
        'kind': 'resource-inventory',
        'title': '三章资源出入盘点',
        'interval': 3,
        'source': '125.25_资源库记录频率',
        'instructions': '核对最近三个完整章稿里的真实资源出入和状态一致性。',
    },
    {
        'kind': 'resource-settlement',
        'title': '十章资源流转大清算',
        'interval': 10,
        'source': '125.25_资源库记录频率',
        'instructions': '用本期十章和此前已接受的记录核对资源流动与去向，记录仍未闭合的项目。',
    },
    {
        'kind': 'commitment-ending',
        'title': '终章开篇承诺兑现核验',
        'interval': None,
        'source': '板块132_创作意图与承诺',
        'instructions': '作者确认终章后，对照开篇承诺与终章已接受稿件核验最终兑现证据。',
    },
)
CHAPTER_REVIEW_BY_KIND: dict[str, dict[str, Any]] = {row['kind']: row for row in CHAPTER_REVIEW_CATALOG}


def resolve_scene_card_body(store: Any, raw_card: dict[str, Any] | None) -> dict[str, Any]:
    """Merge versioned scene_ref card body when present, preserving raw_card for legacy scenes."""
    card_body = dict(raw_card or {})
    story_meta = card_body.get('story') if isinstance(card_body.get('story'), dict) else {}
    scene_ref = story_meta.get('scene_ref') if isinstance(story_meta.get('scene_ref'), dict) else None
    if scene_ref and scene_ref.get('card_id') and scene_ref.get('version'):
        try:
            resolved = read_card(store, CardRef(str(scene_ref['card_id']), int(scene_ref['version'])))
            if isinstance(resolved, dict) and isinstance(resolved.get('body'), dict):
                return {**card_body, **resolved['body']}
        except Exception:
            pass
    return card_body


def scene_display_labels(store: Any) -> dict[str, str]:
    """Map scene_id -> human-readable '第X章·场Y 标题' directly from Store."""
    chapters = {c.id: c for c in store.list('chapter')}
    labels: dict[str, str] = {}
    for sc in store.list('scene'):
        ch = chapters.get(sc.chapter_id)
        ch_idx = ch.index if ch else 0
        try:
            raw = json.loads(sc.card_json) if sc.card_json else {}
        except ValueError:
            raw = {}
        body = resolve_scene_card_body(store, raw)
        title = str(body.get('title') or '').strip()
        suffix = f' {title}' if title else ''
        labels[sc.id] = f'第{ch_idx}章·场{sc.index}{suffix}'
    return labels


def _branch_promises(store: Any, head: StateHead, snapshot: dict[str, Any], current_chapter: int | None) -> dict[str, Any]:
    settings = snapshot.get('settings', [])
    cards = [read_card(store, CardRef(row['card_id'], row['version'])) for row in settings]
    ops = selected_operations(store, snapshot)
    facts = replay(baseline_for(store, head.branch_id), ops)
    snap_rows = approved_promise_snapshot(store, settings, cards, facts, ops)
    reminder = continuation_reminder({}, {
        'promise_continuity': snap_rows,
        'current_chapter': current_chapter,
    }) if snap_rows else None
    return {
        'items': snap_rows,
        'lifecycle_counts': reminder['lifecycle_counts'] if reminder else {'unverified': 0, 'planted': 0, 'hinted': 0, 'paid_off': 0},
        'due': reminder['due_this_scene'] if reminder else [],
        'overdue': reminder['overdue_warnings'] if reminder else [],
        'still_open': reminder['still_open'] if reminder else [],
        'resolved': reminder['resolved'] if reminder else [],
        'unverified': reminder['unverified'] if reminder else [],
        'rule': reminder['rule'] if reminder else '批准包含伏笔/承诺卡的剧情设计后，将在此持续追踪埋设、暗示与回收窗口。',
    }


def _chapter_rows(store: Any, head: StateHead, snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    approved = approved_scene_positions(store, snapshot)
    slots = snapshot.get('slots', {})
    scene_ids = set(approved) | set(slots)
    chapter_ids = {sc.chapter_id for sc in store.list('scene') if sc.id in scene_ids}
    chapters = sorted((ch for ch in store.list('chapter') if ch.id in chapter_ids), key=lambda ch: ch.index)
    if not chapters:
        return [], None
    max_index = chapters[-1].index
    rows: list[dict[str, Any]] = []
    for ch in chapters:
        st = _chapter_state(store, head, snapshot, ch, approved)
        summ = chapter_summary(store, head, ch.index)
        summary_rec = summ.get('record')
        reviews: list[dict[str, Any]] = []
        for meta in CHAPTER_REVIEW_CATALOG:
            kind = meta['kind']
            interval = meta['interval']
            if kind == 'commitment-ending':
                if ch.index != max_index:
                    continue
            elif interval and ch.index % interval != 0:
                continue
            try:
                rev = chapter_review(store, head, ch.index, kind)
            except ValueError:
                continue
            if rev.get('status') == 'not_due':
                continue
            rec = rev.get('record')
            reviews.append({
                'kind': kind,
                'title': meta['title'],
                'interval': interval,
                'source': meta['source'],
                'instructions': meta['instructions'],
                'status': rev['status'],
                'input_sha256': rev.get('input_sha256'),
                'finding': rec['author_record']['finding'] if rec else None,
                'record_id': rec['id'] if rec else None,
                'missing_chapters': rev.get('missing_chapters', []),
                'missing_delta_scene_ids': rev.get('missing_delta_scene_ids', []),
            })
        rows.append({
            'chapter_id': ch.id,
            'index': ch.index,
            'title': ch.title,
            'scope_complete': st['scope_complete'],
            'accepted_scenes_count': len(st['drafts']),
            'pending_scene_ids': st['pending_scene_ids'],
            'missing_delta_scene_ids': st['missing_delta_scene_ids'],
            'world_changes_count': len(st['changes']),
            'character_changes_count': len(st.get('character_changes', ())),
            'identity_disclosures_count': len(st.get('identity_disclosures', ())),
            'affected_characters': st['affected_characters'],
            'summary_status': summ['status'],
            'summary_input_sha256': summ.get('input_sha256'),
            'has_preview': bool((summ.get('inputs') or {}).get('preview')),
            'summary_text': summary_rec['author_record']['summary'] if summary_rec else None,
            'summary_comparison': summary_rec['author_record'].get('comparison') if summary_rec else None,
            'summary_record_id': summary_rec['id'] if summary_rec else None,
            'reviews': reviews,
        })
    return rows, max_index


def continuation_signal(app: Any, novel: dict[str, Any], project: dict[str, Any], store: Any,
                        job: dict[str, Any] | None, upcoming: dict[str, Any] | None) -> dict[str, Any]:
    """Lightweight post-17 routing signal attached to progress() for live Studio banners & toolbar."""
    branch = novel.get('current_branch', 'main')
    managed = store.managed_story()
    accepted_any = any(s.get('accepted_draft_id') for s in project.get('scenes', ()))
    unaccepted_approved = [
        s['id'] for s in project.get('scenes', ())
        if s.get('story_approved_on_branch') and not s.get('accepted_draft_id')
    ]
    from nw.novel_store import _manual_branch_draft
    manual_edits = [
        s['id'] for s in project.get('scenes', ())
        if s.get('story_approved_on_branch') and s.get('latest_draft_id')
        and s['latest_draft_id'] != s.get('accepted_draft_id')
        and _manual_branch_draft(store, store.get('draft', s['latest_draft_id']), branch)
    ]
    idle = not job or job['status'] in ('DONE', 'CANCELLED', 'REJECTED', 'STALE')
    needs_candidate_branch = bool(
        novel.get('status') != 'done'
        and managed
        and branch == 'main'
        and accepted_any
        and idle
        and not unaccepted_approved
        and not manual_edits
    )
    can_promote = False
    needs_revalidation: list[str] = []
    revalidation_details: list[dict[str, str]] = []
    changed_scenes: list[str] = []
    summary_pending_chapters: list[int] = []
    due_review_count = 0
    overdue_promises_count = 0
    latest_completed_chapter = None
    if managed:
        head = current_head(store, branch)
        snapshot = revision_state(store, head)
        labels = scene_display_labels(store)
        if branch != 'main':
            from nw.studio.production_branches import _promotion_preview
            preview = _promotion_preview(store, current_head(store, 'main'), head)
            can_promote = bool(preview['can_promote'])
            needs_revalidation = list(preview['needs_revalidation'])
            changed_scenes = list(preview['changed_scenes'])
            revalidation_details = [{'id': sid, 'label': labels.get(sid, sid)} for sid in needs_revalidation]
        ch_rows, max_idx = _chapter_rows(store, head, snapshot)
        completed = [r for r in ch_rows if r['scope_complete']]
        if completed:
            latest_completed_chapter = completed[-1]['index']
        summary_pending_chapters = [r['index'] for r in completed if r['summary_status'] == 'ready']
        due_review_count = sum(
            1 for r in ch_rows for rv in r['reviews']
            if rv['status'] == 'ready' and rv['kind'] != 'commitment-ending'
        )
        prom = _branch_promises(store, head, snapshot, max_idx)
        overdue_promises_count = len(prom['overdue'])
    return {
        'branch_id': branch,
        'is_candidate': branch != 'main',
        'needs_candidate_branch': needs_candidate_branch,
        'can_promote': can_promote,
        'needs_revalidation': needs_revalidation,
        'revalidation_details': revalidation_details,
        'changed_scenes_count': len(changed_scenes),
        'latest_completed_chapter': latest_completed_chapter,
        'summary_pending_chapters': summary_pending_chapters,
        'due_review_count': due_review_count,
        'overdue_promises_count': overdue_promises_count,
        'next_design': upcoming,
    }


def continuation_overview(app: Any, ident: str) -> dict[str, Any]:
    """Complete post-17 continuation, periodic review, promise continuity & knowledge matrix snapshot."""
    novel = app.db.get(ident)
    project = app.project(novel)
    branch = novel.get('current_branch', 'main')
    with app.open_store(novel) as store:
        if not store.managed_story():
            return {
                'novel_id': ident,
                'managed_story': False,
                'branch_id': branch,
                'chapters': [],
                'promises': {'items': [], 'lifecycle_counts': {}, 'due': [], 'overdue': [], 'still_open': [], 'resolved': [], 'unverified': [], 'rule': ''},
                'knowledge_matrix': {'managed_story': False, 'holders': [], 'matrix': []},
                'chapter_index_markdown': '',
                'branch_guidance': {'branch_id': branch, 'is_candidate': False, 'needs_candidate_branch': False},
                'review_catalog': list(CHAPTER_REVIEW_CATALOG),
            }
        head = current_head(store, branch)
        snapshot = revision_state(store, head)
        ch_rows, max_idx = _chapter_rows(store, head, snapshot)
        idx_report = chapter_index(store, head)
        promises = _branch_promises(store, head, snapshot, max_idx)
        job = asdict(show_job(store, novel['job_id'])) if novel.get('job_id') else None
        upcoming = None
        if novel['wizard'].get('planning_hierarchy') and novel['status'] != 'done':
            if not (branch == 'main' and any(s['accepted_draft_id'] for s in project['scenes'])):
                upcoming = next_design(store, branch)
        guidance = continuation_signal(app, novel, project, store, job, upcoming)
    matrix = app.studio.inspect_state_matrix(novel['project_dir'], branch=branch)
    return {
        'novel_id': ident,
        'managed_story': True,
        'branch_id': branch,
        'head': asdict(head),
        'chapters': ch_rows,
        'chapter_index': idx_report['chapters'],
        'chapter_index_markdown': idx_report['markdown'],
        'promises': promises,
        'knowledge_matrix': matrix,
        'branch_guidance': guidance,
        'review_catalog': list(CHAPTER_REVIEW_CATALOG),
    }


def save_chapter_summary_record(app: Any, ident: str, chapter_idx: int, body: dict[str, Any]) -> dict[str, Any]:
    """Record or update an author chapter summary tied to the branch's accepted chapter evidence."""
    summary_text = str(body.get('summary') or '').strip()
    if not summary_text:
        raise ValueError('章总结不能为空（最多 100 字）')
    if len(summary_text) > 100:
        raise ValueError('章总结不能超过 100 字，请精炼概括本章核心推进与遗留悬念')
    comparison = body.get('comparison')
    with app._lock:
        novel = app.db.get(ident)
        if novel['status'] == 'done':
            raise ValueError('已完稿作品不能修改章总结')
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        with app.open_store(novel) as store:
            if not store.managed_story():
                raise ValueError('旧项目尚未接入故事状态机，无法记录章总结')
            head = current_head(store, branch)
            current = chapter_summary(store, head, int(chapter_idx))
            if current.get('status') == 'drafts_pending':
                raise ValueError('CHAPTER_SCOPE_INCOMPLETE: 本章仍有未接受的场景，请先完成审稿与接受后再填写章总结')
            expected_sha = body.get('input_sha256') or current['input_sha256']
            payload: dict[str, Any] = {'input_sha256': expected_sha, 'summary': summary_text}
            if isinstance(comparison, str) and comparison.strip():
                payload['comparison'] = comparison.strip()
            saved = chapter_summary(store, head, int(chapter_idx), payload)
        app.db.event(
            ident,
            'continuation',
            f'记录第 {chapter_idx} 章章总结（{branch}）',
            {'chapter': int(chapter_idx), 'branch_id': branch, 'record_id': saved['record']['id'], 'summary': summary_text},
        )
        app._wake_repo()
        app.changed.set()
    return saved


def save_chapter_review_record(app: Any, ident: str, chapter_idx: int, kind: str, body: dict[str, Any]) -> dict[str, Any]:
    """Record a periodic or ending chapter checkpoint review (character/cost/commitment/resource)."""
    if kind not in CHAPTER_REVIEW_BY_KIND:
        raise ValueError(f'未知的阶段复盘类型：{kind}')
    finding = str(body.get('finding') or '').strip()
    if not finding:
        raise ValueError('请填写本次阶段复盘的核查结论与后续调整说明')
    with app._lock:
        novel = app.db.get(ident)
        if novel['status'] == 'done':
            raise ValueError('已完稿作品不能修改阶段复盘记录')
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        with app.open_store(novel) as store:
            if not store.managed_story():
                raise ValueError('旧项目尚未接入故事状态机，无法记录周期复盘')
            head = current_head(store, branch)
            current = chapter_review(store, head, int(chapter_idx), kind)
            status = current.get('status')
            if status == 'not_due':
                raise ValueError('CHAPTER_REVIEW_NOT_DUE: 该复盘规则在当前章号尚未到期')
            if status in ('drafts_pending', 'state_evidence_pending'):
                raise ValueError('CHAPTER_SCOPE_INCOMPLETE: 周期复盘要求覆盖窗口内所有章节完成审稿接受并具备状态证据')
            expected_sha = body.get('input_sha256') or current['input_sha256']
            saved = chapter_review(store, head, int(chapter_idx), kind, {
                'input_sha256': expected_sha,
                'finding': finding,
            })
        meta = CHAPTER_REVIEW_BY_KIND[kind]
        app.db.event(
            ident,
            'continuation',
            f"记录第 {chapter_idx} 章{meta['title']}（{branch}）",
            {'chapter': int(chapter_idx), 'kind': kind, 'branch_id': branch,
             'record_id': saved['record']['id'], 'finding': finding},
        )
        app._wake_repo()
        app.changed.set()
    return saved


def finish_readiness(app: Any, ident: str) -> dict[str, Any]:
    """Full read-only preflight mirroring every single invariant enforced by ProductionService.finish()."""
    novel = app.db.get(ident)
    project = app.project(novel)
    branch = novel.get('current_branch', 'main')
    checks: list[dict[str, Any]] = []
    advisories: list[dict[str, Any]] = []

    def add_check(cid: str, title: str, passed: bool, detail: str, *, action: str = '') -> None:
        checks.append({'id': cid, 'title': title, 'passed': bool(passed), 'detail': detail, 'action': action})

    # 1. Branch must be main
    add_check(
        'branch_main', '主线分支确认', branch == 'main',
        '当前位于正式主线（main）。' if branch == 'main' else f'当前位于候选分支「{branch}」，需先审查并合并回主线后再完稿。',
        action='' if branch == 'main' else 'branches',
    )

    # 2. No active worker or pending gates
    worker_alive = bool(app._workers.get(ident) and app._workers[ident].is_alive())
    pending_gates = app.gates(ident)['gates']
    add_check(
        'idle_and_no_gates', '任务与待确认门禁清零', not worker_alive and not pending_gates,
        '当前无运行中任务，所有确认节点已处理完毕。' if (not worker_alive and not pending_gates)
        else (f'仍有 {len(pending_gates)} 个待确认节点' if pending_gates else '仍有制作任务正在运行中。'),
        action='' if (not worker_alive and not pending_gates) else 'studio',
    )

    # 3. Managed story state machine
    managed = bool(project.get('managed_story'))
    add_check(
        'managed_story', '故事状态机已接管', managed,
        '项目已接入版本化故事状态与事实核验。' if managed else '旧项目需先完成故事状态接管（story adopt）后再完稿。',
    )

    active_scenes = [row for row in project['scenes'] if row.get('in_branch_manuscript')]
    with app.open_store(novel) as store:
        labels = scene_display_labels(store)
        # 4. All active scenes accepted
        unaccepted = [labels.get(row['id'], row['id']) for row in active_scenes if not row.get('accepted_draft_id')]
        add_check(
            'all_scenes_accepted', '全部在稿场景已接受', bool(active_scenes) and not unaccepted,
            f'共 {len(active_scenes)} 个在稿场景已全部接受入库。' if (active_scenes and not unaccepted)
            else ('尚无已规划并在稿的场景。' if not active_scenes else f'仍有 {len(unaccepted)} 场未接受：{"、".join(unaccepted[:5])}'),
            action='' if (active_scenes and not unaccepted) else 'studio',
        )

        # 5. No newer unaccepted drafts on active scenes
        stale_drafts = [
            labels.get(row['id'], row['id']) for row in active_scenes
            if row.get('accepted_draft_id') and row.get('latest_draft_id') != row.get('accepted_draft_id')
        ]
        add_check(
            'no_unaccepted_drafts', '无未接受的较新草稿', not stale_drafts,
            '所有已接受场景均为最新版本草稿。' if not stale_drafts
            else f'以下场景存在较新未接受草稿（含手动修改），请先送交独立审稿与接受：{"、".join(stale_drafts[:5])}',
            action='' if not stale_drafts else 'studio',
        )

        # 6. Every accepted draft has a matching passing independent review
        unreviewed: list[str] = []
        for scene in active_scenes:
            if not scene.get('accepted_draft_id'):
                continue
            review = app.review_for_draft(store, scene['id'], scene['accepted_draft_id'])
            if not review or review['result'].get('recommendation') != 'pass':
                unreviewed.append(labels.get(scene['id'], scene['id']))
        add_check(
            'passing_reviews', '已接受稿件独立审稿通过', bool(active_scenes) and not unaccepted and not unreviewed,
            '全部已接受稿件均具备对应版本的通过审稿记录。' if (active_scenes and not unaccepted and not unreviewed)
            else ('需先完成所有场景接受。' if (not active_scenes or unaccepted)
                  else f'以下场景缺少与当前已接受版本匹配的通过审稿：{"、".join(unreviewed[:5])}'),
            action='' if (active_scenes and not unaccepted and not unreviewed) else 'studio',
        )

        # 7. Planned chapter count
        length = manuscript_length(store, novel['wizard'])
        populated_chapters = {scene['chapter_id'] for scene in active_scenes if scene.get('accepted_draft_id')}
        expected_chapters = length.get('effective_chapter_count')
        chapters_ok = not (length.get('length_mode') != 'tiered' and expected_chapters and len(populated_chapters) < expected_chapters)
        add_check(
            'chapter_count', '计划章节数达标', chapters_ok,
            f'已完成 {len(populated_chapters)} 章' + (f'（计划 {expected_chapters} 章）。' if expected_chapters else '。')
            if chapters_ok else f'当前已接受 {len(populated_chapters)} 章，尚未达到立项设定的 {expected_chapters} 章。',
            action='' if chapters_ok else 'length',
        )

        # 8. Word count & per-chapter/scene length compliance
        length_err = ''
        try:
            verify_finish_length(length)
        except ValueError as exc:
            length_err = str(exc)
        add_check(
            'length_compliance', '全书及章场篇幅达标', not length_err,
            f'主稿已接受 {length["accepted_words"]} 字，满足当前篇幅规则。' if not length_err else length_err,
            action='' if not length_err else 'length',
        )

        # 9. Tiered chapter ending break reviews
        break_issues: list[str] = []
        active_by_id = {scene['id']: scene for scene in active_scenes}
        for chapter in length.get('chapters', ()):
            if not chapter.get('scenes'):
                continue
            ending = chapter['scenes'][-1]
            if ending.get('length_mode') == 'tiered':
                sc = active_by_id.get(ending['scene_id'])
                if not sc or not sc.get('accepted_delta_id'):
                    break_issues.append(f"第{chapter['index']}章末场尚未接受状态增量")
                    continue
                try:
                    delta = read_delta(store, sc['accepted_delta_id'])
                    require_break_review(store, store.get('draft', delta.draft_id), delta.manifest_id)
                except ValueError as exc:
                    break_issues.append(f"第{chapter['index']}章：{exc}")
        add_check(
            'chapter_breaks', '章末自然断章审稿核验', not break_issues,
            '章末收束核验通过（或当前未启用分级断章约束）。' if not break_issues else '；'.join(break_issues[:4]),
            action='' if not break_issues else 'studio',
        )

        # Advisory post-17 reminders (non-blocking, guides literary closure).
        if managed:
            head = current_head(store, branch)
            snapshot = revision_state(store, head)
            ch_rows, max_idx = _chapter_rows(store, head, snapshot)
            missing_summaries = [r['index'] for r in ch_rows if r['scope_complete'] and r['summary_status'] == 'ready']
            if missing_summaries:
                advisories.append({
                    'kind': 'chapter_summary',
                    'title': '章总结待补全',
                    'detail': f'第 {", ".join(str(i) for i in missing_summaries[:6])} 章尚未填写章总结（用于续章与全书归档索引）。',
                })
            ending_row = ch_rows[-1] if ch_rows else None
            if ending_row:
                ending_rev = next((rv for rv in ending_row['reviews'] if rv['kind'] == 'commitment-ending'), None)
                if ending_rev and ending_rev['status'] == 'ready':
                    advisories.append({
                        'kind': 'commitment-ending',
                        'title': '终章开篇承诺兑现复盘尚未留档',
                        'detail': f'建议在第 {ending_row["index"]} 章记录「终章开篇承诺兑现核验」，对照开篇承诺回查结局回应。',
                    })
            prom = _branch_promises(store, head, snapshot, max_idx)
            open_cnt = len(prom['still_open']) + len(prom['due']) + len(prom['unverified'])
            if open_cnt:
                advisories.append({
                    'kind': 'open_promises',
                    'title': f'仍有 {open_cnt} 项未回收伏笔/读者承诺',
                    'detail': '请在「连载与复盘」核对各伏笔回收状态或确认属于有意保留的开放结局。',
                })

    blockers = [c['detail'] for c in checks if not c['passed']]
    return {
        'novel_id': ident,
        'novel_status': novel['status'],
        'ready': len(blockers) == 0 and novel['status'] != 'done',
        'blockers': blockers,
        'checks': checks,
        'advisories': advisories,
        'summary': {
            'passed_count': sum(1 for c in checks if c['passed']),
            'total_checks': len(checks),
            'accepted_words': length['accepted_words'],
            'accepted_scenes': sum(1 for row in active_scenes if row.get('accepted_draft_id')),
            'total_active_scenes': len(active_scenes),
            'branch_id': branch,
        },
    }
