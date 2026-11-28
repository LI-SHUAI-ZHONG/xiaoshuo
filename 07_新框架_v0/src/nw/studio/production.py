"""The desktop client's asynchronous adapter over the existing durable workflow."""
from dataclasses import asdict
import json
from pathlib import Path
import threading
from typing import Any, Callable
from uuid import uuid4

from nw.book_direction_flow import CONFIRM as DIRECTION_CONFIRM, GATE_KIND as DIRECTION_GATE, validate_choice
from nw.chapter_break import require_break_review
from nw.config import ConfigRequired, load_config, make_provider
from nw.novel_flow import resume_job
from nw.novel_store import JobRequest, cancel_job, show_job, start_job
from nw.store import Store, now
from nw.project_paths import project_directory
from nw.story_state import adopt_story
from nw.task_models import Budget
from nw.studio.production_inputs import brief_text, freeze_wizard, governance
from nw.studio.production_design import design_route
from nw.studio.production_store import ProductionStore
from nw.story_delta import read_delta
from nw.studio.production_length import change_length, manuscript_length, retire_unstarted_book, verify_finish_length
from nw.studio.production_views import ProductionViews
from nw.studio.production_branches import BranchMixin
from nw.studio.production_methods import ProductionMethodMixin
from nw.studio.novel_cache import NovelCacheMixin


