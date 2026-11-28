"""Read-only production snapshots and exports from actual persisted artifacts."""
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any

from nw.book_direction_flow import (CONFIRM as DIRECTION_CONFIRM, GATE_KIND as DIRECTION_GATE,
                                    LABEL as DIRECTION_LABEL, PROPOSE as DIRECTION_PROPOSE)
from nw.length_plan import count_words
from nw.length_settings import saved_brief_length
from nw.materials.phase_routes import phase_order
from nw.materials.step_guard import build_continuity_ledger
from nw.novel_flow import CHAPTER_OUTLINE_CONFIRM, TERMINAL
from nw.novel_store import show_job
from nw.studio.api import STAGE_LABELS
from nw.studio.production_inputs import SLOTS
from nw.studio.production_design import SCOPE_LABELS, next_design


class ProductionViews:
    @staticmethod
    def call_logs(store: Any, *, limit: int = 100) -> list[dict]:
        calls = [dict(row) for row in store.connection.execute('''SELECT t.id,t.kind,t.status,t.validation,
            t.started_at,t.ended_at,t.usage_json,t.reason,json_extract(t.manifest_json,'$.settings.model') AS model,
            json_extract(m.package_json,'$.study_input.stage') AS stage FROM task_calls t
            JOIN input_manifests m ON m.id=t.manifest_id ORDER BY t.rowid DESC LIMIT ?''', (limit,))]
        calls.extend({**dict(row), 'status': row['finish_reason'] if row['ended_at'] else 'RUNNING',
                      'validation': None, 'reason': None} for row in store.connection.execute('''
            SELECT id,kind,model,started_at,ended_at,usage_json,finish_reason FROM runs ORDER BY rowid DESC LIMIT ?''', (limit,)))
        logs = []
        for row in calls:
            usage = json.loads(row.pop('usage_json'))
            row['usage'] = usage
            end = datetime.fromisoformat(row['ended_at']) if row['ended_at'] else datetime.now(timezone.utc)
            elapsed = max(0, round((end - datetime.fromisoformat(row['started_at'])).total_seconds(), 1))
            row['elapsed_seconds'] = elapsed
            label = ('全书方向短案' if row['kind'] == 'book_directions' else
                     STAGE_LABELS.get(row.get('stage'), {}).get('zh', row['kind']))
            tokens = {key: usage[key] for key in ('total_tokens', 'input_tokens', 'output_tokens', 'prompt_tokens',
                                                 'completion_tokens', 'eval_count', 'prompt_eval_count') if key in usage}
            summary = f"{label} · {row['model'] or '模型未记录'} · {elapsed}s · {row['status']}"
            if tokens:
                summary += ' · ' + ' / '.join(f'{key}={value}' for key, value in tokens.items())
            logs.append({'ts': row['started_at'], 'kind': row['kind'], 'summary': summary, 'ref': row})
        return sorted(logs, key=lambda row: row['ts'])[-limit:]

    def _repo_writable(self) -> bool:
        repo = getattr(self.studio, 'repository_sync', None)
        if not repo or not repo.enabled:
            return True
        return not (repo._draining or repo.restore_required or repo.check_running_source())

    def _wake_repo(self) -> None:
        repo = getattr(self.studio, 'repository_sync', None)
        if repo and repo.enabled:
            repo._wake.set()

    def list(self, status: str = '') -> dict:
        known = {row['project_dir'] for row in self.db.list()}
        discovered = False
        if self._repo_writable():
            for project in self.studio.list_projects():
                if project['dir_name'] in known or project.get('error'):
                    continue
                wizard = {field: [] for field in SLOTS.values()}
                wizard.update(title=project['name'], idea=(project.get('latest_brief') or {}).get('text', ''),
                              constraints=(project.get('latest_brief') or {}).get('constraints', ''),
                              choices=[], author_references=[], upgrade_snapshot={'items': []}, imported=True)
                try:
                    wizard.update(saved_brief_length(wizard['idea']))
                except ValueError:
                    pass  # Handwritten legacy Briefs can contain free-form length preferences.
                if not self.db.add(project['id'], project['dir_name'], project['name'], wizard):
                    continue
                jobs = self.studio.project_overview(project['dir_name']).get('jobs', [])
                self.db.update(project['id'], status='writing', job_id=jobs[0]['id'] if jobs else None)
                self.db.event(project['id'], 'import', '已连接现有工作流项目。原始 Brief 和正文保持原样。')
                discovered = True
            if discovered:
                self._wake_repo()
        items = []
        for row in self.db.list(status):
            try:
                progress = self.progress(row['id'], include_logs=False)
                row.update(words=progress['words'], progress=progress['progress'], pending_gates=len(progress['gates']),
                           current_step=progress['current_step'])
            except (ValueError, FileNotFoundError) as exc:
                row['error'] = str(exc)
            items.append(row)
        return {'novels': items}

    def gates(self, ident: str) -> dict:
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            rows = store.connection.execute("SELECT id,branch_id FROM novel_jobs WHERE status='WAITING' ORDER BY rowid").fetchall()
            result = []
            for row in rows:
                job = show_job(store, row['id'])
                gate = job.outputs.get('gate')
                if gate:
                    method_stage = STAGE_LABELS.get(gate.get('stage', ''), {}).get('zh', gate.get('stage', ''))
                    summary = ('全书方向待选择' if gate.get('kind') == DIRECTION_GATE else
                               (f'制作方法待确认 · {method_stage}' if method_stage else '制作方法待确认')
                               if gate.get('kind') == 'production_method_selection' else
                               '章纲待确认' if gate.get('kind') == 'chapter_outline_approval' else
                               '卷纲待确认' if gate.get('scope') == 'volume' else
                               '场景设计待确认' if gate.get('scope') == 'chapter' else
                               '方案待选择' if str(job.step).startswith('plan:') else
                               '核心设定变化需确认' if 'core' in str(job.step) else '本场稿件与状态待接受')
                    if type(index := gate.get('chapter_index')) is int:
                        summary = f'第 {index} 章 · {summary}'
                    result.append({'id': gate['token'], 'job_id': job.id, 'step': job.step, 'token': gate['token'],
                                   'branch_id': row['branch_id'],
                                   'actions': gate['actions'], 'target': gate,
                                   'summary': summary})
        return {'gates': result}

    @staticmethod
    def _phase_rows(store: Any) -> list[dict]:
        rows = store.connection.execute('''SELECT t.id,t.budget_id,t.status,t.validation,t.result_json,t.reason,
            t.started_at,t.ended_at,json_extract(m.package_json,'$.study_input.stage') AS stage,
            json_extract(m.package_json,'$.study_input.scope') AS scope,
            json_extract(m.package_json,'$.study_input.continuity_ledger') AS continuity_ledger
            FROM task_calls t JOIN input_manifests m ON t.manifest_id=m.id
            WHERE t.kind='material_work' AND json_type(m.package_json,'$.study_input.stage')='text'
            ORDER BY t.rowid''').fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _compiled_stages(store: Any) -> dict[tuple[str, str, str], dict]:
        rows = store.connection.execute(
            "SELECT package_json FROM input_manifests WHERE id LIKE 'plan:%:stages' ORDER BY rowid"
        ).fetchall()
        compiled: dict[tuple[str, str, str], dict] = {}
        for row in rows:
            try:
                pkg = json.loads(row['package_json'])
            except (ValueError, TypeError):
                continue
            budget_id = (pkg.get('plan_checkpoint') or {}).get('budget_id')
            scope = pkg.get('scope')
            session = pkg.get('material_work') or {}
            if not budget_id or not scope:
                continue
            for record in session.get('stages') or []:
                stage = record.get('stage')
                if stage:
                    compiled[(budget_id, scope, stage)] = record
        return compiled

    @staticmethod
    def _direction_node(job: dict, row: dict | None) -> dict:
        target = json.loads(row['input_json']) if row else {}
        choice = json.loads(row['output_json']).get('choice', {}) if row else {}
        selected = choice.get('root') if choice.get('action') == 'approve' else None
        if selected or choice.get('action') == 'reject':
            status = 'done' if selected else 'rejected'
        elif job['status'] in ('BLOCKED', 'STALE', 'CANCELLED'):
            status = 'blocked'
        elif target:
            status = 'waiting'
        else:
            status = 'running' if job['status'] == 'RUNNING' else 'pending'
        return {'id': f"{job['id']}:book:direction", 'job_id': job['id'], 'scope': 'book',
                'kind': 'book_direction', 'label': DIRECTION_LABEL, 'status': status,
                'output': {'candidates': target.get('candidates', []), 'selected_id': selected}, 'children': []}

    @staticmethod
    def _chapter_outline_node(job: dict, row: dict | None) -> dict:
        target = json.loads(row['input_json']) if row else {}
        choice = json.loads(row['output_json']).get('choice', {}) if row else {}
        state = {'approve': 'done', 'reject': 'rejected'}.get(choice.get('action'))
        if state is None:
            state = 'waiting' if job['status'] == 'WAITING' and target else 'pending'
        label = f"第 {target['chapter_index']} 章 · 章纲确认" if 'chapter_index' in target else '章纲确认'
        return {'id': f"{job['id']}:chapter:outline", 'job_id': job['id'], 'scope': 'chapter',
                'stage': 'chapter_outline', 'label': label, 'status': state, 'children': [],
                'output': {'members': [target['chapter']], 'event_nodes': target.get('event_nodes', [])}
                if target else None}

    def progress(self, ident: str, *, include_logs: bool = True) -> dict:
        novel = self.db.get(ident)
        project = self.project(novel)
        upcoming = None
        can_plan_volume = False
        with self.open_store(novel) as store:
            job = asdict(show_job(store, novel['job_id'])) if novel['job_id'] else None
            phases = self._phase_rows(store)
            compiled_stages = self._compiled_stages(store)
            model_logs = self.call_logs(store) if include_logs else []
            rows = store.connection.execute('SELECT id,request_json,status FROM novel_jobs ORDER BY rowid').fetchall()
            job_requests = {row['id']: json.loads(row['request_json']) for row in rows}
            checkpoints = {(row['job_id'], row['step_key']): dict(row) for row in store.connection.execute(
                'SELECT job_id,step_key,input_json,output_json FROM novel_steps WHERE step_key IN (?,?)',
                (DIRECTION_CONFIRM, CHAPTER_OUTLINE_CONFIRM))}
            if include_logs and novel['wizard'].get('planning_hierarchy') and novel['status'] != 'done':
                branch = novel.get('current_branch', 'main')
                blocked_by_manuscript = branch == 'main' and any(s['accepted_draft_id'] for s in project['scenes'])
                if not blocked_by_manuscript and (not job or job['status'] in TERMINAL):
                    route = next_design(store, branch)
                    can_plan_volume = route['scope'] != 'book'
                    if not any(s['story_approved_on_branch'] and not s['accepted_draft_id'] for s in project['scenes']):
                        upcoming = route
            continuation = None
            if include_logs:
                from nw.studio.continuation_views import continuation_signal
                continuation = continuation_signal(self, novel, project, store, job, upcoming)
            reviews = {scene['id']: self.review_for_draft(store, scene['id'], scene['latest_draft_id'])
                       for scene in project['scenes'] if scene['latest_draft_id']}
            words = 0
            for scene in project['scenes']:
                draft_id = scene['accepted_draft_id'] or scene['latest_draft_id']
                if draft_id and scene['in_branch_manuscript']:
                    words += count_words(store.get('draft', draft_id).text)
            jobs_by_id = {row['id']: row for row in project['jobs']}
            design_jobs = [jobs_by_id.get(row['id']) or asdict(show_job(store, row['id']))
                           for row in reversed(rows)
                           if job_requests.get(row['id'], {}).get('mode') == 'design']
        tree = []
        current_branch = novel.get('current_branch', 'main')
        visible_branches = {'main'} if current_branch == 'main' else {'main', current_branch}
        from nw.materials.creative_workflow import step_label as creative_step_label, step_meta as creative_step_meta, workflow_overview
        for job_row in design_jobs:
            request = job_requests.get(job_row['id'], {})
            if (job_row.get('branch_id') or request.get('branch_id', 'main')) not in visible_branches:
                continue
            scope = request.get('design_scope', 'chapter')
            scopes = ['book', scope] if scope != 'book' and not request.get('parent_id') else [scope]
            creative_mode = bool(request.get('creative_workflow'))
            gov_ts = (request.get('governance_inputs') or {}).get('type_selection', {})
            from nw.studio.catalog import single_genre_path
            chosen_genre_ids = (
                [r['id'] for r in gov_ts.get('creation_plan', {}).get('types', []) if r.get('id')]
                or list((request.get('production_method_policy') or {}).get('type_ids') or [])
            )
            single_genre_book = bool(gov_ts.get('single_genre_selection') or single_genre_path(chosen_genre_ids))
            for node_scope in scopes:
                matching = {row['stage']: row for row in phases
                            if row['budget_id'] == job_row['id'] and row['scope'] == node_scope}
                blocked = job_row['outputs'].get('blocked_design', {})
                stage_nodes = []
                auto_contracts = []
                direction_enabled = node_scope == 'book' and request.get('direction_review')
                hierarchical = request.get('planning_hierarchy', False)
                if direction_enabled:
                    dir_node = self._direction_node(job_row, checkpoints.get((job_row['id'], DIRECTION_CONFIRM)))
                    if creative_mode:
                        dir_node['label'] = '全书方向与故事大纲'
                        dir_node['group'] = 'book_direction'
                        dir_node['group_label'] = '零、全书方向与故事大纲'
                    stage_nodes.append(dir_node)
                for stage in phase_order(node_scope, planning_hierarchy=hierarchical):
                    phase = matching.get(stage)
                    compiled = compiled_stages.get((job_row['id'], node_scope, stage))
                    parsed = json.loads(phase['result_json']) if phase and phase['result_json'] else {}
                    products_out = (parsed or {}).get('products') or (compiled.get('products') if compiled else None)
                    is_programmatic = bool(compiled and str(compiled.get('execution_mode', '')).startswith('programmatic_'))
                    complete = bool((phase and phase['validation'] == 'VALID' and (parsed or {}).get('products')) or is_programmatic)
                    blocked_here = (job_row['status'] == 'BLOCKED'
                                    and blocked.get('scope') == node_scope and blocked.get('stage') == stage)
                    state = 'blocked' if blocked_here else 'done' if complete else ('running' if phase and phase['status'] == 'STARTED' else
                            ('failed' if phase and phase['validation'] == 'INVALID' else 'pending'))
                    meta = creative_step_meta(node_scope, stage) if creative_mode else {}
                    node_entry = {
                        'id': f"{job_row['id']}:{node_scope}:{stage}", 'stage': stage,
                        'label': creative_step_label(node_scope, stage, fallback=STAGE_LABELS[stage]['zh']) if creative_mode else STAGE_LABELS[stage]['zh'],
                        'status': state, 'scope': node_scope,
                        'output': products_out, 'children': [],
                        **({'execution_mode': compiled.get('execution_mode')} if is_programmatic else {}),
                        **({'group': meta['group'], 'group_label': meta.get('group_label', '')} if creative_mode and meta.get('group') else {}),
                    }
                    # In creative workflow mode, auto-compiled/inherited type contracts and empty volume bind_scope
                    # do not clutter the author's step list unless they ran via LLM or blocked/failed.
                    auto_expected = (
                        creative_mode and not blocked_here and state != 'failed' and phase is None and (
                            (node_scope in ('volume', 'chapter') and stage in ('type_selection', 'type_adaptation'))
                            or (node_scope == 'volume' and stage == 'bind_scope')
                            or (node_scope == 'book' and stage == 'type_selection' and bool(chosen_genre_ids))
                            or (node_scope == 'book' and stage == 'type_adaptation' and single_genre_book)
                        )
                    )
                    if is_programmatic or auto_expected:
                        node_entry['status'] = 'done' if (is_programmatic or any(
                            matching.get(later) for later in phase_order(node_scope, planning_hierarchy=hierarchical)
                            if later not in ('type_selection', 'type_adaptation', 'bind_scope')
                        )) else state
                        auto_contracts.append(node_entry)
                    else:
                        stage_nodes.append(node_entry)
                    if hierarchical and node_scope == 'chapter' and stage == 'plot_design':
                        ch_node = self._chapter_outline_node(
                            job_row, checkpoints.get((job_row['id'], CHAPTER_OUTLINE_CONFIRM)))
                        if creative_mode:
                            ch_node['group'] = 'chapter_outline_prep'
                            ch_node['group_label'] = '一、本章承接与章纲确认'
                        stage_nodes.append(ch_node)
                applied = any(step['step_key'] == f'plan:{node_scope}:apply' and step['status'] == 'DONE'
                              for step in job_row['outputs']['steps'])
                if direction_enabled:
                    label = '全书创作大纲与定稿' if creative_mode else '全书制作'
                elif creative_mode:
                    label = {'book': '全书大纲与设定', 'volume': '卷纲与逐章切分', 'chapter': '章细纲与可写场景包'}.get(
                        node_scope, SCOPE_LABELS.get(node_scope, '设计'))
                else:
                    label = SCOPE_LABELS.get(node_scope, '设计') if hierarchical or node_scope == 'volume' else (
                        '全书设计' if node_scope == 'book' else '章节设计')
                entry = {'id': f"{job_row['id']}:{node_scope}", 'label': label,
                         'scope': node_scope, 'status': 'done' if applied else job_row['status'].lower(),
                         'children': stage_nodes,
                         **({'creative_workflow': True} if creative_mode else {}),
                         **({'auto_contracts': auto_contracts} if auto_contracts else {})}
                if lineage := request.get('outline_lineage'):
                    entry['approved_parent'] = lineage[-1]
                tree.append(entry)
        for chapter in project['chapters']:
            children = []
            chapter_scenes = [row for row in project['scenes'] if row['chapter_id'] == chapter['id']]
            visible_scenes = [row for row in chapter_scenes if row['in_branch_workbench']]
            if chapter_scenes and not visible_scenes:
                continue
            for scene in visible_scenes:
                review = reviews.get(scene['id'])
                reviewed = bool(review and review['result'].get('recommendation') == 'pass')
                accepted_current = bool(scene['accepted_draft_id'] and
                                        scene['accepted_draft_id'] == scene['latest_draft_id'])
                current = bool(job and scene['id'] in str(job.get('step')) and job['status'] == 'RUNNING')
                children.append({'id': scene['id'], 'scene_id': scene['id'],
                    'label': f"场{scene['index']} · {scene.get('title') or scene['card'].get('title') or '场景'}",
                    'status': 'done' if accepted_current else 'running' if current else 'pending',
                    'draft_id': scene['latest_draft_id'], 'accepted_draft_id': scene['accepted_draft_id'],
                    'segments': {'write': bool(scene['latest_draft_id']), 'review': reviewed,
                                 'accept': accepted_current}, 'children': []})
            tree.append({'id': chapter['id'], 'label': f"第{chapter['index']}章 · {chapter['title']}",
                         'status': 'done' if children and all(row['status'] == 'done' for row in children) else 'pending',
                         'children': children})
        leaves = [child for node in tree for child in node['children']]
        percentage = round(100 * sum(row['status'] == 'done' for row in leaves) / len(leaves)) if leaves else 0
        if novel['status'] != 'done':
            percentage = min(99, percentage)
        runtime = novel['runtime_status']
        if job and runtime not in ('CONFIG_REQUIRED', 'PAUSED', 'PAUSING', 'BLOCKED'):
            runtime = job['status']
        current_job_req = job_requests.get(job['id'], {}) if job else {}
        current_creative = bool(current_job_req.get('creative_workflow'))
        current_scope = current_job_req.get('design_scope', 'chapter')
        current_step = job.get('step') if job else None
        if current_step in (DIRECTION_PROPOSE, DIRECTION_CONFIRM):
            current_step = '全书方向与故事大纲' if current_creative else DIRECTION_LABEL
        elif current_step == CHAPTER_OUTLINE_CONFIRM:
            current_step = '章纲确认'
        active = next((row for row in reversed(phases) if job and row['budget_id'] == job['id']
                       and row['status'] == 'STARTED'), None)
        if active and runtime == 'RUNNING':
            current_step = (creative_step_label(active.get('scope') or current_scope, active['stage'],
                                                fallback=STAGE_LABELS[active['stage']]['zh'])
                            if current_creative else STAGE_LABELS[active['stage']]['zh'])
        blocked_design = None
        if job and runtime == 'BLOCKED':
            blocked = job['outputs'].get('blocked_design', {})
            if blocked.get('stage') in STAGE_LABELS:
                current_step = (creative_step_label(blocked.get('scope') or current_scope, blocked['stage'],
                                                    fallback=STAGE_LABELS[blocked['stage']]['zh'])
                                if current_creative else STAGE_LABELS[blocked['stage']]['zh'])
                blocked_design = blocked
        logs = self.db.timeline(ident)['events'][-100:] if include_logs else []
        if include_logs:
            logs.extend(model_logs)
            logs.sort(key=lambda row: row['ts'])
        return {'novel_id': ident, 'status': runtime, 'novel_status': novel['status'], 'job': job,
                'branch_id': novel.get('current_branch', 'main'),
                'main_revision': next((row['head_revision'] for row in project['branches'] if row['id'] == 'main'), None),
                'current_step': current_step, 'blocked_design': blocked_design, 'progress': percentage, 'tree': tree,
                'creative_workflow': bool(novel['wizard'].get('creative_workflow')),
                'workflow_overview': workflow_overview(),
                'next_design': upcoming, 'can_plan_volume': can_plan_volume,
                **({'continuation': continuation} if continuation is not None else {}),
                'gates': self.gates(ident)['gates'], 'words': words, 'connection': True,
                'reason': novel['reason'] or (job.get('reason') if job else None),
                'logs': logs[-100:]}

    def continuation(self, ident: str) -> dict:
        from nw.studio.continuation_views import continuation_overview
        return continuation_overview(self, ident)

    def save_chapter_summary(self, ident: str, chapter_idx: int, body: dict) -> dict:
        from nw.studio.continuation_views import save_chapter_summary_record
        return save_chapter_summary_record(self, ident, chapter_idx, body)

    def save_chapter_review(self, ident: str, chapter_idx: int, kind: str, body: dict) -> dict:
        from nw.studio.continuation_views import save_chapter_review_record
        return save_chapter_review_record(self, ident, chapter_idx, kind, body)

    def finish_check(self, ident: str) -> dict:
        from nw.studio.continuation_views import finish_readiness
        return finish_readiness(self, ident)

    def sync_history(self, ident: str) -> None:
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            for log in self.call_logs(store, limit=10000):
                row = log['ref']
                self.db.event(ident, log['kind'], log['summary'], row,
                              dedup=f"{ident}:call:{row['id']}:{row['status']}:{row['validation']}", timestamp=log['ts'])
            for row in store.connection.execute('SELECT id,kind,status,validation,started_at,ended_at,reason FROM task_calls'):
                self.db.event(ident, 'design' if row['kind'] in ('plan', 'material_work') else row['kind'],
                              f"{row['kind']} · {row['status']} · {row['validation']}", dict(row),
                              dedup=f"{ident}:task:{row['id']}:{row['status']}:{row['validation']}",
                              timestamp=row['ended_at'] or row['started_at'])
            for draft in store.list('draft'):
                self.db.event(ident, 'write', f'草稿 v{draft.version} 已保存',
                              {'scene_id': draft.scene_id, 'draft_id': draft.id, 'version': draft.version},
                              dedup=f'{ident}:draft:{draft.id}', timestamp=draft.created_at)
            for row in store.connection.execute('SELECT * FROM story_decisions'):
                self.db.event(ident, 'confirmation', row['reason'],
                              {'action': row['action'], 'targets': json.loads(row['targets_json'])},
                              dedup=f"{ident}:decision:{row['id']}", timestamp=row['created_at'])

    def timeline(self, ident: str) -> dict:
        if self._repo_writable():
            self.sync_history(ident)
            self.sync_adoptions(ident)
            self._wake_repo()
        return self.db.timeline(ident)

    def sync_adoptions(self, ident: str) -> None:
        """Count only choices present in accepted design and its passing draft review."""
        from nw.materials.evidence import scene_materials
        from nw.studio import catalog
        novel = self.db.get(ident)
        project = self.studio.project_overview(novel['project_dir'])
        selected = {row['option_key'] for row in novel['wizard'].get('choices', [])}
        options = catalog.option_map()
        with self.open_store(novel) as store:
            for scene in project['scenes']:
                if not scene['accepted_draft_id'] or not scene['story_approved_on_main']:
                    continue
                review = self.review_for_draft(store, scene['id'], scene['accepted_draft_id'])
                if not review or review['result'].get('recommendation') != 'pass':
                    continue
                design = scene_materials(store, scene['id'])
                stages = design.get('work_session', {}).get('stages', []) if design else []
                type_product = next((row['products'] for row in stages if row['stage'] == 'type_selection'), {})
                used = {row.get('id') for row in type_product.get('selection', []) if isinstance(row, dict)}
                # project_config is the author's preference, not evidence of use.
                # Only an actual selected product or an explicit passing material
                # check can increment the reviewed adoption count.
                keys = {key for key in selected if key in options and options[key]['id'] in used}
                keys.update(check['option_key'] for check in review['result'].get('material_checks', [])
                            if check.get('option_key') in selected and check.get('status') == 'pass')
                if keys:
                    self.library.record_adoption(ident, scene['id'], sorted(keys), review['run_id'])

    def quality(self, ident: str, scene: str = '') -> dict:
        novel = self.db.get(ident)
        project = self.project(novel)
        if not scene:
            scene = next((row['id'] for row in project['scenes'] if row['in_branch_workbench']), '')
        result = {'scene_id': scene or None, 'review': None, 'guards': [], 'materials': [], 'metrics': {}}
        with self.open_store(novel) as store:
            phases = self._phase_rows(store)
            active_phases = [row for row in phases if not novel.get('job_id') or row['budget_id'] == novel['job_id']]
            products = {row['stage']: {'products': (json.loads(row['result_json']) or {}).get('products', {})}
                        for row in active_phases if row['validation'] == 'VALID'}
            if scene:
                from nw.materials.evidence import scene_materials
                design = scene_materials(store, scene)
                session = design.get('work_session', {}) if design else {}
                products = {row['stage']: row for row in session.get('stages', [])}
            if products:
                ledger = build_continuity_ledger('expression_design', products, [], {}) or {}
                for key in ('character_voice_guard', 'foreshadow_reminder', 'multi_char_guard'):
                    if ledger.get(key):
                        result['guards'].append({'kind': key, 'detail': ledger[key], 'severity': 'info'})
            current_phases = {(row['scope'], row['stage']): row for row in phases if row['budget_id'] == novel['job_id']}
            for row in current_phases.values() if not scene else ():
                if row['reason'] and row['validation'] != 'VALID':
                    result['guards'].append({'kind': 'step_guard', 'detail': row['reason'], 'severity': 'error'})
            if scene and novel['job_id']:
                job = show_job(store, novel['job_id'])
                if job.status == 'BLOCKED' and scene in str(job.step) and job.reason != 'AUTHOR_PAUSED':
                    result['guards'].append({'kind': 'step_guard', 'detail': job.reason, 'severity': 'error'})
            if scene:
                store.get('scene', scene)
                runs = [run for run in store.list('run') if run.scene_id == scene]
                drafts = store.drafts(scene)
                scene_row = next(row for row in project['scenes'] if row['id'] == scene)
                from nw.studio.cast_view import scene_cast_view
                if cast := scene_cast_view(store, design, scene_row):
                    result['cast'] = cast
                draft_id = scene_row['latest_draft_id']
                accepted_id = scene_row['accepted_draft_id']
                draft_obj = store.get('draft', draft_id) if draft_id else None
                draft_run = store.get('run', draft_obj.run_id) if draft_obj else None
                is_manual = bool(draft_run and draft_run.provider == 'author')
                review = self.review_for_draft(store, scene, draft_id) if draft_id else None
                if review:
                    result['review'] = {**review['result'], 'draft_id': draft_id, 'run_id': review['run_id']}
                    result['materials'] = review['result'].get('material_checks', [])
                    if review['result'].get('length_feedback'):
                        result['length_feedback'] = review['result']['length_feedback']
                    if review['result'].get('chapter_break'):
                        result['chapter_break'] = review['result']['chapter_break']
                # 17 State extraction & fact-review ledger for the active draft on current branch.
                delta_info = None
                fact_findings: list[dict] = []
                if draft_id:
                    branch_id = novel.get('current_branch', 'main')
                    drow = store.connection.execute(
                        'SELECT id FROM state_deltas WHERE draft_id=? AND branch_id=? ORDER BY rowid DESC LIMIT 1',
                        (draft_id, branch_id),
                    ).fetchone()
                    if drow:
                        from nw.story_delta import check_delta, read_delta
                        delta_obj = read_delta(store, drow['id'])
                        fact_findings = [asdict(f) for f in check_delta(store, delta_obj)]
                        delta_info = {
                            'id': delta_obj.id,
                            'draft_id': delta_obj.draft_id,
                            'manifest_id': delta_obj.manifest_id,
                            'branch_id': delta_obj.branch_id,
                            'base_revision': delta_obj.base_revision,
                            'operations': list(delta_obj.operations),
                            'world_operations': [op for op in delta_obj.operations if op.get('holder') == 'WORLD'],
                            'character_operations': [op for op in delta_obj.operations if op.get('holder') != 'WORLD'],
                        }
                result['delta'] = delta_info
                result['fact_findings'] = fact_findings
                # 15 Writing contract: upstream 09/12/13/14 handoff summary + genre 15–17 focuses.
                card_body = dict(scene_row.get('card') or {})
                story_meta = card_body.get('story') if isinstance(card_body.get('story'), dict) else {}
                scene_ref = story_meta.get('scene_ref') if isinstance(story_meta.get('scene_ref'), dict) else None
                if scene_ref and scene_ref.get('card_id') and scene_ref.get('version'):
                    try:
                        from nw.cards import read_card
                        from nw.story_models import CardRef
                        resolved = read_card(store, CardRef(str(scene_ref['card_id']), int(scene_ref['version'])))
                        if isinstance(resolved, dict) and isinstance(resolved.get('body'), dict):
                            card_body = {**card_body, **resolved['body']}
                    except Exception:
                        pass
                mkey = design.get('material_key') if design else None
                stages_by_name = {row['stage']: row.get('products', {}) for row in session.get('stages', [])} if design else {}
                anchor_beats = [b for b in stages_by_name.get('anchor_design', {}).get('beats', ())
                                if isinstance(b, dict) and (not mkey or b.get('scene') == mkey)]
                expr_guidance = [g for g in stages_by_name.get('expression_design', {}).get('guidance', ())
                                 if isinstance(g, dict) and (not mkey or g.get('scene') == mkey)]
                bind_guidance = [g for g in stages_by_name.get('bind_scope', {}).get('method_guidance', ())
                                 if isinstance(g, dict) and (not mkey or g.get('scene') == mkey)]
                from nw.studio.craft_materials import craft_profile_for_types
                try:
                    cprof = craft_profile_for_types(novel['wizard'].get('genre_ids') or ())
                except ValueError:
                    cprof = craft_profile_for_types(())
                result['writing_contract'] = {
                    'title': card_body.get('title', ''),
                    'pov': card_body.get('pov', ''),
                    'goal': card_body.get('goal', ''),
                    'conflict': card_body.get('conflict', ''),
                    'allowed_disclosure': card_body.get('allowed_disclosure', ''),
                    'characters': list(card_body.get('characters', ())) if isinstance(card_body.get('characters'), list) else [],
                    'anchor_beats_count': len(anchor_beats),
                    'expression_guidance_count': len(expr_guidance),
                    'method_guidance_count': len(bind_guidance),
                    'anchor_beats': list(anchor_beats[:8]),
                    'expression_guidance': list(expr_guidance[:8]),
                    'method_guidance': list(bind_guidance[:8]),
                    'writer_review_focus': cprof['craft_profile']['writer_review_focus'],
                    'acceptance_focus': cprof['craft_profile']['acceptance_focus'],
                }
                # 15–17 live execution status for this scene's current draft.
                rec = review['result'].get('recommendation') if review else None
                hard_count = sum(1 for f in fact_findings if f.get('severity') == 'hard')
                is_accepted = bool(draft_id and accepted_id == draft_id)
                if not draft_id:
                    stage_label = '15 待写作'
                elif is_accepted:
                    stage_label = '17 已接受入库'
                elif is_manual and not review:
                    stage_label = '15 手动修改待独立审稿'
                elif not review:
                    stage_label = '16 待独立审稿'
                elif rec != 'pass':
                    stage_label = '16 审稿未通过待修订'
                elif not delta_info:
                    stage_label = '17 审稿通过待提取状态'
                elif hard_count:
                    stage_label = f'17 事实复核受阻（{hard_count} 项硬问题）'
                else:
                    stage_label = '17 已提取状态待批次接受'
                result['draft_status'] = {
                    'draft_id': draft_id,
                    'accepted_draft_id': accepted_id,
                    'is_accepted': is_accepted,
                    'is_manual': is_manual,
                    'needs_review': bool(draft_id and not is_accepted and rec != 'pass'),
                    'review_recommendation': rec,
                    'has_delta': bool(delta_info),
                    'hard_findings_count': hard_count,
                    'stage_label': stage_label,
                }
                result['draft_id'] = draft_id
                from nw.cold_read import cold_read_summary
                result['cold_read'] = cold_read_summary(
                    store, scene_id=scene, draft_id=draft_id, chapter_index=scene_row.get('chapter_index'),
                )
                result['metrics'] = {'draft_versions': len(drafts), 'review_rounds': sum(run.kind == 'review' for run in runs),
                                     'words': count_words(draft_obj.text) if draft_obj else 0,
                                     'model_calls': sum(run.provider != 'author' for run in runs)}
            from nw.craft_specs import load_all_craft_specs, summarize_craft_specs
            from nw.writing_craft import style_reference_overview
            from nw.voice_specs import load_book_voice_spec
            style_ov = style_reference_overview(store, branch=novel.get('current_branch', 'main'))
            result['style_reference'] = {
                'enabled': style_ov['enabled'],
                'mode': style_ov['mode'],
                'title': style_ov['title'],
                'excerpt_chars': len(style_ov.get('excerpt') or ''),
                'can_use_auto_book_prose': style_ov['can_use_auto_book_prose'],
            }
            all_specs = load_all_craft_specs(store, wizard=novel['wizard'])
            result['craft_specs'] = summarize_craft_specs(all_specs)
            vspec = all_specs.get('voice') or load_book_voice_spec(store)
            result['voice_spec'] = (
                {
                    'enabled': bool(vspec.get('enabled', True)),
                    'base_voice_id': vspec.get('base_voice_id', ''),
                    'base_voice_name': vspec.get('base_voice_name', ''),
                    'fingerprint_count': len(vspec.get('fingerprints') or ()),
                    'drift_redlines_count': len(vspec.get('drift_redlines') or ()),
                }
                if vspec else None
            )
        return result

    @staticmethod
    def review_for_draft(store: Any, scene: str, draft_id: str) -> dict | None:
        """Only a review whose frozen prompt names this exact version can clear it."""
        records = store.connection.execute("""SELECT id,input_snapshot_json,output_text FROM runs
            WHERE scene_id=? AND kind='review' AND finish_reason='complete' ORDER BY rowid DESC""", (scene,))
        for run in records:
            try:
                snapshot = json.loads(run['input_snapshot_json'])
                payload = json.loads(snapshot['messages'][-1]['content'])
                if payload.get('draft', {}).get('id') != draft_id:
                    continue
                result = json.loads(run['output_text'])
                if isinstance(result, dict):
                    checkpoint = store.connection.execute('''SELECT status,output_json FROM novel_steps
                        WHERE json_extract(output_json,'$.run_id')=? ORDER BY rowid DESC LIMIT 1''', (run['id'],)).fetchone()
                    if checkpoint is not None:
                        validated = json.loads(checkpoint['output_json'])
                        if checkpoint['status'] != 'DONE':
                            return {'run_id': run['id'], 'result': {'recommendation': 'invalid',
                                    'notes': validated.get('reason', '审稿输出尚未通过校验')}}
                        if validated.get('recommendation') in ('pass', 'revise'):
                            result = {key: value for key, value in validated.items()
                                      if key not in ('manifest_id', 'draft_id', 'run_id')}
                    return {'run_id': run['id'], 'result': result}
            except (ValueError, KeyError, TypeError, IndexError):
                continue
        return None

    def export(self, ident: str, fmt: str = 'txt', scope: str = 'book') -> tuple[str, str]:
        if fmt not in ('txt', 'md'):
            raise ValueError('首版支持 TXT / Markdown 导出')
        novel = self.db.get(ident)
        project = self.project(novel)
        chapters = project['chapters']
        label = '全书'
        if scope.startswith('chapter:'):
            target = scope.split(':', 1)[1]
            chapters = [row for row in chapters if row['id'] == target or str(row['index']) == target]
            if chapters:
                label = f"第{chapters[0]['index']}章"
        elif scope.startswith('volume:'):
            target = scope.split(':', 1)[1]
            with self.open_store(novel) as store:
                chapter_ids = self.volume_chapters(store, target, project['active_settings'])
            chapters = [row for row in chapters if row['id'] in chapter_ids]
            label = '卷-' + self._export_label(target)
        elif scope not in ('book', 'all', ''):
            raise ValueError('无效的导出范围')
        with self.open_store(novel) as store:
            text = self._write_export(store, novel, chapters, project['scenes'], label, fmt)
        return text, f"{novel['id']}.{fmt}"

    def _write_export(self, store: Any, novel: dict, chapters: list, scenes: list, label: str, fmt: str) -> str:
        lines = [('# ' if fmt == 'md' else '') + novel['title'], '']
        count = 0
        for chapter in chapters:
            texts = [store.get('draft', scene['accepted_draft_id']).text for scene in scenes
                     if scene['chapter_id'] == chapter['id'] and scene['in_branch_manuscript'] and scene['accepted_draft_id']]
            if texts:
                count += len(texts)
                lines.extend([('## ' if fmt == 'md' else '') + f"第{chapter['index']}章 {chapter['title']}", '', '\n\n'.join(texts), ''])
        if not count:
            raise ValueError('所选范围还没有已接受的正文，完成审稿并接受后即可导出')
        text = '\n'.join(lines)
        branch = novel.get('current_branch', 'main')
        if branch != 'main':
            label += '-候选-' + self._export_label(branch)
        path = store.data_file('成品', f'{label}.{fmt}')
        path.parent.mkdir(exist_ok=True)
        # A download and its on-disk copy represent the same accepted set of scenes.
        staged = NamedTemporaryFile('w', encoding='utf-8', newline='', dir=path.parent,
                                   prefix='.export-', suffix='.tmp', delete=False)
        tmp = Path(staged.name)
        try:
            with staged:
                staged.write(text)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
        return text

    @staticmethod
    def _export_label(identity: str) -> str:
        if re.fullmatch(r'[\w-]{1,56}', identity):
            return identity
        return sha256(identity.encode('utf-8')).hexdigest()[:24]

    @staticmethod
    def volume_chapters(store: Any, volume_id: str, active_settings: list[dict]) -> set[str]:
        """Resolve actual applied volume plans and their applied descendants; never guess."""
        from nw.cards import read_card
        from nw.planning import plan_input, show_plan
        from nw.story_models import CardRef
        active = {(row['card_id'], row['version']) for row in active_settings}
        applications = {}
        roots = set()
        for row in store.connection.execute('SELECT proposal_id FROM plan_applications'):
            proposal = show_plan(store, row['proposal_id'])
            app = proposal.application
            if not app or (app['root']['card_id'], app['root']['version']) not in active:
                continue
            _, frozen = plan_input(store, proposal.id)
            applications[proposal.id] = (app, frozen.get('parent_id'))
            if proposal.scope == 'volume':
                volumes = [ref for ref in app['approvals'] if read_card(store, CardRef(ref['card_id'], ref['version']))['kind'] == 'volume']
                if any(ref['card_id'] == volume_id for ref in volumes):
                    if len(volumes) != 1:
                        raise ValueError('此方案包含多个卷但未记录逐章归属，不能推断卷导出范围')
                    roots.add(proposal.id)
        if not roots:
            raise ValueError('所选卷没有当前分支已批准的卷方案和章节归属')
        previous = set()
        while previous != roots:
            previous = set(roots)
            roots.update(ident for ident, (_, parent) in applications.items() if parent in roots)
        return {row['chapter_id'] for ident in roots for row in applications[ident][0]['chapters']}
