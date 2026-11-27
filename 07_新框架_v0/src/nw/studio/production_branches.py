"""Client branch controls backed by the existing acceptance and promotion guards."""
from __future__ import annotations

from dataclasses import asdict
import json
import re
from uuid import uuid4

from nw.acceptance import (_require_promotion_reviews, _snapshot_dependencies, _topological,
                           promote_branch as apply_promotion, promotion_impacts, record_story_decision)
from nw.materials.action_review import check_material_acceptance
from nw.novel_store import show_job
from nw.story_delta import read_delta
from nw.story_models import StateHead
from nw.story_state import (baseline_for, branch_row, current_head, fork_story,
                            replay, revision_state, selected_operations)


def latest_branch_draft_id(store: object, scene_id: str, branch: str, accepted_id: str | None) -> str | None:
    """Keep inherited accepted prose until a later draft belongs to this branch."""
    versions = store.connection.execute("""
        SELECT d.id, COALESCE(json_extract(m.payload_json, '$.branch_id'),
            CASE WHEN r.provider = 'author' AND json_extract(r.input_snapshot_json, '$.source') = 'studio_manual_author'
                 THEN json_extract(r.input_snapshot_json, '$.branch_id') END) AS branch_id
        FROM drafts d JOIN runs r ON r.id = d.run_id
        LEFT JOIN input_manifests m ON m.id = json_extract(r.input_snapshot_json, '$.manifest_id')
            AND json_extract(m.payload_json, '$.purpose') = r.kind
        WHERE d.scene_id = ? AND d.version > COALESCE((SELECT version FROM drafts WHERE id = ?), 0)
        ORDER BY d.version DESC
        """, (scene_id, accepted_id))
    for draft in versions:
        if draft['branch_id']:
            if draft['branch_id'] == branch:
                return draft['id']
            continue
        # Unattributed historical drafts default to main unless commits prove their branch.
        branches = {row[0] for row in store.connection.execute("""
            SELECT DISTINCT c.branch_id FROM story_commits c, json_each(c.state_json, '$.slots') slot
            WHERE slot.key = ? AND json_extract(slot.value, '$.draft_id') = ?
            """, (scene_id, draft['id']))}
        if branch in (branches or {'main'}):
            return draft['id']
    return accepted_id


def _promotion_preview(store: object, main: StateHead, candidate: StateHead) -> dict:
    """Read-only checks mirror core preconditions; core remains authoritative."""
    old, new = revision_state(store, main), revision_state(store, candidate)
    branch = branch_row(store, candidate.branch_id)
    blockers: list[str] = []
    needs = set(promotion_impacts(store, old, new))
    updates = [key for key, slot in new['slots'].items() if old['slots'].get(key) != slot]
    if branch['parent_branch_id'] != 'main' or branch['parent_at_fork'] != main.revision:
        blockers.append('STALE_HEAD: 主线已改变；当前候选不能提升，请从当前主线重新建立候选。')
    if old == new:
        blockers.append('候选尚无已接受的变更。')
    if needs:
        blockers.append('需在当前候选重新审稿并接受场景：' + ', '.join(sorted(needs)))
    try:
        _topological(_snapshot_dependencies(store, new))
        replay(baseline_for(store, candidate.branch_id), selected_operations(store, new))
    except ValueError as exc:
        message = str(exc)
        needs.update(ident for ident in new['slots'] if ident in message)
        blockers.append(message)
    # Attribute failures with no scene ID in the core message to their scene.
    for ident in updates:
        try:
            _require_promotion_reviews(store, candidate.branch_id, old, new, [ident])
            slot = new['slots'][ident]
            draft = store._check_acceptable(slot['draft_id'])
            check_material_acceptance(store, draft, read_delta(store, slot['delta_id']))
        except ValueError as exc:
            needs.add(ident)
            blockers.append(f'{ident}: {exc}')
    try:
        _require_promotion_reviews(store, candidate.branch_id, old, new, updates)
    except ValueError as exc:
        message = str(exc)
        needs.update(ident for ident in updates if ident in message)
        if message not in blockers:
            blockers.append(message)
    return {'can_promote': not blockers, 'needs_revalidation': sorted(needs),
            'blockers': list(dict.fromkeys(blockers)), 'changed_scenes': updates,
            'settings_changed': old['settings'] != new['settings']}