class ProductionService(NovelCacheMixin, ProductionMethodMixin, BranchMixin, ProductionViews):
    def __init__(self, studio: Any, library: Any, *, test_mode: bool = False,
                 runtime_factory: Callable | None = None) -> None:
        self.studio, self.library = studio, library
        self.db = ProductionStore(studio.workspace)
        self.test_mode, self.runtime_factory = test_mode, runtime_factory
        self._lock = threading.RLock()
        self._workers: dict[str, threading.Thread] = {}
        self.changed = threading.Event()
        self.novel_cache()

    def open_store(self, novel: dict, *, create: bool = False) -> Store:
        directory = project_directory(self.studio.workspace, novel['project_dir'])
        return Store(directory, test_mode=self.test_mode, create=create, projects_root=self.studio.projects_root)

    @staticmethod
    def budget(raw: dict | None = None) -> Budget:
        value = {'max_calls': 40, 'context_char_limit': 150000, 'output_limit': 4096, 'max_revisions': 2}
        raw = {} if raw is None else raw
        if not isinstance(raw, dict) or set(raw) - set(value):
            raise ValueError('无效的调用预算')
        value.update(raw)
        if any(type(item) is not int for item in value.values()) or not (
            1 <= value['max_calls'] <= 1000 and 1000 <= value['context_char_limit'] <= 1000000
            and 128 <= value['output_limit'] <= 100000 and 0 <= value['max_revisions'] <= 2
        ):
            raise ValueError('调用预算超出允许范围')
        return Budget(**value)

    def create(self, body: dict) -> dict:
        with self._lock:
            return self._create(body)

    def _create(self, body: dict) -> dict:
        wizard = freeze_wizard(body, self.library)
        budget = self.budget(body.get('budget'))
        if body.get('budget'):
            wizard['call_budget'] = dict(body['budget'])
        ident = uuid4().hex
        directory = f'novel-{ident[:12]}'
        # Reserve the directory before publishing nw.db to workspace discovery.
        # Concurrent shelf polling must not import a half-created book under a
        # second ID or replace the author's frozen choices.
        if not self.db.add(ident, directory, wizard['title'], wizard):
            raise ValueError('立项目录已被占用，请重新提交立项')
        try:
            with self.open_store({'project_dir': directory}, create=True) as store:
                project = store.init_project(wizard['title'])
                self.db.update(ident, project_id=project.id)
                store.add_brief(brief_text(wizard), wizard['constraints'])
                if isinstance(wizard.get('craft_specs'), dict):
                    from nw.craft_specs import save_craft_spec
                    for dom, sp in wizard['craft_specs'].items():
                        if isinstance(sp, dict):
                            save_craft_spec(store, dom, sp)
                elif isinstance(wizard.get('voice_spec'), dict):
                    from nw.voice_specs import save_book_voice_spec
                    save_book_voice_spec(store, wizard['voice_spec'])
                adopt_story(store, {'as_of_story_order': 0, 'disclosure_order': [0, 0, 0],
                    'coverage': {'entities': [], 'predicates': []}, 'facts': [], 'card_refs': []}, {})
                job = start_job(store, JobRequest('design', design_scope='book', budget=budget,
                                                 governance_inputs=governance(wizard, library=self.library, store=store, scope='book'),
                                                 production_method_policy=wizard.get('production_methods',{}),
                                                 direction_review=wizard.get('direction_review', False),
                                                 planning_hierarchy=wizard.get('planning_hierarchy', False),
                                                 creative_workflow=wizard.get('creative_workflow', False)))
        except Exception as exc:
            self.db.update(ident, status='paused', runtime_status='BLOCKED', reason=f'立项初始化未完成：{exc}')
            raise
        self.db.update(ident, job_id=job.id)
        self.db.event(ident, 'creation', '立项完成，已保存作者偏好、参考来源和 Brief。', {'wizard': wizard})
        return {'novel': self.db.get(ident), 'run': self.run(ident, {})}

    def detail(self, ident: str) -> dict:
        novel = self.db.get(ident)
        project = self.project(novel)
        volumes = []
        active = {(row['card_id'], row['version']) for row in project['active_settings']}
        with self.open_store(novel) as store:
            length = manuscript_length(store, novel['wizard'])
            length['budget'] = asdict(self.budget(novel['wizard'].get('call_budget')))
            for card in project['cards']:
                if card['kind'] != 'volume' or (card['card_id'], card['version']) not in active:
                    continue
                try:
                    chapter_ids = self.volume_chapters(store, card['card_id'], project['active_settings'])
                except ValueError:
                    continue
                if chapter_ids:
                    volumes.append({'id': card['card_id'], 'title': card['body'].get('title', card['card_id']),
                                    'chapter_ids': sorted(chapter_ids)})
        project['volumes'] = volumes
        return {'novel': novel, 'project': project, 'volumes': volumes, 'length_plan': length}

    def configure_length(self, ident: str, body: dict) -> dict:
        return change_length(self, ident, body)

    def project(self, novel: dict) -> dict:
        return self.studio.project_overview(novel['project_dir'], branch=novel.get('current_branch', 'main'))

    def _runtime(self) -> tuple[Any, Any]:
        if self.runtime_factory is not None:
            if not self.test_mode:
                raise ValueError('测试模型只允许用于隔离测试库')
            return self.runtime_factory()
        config = load_config(self.studio.config_path)
        provider = make_provider(config)
        for spec in config.stage_models.values():
            if spec.get('api_key_env'):
                import os
                if not os.environ.get(spec['api_key_env']):
                    raise ConfigRequired(f"Missing environment variable: {spec['api_key_env']}")
        return config, provider

    @staticmethod
    def _rejected_direction_job(store: Store, novel: dict) -> str | None:
        row = store.connection.execute('''SELECT id,request_json FROM novel_jobs
            WHERE id=? AND branch_id=? AND status='REJECTED' AND step_key=?''',
            (novel['job_id'], novel.get('current_branch', 'main'), DIRECTION_CONFIRM)).fetchone()
        if row is None:
            return None
        from nw.story_dependencies import legacy_ref

        brief = store.briefs()[-1]
        if json.loads(row['request_json'])['brief_ref'] == asdict(legacy_ref('brief', store.project().id, brief)):
            return row['id']
        return None

    def _new_job(self, novel: dict, body: dict, store: Store) -> str:
        overview = self.project(novel)
        branch = novel.get('current_branch', 'main')
        scenes = [row['id'] for row in overview['scenes']
                  if row['story_approved_on_branch'] and not row['accepted_draft_id']]
        from nw.novel_store import _manual_branch_draft
        manual_edits = [
            row['id'] for row in overview['scenes']
            if row['story_approved_on_branch'] and row['latest_draft_id']
            and row['latest_draft_id'] != row['accepted_draft_id']
            and _manual_branch_draft(store, store.get('draft', row['latest_draft_id']), branch)
        ]
        from nw.length_plan import approved_book_application
        wizard = novel['wizard']
        needs_tier_proposal = wizard.get('length_mode') == 'tiered' and not wizard.get('target_words')
        book_id, _ = approved_book_application(store, {'settings': overview['active_settings']},
                                                tiered_only=needs_tier_proposal)
        needs = self.branch_status(novel['id'])['needs_revalidation'] if branch != 'main' else []
        revalidate = [row['id'] for row in overview['scenes'] if row['id'] in needs and row['accepted_draft_id']]
        mode = body.get('mode') or ('revise' if (revalidate or manual_edits) else 'write' if scenes else 'design')
        hierarchy = mode == 'design' and wizard.get('planning_hierarchy', False)
        if hierarchy:
            scope, parent_id = design_route(store, branch, body.get('scope'), body.get('parent_id'))
        else:
            scope = body.get('scope') or ('chapter' if book_id else 'book')
            parent_id = book_id if mode == 'design' and scope != 'book' else None
        if mode == 'design' and branch == 'main' and any(scene['accepted_draft_id'] for scene in overview['scenes']):
            raise ValueError('已有正文后的追加设计需先建立候选分支并复核旧稿。'
                             '请打开“⋯ → 制作候选与主线 → 建立候选”，完成旧稿复核后再合并。未启动模型调用。')
        selected = body.get('scene_ids', revalidate[:1] if mode == 'revise' and revalidate else
                            manual_edits[:1] if mode == 'revise' and manual_edits else
                            scenes if mode in ('write', 'revise', 'continue') else [])
        if not isinstance(selected, list):
            raise ValueError('场景必须是 ID 列表')
        overrides = body.get('budget', {})
        if not isinstance(overrides, dict):
            raise ValueError('无效的调用预算')
        budget = self.budget({**novel['wizard'].get('call_budget', {}), **overrides})
        direction_review = mode == 'design' and scope == 'book' and wizard.get('direction_review', False)
        req = JobRequest(str(mode), branch_id=branch,
                         design_scope=str(scope) if mode == 'design' else 'chapter',
                         parent_id=parent_id,
                         scene_ids=selected, budget=budget,
                         governance_inputs=governance(novel['wizard'], library=self.library, store=store, scope=str(scope)) if mode == 'design' else {},
                         production_method_policy=novel['wizard'].get('production_methods',{}) if mode=='design' else {},
                         direction_review=direction_review,
                         direction_retry_of=self._rejected_direction_job(store, novel) if direction_review else None,
                         planning_hierarchy=hierarchy,
                         creative_workflow=(mode == 'design' and bool(wizard.get('creative_workflow', False))))
        job = start_job(store, req)
        self.db.update(novel['id'], job_id=job.id, status='designing' if mode == 'design' else 'writing')
        self.db.event(novel['id'], 'design' if mode == 'design' else 'write',
                      f'开始{scope if mode == "design" else "场景"}制作任务', {'job_id': job.id, 'mode': mode, 'scope': scope})
        return job.id

    def run(self, ident: str, body: dict, *, retry: bool = False, decision: dict | None = None) -> dict:
        worker = self._workers.get(ident)
        if worker and worker.is_alive():
            novel = self.db.get(ident)
            with self.open_store(novel) as store:
                current = show_job(store, novel['job_id']) if novel['job_id'] else None
            if current and current.status in ('DONE', 'CANCELLED', 'REJECTED', 'STALE'):
                worker.join(timeout=5)
        with self._lock:
            novel = self.db.get(ident)
            worker = self._workers.get(ident)
            if worker and worker.is_alive():
                if decision or body.get('mode'):
                    raise ValueError('当前任务仍在运行或保存检查点，请等待完成或先取消当前任务')
                return {'status': 'RUNNING', 'job_id': novel['job_id']}
            if novel['status'] == 'done':
                raise ValueError('已完稿书籍不能继续启动制作')
            try:
                config, provider = self._runtime()
            except ConfigRequired as exc:
                reason = f'CONFIG_REQUIRED: {exc}'
                self.db.update(ident, runtime_status='CONFIG_REQUIRED', status='paused', reason=reason)
                self.db.event(ident, 'configuration', reason, dedup=f'{ident}:config:{reason}')
                return {'status': 'CONFIG_REQUIRED', 'reason': reason, 'job_id': novel['job_id']}
            with self.open_store(novel) as store:
                if decision and decision.get('job_id'):
                    novel['job_id'] = decision['job_id']
                    request = json.loads(store.connection.execute('SELECT request_json FROM novel_jobs WHERE id=?',
                                                                  (novel['job_id'],)).fetchone()[0])
                    novel['current_branch'] = request['branch_id']
                    self.db.update(ident, job_id=novel['job_id'], current_branch=novel['current_branch'])
                if not decision and not body.get('mode'):
                    retire_unstarted_book(store, novel, self.budget(novel['wizard'].get('call_budget')))
                current = show_job(store, novel['job_id']) if novel['job_id'] else None
                if 'use_saved_context_budget' in body:
                    if (not retry or body['use_saved_context_budget'] is not True or not current
                            or current.status != 'BLOCKED' or not any(code in (current.reason or '')
                                for code in ('CONTEXT_TOO_LARGE', 'MODEL_CONTEXT_WINDOW'))):
                        raise ValueError('只有因上下文超限而受阻的当前任务可使用已保存的预算重试')
                    from nw.call_budget import raise_context_limits, read_budget
                    saved = self.budget(novel['wizard'].get('call_budget'))
                    actual = read_budget(store, current.id)
                    change = raise_context_limits(store, current.id,
                        context_char_limit=max(actual.context_char_limit, saved.context_char_limit),
                        output_limit=max(actual.output_limit, saved.output_limit))
                    if change['before'] != change['after']:
                        self.db.event(ident, 'context_budget', '按已保存的设置提高受阻任务预算',
                                      {'job_id':current.id, **change})
                if body.get('mode') and current and current.status not in ('DONE', 'CANCELLED', 'REJECTED', 'STALE'):
                    raise ValueError('请先处理或取消当前未完成任务，再启动指定的写作或重写操作')
                if current is None or current.status in ('DONE', 'CANCELLED', 'REJECTED', 'STALE'):
                    if decision:
                        raise ValueError('确认节点已经失效')
                    job_id = self._new_job(novel, body, store)
                else:
                    job_id = current.id
                    if current.status == 'WAITING' and not decision:
                        return {'status': 'WAITING', 'job_id': job_id, 'reason': '请先处理待确认节点'}
                    with store.connection:
                        store.connection.execute("UPDATE novel_jobs SET status='READY',reason=NULL WHERE id=? AND reason='AUTHOR_PAUSED'", (job_id,))
                actual_mode = json.loads(store.connection.execute('SELECT request_json FROM novel_jobs WHERE id=?', (job_id,)).fetchone()[0])['mode']
            self.db.update(ident, runtime_status='RUNNING', reason=None, status='designing' if
                           actual_mode == 'design' else 'writing')
            worker = threading.Thread(target=self._execute, args=(ident, job_id, config, provider, retry, decision), daemon=True)
            self._workers[ident] = worker
            worker.start()
            return {'status': 'RUNNING', 'job_id': job_id}

    def _execute(self, ident: str, job_id: str, config: Any, provider: Any, retry: bool, decision: dict | None) -> None:
        def choose(step: str, gate: dict) -> dict | None:
            if decision is None or decision['step'] != step or decision['token'] != gate['token']:
                return None
            return decision['choice']
        try:
            novel = self.db.get(ident)
            with self.open_store(novel) as store:
                result = resume_job(store, job_id, provider, config, choose, retry_failed=retry)
            status = 'PAUSED' if result.reason == 'AUTHOR_PAUSED' else result.status
            with self._lock:
                latest = self.db.get(ident)
                if not (latest['runtime_status'] == 'CANCELLED' and status != 'CANCELLED'):
                    self.db.update(ident, runtime_status=status, reason=result.reason,
                                   status='paused' if status in ('PAUSED', 'BLOCKED', 'CANCELLED', 'REJECTED', 'STALE') else
                                   ('writing' if result.status == 'DONE' else latest['status']))
                self.db.event(ident, 'status', result.reason or f'制作任务：{status}',
                              {'job_id': job_id, 'status': status, 'step': result.step})
            self.sync_history(ident)
            self.sync_adoptions(ident)
        except Exception as exc:
            with self._lock:
                self.db.update(ident, runtime_status='BLOCKED', status='paused', reason=str(exc))
                self.db.event(ident, 'error', str(exc), {'job_id': job_id})
        finally:
            self.changed.set()

    def pause(self, ident: str) -> dict:
        with self._lock:
            novel = self.db.get(ident)
            with self.open_store(novel) as store, store.connection:
                if novel['job_id']:
                    store.connection.execute("""UPDATE novel_jobs SET status='BLOCKED',reason='AUTHOR_PAUSED'
                        WHERE id=? AND status IN ('READY','RUNNING','WAITING','BLOCKED')""", (novel['job_id'],))
            active = bool(self._workers.get(ident) and self._workers[ident].is_alive())
            self.db.update(ident, status='paused', runtime_status='PAUSING' if active else 'PAUSED', reason='AUTHOR_PAUSED')
            self.db.event(ident, 'pause', '暂停请求已记录；当前模型调用完成后在下一检查点暂停。')
            return {'status': 'PAUSING' if active else 'PAUSED', 'job_id': novel['job_id']}

    def cancel(self, ident: str) -> dict:
        with self._lock:
            novel = self.db.get(ident)
            if novel['job_id']:
                with self.open_store(novel) as store:
                    cancel_job(store, novel['job_id'])
            self.db.update(ident, status='paused', runtime_status='CANCELLED', reason='CANCELLED')
            self.db.event(ident, 'cancel', '作者取消了当前任务；已有产物和调用记录已保留。')
            worker = self._workers.get(ident)
            result = {'status': 'CANCELLED', 'job_id': novel['job_id']}
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join(timeout=1)
        return result

    def accept_scene(self, ident: str, scene_id: str, body: dict) -> dict:
        with self._lock:
            worker = self._workers.get(ident)
            if worker and worker.is_alive():
                raise ValueError('当前制作任务仍在运行，请等待当前步骤结束后再单独接受本场')
            novel = self.db.get(ident)
            branch = str(body.get('branch') or novel.get('current_branch') or 'main')
            result = self.studio.accept_scene_delta(novel['project_dir'], {**body, 'scene_id': scene_id, 'branch': branch})
            try:
                from nw.craft_evolution import auto_extract_chapter1_calibration_anchor
                with self.open_store(novel) as store:
                    auto_extract_chapter1_calibration_anchor(store, branch=branch, force=False)
            except Exception:
                pass
            self.db.event(ident, 'confirmation', str(body.get('reason') or '客户端审核通过并接收本场正文与状态增量'),
                          {'scene_id': scene_id, 'branch': branch, **result})
            self.sync_history(ident)
            self.sync_adoptions(ident)
            self.changed.set()
            return result

    def decide(self, ident: str, gate_id: str, body: dict) -> dict:
        # The workflow can expose WAITING before its worker has finished
        # archiving call history. Let that checkpoint settle before resuming;
        # an early click must not race a second worker against the first one.
        worker = self._workers.get(ident)
        if worker and worker.is_alive():
            novel = self.db.get(ident)
            with self.open_store(novel) as store:
                job = show_job(store, novel['job_id']) if novel['job_id'] else None
                settling_gate = job.outputs.get('gate') if job and job.status == 'WAITING' else None
            if settling_gate and settling_gate.get('token') == gate_id:
                worker.join(timeout=5)
        with self._lock:
            gate = next((gate for gate in self.gates(ident)['gates'] if gate['id'] == gate_id), None)
            if gate is None or body.get('token') != gate['token']:
                raise ValueError('确认节点已变化，请刷新后重新确认')
            action, reason = body.get('action'), str(body.get('reason', '')).strip()
            if action not in gate['actions'] or not reason:
                raise ValueError('请选择当前节点允许的操作并填写确认理由')
            if gate['target'].get('kind')=='production_method_selection':
                self.validate_method_choice(gate['target'],body)
            elif gate['target'].get('kind') == DIRECTION_GATE:
                validate_choice(gate['target'], body)
            elif action == 'approve' and gate['target'].get('candidates'):
                roots = [row['root']['card_id'] for row in gate['target']['candidates']]
                if body.get('root') not in roots:
                    raise ValueError('请选择当前方案中的一个候选方案')
            choice = {key: value for key, value in body.items() if key != 'token'}
            result = self.run(ident, {}, decision={'token': gate['token'], 'step': gate['step'],
                                                  'job_id': gate['job_id'], 'choice': choice})
            if result['status'] == 'RUNNING':
                self.db.event(ident, 'confirmation', f'作者提交确认：{action} · {reason}',
                              {'gate_id': gate_id, 'choice': choice, 'token': gate['token']})
            return result

    def finish(self, ident: str) -> dict:
        with self._lock:
            novel = self.db.get(ident)
            if novel.get('current_branch', 'main') != 'main':
                raise ValueError('候选分支合并回主稿后才能标记全书完稿')
            project = self.project(novel)
            if self._workers.get(ident) and self._workers[ident].is_alive() or self.gates(ident)['gates']:
                raise ValueError('请先完成正在运行的任务和待确认节点')
            if not project['managed_story']:
                raise ValueError('旧项目需完成故事状态接管及独立审稿后才能标记完稿')
            active_scenes = [row for row in project['scenes'] if row['in_branch_manuscript']]
            if not active_scenes or any(not row['accepted_draft_id'] for row in active_scenes):
                raise ValueError('所有场景通过审稿并接受后才能标记完稿')
            populated_chapters = {scene['chapter_id'] for scene in active_scenes}
            with self.open_store(novel) as store:
                for scene in active_scenes:
                    if scene['latest_draft_id'] != scene['accepted_draft_id']:
                        raise ValueError('仍有较新草稿尚未接受，请先完成审稿')
                    review = self.review_for_draft(store, scene['id'], scene['accepted_draft_id'])
                    if not review or review['result'].get('recommendation') != 'pass':
                        raise ValueError('已接受稿还缺少对应版本的通过审稿记录')
                length = manuscript_length(store, novel['wizard'])
                expected = length['effective_chapter_count']
                if length.get('length_mode') != 'tiered' and expected and len(populated_chapters) < expected:
                    raise ValueError('存在空章或尚未达到立项设定的有效章节数')
                verify_finish_length(length)
                active_by_id = {scene['id']: scene for scene in active_scenes}
                for chapter in length['chapters']:
                    ending = chapter['scenes'][-1]
                    if ending.get('length_mode') == 'tiered':
                        scene = active_by_id[ending['scene_id']]
                        delta = read_delta(store, scene['accepted_delta_id'])
                        require_break_review(store, store.get('draft', delta.draft_id), delta.manifest_id)
                for fmt in ('txt', 'md'):
                    self._write_export(store, novel, project['chapters'], active_scenes, '全书', fmt)
            self.db.update(ident, status='done', runtime_status='DONE', finished_at=now(), reason=None)
            self.db.event(ident, 'completion', '作者确认全书完稿。')
            return {'status': 'DONE'}

    def style_reference(self, ident: str) -> dict:
        from nw.writing_craft import style_reference_overview
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            return style_reference_overview(store, branch=novel.get('current_branch', 'main'))

    def voice_spec(self, ident: str) -> dict:
        from nw.voice_specs import (
            VOICE_KNOBS,
            compile_book_voice_spec,
            load_book_voice_spec,
            recommend_voice_bases,
        )
        from nw.writing_craft import style_reference_overview
        novel = self.db.get(ident)
        genre_ids = novel['wizard'].get('genre_ids') or []
        available_fps = self.library.voice_fingerprints(types=genre_ids or None, status='approved')
        with self.open_store(novel) as store:
            spec = load_book_voice_spec(store)
            if spec is None:
                spec = novel['wizard'].get('voice_spec') or compile_book_voice_spec(
                    genre_ids,
                    tone_ids=novel['wizard'].get('tone_ids') or (),
                    style_ids=novel['wizard'].get('style_ids') or (),
                    fingerprints=available_fps[:1],
                    enabled=False,
                )
            style_ov = style_reference_overview(store, branch=novel.get('current_branch', 'main'))
        return {
            'novel_id': ident,
            'genre_ids': genre_ids,
            'voice_spec': spec,
            'voice_bases': recommend_voice_bases(genre_ids),
            'knobs': VOICE_KNOBS,
            'available_fingerprints': available_fps,
            'style_reference': style_ov,
        }

    def save_voice_spec(self, ident: str, body: dict) -> dict:
        from nw.voice_specs import VOICE_BASE_MAP, compile_book_voice_spec, save_book_voice_spec
        if not isinstance(body, dict):
            raise ValueError('语感规范配置必须是对象')
        with self._lock:
            novel = self.db.get(ident)
            if novel['status'] == 'done':
                raise ValueError('已完稿作品不能修改本书语感规范')
            genre_ids = novel['wizard'].get('genre_ids') or []
            base_id = str(body.get('base_voice_id') or '').strip()
            if base_id and base_id not in VOICE_BASE_MAP:
                raise ValueError(f'未知的语感规范基座: {base_id}')
            fp_ids = body.get('fingerprint_ids') or []
            if not isinstance(fp_ids, list) or len(fp_ids) > 5:
                raise ValueError('语感指纹最多叠加 5 项')
            fps = self.library.voice_fingerprints_by_ids(fp_ids) if fp_ids else []
            spec = compile_book_voice_spec(
                genre_ids,
                base_voice_id=base_id or None,
                knobs=body.get('knobs') if isinstance(body.get('knobs'), dict) else None,
                tone_ids=novel['wizard'].get('tone_ids') or (),
                style_ids=novel['wizard'].get('style_ids') or (),
                fingerprints=fps,
                custom_notes=str(body.get('custom_notes') or ''),
                enabled=bool(body.get('enabled', True)),
            )
            with self.open_store(novel) as store:
                save_book_voice_spec(store, spec)
            self.db.event(
                ident, 'voice_spec',
                f"更新本书语感规范：{spec['base_voice_name']}（{'启用' if spec['enabled'] else '暂停'}，叠加 {len(spec['fingerprints'])} 项语感指纹）",
                {'base_voice_id': spec['base_voice_id'], 'enabled': spec['enabled'],
                 'fingerprint_ids': spec['fingerprint_ids'], 'sha256': spec['sha256']},
            )
            return self.voice_spec(ident)

    def craft_specs(self, ident: str) -> dict:
        from nw.craft_specs import (
            compile_craft_spec,
            load_all_craft_specs,
            recommend_all_craft_setup,
        )
        from nw.craft_specs_base import CRAFT_DOMAINS
        from nw.writing_craft import style_reference_overview

        novel = self.db.get(ident)
        wiz = novel['wizard']
        genre_ids = wiz.get('genre_ids') or []
        target_words = wiz.get('target_words') if isinstance(wiz.get('target_words'), int) else None
        setup = recommend_all_craft_setup(genre_ids, target_words=target_words, library=self.library)
        with self.open_store(novel) as store:
            loaded = load_all_craft_specs(store, wizard=wiz)
            style_ov = style_reference_overview(store, branch=novel.get('current_branch', 'main'))
        specs: dict[str, dict] = {}
        for dom in CRAFT_DOMAINS:
            if isinstance(loaded.get(dom), dict):
                specs[dom] = loaded[dom]
            else:
                fps = setup[dom]['available_fingerprints'][:1]
                specs[dom] = compile_craft_spec(
                    dom, genre_ids, fingerprints=fps, enabled=False, target_words=target_words, wizard=wiz,
                )
        return {
            'novel_id': ident,
            'genre_ids': genre_ids,
            'target_words': target_words,
            'domains': list(CRAFT_DOMAINS),
            'specs': specs,
            'setup': setup,
            'style_reference': style_ov,
        }

    def save_craft_spec(self, ident: str, domain: str, body: dict) -> dict:
        from nw.craft_specs import compile_craft_spec, domain_base_map, save_craft_spec as _save_spec
        from nw.craft_specs_base import CRAFT_DOMAINS, DOMAIN_META

        if domain not in CRAFT_DOMAINS:
            raise ValueError(f'未知的基座域: {domain}')
        if not isinstance(body, dict):
            raise ValueError('基座配置必须是对象')
        with self._lock:
            novel = self.db.get(ident)
            if novel['status'] == 'done':
                raise ValueError('已完稿作品不能修改本书基座规范')
            wiz = novel['wizard']
            genre_ids = wiz.get('genre_ids') or []
            bmap = domain_base_map(domain)
            base_id = str(body.get('base_id') or body.get('base_voice_id') or '').strip()
            if base_id and base_id not in bmap:
                raise ValueError(f'未知的{DOMAIN_META[domain]["name"]}: {base_id}')
            fp_ids = body.get('fingerprint_ids') or []
            if not isinstance(fp_ids, list) or len(fp_ids) > 5:
                raise ValueError('指纹最多叠加 5 项')
            fps = self.library.craft_fingerprints_by_ids(fp_ids, domain=domain) if fp_ids else []
            target_words = wiz.get('target_words') if isinstance(wiz.get('target_words'), int) else None
            with self.open_store(novel) as store:
                from nw.craft_specs import load_craft_spec
                prior_spec = load_craft_spec(store, domain)
                spec = compile_craft_spec(
                    domain,
                    genre_ids,
                    base_id=base_id or None,
                    knobs=body.get('knobs') if isinstance(body.get('knobs'), dict) else None,
                    fingerprints=fps,
                    custom_notes=str(body.get('custom_notes') or ''),
                    enabled=bool(body.get('enabled', True)),
                    target_words=target_words,
                    wizard=wiz,
                )
                # Preserve living evolution layer (learned author contrasts & promoted redlines) across re-saves!
                if isinstance(prior_spec, dict):
                    if prior_spec.get('learned_contrasts'):
                        spec['learned_contrasts'] = list(prior_spec['learned_contrasts'])
                    if prior_spec.get('learned_redlines'):
                        spec['learned_redlines'] = list(prior_spec['learned_redlines'])
                        rl_key = 'drift_redlines' if domain == 'voice' else 'anti_drift_redlines'
                        cur_rls = list(spec.get(rl_key) or [])
                        for lr in prior_spec['learned_redlines']:
                            rtxt = lr.get('rule') if isinstance(lr, dict) else ''
                            if rtxt and rtxt not in cur_rls:
                                cur_rls.append(rtxt)
                        spec[rl_key] = cur_rls[:14]
                _save_spec(store, domain, spec)
            spec_name = spec.get('base_name') or spec.get('base_voice_name') or base_id
            self.db.event(
                ident, f'craft_spec:{domain}',
                f"更新{DOMAIN_META[domain]['name']}：{spec_name}（{'启用' if spec['enabled'] else '暂停'}，叠加 {len(spec.get('fingerprints') or ())} 项指纹）",
                {'domain': domain, 'base_id': spec.get('base_id') or spec.get('base_voice_id'),
                 'enabled': spec['enabled'], 'fingerprint_ids': spec.get('fingerprint_ids', []), 'sha256': spec.get('sha256', '')},
            )
            return self.craft_specs(ident)

    def save_style_reference(self, ident: str, body: dict) -> dict:
        from nw.writing_craft import save_style_reference, style_reference_overview
        with self._lock:
            novel = self.db.get(ident)
            if novel['status'] == 'done':
                raise ValueError('已完稿作品不能修改写前语感参照')
            with self.open_store(novel) as store:
                saved = save_style_reference(store, body)
                overview = style_reference_overview(store, branch=novel.get('current_branch', 'main'))
            mode_label = {'off': '关闭', 'author_sample': '作者参照样段', 'auto_book_prose': '本书已采用正文语感'}.get(
                saved['mode'], saved['mode'])
            self.db.event(
                ident, 'style_reference',
                f"更新写前语感参照：{mode_label}" + (f"（{saved['title']}）" if saved.get('title') else ''),
                {'mode': saved['mode'], 'enabled': saved['enabled'], 'title': saved.get('title', ''),
                 'excerpt_chars': len(saved.get('excerpt') or '')},
            )
            return overview

    def cold_reads(self, ident: str, scene: str = '') -> dict:
        from nw.cold_read import cold_read_summary, list_cold_reads
        novel = self.db.get(ident)
        project = self.project(novel)
        branch = novel.get('current_branch', 'main')
        scene_row = next((r for r in project['scenes'] if r['id'] == scene), None) if scene else None
        draft_id = scene_row['latest_draft_id'] if scene_row else None
        chapter_index = scene_row.get('chapter_index') if scene_row else None
        with self.open_store(novel) as store:
            reports = list_cold_reads(store, scene_id=scene, limit=30)
            summary = cold_read_summary(store, scene_id=scene, draft_id=draft_id, chapter_index=chapter_index)
        chapters = [
            {'index': c['index'], 'title': c['title']}
            for c in sorted(project.get('chapters') or (), key=lambda r: int(r.get('index') or 0))
        ]
        return {
            'novel_id': ident,
            'branch_id': branch,
            'scene_id': scene or None,
            'draft_id': draft_id,
            'summary': summary,
            'reports': reports,
            'chapters': chapters,
        }

    def run_cold_read(self, ident: str, body: dict) -> dict:
        from nw.cold_read import cold_read_summary, run_cold_read
        novel = self.db.get(ident)
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        scope = str(body.get('scope') or 'scene').strip()
        scene_id = str(body.get('scene_id') or '').strip()
        draft_id = str(body.get('draft_id') or '').strip()
        chapter_index = int(body['chapter_index']) if body.get('chapter_index') not in (None, '') else None
        chapter_start = int(body['chapter_start']) if body.get('chapter_start') not in (None, '') else None
        chapter_end = int(body['chapter_end']) if body.get('chapter_end') not in (None, '') else None
        include_prior = bool(body.get('include_prior_chapters', True))
        custom_focus = str(body.get('custom_focus') or '').strip()
        config, provider = self._runtime()
        with self.open_store(novel) as store:
            report = run_cold_read(
                store, config, provider,
                scope=scope,
                scene_id=scene_id,
                draft_id=draft_id,
                chapter_index=chapter_index,
                chapter_start=chapter_start,
                chapter_end=chapter_end,
                branch=branch,
                include_prior_chapters=include_prior,
                custom_focus=custom_focus,
            )
            summary = cold_read_summary(
                store,
                scene_id=report.get('scene_id', ''),
                draft_id=report.get('draft_id'),
                chapter_index=(report.get('chapter_indices') or [None])[0],
            )
        want = (report.get('parsed') or {}).get('keep_reading', {}).get('want_next', 'unknown')
        self.db.event(
            ident, 'cold_read',
            f"完成陌生读者盲态冷读：{report.get('label', scope)}（追读意愿：{want}）",
            {'report_id': report['id'], 'scope': scope, 'label': report.get('label'), 'want_next': want,
             'model': report.get('model'), 'isolated_input_keys': report.get('isolated_input_keys')},
        )
        return {'report': report, 'summary': summary}

    # ── P0/P1/P2 Fusion Cockpit APIs (Serial Health, Overrides, Evolution, Doctor, Briefing) ──

    def serial_health(self, ident: str) -> dict:
        from nw.context.memory_orchestrator import list_volume_summaries
        from nw.craft_specs import load_all_craft_specs
        from nw.serial_health import build_foreshadowing_opportunity_brief, build_serial_health_board
        novel = self.db.get(ident)
        branch = novel.get('current_branch', 'main')
        wiz = novel['wizard']
        tw = wiz.get('target_words') if isinstance(wiz.get('target_words'), int) else None
        with self.open_store(novel) as store:
            specs = load_all_craft_specs(store, wizard=wiz)
            board = build_serial_health_board(store, branch=branch, plot_spec=specs.get('plot_pacing'), target_words=tw)
            foreshadow = build_foreshadowing_opportunity_brief(store, branch=branch)
            vol_summaries = list_volume_summaries(store, branch_id=branch)
        return {
            'novel_id': ident,
            'branch_id': branch,
            'board': board,
            'foreshadowing_opportunities': foreshadow,
            'volume_summaries': vol_summaries,
        }

    def save_chapter_telemetry(self, ident: str, body: dict) -> dict:
        from nw.serial_health import record_chapter_telemetry
        novel = self.db.get(ident)
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        ch_idx = int(body.get('chapter_index') or 0)
        if ch_idx < 1:
            raise ValueError('请提供有效的章节序号')
        with self.open_store(novel) as store:
            saved = record_chapter_telemetry(
                store,
                branch_id=branch,
                chapter_index=ch_idx,
                dominant_strand=str(body.get('dominant_strand') or 'quest'),
                hook_type=str(body.get('hook_type') or ''),
                hook_strength=str(body.get('hook_strength') or 'medium'),
                micro_payoff_count=int(body.get('micro_payoff_count') or 1),
                promise_touched=bool(body.get('promise_touched', False)),
            )
        return {'saved': saved, 'health': self.serial_health(ident)}

    def save_volume_summary_record(self, ident: str, body: dict) -> dict:
        from nw.context.memory_orchestrator import draft_volume_summary_from_chapters, save_volume_summary
        novel = self.db.get(ident)
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        vol_idx = int(body.get('volume_index') or 1)
        title = str(body.get('title') or f'第{vol_idx}卷')
        ch_start = int(body.get('chapter_start') or 1)
        ch_end = int(body.get('chapter_end') or ch_start)
        with self.open_store(novel) as store:
            if body.get('mode') == 'draft':
                return draft_volume_summary_from_chapters(
                    store, branch_id=branch, volume_index=vol_idx, title=title,
                    chapter_start=ch_start, chapter_end=ch_end,
                )
            saved = save_volume_summary(
                store,
                branch_id=branch,
                volume_index=vol_idx,
                title=title,
                chapter_start=ch_start,
                chapter_end=ch_end,
                summary_text=str(body.get('summary_text') or ''),
                open_promises=body.get('open_promises') if isinstance(body.get('open_promises'), list) else [],
                relation_shifts=body.get('relation_shifts') if isinstance(body.get('relation_shifts'), list) else [],
            )
        self.db.event(ident, 'volume_summary', f'已保存卷级摘要：第{vol_idx}卷《{title}》', {'volume_index': vol_idx})
        return {'saved': saved, 'health': self.serial_health(ident)}

    def overrides(self, ident: str, scene: str = '', status: str = 'active') -> dict:
        from nw.override_ledger import HARD_NON_OVERRIDABLE_CODES, OVERRIDE_RATIONALE_TAGS, list_overrides
        novel = self.db.get(ident)
        branch = novel.get('current_branch', 'main')
        with self.open_store(novel) as store:
            rows = list_overrides(store, branch_id=branch, scene_id=scene or None, status=status or None)
        return {
            'novel_id': ident,
            'branch_id': branch,
            'overrides': rows,
            'rationale_tags': OVERRIDE_RATIONALE_TAGS,
            'hard_non_overridable_codes': sorted(HARD_NON_OVERRIDABLE_CODES),
        }

    def record_soft_override(self, ident: str, body: dict) -> dict:
        from nw.override_ledger import record_override
        novel = self.db.get(ident)
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        with self.open_store(novel) as store:
            rec = record_override(
                store,
                branch_id=branch,
                constraint_kind=str(body.get('constraint_kind') or 'soft_gate'),
                constraint_code=str(body.get('constraint_code') or ''),
                reason_tag=str(body.get('reason_tag') or 'EDITORIAL_INTENT'),
                reason_text=str(body.get('reason_text') or ''),
                scene_id=str(body.get('scene_id') or '') or None,
                chapter_index=int(body['chapter_index']) if body.get('chapter_index') not in (None, '') else None,
                draft_id=str(body.get('draft_id') or '') or None,
                details=body.get('details') if isinstance(body.get('details'), dict) else None,
            )
        self.db.event(
            ident, 'override',
            f'登记软约束显式豁免：{rec["constraint_code"]}（{rec["reason_label"]}）',
            rec,
        )
        return {'override': rec}

    def revoke_soft_override(self, ident: str, override_id: str) -> dict:
        from nw.override_ledger import revoke_override
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            return revoke_override(store, override_id)

    def craft_evolution(self, ident: str, scene: str = '') -> dict:
        from nw.craft_evolution import (
            check_style_drift,
            detect_author_edit_candidates,
            list_promotion_proposals,
        )
        from nw.craft_specs import load_all_craft_specs
        from nw.craft_specs_base import CRAFT_DOMAINS
        novel = self.db.get(ident)
        branch = novel.get('current_branch', 'main')
        with self.open_store(novel) as store:
            specs = load_all_craft_specs(store, wizard=novel['wizard'])
            drift = check_style_drift(store, branch=branch)
            proposals = list_promotion_proposals(store, branch=branch, min_count=3)
            pending_contrasts: list[dict] = []
            if scene:
                pending_contrasts = detect_author_edit_candidates(store, scene_id=scene, branch=branch)
            else:
                for sc in store.list('scene'):
                    cands = detect_author_edit_candidates(store, scene_id=sc.id, branch=branch, max_candidates=1)
                    pending_contrasts.extend(cands)
                    if len(pending_contrasts) >= 4:
                        break
        voice_spec = specs.get('voice') or {}
        learned_redlines = {
            dom: list((specs.get(dom) or {}).get('learned_redlines') or ())
            for dom in CRAFT_DOMAINS
        }
        return {
            'novel_id': ident,
            'branch_id': branch,
            'style_drift': drift,
            'promotion_proposals': proposals,
            'learned_contrasts': list(voice_spec.get('learned_contrasts') or ()),
            'learned_redlines_by_domain': learned_redlines,
            'pending_author_edit_contrasts': pending_contrasts[:4],
        }

    def accept_evolution_contrast(self, ident: str, body: dict) -> dict:
        from nw.craft_evolution import accept_learned_contrast
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            res = accept_learned_contrast(store, body)
        self.db.event(ident, 'craft_evolution', f'收录作者亲改语感微对照：{res["entry"]["label"]}', res['entry'])
        return {'entry': res['entry'], 'learned_count': res['learned_count']}

    def remove_evolution_contrast(self, ident: str, body: dict) -> dict:
        from nw.craft_evolution import remove_learned_contrast
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            return remove_learned_contrast(store, str(body.get('contrast_id') or ''))

    def promote_evolution_rule(self, ident: str, body: dict) -> dict:
        from nw.craft_evolution import promote_pattern_to_craft_spec
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            res = promote_pattern_to_craft_spec(
                store,
                target_domain=str(body.get('target_domain') or 'voice'),
                redline_text=str(body.get('redline_text') or body.get('proposed_redline') or ''),
                override_ids=body.get('override_ids') if isinstance(body.get('override_ids'), list) else [],
                chapters=body.get('chapters') if isinstance(body.get('chapters'), list) else [],
                pattern_key=str(body.get('pattern_key') or ''),
            )
        self.db.event(
            ident, 'craft_evolution',
            f'升格活体工艺红线至{res["domain_name"]}：{res["entry"]["rule"][:60]}',
            res,
        )
        return res

    def pin_evolution_baseline(self, ident: str, body: dict) -> dict:
        from nw.craft_evolution import pin_style_baseline
        novel = self.db.get(ident)
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        start_ch = int(body.get('start_chapter') or 1)
        end_ch = int(body.get('end_chapter') or max(start_ch, 10))
        with self.open_store(novel) as store:
            res = pin_style_baseline(store, branch=branch, start_chapter=start_ch, end_chapter=end_ch)
        self.db.event(ident, 'craft_evolution', f'锁定文体基线：第 {res["range_start"]}–{res["range_end"]} 章', {'id': res['id']})
        return res

    def doctor(self, ident: str, *, repair_cache: bool = False) -> dict:
        from nw.project_doctor import run_project_doctor
        novel = self.db.get(ident)
        branch = novel.get('current_branch', 'main')
        with self.open_store(novel) as store:
            return run_project_doctor(store, branch=branch, wizard=novel['wizard'], repair_cache=repair_cache)

    def scene_briefing(self, ident: str, scene: str) -> dict:
        from nw.context.briefing_compiler import compile_writer_briefing
        from nw.context.story import build_story_context, scene_scope
        novel = self.db.get(ident)
        branch = novel.get('current_branch', 'main')
        if not scene:
            raise ValueError('需要指定 scene 参数以预览写前自然语境任务书')
        with self.open_store(novel) as store:
            scope = scene_scope(store, scene, branch)
            work = build_story_context(store, scene, scope, self.budget(novel['wizard'].get('call_budget')).context_char_limit)
            briefing = compile_writer_briefing(work.package)
        return {
            'scene_id': scene,
            'branch_id': branch,
            'briefing_text': briefing,
            'briefing_chars': len(briefing),
            'package_items_count': len(work.package.get('items') or ()),
            'omitted_optional_groups': list(work.omitted_optional_groups),
        }

    # ── InkOS-Fused Cockpit APIs: Multi-Branch Forecast, Fact-Frozen Deslop, Manuscript Import ──

    def forecasts(self, ident: str) -> dict:
        from nw.narrative_forecast import active_adopted_forecast_constraint, list_narrative_forecasts
        novel = self.db.get(ident)
        branch = novel.get('current_branch', 'main')
        with self.open_store(novel) as store:
            items = list_narrative_forecasts(store, branch_id=branch)
            active_c = active_adopted_forecast_constraint(store, branch_id=branch)
        return {
            'novel_id': ident,
            'branch_id': branch,
            'forecasts': items,
            'active_constraint': active_c,
        }

    def create_forecast(self, ident: str, body: dict) -> dict:
        from nw.narrative_forecast import create_narrative_forecast
        novel = self.db.get(ident)
        branch = str(body.get('branch') or novel.get('current_branch') or 'main')
        divergence = str(body.get('divergence') or '').strip()
        branch_count = int(body.get('branch_count') or 3)
        horizon = int(body.get('horizon') or 5)
        offline_preview = bool(body.get('offline_preview', False))
        tw = novel['wizard'].get('target_words') if isinstance(novel['wizard'].get('target_words'), int) else None
        provider, model, params = None, '', {}
        if not offline_preview:
            config, provider = self._runtime()
            model, params = config.model, dict(config.params)
        with self.open_store(novel) as store:
            fc = create_narrative_forecast(
                store,
                divergence=divergence,
                branch_id=branch,
                branch_count=branch_count,
                horizon=horizon,
                provider=provider,
                model=model,
                params=params,
                offline_preview=offline_preview,
                target_words=tw,
            )
        self.db.event(ident, 'forecast', f'完成剧情沙盘推演（{len(fc["branches"])} 条 × {fc["horizon"]} 章）：{divergence[:48]}', {'forecast_id': fc['id']})
        return {'forecast': fc}

    def select_forecast(self, ident: str, forecast_id: str, body: dict) -> dict:
        from nw.narrative_forecast import select_forecast_branch
        novel = self.db.get(ident)
        choice_id = str(body.get('branch_choice_id') or body.get('branch_id') or '').strip()
        mode = str(body.get('mode') or 'adopt_constraint').strip()
        new_branch = str(body.get('new_branch_id') or '').strip()
        with self.open_store(novel) as store:
            fc = select_forecast_branch(
                store, forecast_id, choice_id, mode=mode, new_branch_id=new_branch,
            )
        msg = (
            f'已孵化沙盘真实候选分支：{fc["forked_branch_id"]}'
            if mode == 'fork_branch' else f'已采纳沙盘分支「{choice_id}」作为下步策划约束'
        )
        self.db.event(ident, 'forecast', msg, {'forecast_id': fc['id'], 'mode': mode, 'branch_choice_id': choice_id})
        return {'forecast': fc}

    def analyze_deslop(self, ident: str, scene: str = '', draft_id: str = '') -> dict:
        from nw.semantic_deslop import analyze_deslop_targets
        novel = self.db.get(ident)
        project = self.project(novel)
        scene_row = next((r for r in project['scenes'] if r['id'] == scene), None) if scene else None
        target_draft_id = draft_id or (scene_row['latest_draft_id'] if scene_row else '')
        if not target_draft_id:
            return {'scene_id': scene, 'draft_id': None, 'analysis': analyze_deslop_targets('')}
        with self.open_store(novel) as store:
            draft = store.get('draft', target_draft_id)
            analysis = analyze_deslop_targets(draft.text)
        return {'scene_id': draft.scene_id, 'draft_id': draft.id, 'analysis': analysis}

    def run_deslop(self, ident: str, body: dict) -> dict:
        from nw.llm.base import GenResult
        from nw.models import Run
        from nw.semantic_deslop import run_semantic_deslop
        from nw.store import now
        from nw.task_models import canonical

        novel = self.db.get(ident)
        scene_id = str(body.get('scene_id') or '').strip()
        draft_id = str(body.get('draft_id') or '').strip()
        apply_flag = bool(body.get('apply', False))
        project = self.project(novel)
        scene_row = next((r for r in project['scenes'] if r['id'] == scene_id), None) if scene_id else None
        target_draft_id = draft_id or (scene_row['latest_draft_id'] if scene_row else '')
        if not target_draft_id:
            raise ValueError('当前场景暂无可润色的草稿')

        if apply_flag and isinstance(body.get('polished_text'), str) and body['polished_text'].strip():
            polished = body['polished_text']
            with self.open_store(novel) as store:
                src = store.get('draft', target_draft_id)
                rid = f'deslop-{src.id[:8]}-{now().replace(":", "").replace("-", "")[:14]}'
                store.add_run(Run(
                    rid, src.scene_id, 'revise', 'author', 'semantic-deslop', '{}',
                    canonical({'source': 'studio_manual_author', 'deslop_from': src.id}),
                    canonical({'deslop': True}), '', 'error', '{}', now(), '',
                ))
                _, new_draft = store.finish_run(rid, GenResult(
                    text=polished, finish_reason='complete', usage={'source': 'semantic_deslop'},
                    request_id=rid, raw={'deslop_from': src.id},
                ))
            self.db.event(ident, 'deslop', f'已应用事实冻结去 AI 味润色至草稿 v{new_draft.version}', {'draft_id': new_draft.id})
            return {'applied': True, 'draft_id': new_draft.id, 'version': new_draft.version}

        config, provider = self._runtime()
        targets = body.get('target_paragraphs') if isinstance(body.get('target_paragraphs'), list) else None
        extra = str(body.get('extra_instruction') or '')
        with self.open_store(novel) as store:
            src = store.get('draft', target_draft_id)
            res = run_semantic_deslop(
                store, src.text, provider, config.model, dict(config.params),
                target_paragraphs=targets, extra_instruction=extra,
            )
        return {'scene_id': src.scene_id, 'draft_id': src.id, **res}

    def manuscript_imports(self, ident: str) -> dict:
        from nw.manuscript_import import list_manuscript_imports
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            return {'novel_id': ident, 'imports': list_manuscript_imports(store)}

    def analyze_manuscript_import(self, ident: str, body: dict) -> dict:
        from nw.manuscript_import import analyze_manuscript, save_manuscript_import
        novel = self.db.get(ident)
        raw_text = str(body.get('text') or '')
        title = str(body.get('title') or novel.get('title') or '')
        report = analyze_manuscript(raw_text, title=title)
        with self.open_store(novel) as store:
            saved = save_manuscript_import(store, report)
        self.db.event(ident, 'manuscript_import', f'分析导入书稿：{saved["chapter_count"]} 章（冲突 {len(saved["conflicts"])} 处）', {'import_id': saved['id']})
        return {'import': saved}

    def apply_manuscript_import(self, ident: str, import_id: str, body: dict) -> dict:
        from nw.manuscript_import import apply_manuscript_import_to_baseline
        novel = self.db.get(ident)
        resolutions = body.get('resolved_conflicts') if isinstance(body.get('resolved_conflicts'), dict) else {}
        with self.open_store(novel) as store:
            res = apply_manuscript_import_to_baseline(store, import_id, resolved_conflicts=resolutions)
        self.db.event(ident, 'manuscript_import', f'已将 {res["chapters_imported"]} 章导入书稿写入正史基线', res)
        return res

    def author_memory(self, ident: str, workflow_stage: str = '') -> dict:
        from nw.author_memory import list_book_preferences, list_global_preferences, query_merged_author_memory
        from nw.voice_specs import load_book_style_whitelist
        novel = self.db.get(ident)
        genres = list(novel.get('wizard', {}).get('genres') or ())
        with self.open_store(novel) as store, self.library.connect() as lib_conn:
            merged = query_merged_author_memory(
                lib_conn, store, genre_ids=genres or None, workflow_stage=workflow_stage or 'writing',
            )
            global_items = list_global_preferences(lib_conn, status='active')
            book_items = list_book_preferences(store, status='active')
            whitelist = load_book_style_whitelist(store)
        return {
            'novel_id': ident,
            'merged': merged,
            'global_items': global_items,
            'book_items': book_items,
            'style_whitelist': whitelist,
        }

    def save_author_memory(self, ident: str, body: dict) -> dict:
        from nw.author_memory import (
            forget_preference,
            promote_book_preference_to_global,
            remember_book_preference,
            remember_global_preference,
            replace_preference,
        )
        novel = self.db.get(ident)
        action = str(body.get('action') or 'remember').strip().lower()
        level = str(body.get('level') or 'book').strip().lower()

        with self.open_store(novel) as store, self.library.connect() as lib_conn:
            if action == 'forget':
                res = forget_preference(str(body.get('id') or ''), library_conn=lib_conn, store=store)
                self.db.event(ident, 'author_memory', f'遗忘作者偏好 {res["id"]}', res)
                return res
            if action == 'replace':
                res = replace_preference(
                    str(body.get('id') or ''),
                    new_assertion=str(body.get('assertion') or body.get('new_assertion') or ''),
                    importance=(int(body['importance']) if body.get('importance') is not None else None),
                    kind=(str(body['kind']) if body.get('kind') else None),
                    library_conn=lib_conn,
                    store=store,
                )
                self.db.event(ident, 'author_memory', f'更新作者偏好 {res["replaced_id"]} → {res["new_item"]["id"]}', res)
                return res
            if action == 'promote':
                res = promote_book_preference_to_global(
                    store, lib_conn, str(body.get('id') or ''),
                    scope=str(body.get('scope') or 'global'),
                    genre_tags=body.get('genre_tags') if isinstance(body.get('genre_tags'), list) else None,
                    workflow_stage=str(body.get('workflow_stage') or ''),
                )
                self.db.event(ident, 'author_memory', f'将本书偏好 {res["promoted_from"]} 升格为跨书全局偏好 {res["global_item"]["id"]}', res)
                return res

            if level == 'global':
                item = remember_global_preference(
                    lib_conn,
                    assertion=str(body.get('assertion') or ''),
                    kind=str(body.get('kind') or 'prose'),
                    scope=str(body.get('scope') or 'global'),
                    genre_tags=body.get('genre_tags') if isinstance(body.get('genre_tags'), list) else None,
                    workflow_stage=str(body.get('workflow_stage') or ''),
                    importance=int(body.get('importance') or 3),
                )
                self.db.event(ident, 'author_memory', f'新增跨书全局偏好 {item["id"]}', {'id': item['id']})
                return {'item': item}
            item = remember_book_preference(
                store,
                assertion=str(body.get('assertion') or ''),
                kind=str(body.get('kind') or 'prose'),
                importance=int(body.get('importance') or 3),
                overrides_global_id=str(body.get('overrides_global_id') or ''),
            )
            self.db.event(ident, 'author_memory', f'新增本书偏好 {item["id"]}', {'id': item['id']})
            return {'item': item}

    def save_style_whitelist(self, ident: str, body: dict) -> dict:
        from nw.voice_specs import save_book_style_whitelist
        novel = self.db.get(ident)
        raw_items = body.get('items')
        if isinstance(raw_items, str):
            items = [ln.strip() for ln in raw_items.splitlines() if ln.strip()]
        elif isinstance(raw_items, list):
            items = [str(x).strip() for x in raw_items if str(x).strip()]
        else:
            items = []
        with self.open_store(novel) as store:
            saved = save_book_style_whitelist(store, items)
        self.db.event(ident, 'style_whitelist', f'更新本书样式白名单（{len(saved)} 条）', {'count': len(saved)})
        return {'novel_id': ident, 'style_whitelist': saved}

    def publish_preflight(self, ident: str, body: dict | None = None) -> dict:
        from nw.publish_preflight import PLATFORM_SPECS, sweep_book_for_publish, validate_publish_package
        novel = self.db.get(ident)
        payload = body if isinstance(body, dict) else {}
        platform = str(payload.get('platform') or 'fanqie').strip().lower()
        quote_mode = str(payload.get('quote_mode') or 'keep').strip().lower()
        branch = str(payload.get('branch') or novel.get('current_branch') or 'main')
        title = str(payload.get('title') if payload.get('title') is not None else (novel.get('title') or ''))
        wizard = novel.get('wizard') or {}
        synopsis = str(payload.get('synopsis') if payload.get('synopsis') is not None else (wizard.get('summary') or wizard.get('idea') or ''))
        tags = payload.get('tags')
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace('，', ',').split(',') if t.strip()]
        elif not isinstance(tags, list):
            tags = list(wizard.get('genres') or ())[:4]
        category = str(payload.get('category') or (wizard.get('genres')[0] if wizard.get('genres') else ''))

        metadata_check = validate_publish_package(
            platform, title=title, synopsis=synopsis, tags=tags, category=category,
        )
        with self.open_store(novel) as store:
            sweep = sweep_book_for_publish(store, branch=branch, platform=platform, quote_mode=quote_mode)
        return {
            'novel_id': ident,
            'platforms': [{'id': k, 'name': v['name'], 'signing_notes': v['signing_notes']} for k, v in PLATFORM_SPECS.items()],
            'metadata_check': metadata_check,
            'chapter_sweep': sweep,
            'overall_passed': bool(metadata_check['passed'] and sweep['passed']),
        }

    def run_ab_blind_judge(self, ident: str, body: dict) -> dict:
        from nw.ab_judge import run_position_swapped_ab_judge
        novel = self.db.get(ident)
        scene_id = str(body.get('scene_id') or '').strip()
        draft_a_id = str(body.get('draft_a_id') or '').strip()
        draft_b_id = str(body.get('draft_b_id') or '').strip()
        draft_a_text = str(body.get('draft_a_text') or '')
        draft_b_text = str(body.get('draft_b_text') or '')
        label_a = str(body.get('label_a') or '稿件 A')
        label_b = str(body.get('label_b') or '稿件 B')
        outline_text = str(body.get('outline_text') or '')
        criteria = str(body.get('criteria') or '')

        with self.open_store(novel) as store:
            if scene_id and (not draft_a_text or not draft_b_text):
                drafts = store.drafts(scene_id)
                by_id = {d.id: d for d in drafts}
                if draft_a_id in by_id:
                    draft_a_text = by_id[draft_a_id].text
                    label_a = f'草稿 v{by_id[draft_a_id].version}'
                elif len(drafts) >= 2 and not draft_a_text:
                    draft_a_text = drafts[-2].text
                    label_a = f'草稿 v{drafts[-2].version}'
                if draft_b_id in by_id:
                    draft_b_text = by_id[draft_b_id].text
                    label_b = f'草稿 v{by_id[draft_b_id].version}'
                elif len(drafts) >= 1 and not draft_b_text:
                    draft_b_text = drafts[-1].text
                    label_b = f'草稿 v{drafts[-1].version}'

        config, provider = self._runtime()
        result = run_position_swapped_ab_judge(
            draft_a_text, draft_b_text,
            provider=provider, model=config.model, params=dict(config.params),
            outline_text=outline_text, criteria=criteria,
            label_a=label_a, label_b=label_b,
        )
        self.db.event(ident, 'ab_judge', f'完成双向换位双盲评审：{result["winner_label"]}', {'scene_id': scene_id, 'winner': result['winner']})
        return result

    # ---------- Fusion M-Q: Whole-Book Mechanical Audit, Fact Ledger, Calibration Anchor & Wizard Preferences ----------

    def book_audit(self, ident: str, *, min_words: int = 1800) -> dict:
        from nw.book_audit import run_whole_book_audit
        from nw.craft_evolution import load_book_calibration_anchor
        novel = self.db.get(ident)
        branch = str(novel.get('current_branch') or 'main')
        with self.open_store(novel) as store:
            report = run_whole_book_audit(store, branch=branch, min_chapter_words=max(0, int(min_words)))
            anchor = load_book_calibration_anchor(store)
        return {'novel_id': ident, 'calibration_anchor': anchor, **report}

    def fact_ledger(self, ident: str, *, category: str = '', status: str = '') -> dict:
        from nw.fact_ledger import CATEGORY_LABELS, list_fact_entries
        novel = self.db.get(ident)
        branch = str(novel.get('current_branch') or 'main')
        with self.open_store(novel) as store:
            entries = list_fact_entries(store, branch_id=branch, category=category, status=status)
        return {'novel_id': ident, 'branch_id': branch, 'categories': CATEGORY_LABELS, 'entries': entries}

    def save_fact_ledger_entry(self, ident: str, body: dict) -> dict:
        from nw.fact_ledger import upsert_fact_entry
        novel = self.db.get(ident)
        branch = str(body.get('branch_id') or novel.get('current_branch') or 'main')
        with self.open_store(novel) as store:
            saved = upsert_fact_entry(
                store,
                entry_id=str(body.get('id') or ''),
                name=str(body.get('name') or ''),
                category=str(body.get('category') or 'term'),
                first_chapter=int(body.get('first_chapter') or 1),
                reader_known=str(body.get('reader_known') or ''),
                full_truth=str(body.get('full_truth') or ''),
                planned_reveal_chapter=(int(body['planned_reveal_chapter']) if body.get('planned_reveal_chapter') not in (None, '') else None),
                status=str(body.get('status') or 'active'),
                branch_id=branch,
                source_scene_id=str(body.get('source_scene_id') or ''),
            )
        return {'novel_id': ident, 'entry': saved}

    def delete_fact_ledger_entry(self, ident: str, entry_id: str) -> dict:
        from nw.fact_ledger import delete_fact_entry
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            return {'novel_id': ident, **delete_fact_entry(store, entry_id)}

    def calibration_anchor(self, ident: str) -> dict:
        from nw.craft_evolution import load_book_calibration_anchor
        novel = self.db.get(ident)
        with self.open_store(novel) as store:
            return {'novel_id': ident, 'anchor': load_book_calibration_anchor(store)}

    def save_calibration_anchor(self, ident: str, body: dict | None = None) -> dict:
        from nw.craft_evolution import auto_extract_chapter1_calibration_anchor, save_book_calibration_anchor
        novel = self.db.get(ident)
        branch = str(novel.get('current_branch') or 'main')
        payload = body if isinstance(body, dict) else {}
        with self.open_store(novel) as store:
            if str(payload.get('excerpt') or '').strip():
                saved = save_book_calibration_anchor(
                    store, str(payload['excerpt']),
                    chapter_index=int(payload.get('chapter_index') or 1),
                    source='author_pinned',
                )
            else:
                saved = auto_extract_chapter1_calibration_anchor(store, branch=branch, force=True)
                if saved is None:
                    raise ValueError('当前尚无可用于提取校准锚段的已接受正文（请至少完成并接受第 1 章正文）')
        return {'novel_id': ident, 'anchor': saved}

    def wizard_preferences(self) -> dict:
        """Aggregate cross-project global author memory & recent creation history for Wizard ⭐ prefill."""
        from collections import Counter
        novels = self.db.list()
        genre_counter: Counter[str] = Counter()
        mode_counter: Counter[str] = Counter()
        history: list[dict] = []
        for n in novels[:30]:
            wiz = n.get('wizard') or {}
            gids = wiz.get('genre_ids') or []
            if isinstance(gids, list):
                for g in gids[:2]:
                    if g:
                        genre_counter[str(g)] += 1
            if wiz.get('length_mode'):
                mode_counter[str(wiz['length_mode'])] += 1
            history.append({'id': n.get('id'), 'title': n.get('title'), 'genre_ids': gids[:2], 'status': n.get('status')})
        global_mem = self.library.list_global_author_memory(status='active')
        taboos = [m['assertion'] for m in global_mem if m.get('kind') == 'taboo'][:6]
        prose_prefs = [m['assertion'] for m in global_mem if m.get('kind') != 'taboo'][:6]
        return {
            'favorite_genre_ids': [g for g, _ in genre_counter.most_common(5)],
            'preferred_length_mode': mode_counter.most_common(1)[0][0] if mode_counter else 'tiered',
            'taboos': taboos,
            'prose_preferences': prose_prefs,
            'recent_novels': history[:6],
        }
