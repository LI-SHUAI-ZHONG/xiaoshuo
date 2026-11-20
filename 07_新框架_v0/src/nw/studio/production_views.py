"""Read-only production snapshots and exports from actual persisted artifacts."""
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any

from nw.length_plan import count_words
from nw.length_settings import saved_brief_length
from nw.materials.phase_routes import phase_order
from nw.materials.step_guard import build_continuity_ledger
from nw.novel_store import show_job
from nw.studio.api import STAGE_LABELS
from nw.studio.production_inputs import SLOTS


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
            label = STAGE_LABELS.get(row.get('stage'), {}).get('zh', row['kind'])
            tokens = {key: usage[key] for key in ('total_tokens', 'input_tokens', 'output_tokens', 'prompt_tokens',
                                                 'completion_tokens', 'eval_count', 'prompt_eval_count') if key in usage}
            summary = f"{label} · {row['model'] or '模型未记录'} · {elapsed}s · {row['status']}"
            if tokens:
                summary += ' · ' + ' / '.join(f'{key}={value}' for key, value in tokens.items())
            logs.append({'ts': row['started_at'], 'kind': row['kind'], 'summary': summary, 'ref': row})
        return sorted(logs, key=lambda row: row['ts'])[-limit:]

    def list(self, status: str = '') -> dict:
        known = {row['project_dir'] for row in self.db.list()}
        for project in self.studio.list_projects():
            if project['dir_name'] in known or project.get('error'):
                continue
            wizard = {field: [] for field in SLOTS.values()}
            wizard.update(title=project['name'], idea=(project.get('latest_brief') or {}).get('text', ''),
                          constraints='', choices=[], author_references=[], upgrade_snapshot={'items': []}, imported=True)
            try:
                wizard.update(saved_brief_length(wizard['idea']))
            except ValueError:
                pass  # Handwritten legacy Briefs can contain free-form length preferences.
            if not self.db.add(project['id'], project['dir_name'], project['name'], wizard):
                continue
            jobs = self.studio.project_overview(project['dir_name']).get('jobs', [])
            self.db.update(project['id'], status='writing', job_id=jobs[0]['id'] if jobs else None)
            self.db.event(project['id'], 'import', '已连接现有工作流项目。原始 Brief 和正文保持原样。')
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
                    result.append({'id': gate['token'], 'job_id': job.id, 'step': job.step, 'token': gate['token'],
                                   'branch_id': row['branch_id'],
                                   'actions': gate['actions'], 'target': gate,
                                   'summary': '方案待选择' if str(job.step).startswith('plan:') else
                                   ('核心设定变化需确认' if 'core' in str(job.step) else '本场稿件与状态待接受')})
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

    def progress(self, ident: str, *, include_logs: bool = True) -> dict:
        novel = self.db.get(ident)
        project = self.project(novel)
        with self.open_store(novel) as store:
            job = asdict(show_job(store, novel['job_id'])) if novel['job_id'] else None
            phases = self._phase_rows(store)
            model_logs = self.call_logs(store) if include_logs else []
            rows = store.connection.execute('SELECT id,request_json,status FROM novel_jobs ORDER BY rowid').fetchall()
            job_requests = {row['id']: json.loads(row['request_json']) for row in rows}
            reviews = {scene['id']: self.review_for_draft(store, scene['id'], scene['latest_draft_id'])
                       for scene in project['scenes'] if scene['latest_draft_id']}
            words = 0
            for scene in project['scenes']:
                draft_id = scene['accepted_draft_id'] or scene['latest_draft_id']
                if draft_id and scene['in_branch_manuscript']:
                    words += count_words(store.get('draft', draft_id).text)
        tree = []
        for job_row in reversed(project['jobs']):
            request = job_requests.get(job_row['id'], {})
            if request.get('mode') != 'design':
                continue
            scope = request.get('design_scope', 'chapter')
            scopes = ['book', scope] if scope != 'book' and not request.get('parent_id') else [scope]
            for node_scope in scopes:
                matching = {row['stage']: row for row in phases
                            if row['budget_id'] == job_row['id'] and row['scope'] == node_scope}
                stage_nodes = []
                for stage in phase_order(node_scope):
                    phase = matching.get(stage)
                    parsed = json.loads(phase['result_json']) if phase and phase['result_json'] else {}
                    complete = bool(phase and phase['validation'] == 'VALID' and (parsed or {}).get('products'))
                    state = 'done' if complete else ('running' if phase and phase['status'] == 'STARTED' else
                            ('failed' if phase and phase['validation'] == 'INVALID' else 'pending'))
                    stage_nodes.append({'id': f"{job_row['id']}:{node_scope}:{stage}", 'stage': stage,
                        'label': STAGE_LABELS[stage]['zh'], 'status': state, 'scope': node_scope,
                        'output': (parsed or {}).get('products'), 'children': []})
                applied = any(step['step_key'] == f'plan:{node_scope}:apply' and step['status'] == 'DONE'
                              for step in job_row['outputs']['steps'])
                tree.append({'id': f"{job_row['id']}:{node_scope}", 'label': '全书设计' if node_scope == 'book' else '章节设计',
                             'scope': node_scope, 'status': 'done' if applied else job_row['status'].lower(), 'children': stage_nodes})
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
                    'label': f"场{scene['index']} · {scene['card'].get('title', '场景')}",
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
        current_step = job.get('step') if job else None
        active = next((row for row in reversed(phases) if row['status'] == 'STARTED'), None)
        if active and runtime == 'RUNNING':
            current_step = STAGE_LABELS[active['stage']]['zh']
        logs = self.db.timeline(ident)['events'][-100:] if include_logs else []
        if include_logs:
            logs.extend(model_logs)
            logs.sort(key=lambda row: row['ts'])
        return {'novel_id': ident, 'status': runtime, 'novel_status': novel['status'], 'job': job,
                'branch_id': novel.get('current_branch', 'main'),
                'main_revision': next((row['head_revision'] for row in project['branches'] if row['id'] == 'main'), None),
                'current_step': current_step, 'progress': percentage, 'tree': tree,
                'gates': self.gates(ident)['gates'], 'words': words, 'connection': True,
                'reason': novel['reason'] or (job.get('reason') if job else None),
                'logs': logs[-100:]}

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
        self.sync_history(ident)
        self.sync_adoptions(ident)
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
            products = {row['stage']: {'products': (json.loads(row['result_json']) or {}).get('products', {})}
                        for row in phases if row['validation'] == 'VALID'}
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
                draft_id = next(row['latest_draft_id'] for row in project['scenes'] if row['id'] == scene)
                review = self.review_for_draft(store, scene, draft_id) if draft_id else None
                if review:
                    result['review'] = {**review['result'], 'draft_id': draft_id, 'run_id': review['run_id']}
                    result['materials'] = review['result'].get('material_checks', [])
                result['draft_id'] = draft_id
                result['metrics'] = {'draft_versions': len(drafts), 'review_rounds': sum(run.kind == 'review' for run in runs),
                                     'words': count_words(store.get('draft', draft_id).text) if draft_id else 0,
                                     'model_calls': sum(run.provider != 'author' for run in runs)}
        return result

    @staticmethod
    def review_for_draft(store: Any, scene: str, draft_id: str) -> dict | None:
        """Only a review whose frozen prompt names this exact version can clear it."""
        for run in reversed(store.list('run')):
            if run.scene_id != scene or run.kind != 'review' or run.finish_reason != 'complete':
                continue
            try:
                snapshot = json.loads(run.input_snapshot_json)
                payload = json.loads(snapshot['messages'][-1]['content'])
                if payload.get('draft', {}).get('id') != draft_id:
                    continue
                result = json.loads(run.output_text)
                if isinstance(result, dict):
                    checkpoint = store.connection.execute('''SELECT status,output_json FROM novel_steps
                        WHERE json_extract(output_json,'$.run_id')=? ORDER BY rowid DESC LIMIT 1''', (run.id,)).fetchone()
                    if checkpoint is not None and checkpoint['status'] != 'DONE':
                        return {'run_id': run.id, 'result': {'recommendation': 'invalid',
                                'notes': json.loads(checkpoint['output_json']).get('reason', '审稿输出尚未通过校验')}}
                    return {'run_id': run.id, 'result': result}
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