class BranchMixin:
    """Requires ProductionService's db, open_store, _lock and _workers."""

    def _branch_idle(self, novel: dict, store: object) -> None:
        worker = self._workers.get(novel['id'])
        if worker and worker.is_alive():
            raise ValueError('制作任务仍在运行，请等待当前调用结束后再操作分支')
        if novel.get('job_id'):
            job = show_job(store, novel['job_id'])
            if job.status not in ('DONE', 'CANCELLED', 'REJECTED', 'STALE'):
                raise ValueError('请先完成或取消当前任务及待确认节点，再切换或提升分支')

    def branch_status(self, ident: str) -> dict:
        novel = self.db.get(ident)
        selected = novel.get('current_branch', 'main')
        with self.open_store(novel) as store:
            if not store.managed_story():
                return {'current_branch': 'main', 'branch_id': 'main', 'managed_story': False,
                        'main_head': None, 'candidate_head': None, 'branches': [],
                        'can_promote': False, 'needs_revalidation': [],
                        'blockers': ['旧项目尚未接入故事状态，请先按已有工作流完成 story adopt。']}
            main = current_head(store)
            rows = store.connection.execute('SELECT * FROM story_branches WHERE enabled=1 ORDER BY id').fetchall()
            branches = []
            for row in rows:
                head = current_head(store, row['id'])
                preview = (_promotion_preview(store, main, head) if row['id'] != 'main' else
                           {'can_promote': False, 'needs_revalidation': [], 'blockers': [], 'changed_scenes': []})
                branches.append({'id': row['id'], 'head': asdict(head), 'parent_branch': row['parent_branch_id'],
                                 'parent_at_fork': row['parent_at_fork'], 'is_current': selected == row['id'], **preview})
            candidate = next((row for row in branches if row['id'] == selected), None)
            if candidate is None:
                raise ValueError('当前分支不存在或已停用，请重新选择有效候选')
            active = revision_state(store, current_head(store, selected))
        return {'current_branch': selected, 'branch_id': selected, 'managed_story': True,
                'main_head': asdict(main), 'candidate_head': candidate['head'] if selected != 'main' else None,
                'branches': branches, 'active_snapshot': active,
                **{key: candidate[key] for key in ('can_promote', 'needs_revalidation', 'blockers', 'changed_scenes')}}

    def fork_branch(self, ident: str, body: dict) -> dict:
        with self._lock:
            novel = self.db.get(ident)
            if novel['status'] == 'done':
                raise ValueError('已完稿作品不能建立制作候选')
            name = str(body.get('name') or f'candidate-{uuid4().hex[:10]}').strip()
            if not re.fullmatch(r'[A-Za-z0-9_\-\u4e00-\u9fff]{1,64}', name) or name == 'main':
                raise ValueError('分支名称限 1–64 个中英文字、数字、横线或下划线，不能为 main')
            reason = str(body.get('reason') or '作者建立后续制作候选').strip()
            with self.open_store(novel) as store:
                self._branch_idle(novel, store)
                main = current_head(store)
                if 'expected_main' in body and (type(body['expected_main']) is not int or body['expected_main'] != main.revision):
                    raise ValueError('STALE_HEAD: 主线版本已改变，请刷新后建立候选')
                branch = fork_story(store, main, name)
            self.db.update(ident, current_branch=name, job_id=None, status='designing', runtime_status='READY', reason=None)
            self.db.event(ident, 'branch', f'建立候选 {name}：{reason}',
                          {'branch': asdict(branch), 'from': asdict(main)})
            self.changed.set()
        return self.branch_status(ident)

    def select_branch(self, ident: str, body: dict) -> dict:
        """Reopen a persisted candidate without creating or discarding content."""
        branch_id = str(body.get('branch_id', '')).strip()
        with self._lock:
            novel = self.db.get(ident)
            if novel['status'] == 'done':
                raise ValueError('已完稿作品不能切换制作分支')
            with self.open_store(novel) as store:
                self._branch_idle(novel, store)
                current_head(store, branch_id)
                jobs = store.connection.execute('SELECT id,request_json FROM novel_jobs ORDER BY rowid DESC').fetchall()
                matched = next(((row['id'], json.loads(row['request_json']))
                                for row in jobs if json.loads(row['request_json'])['branch_id'] == branch_id), None)
                job_id, job_req = matched if matched else (None, {})
                job = show_job(store, job_id) if job_id else None
            runtime = 'PAUSED' if job and job.reason == 'AUTHOR_PAUSED' else (job.status if job else 'READY')
            reason = job.reason if job else None
            status = ('paused' if runtime in ('PAUSED', 'BLOCKED', 'CANCELLED', 'REJECTED', 'STALE')
                      else ('designing' if job and job_req.get('mode') == 'design' and runtime != 'DONE' else 'writing'))
            self.db.update(ident, current_branch=branch_id, job_id=job_id, status=status, runtime_status=runtime, reason=reason)
            self.db.event(ident, 'branch', f'作者切换到 {branch_id}', {'branch_id': branch_id})
            self.changed.set()
        return self.branch_status(ident)

    def promote_branch(self, ident: str, body: dict) -> dict:
        reason = body.get('reason', '')
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError('提升主线需要作者填写确认理由')
        if any(type(body.get(key)) is not int for key in ('expected_main', 'expected_candidate')):
            raise ValueError('提升主线必须确认当前主线和候选的版本号')
        with self._lock:
            novel = self.db.get(ident)
            if novel['status'] == 'done':
                raise ValueError('已完稿作品不能提升制作候选')
            selected = novel.get('current_branch', 'main')
            if selected == 'main' or body.get('branch_id', selected) != selected:
                raise ValueError('请先选中要提升的候选分支')
            with self.open_store(novel) as store:
                self._branch_idle(novel, store)
                main, candidate = current_head(store), current_head(store, selected)
                if (main.revision, candidate.revision) != (body['expected_main'], body['expected_candidate']):
                    raise ValueError('STALE_HEAD: 确认后分支版本已改变，请刷新后重新审查')
                preview = _promotion_preview(store, main, candidate)
                if preview['blockers']:
                    return {'status': 'BLOCKED', 'current_branch': selected, 'branch_id': selected,
                            'main_head': asdict(main), 'candidate_head': asdict(candidate), **preview}
                decision_id = record_story_decision(store, 'promote',
                    {'candidate': asdict(candidate), 'expected_main': asdict(main)}, reason.strip())
                promoted = apply_promotion(store, selected, main, decision_id, f'studio-promote:{decision_id}')
            self.db.update(ident, current_branch='main', job_id=None, status='writing', runtime_status='READY', reason=None)
            self.db.event(ident, 'confirmation', f'作者提升候选 {selected} 到主线：{reason.strip()}',
                          {'candidate': asdict(candidate), 'main': asdict(promoted), 'decision_id': decision_id})
            self.changed.set()
        return {'status': 'PROMOTED', 'promoted_head': asdict(promoted), **self.branch_status(ident)}
