"""Backend service layer for the Novel Workflow Studio client (offline-first, API-optional)."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import threading
import tomllib
from typing import Any
from uuid import uuid4

from nw.acceptance import accept_batch
from nw.cards import decide_card, decision_history, link_cards, read_card, read_decision, read_links, save_card
from nw.chapter_records import chapter_index, chapter_review, chapter_summary
from nw.chapter_state import chapter_state
from nw.cli import project_directory
from nw.config import ConfigRequired, ROOT, load_config
from nw.context.story import StoryScope, WRITE_PROMPT, build_story_context, scene_scope
from nw.materials.phase_contract import FIELDS
from nw.materials.phase_flow import (
    FUNCTION_QUERIES,
    SCHEMAS,
    STAGE_INSTRUCTIONS,
    STAGE_MATERIALS,
    STEP_PROMPT,
    STEP_SOURCE_PROMPT,
    _sources,
    _step_source_pool,
)
from nw.materials.phase_routes import EXTERNAL_REQUIRES, ORDER, POLICY, REQUIRES, phase_order, route_method
from nw.materials.stage_input import STEP_SOURCE_POLICY, step_material_prompt
from nw.materials.step_guard import (
    PRIORITY_HIERARCHY,
    build_continuity_ledger,
    build_joint_material_plan,
    build_multi_character_coordination,
)
from nw.materials.steps.review import MATERIAL as REVIEW_MATERIAL
from nw.materials.steps.review_scope import MATERIAL as SCOPE_REVIEW_MATERIAL
from nw.materials.steps.state_extract import MATERIAL as STATE_EXTRACT_MATERIAL
from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
from nw.llm.base import GenResult
from nw.models import Run
from nw.novel_scene import REVIEW_PROMPT, REVISE_PROMPT
from nw.novel_store import JobRequest, cancel_job, show_job, start_job
from nw.planning import show_plan
from nw.store import Store, now
from nw.story_delta import check_delta, draft_digest, read_delta, save_delta
from nw.story_extract import freeze_delta_input
from nw.story_models import AcceptanceRequest, CardRef, StateHead
from nw.story_state import adopt_story, approved_scene_positions, current_head, fork_story, position, revision_state, state_at
from nw.task_models import Budget, canonical, content_sha256

STAGE_LABELS: dict[str, dict[str, str]] = {
    'type_selection': {'zh': '01. 类型判定与承诺', 'group': '全书与细化共用', 'owner_hint': 'Carbon 主力'},
    'type_adaptation': {'zh': '02. 类型组合与适配', 'group': '全书与细化共用', 'owner_hint': 'Carbon 主力'},
    'world_design': {'zh': '03. 世界设定与限制', 'group': '全书与细化共用', 'owner_hint': 'Carbon 主力'},
    'character_design': {'zh': '04. 人物动机与弧线', 'group': '全书与细化共用', 'owner_hint': 'Opus 5.5 推荐'},
    'static_relations': {'zh': '05. 静态关系与张力', 'group': '全书与细化共用', 'owner_hint': 'Carbon 主力'},
    'plot_design': {'zh': '06. 剧情因果与伏笔', 'group': '全书与细化共用', 'owner_hint': 'Carbon 主力'},
    'event_design': {'zh': '07. 事件链与候选分支', 'group': '卷/章/场细化专用', 'owner_hint': 'Carbon 主力'},
    'action_design': {'zh': '08. 行动博弈与试错代价', 'group': '卷/章/场细化专用', 'owner_hint': 'Opus 5.5 推荐'},
    'scene_design': {'zh': '09. 场景结构与POV边界', 'group': '卷/章/场细化专用', 'owner_hint': 'Carbon 主力'},
    'state_transition': {'zh': '10. 状态变化与外部因果', 'group': '卷/章/场细化专用', 'owner_hint': 'Carbon 主力'},
    'state_propagation': {'zh': '11. 状态传播与连锁感知', 'group': '卷/章/场细化专用', 'owner_hint': 'Carbon 主力'},
    'anchor_design': {'zh': '12. 具象锚点与身体节拍', 'group': '卷/章/场细化专用', 'owner_hint': 'Opus 5.5 推荐'},
    'expression_design': {'zh': '13. 叙述距离与表达设计', 'group': '卷/章/场细化专用', 'owner_hint': 'Opus 5.5 主力'},
    'bind_scope': {'zh': '14. 范围绑定与检验收口', 'group': '全书收口(第7步)/细化收口(第14步)', 'owner_hint': 'Carbon 主力'},
}

RUNTIME_STAGE_LABELS: dict[str, dict[str, str]] = {
    'plan': {'zh': '设计总装冻结 (plan assembly)', 'owner_hint': 'Carbon 主力'},
    'write': {'zh': '场景正文创作 (write)', 'owner_hint': 'Opus 5.5 主力'},
    'review': {'zh': '独立场景审稿与证据核验 (review)', 'owner_hint': 'Carbon 主力'},
    'revise': {'zh': '按审稿意见修订正文 (revise)', 'owner_hint': 'Opus 5.5 主力'},
    'state_extract': {'zh': '正文事实增量提取 (state_extract)', 'owner_hint': 'Carbon 主力'},
    'fact_review': {'zh': '独立事实证据复核 (fact_review)', 'owner_hint': 'Carbon 主力'},
    'scope_review': {'zh': '整章/跨章资料范围独立审稿 (scope_review)', 'owner_hint': 'Carbon 主力'},
}

ROUTING_PRESETS: dict[str, dict[str, Any]] = {
    'offline_sandbox': {
        'id': 'offline_sandbox',
        'name': '暂不接 API · 离线沙盘与架构调校模式（当前默认）',
        'description': '不发起任何外部大模型网络调用；完整开放项目管理、14步联合资料干跑预演、POV上下文检查、手工草稿与状态增量排练、2.29万条资料库及F2问题台账检视。',
        'live_api': False,
        'model': {
            'provider': 'ollama',
            'base_url': 'http://127.0.0.1:11434',
            'model': 'qwen2.5:14b',
            'api_key_env': '',
            'timeout': 120,
        },
        'params': {'temperature': 0.2},
        'stage_models': {},
    },
    'carbon_opus_dual': {
        'id': 'carbon_opus_dual',
        'name': 'Gemini 4 Carbon + Claude Opus 5.5 黄金双模型分工模式',
        'description': 'Carbon 负责严密因果、世界规则、状态迁移、独立审稿与事实核验；Opus 5.5 负责人物弧线、行动博弈、锚点细节、文学表达与正文写作修订。',
        'live_api': True,
        'model': {
            'provider': 'openai_compat',
            'base_url': 'https://api.example-gateway.com/v1',
            'model': 'gemini-4-carbon',
            'api_key_env': 'NOVEL_GATEWAY_API_KEY',
            'timeout': 180,
        },
        'params': {'temperature': 0.3, 'max_tokens': 8192},
        'stage_models': {
            'character_design': {'model': 'claude-opus-5-5', 'params': {'temperature': 0.5, 'max_tokens': 8192}},
            'action_design': {'model': 'claude-opus-5-5', 'params': {'temperature': 0.5, 'max_tokens': 8192}},
            'anchor_design': {'model': 'claude-opus-5-5', 'params': {'temperature': 0.55, 'max_tokens': 8192}},
            'expression_design': {'model': 'claude-opus-5-5', 'params': {'temperature': 0.6, 'max_tokens': 8192}},
            'write': {'model': 'claude-opus-5-5', 'params': {'temperature': 0.72, 'max_tokens': 8192}},
            'revise': {'model': 'claude-opus-5-5', 'params': {'temperature': 0.65, 'max_tokens': 8192}},
        },
    },
    'opus_single': {
        'id': 'opus_single',
        'name': 'Claude Opus 5.5 单模型主力创作模式',
        'description': '全流程统一使用 Claude Opus 5.5（适合接入单一 Anthropic 兼容网关进行全链路实测）。',
        'live_api': True,
        'model': {
            'provider': 'openai_compat',
            'base_url': 'https://api.example-gateway.com/v1',
            'model': 'claude-opus-5-5',
            'api_key_env': 'ANTHROPIC_COMPAT_API_KEY',
            'timeout': 180,
        },
        'params': {'temperature': 0.5, 'max_tokens': 8192},
        'stage_models': {},
    },
    'ollama_local': {
        'id': 'ollama_local',
        'name': '本地 Ollama 离线大模型联调模式',
        'description': '连接本机 127.0.0.1:11434 的本地模型验证全自动任务状态机，无需云端 API Key。',
        'live_api': True,
        'model': {
            'provider': 'ollama',
            'base_url': 'http://127.0.0.1:11434',
            'model': 'qwen2.5:14b',
            'api_key_env': '',
            'timeout': 180,
        },
        'params': {'temperature': 0.3, 'num_predict': 4096},
        'stage_models': {},
    },
}

_SECRET_LIKE_RE = re.compile(r'^(?:sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}|Bearer\s+)', re.IGNORECASE)
_ENV_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{1,63}$')


def _default_ledger_path(workspace: Path | None = None) -> Path:
    ws = workspace or (ROOT / 'workspace')
    for candidate in (
        ws / 'materials' / 'F2_统一问题台账.jsonl',
        ROOT / 'workspace' / 'materials' / 'F2_统一问题台账.jsonl',
        ROOT.parent / '08_工作流设计' / 'F2_统一问题台账.jsonl',
        ROOT.parent / '08_工作流设计' / '05_资料问题台账.jsonl',
    ):
        if candidate.is_file():
            return candidate
    return ws / 'materials' / 'F2_统一问题台账.jsonl'


def _anti_forgetting_notes(stage: str) -> list[str]:
    deps = set(REQUIRES[stage])
    notes: list[str] = []
    if stage == 'type_selection':
        return ['首步锚定主/副类型、核心标签与题材禁区，向后续全流程广播边界。']
    if 'type_selection' not in deps or 'type_adaptation' not in deps:
        notes.append('自动注入 type_guard：保留第1–2步已选类型ID与适配禁区，防中后段偏离题材承诺。')
    if 'world_design' not in deps and stage not in ('type_selection', 'type_adaptation', 'world_design'):
        notes.append('自动注入 world_guard：在未直连 world_design 的步骤仍保留世界硬规则、限制与待决未知项，防战力/设定崩塌。')
    if 'plot_design' not in deps and stage in ('anchor_design', 'bind_scope'):
        notes.append('自动注入 plot_guard：保留伏笔埋设/回收窗口与读者情绪转向目标，使锚点紧扣伏笔与情绪。')
    if stage in ('event_design', 'scene_design', 'state_transition', 'anchor_design', 'expression_design'):
        notes.append('自动注入 entity_guard：提醒非公开实体(visibility!=public)与不可行动实体(can_act=false)，防越权出场与视角泄密。')
    if stage in ('event_design', 'action_design', 'scene_design', 'state_transition', 'anchor_design', 'expression_design', 'bind_scope'):
        notes.append('自动注入 character_voice_guard：跨场锁定人物嗓音(voice)、性格基线(behavior)与知情边界，防OOC与性格无因漂移。')
    if stage in ('scene_design', 'anchor_design', 'expression_design', 'bind_scope'):
        notes.append('自动注入 foreshadow_reminder：伏笔三态(埋设/暗示/回收)追踪，自动提示本场到期回收项与超期滞后预警。')
    if stage in ('event_design', 'action_design', 'scene_design', 'state_transition', 'anchor_design', 'expression_design', 'bind_scope'):
        notes.append('自动注入 multi_char_guard：多角色群戏协同，隔离各角色知情差、声线与行动能力上限，防对白张冠李戴与知情交叉污染。')
    if stage == 'plot_design':
        notes.append('硬校验 validate_cross_step_consistency：拦截因果链未闭合、非行动实体充当actor、重复事件循环及伏笔同事件自埋自收矛盾。')
    if stage == 'scene_design':
        notes.append('硬校验 validate_cross_step_consistency：拦截同场 before_state 矛盾、场外幽灵角色事件、同刻异地分身及无过渡时间线跳跃。')
    if stage == 'state_transition':
        notes.append('硬校验 validate_cross_step_consistency：严禁冲突 after_state、占位幻觉及无驱动事件的人物性格突变。')
    return notes


class StudioService:
    """Thread-safe local service exposing the complete novel workflow to the Studio frontend."""

    def __init__(self, workspace: Path | None = None, *, config_path: Path | None = None,
                 ledger_path: Path | None = None) -> None:
        shared = ROOT / 'studio.config.toml'
        default_config = shared if shared.is_file() else ROOT / 'config.toml'
        self.config_path = (config_path or default_config).resolve()
        if workspace is not None:
            self.workspace = workspace.resolve()
        elif self.config_path.is_file():
            try:
                self.workspace = load_config(self.config_path).workspace.resolve()
            except ConfigRequired:
                self.workspace = (ROOT / 'workspace').resolve()
        else:
            self.workspace = (ROOT / 'workspace').resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.ledger_path = (ledger_path or _default_ledger_path(self.workspace)).resolve()
        self._lock = threading.Lock()
        self._desk = None
        self._ledger_cache: list[dict] | None = None
        self._ledger_mtime: float = 0.0

    def _get_desk(self):
        if not (self.workspace / 'materials/catalog.db').is_file():
            return None
        with self._lock:
            if self._desk is None:
                from nw.materials.work_catalog import SourceDesk
                self._desk = SourceDesk(self.workspace)
            return self._desk

    def _get_ledger(self) -> list[dict]:
        if not self.ledger_path.is_file():
            return []
        with self._lock:
            try:
                current_mtime = self.ledger_path.stat().st_mtime
            except OSError:
                return self._ledger_cache or []
            if self._ledger_cache is None or current_mtime != self._ledger_mtime:
                rows: list[dict] = []
                for idx, line in enumerate(self.ledger_path.read_text(encoding='utf-8').splitlines(), start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        item.setdefault('_line', idx)
                        rows.append(item)
                    except ValueError:
                        continue
                self._ledger_cache = rows
                self._ledger_mtime = current_mtime
            return self._ledger_cache

    def _open_store(self, project_name: str, *, create: bool = False) -> Store:
        directory = project_directory(self.workspace, project_name)
        return Store(directory, create=create)

    # ---------- 1. System & Workspace Status ----------

    def system_status(self) -> dict[str, Any]:
        cfg_state = self.get_routing_config()
        desk = self._get_desk()
        catalog_info: dict[str, Any] = {'available': desk is not None, 'total_sources': 0, 'by_state': {}, 'by_profile': {}}
        if desk is not None:
            by_state = Counter(row['state'] for row in desk.rows)
            by_profile = Counter(row['profile'] for row in desk.rows)
            catalog_info = {
                'available': True,
                'has_reviews': desk.has_reviews,
                'total_sources': len(desk.rows),
                'by_state': dict(sorted(by_state.items())),
                'by_profile': dict(sorted(by_profile.items(), key=lambda kv: (-kv[1], kv[0]))),
            }
        ledger = self._get_ledger()
        ledger_summary = {
            'available': self.ledger_path.is_file(),
            'path': str(self.ledger_path),
            'total_issues': len(ledger),
            'by_disposition': dict(Counter(
                str(r.get('disposition') or r.get('status') or r.get('action') or 'unknown') for r in ledger
            )),
        }
        return {
            'workspace': str(self.workspace),
            'config_path': str(self.config_path),
            'api_mode': cfg_state['mode'],
            'config_valid': cfg_state['valid'],
            'projects_count': len(self.list_projects()),
            'catalog': catalog_info,
            'f2_ledger': ledger_summary,
            'policy': POLICY,
            'priority_hierarchy': PRIORITY_HIERARCHY,
            'repository_sync': self.repository_sync.status() if hasattr(self, 'repository_sync') else None,
        }

    # ---------- 2. Projects, Brief, Bible, Outline, Story Adoption ----------

    def list_projects(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if not self.workspace.is_dir():
            return items
        for child in sorted(self.workspace.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir() or child.name == 'materials' or not (child / 'nw.db').is_file():
                continue
            try:
                with Store(child) as store:
                    proj = store.project()
                    managed = store.managed_story()
                    head = asdict(current_head(store, 'main')) if managed else None
                    briefs = store.briefs()
                    chapters = store.list('chapter')
                    scenes = store.list('scene')
                    cards_count = store.connection.execute('SELECT COUNT(DISTINCT card_id) FROM cards').fetchone()[0]
                    jobs_count = store.connection.execute('SELECT COUNT(*) FROM novel_jobs').fetchone()[0]
                    items.append({
                        'dir_name': child.name,
                        'id': proj.id,
                        'name': proj.name,
                        'created_at': proj.created_at,
                        'managed_story': managed,
                        'head': head,
                        'brief_versions': len(briefs),
                        'latest_brief': asdict(briefs[-1]) if briefs else None,
                        'chapters_count': len(chapters),
                        'scenes_count': len(scenes),
                        'cards_count': cards_count,
                        'jobs_count': jobs_count,
                    })
            except Exception as exc:
                items.append({'dir_name': child.name, 'name': child.name, 'error': str(exc)})
        return items

    def create_project(self, dir_name: str, title: str, *, brief_text: str = '', constraints: str = '') -> dict[str, Any]:
        with self._open_store(dir_name, create=True) as store:
            proj = store.init_project(title.strip() or dir_name)
            if brief_text.strip():
                store.add_brief(brief_text.strip(), constraints.strip())
        return self.project_overview(dir_name)

    def project_overview(self, project_name: str, *, branch: str = 'main') -> dict[str, Any]:
        with self._open_store(project_name) as store:
            proj = store.project()
            managed = store.managed_story()
            branches: list[dict[str, Any]] = []
            active_slots: dict[str, Any] = {}
            active_settings: list[dict[str, Any]] = []
            approved_positions: dict[str, tuple[int, int]] = {}
            main_positions: dict[str, tuple[int, int]] = {}
            if managed:
                for brow in store.connection.execute('SELECT id, head_revision, parent_branch_id AS parent_branch, parent_at_fork AS forked_revision FROM story_branches WHERE enabled=1 ORDER BY id'):
                    branches.append(dict(brow))
                head = current_head(store, branch)
                snap = revision_state(store, head)
                active_slots = snap.get('slots', {})
                active_settings = snap.get('settings', [])
                approved_positions = approved_scene_positions(store, snap)
                main_positions = approved_positions if branch == 'main' else approved_scene_positions(
                    store, revision_state(store, current_head(store, 'main')))
            briefs = [asdict(b) for b in store.briefs()]
            bibles = [asdict(b) for b in store.bible()]
            chapters = [asdict(c) for c in store.list('chapter')]
            chapter_by_id = {c['id']: c for c in chapters}
            scenes: list[dict[str, Any]] = []
            for sc in store.list('scene'):
                card_obj = json.loads(sc.card_json)
                drafts = store.drafts(sc.id)
                legacy_acc = store.accepted(sc.id)
                slot = active_slots.get(sc.id)
                scenes.append({
                    'id': sc.id,
                    'chapter_id': sc.chapter_id,
                    'chapter_index': chapter_by_id.get(sc.chapter_id, {}).get('index', 0),
                    'index': sc.index,
                    'card': card_obj,
                    'drafts_count': len(drafts),
                    'latest_draft_id': drafts[-1].id if drafts else None,
                    'accepted_draft_id': slot['draft_id'] if slot else (legacy_acc.draft_id if legacy_acc and not managed else None),
                    'accepted_delta_id': slot['delta_id'] if slot else None,
                    'story_approved_on_main': sc.id in main_positions,
                    'story_approved_on_branch': sc.id in approved_positions,
                })
            scenes.sort(key=lambda s: (s['chapter_index'], s['index']))
            plans = self._list_plans(store)
            jobs = self._list_jobs(store)
            cards = self._list_cards_internal(store)
            return {
                'dir_name': project_name,
                'branch_id': branch,
                'project': asdict(proj),
                'managed_story': managed,
                'branches': branches,
                'active_settings': active_settings,
                'briefs': briefs,
                'bible': bibles,
                'chapters': sorted(chapters, key=lambda c: c['index']),
                'scenes': scenes,
                'cards': cards,
                'plans': plans,
                'jobs': jobs,
            }

    def save_brief(self, project_name: str, text: str, constraints: str = '') -> dict[str, Any]:
        if not text.strip():
            raise ValueError('Brief 需求正文不能为空')
        with self._open_store(project_name) as store:
            brief = store.add_brief(text.strip(), constraints.strip())
            return asdict(brief)

    def save_bible(self, project_name: str, kind: str, name: str, body: str) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            entry = store.add_bible(kind, name.strip(), body.strip())
            return asdict(entry)

    def create_chapter(self, project_name: str, index: int, title: str) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            return asdict(store.add_chapter(int(index), title.strip()))

    def create_scene(self, project_name: str, chapter_id: str, index: int, card: dict[str, Any]) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            sc = store.add_scene(chapter_id, int(index), canonical(card))
            return {'id': sc.id, 'chapter_id': sc.chapter_id, 'index': sc.index, 'card': json.loads(sc.card_json)}

    def adopt_project_story(self, project_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            entities = [str(x).strip() for x in payload.get('entities', ['protagonist']) if str(x).strip()] or ['protagonist']
            predicates = [str(x).strip() for x in payload.get('predicates', ['status', 'location', 'goal']) if str(x).strip()] or ['status']
            facts = payload.get('facts', [])
            card_refs: list[dict[str, Any]] = []
            if payload.get('include_approved_cards', True):
                seen_ids: set[str] = set()
                for row in store.connection.execute(
                    'SELECT card_id, MAX(version) AS version, kind FROM cards GROUP BY card_id ORDER BY card_id'
                ):
                    if row['kind'] == 'rule' or row['card_id'] in seen_ids:
                        continue
                    ref = CardRef(row['card_id'], row['version'])
                    card = read_card(store, ref)
                    if card['status'] == 'approved':
                        hist = decision_history(store, ref)
                        if hist and hist[-1].decision == 'approved':
                            card_refs.append({'card_id': ref.card_id, 'version': ref.version, 'decision_id': hist[-1].id})
                            seen_ids.add(ref.card_id)
            baseline = {
                'as_of_story_order': int(payload.get('as_of_story_order', 0)),
                'disclosure_order': list(payload.get('disclosure_order', [0, 0, 0])),
                'coverage': {'entities': entities, 'predicates': predicates},
                'facts': facts,
                'card_refs': card_refs,
            }
            expected_accepted = {row.scene_id: row.draft_id for row in store.list('accepted')}
            head = adopt_story(store, baseline, expected_accepted)
            return asdict(head)

    def fork_branch(self, project_name: str, from_branch: str, revision: int, new_name: str) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            head = fork_story(store, StateHead(from_branch, int(revision)), new_name.strip())
            return asdict(head)

    # ---------- 3. Cards & Multi-Holder Knowledge Matrix ----------

    def _list_cards_internal(self, store: Store) -> list[dict[str, Any]]:
        rows = store.connection.execute(
            'SELECT card_id, MAX(version) AS latest_version FROM cards GROUP BY card_id ORDER BY kind, card_id'
        ).fetchall()
        cards: list[dict[str, Any]] = []
        for row in rows:
            ref = CardRef(row['card_id'], row['latest_version'])
            card = read_card(store, ref)
            card['links'] = [asdict(link) for link in read_links(store, ref)]
            card['decisions'] = [asdict(read_decision(store, d.id)) for d in decision_history(store, ref)]
            cards.append(card)
        return cards

    def list_cards(self, project_name: str) -> list[dict[str, Any]]:
        with self._open_store(project_name) as store:
            return self._list_cards_internal(store)

    def list_jobs(self, project_name: str) -> dict[str, Any]:
        """List jobs for the Job Stepper Drawer."""
        with self._open_store(project_name) as store:
            jobs: list[dict[str, Any]] = []
            try:
                for row in store.connection.execute(
                    'SELECT id, scene_id, status, step, created FROM jobs ORDER BY rowid DESC LIMIT 20'
                ):
                    jobs.append({
                        'id': row['id'],
                        'scene_id': row['scene_id'],
                        'status': row['status'],
                        'current_step': row['step'],
                        'created': row['created'],
                        'scope': 'scene',
                        'needs_confirm': row['status'] == 'needs_confirm',
                    })
            except Exception:
                pass  # jobs table may not exist in offline mode
            return {'jobs': jobs}

    def save_author_card(self, project_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            card_id = str(payload['card_id']).strip()
            row = store.connection.execute(
                'SELECT MAX(version) AS v FROM cards WHERE card_id=?', (card_id,)
            ).fetchone()
            expected = row['v'] if row and row['v'] is not None else None
            card_doc = {
                'card_id': card_id,
                'kind': payload['kind'],
                'origin': 'author',
                'body': payload['body'],
                'source_refs': payload.get('source_refs', []),
            }
            if expected is not None:
                card_doc['version'] = expected
            ref = save_card(store, card_doc, expected)
            if payload.get('auto_approve'):
                decide_card(store, ref, 'approved', str(payload.get('reason') or '作者在客户端确认启用'))
                if store.managed_story() and payload.get('apply_to_branch') and payload['kind'] != 'rule':
                    from nw.story_state import apply_settings
                    branch = str(payload.get('branch') or 'main')
                    head = current_head(store, branch)
                    snap = revision_state(store, head)
                    hist = decision_history(store, ref)
                    updated = [s for s in snap['settings'] if s['card_id'] != ref.card_id]
                    updated.append({'card_id': ref.card_id, 'version': ref.version, 'decision_id': hist[-1].id})
                    apply_settings(store, head, updated, f'studio-card:{ref.card_id}:v{ref.version}:{uuid4().hex[:8]}')
            if payload.get('bind_scene_id') and payload['kind'] == 'scene':
                sc_id = str(payload['bind_scene_id'])
                story_order = int(payload.get('story_order', 1))
                sc = store.get('scene', sc_id)
                card_json = json.loads(sc.card_json)
                card_json['story'] = {'scene_ref': {'card_id': ref.card_id, 'version': ref.version}, 'story_order': story_order}
                with store.connection:
                    store.connection.execute('UPDATE scenes SET card_json=? WHERE id=?', (canonical(card_json), sc_id))
            return read_card(store, ref)

    def decide_project_card(self, project_name: str, card_id: str, version: int, decision: str, reason: str) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            ref = CardRef(card_id, int(version))
            dref = decide_card(store, ref, decision, reason.strip() or '客户端决策')
            return {'decision': asdict(dref), 'card': read_card(store, ref)}

    def add_card_link(self, project_name: str, source_id: str, source_ver: int, relation: str,
                      target_id: str, target_ver: int) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            link = link_cards(store, CardRef(source_id, int(source_ver)), relation, CardRef(target_id, int(target_ver)))
            return asdict(link)

    def inspect_state_matrix(self, project_name: str, *, branch: str = 'main', revision: int | None = None,
                             story_order: int = 999999, disclosure: list[int] | None = None) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            if not store.managed_story():
                return {'managed_story': False, 'holders': [], 'matrix': []}
            head = current_head(store, branch) if revision is None else StateHead(branch, int(revision))
            disc = position(disclosure) if disclosure else (9999, 9999, 9999)
            snap = revision_state(store, head)
            char_holders: list[str] = []
            for sref in snap.get('settings', ()):
                c = read_card(store, CardRef(sref['card_id'], sref['version']))
                if c['kind'] == 'character':
                    char_holders.append(c['card_id'])
            holders = ['WORLD', 'READER', *char_holders]
            views: dict[str, dict[str, Any]] = {}
            rows_map: dict[tuple[str, str], dict[str, Any]] = {}
            for holder in holders:
                view = state_at(store, head.branch_id, head.revision, int(story_order), holder, disc)
                views[holder] = {
                    'visible_cards': [c['card_id'] for c in view.settings],
                    'facts_count': len(view.facts),
                }
                for f in view.facts:
                    key = (f.entity_id, f.predicate)
                    entry = rows_map.setdefault(key, {'entity_id': f.entity_id, 'predicate': f.predicate, 'cells': {}})
                    entry['cells'].setdefault(holder, []).append({
                        'claim': f.claim,
                        'value': f.value,
                        'story_order': f.story_order,
                        'disclosure_order': list(f.disclosure_order),
                    })
            return {
                'managed_story': True,
                'head': asdict(head),
                'story_order': int(story_order),
                'disclosure_order': list(disc),
                'holders': holders,
                'holder_summaries': views,
                'matrix': [rows_map[k] for k in sorted(rows_map)],
            }

    # ---------- 4. 14-Step Pipeline Blueprint & Joint-Material Dry-Run ----------

    def pipeline_blueprint(self, scope: str = 'chapter') -> dict[str, Any]:
        stages = phase_order(scope)
        steps: list[dict[str, Any]] = []
        for idx, stage in enumerate(stages, start=1):
            meta = STAGE_LABELS.get(stage, {'zh': stage, 'group': '', 'owner_hint': ''})
            mat_text = STAGE_MATERIALS.get(stage, '')
            steps.append({
                'step_no': idx,
                'stage': stage,
                'zh_title': meta['zh'],
                'group': meta['group'],
                'owner_hint': meta['owner_hint'],
                'requires': list(REQUIRES[stage]),
                'output_fields': sorted(FIELDS[stage]),
                'function_queries': list(FUNCTION_QUERIES.get(stage, ())),
                'anti_forgetting_guards': _anti_forgetting_notes(stage),
                'stage_instruction': STAGE_INSTRUCTIONS.get(stage, ''),
                'schema_summary': SCHEMAS.get(stage, ''),
                'stage_material_chars': len(mat_text),
            })
        runtime_steps = [
            {'stage': 'write', **RUNTIME_STAGE_LABELS['write'], 'requires': list(EXTERNAL_REQUIRES['writer']),
             'base_prompt': WRITE_PROMPT, 'material_chars': len(WRITING_MATERIAL)},
            {'stage': 'review', **RUNTIME_STAGE_LABELS['review'], 'requires': list(EXTERNAL_REQUIRES['review']),
             'base_prompt': REVIEW_PROMPT, 'material_chars': len(REVIEW_MATERIAL)},
            {'stage': 'revise', **RUNTIME_STAGE_LABELS['revise'], 'requires': ['frozen_context', 'draft', 'review_notes'],
             'base_prompt': REVISE_PROMPT, 'material_chars': len(WRITING_MATERIAL)},
            {'stage': 'state_extract', **RUNTIME_STAGE_LABELS['state_extract'], 'requires': ['reviewed_draft', 'frozen_facts'],
             'base_prompt': '从通过审稿的正文中提取含精确 Unicode 证据区间的状态变更。', 'material_chars': len(STATE_EXTRACT_MATERIAL)},
            {'stage': 'fact_review', **RUNTIME_STAGE_LABELS['fact_review'], 'requires': ['draft', 'candidate_operations'],
             'base_prompt': '独立核对候选事实变更与正文证据，拦截未发生计划或人物误信冒充 WORLD 事实。', 'material_chars': len(STATE_EXTRACT_MATERIAL)},
            {'stage': 'scope_review', **RUNTIME_STAGE_LABELS['scope_review'], 'requires': ['complete_chapter_drafts', 'scoped_contracts'],
             'base_prompt': '跨场/整章范围独立核验原始资料义务与实际落文证据。', 'material_chars': len(SCOPE_REVIEW_MATERIAL)},
            {'stage': 'acceptance', 'zh': '批次原子提交与章总结复盘 (accept_batch + chapter_records)', 'owner_hint': '确定性状态机 + 作者确认',
             'requires': list(EXTERNAL_REQUIRES['acceptance']), 'base_prompt': '无模型幻觉介入：SQLite 事务原子推进版本头并导出 Markdown。', 'material_chars': 0},
        ]
        return {
            'scope': scope,
            'policy': POLICY,
            'priority_hierarchy': PRIORITY_HIERARCHY,
            'design_steps': steps,
            'runtime_steps': runtime_steps,
        }

    def simulate_step_materials(self, *, scope: str = 'chapter', stage: str = 'character_design',
                                brief_text: str = '', constraints: str = '',
                                project_name: str | None = None,
                                simulate_prior_products: bool = True) -> dict[str, Any]:
        if stage not in ORDER:
            raise ValueError(f'Unknown planning stage: {stage}')
        if project_name and not brief_text.strip():
            with self._open_store(project_name) as store:
                briefs = store.briefs()
                if briefs:
                    brief_text = briefs[-1].text
                    constraints = constraints or briefs[-1].constraints
        brief_text = brief_text.strip() or '一部冷峻现实向悬疑长篇：基层刑警在滨海旧港追查十年前沉船旧案，线索与亲情互相撕扯。'
        constraints = constraints.strip() or '单章单POV；严禁全知视角偷看他人心理；每一次试错必须付出真实社会关系或体力代价。'

        desk = self._get_desk()
        package: dict[str, Any] = {
            'scope': scope,
            'brief': {'text': brief_text, 'constraints': constraints, 'version': 1},
            'action_template_priority_enabled': True,
        }
        if desk is not None:
            from nw.materials.source_set import selection_status
            selected = selection_status(self.workspace)
            if selected:
                package['current_source_set'] = selected['sha256']
                package['stage_materials'] = {stage: STAGE_MATERIALS.get(stage, '')}
                package['stage_source_policy'] = STEP_SOURCE_POLICY
        mock_products: dict[str, dict] = {}
        if simulate_prior_products:
            if stage != 'type_selection':
                mock_products['type_selection'] = {
                    'products': {
                        'selection': [{'id': 'TYPE_SUSPENSE', 'label': '悬疑推理'}],
                        'boundaries': ['单视角受限知情，禁止未铺垫的机械降神解谜'],
                    }
                }
            if stage not in ('type_selection', 'type_adaptation'):
                mock_products['type_adaptation'] = {
                    'products': {
                        'boundaries': ['现实向硬逻辑约束，社会调查受程序与时间窗口限制'],
                        'adaptations': [{'limits': ['非公开档案须经合法或高风险渠道获取']}],
                    }
                }
            if stage not in ('type_selection', 'type_adaptation', 'world_design'):
                mock_products['world_design'] = {
                    'products': {
                        'members': [{'key': 'world_harbor', 'body': {'rule': '旧港潮汐与档案封存制度固定', 'limits': '夜间涨潮封锁栈桥，越权调档留痕'}}],
                        'limitations': ['体力与取证时效硬约束'],
                        'unknowns': ['沉船当晚第三名目击者真实去向'],
                    }
                }
            if stage in ('event_design', 'action_design', 'scene_design', 'state_transition', 'state_propagation', 'anchor_design', 'expression_design', 'bind_scope'):
                mock_products['character_design'] = {
                    'products': {
                        'members': [
                            {'key': 'char_lin', 'body': {
                                'name': '林沉', 'visibility': 'public',
                                'voice': '语速偏慢、克制简短', 'behavior': '高压下先观察物证再开口',
                                'change_conditions': '唯有铁证推翻旧案定论才动摇',
                            }},
                            {'key': 'char_informant', 'body': {
                                'name': '线人老周', 'visibility': 'holders', 'holders': ['char_lin'],
                                'voice': '压低嗓音、多用港口暗语', 'behavior': '谨慎多疑、留退路',
                            }},
                        ],
                        'capabilities': [{'entity': 'evidence_locker', 'can_act': False}],
                    }
                }
            if stage in ('anchor_design', 'expression_design', 'bind_scope'):
                mock_products['scene_design'] = {
                    'products': {
                        'members': [{
                            'key': 'sc_dock_01',
                            'kind': 'scene',
                            'body': {
                                'pov': 'char_lin',
                                'characters': ['char_lin', 'char_informant'],
                                'character_goals': {'char_lin': '核实停摆怀表来源', 'char_informant': '试探警方底牌'},
                            },
                        }],
                        'selected_events': [{'scene': 'sc_dock_01', 'event': 'ev_4'}],
                    }
                }
            if stage in ('scene_design', 'anchor_design', 'expression_design', 'bind_scope'):
                mock_products['plot_design'] = {
                    'products': {
                        'promise_plan': [{'promise': 'promise_watch', 'plant_event': 'ev_1', 'payoff_event': 'ev_4', 'setup': '停摆怀表指向23:15'}],
                        'reader_plan': [{'event': 'ev_2', 'before_emotion': '疑虑', 'after_emotion': '紧迫', 'trigger': '证词时间差暴露'}],
                    }
                }

        deps = list(REQUIRES[stage])
        continuity_ledger = build_continuity_ledger(stage, mock_products, deps, {'approved_cards': []})
        multi_char = build_multi_character_coordination(stage, mock_products, {'approved_cards': []})
        if desk is None:
            return {
                'catalog_available': False,
                'stage': stage,
                'scope': scope,
                'brief': package['brief'],
                'requires': deps,
                'continuity_ledger': continuity_ledger,
                'multi_character_coordination': multi_char,
                'joint_material_plan': None,
                'sources': [],
                'rendered_prompt': STEP_PROMPT + '\n' + STAGE_INSTRUCTIONS.get(stage, ''),
            }

        deferred: list[dict] = []
        selection = {
            'policy': 'task-block-subitem-selection-v1',
            'before_stage': stage,
            'queries': [],
            'offered': [],
            'selected': [],
        }
        step_pool = _step_source_pool(desk, stage, package)
        sources = _sources(desk, stage, package, mock_products, [], reviewed_only=True, deferrals=deferred,
                           trace=selection, step_pool=step_pool)
        joint_plan = build_joint_material_plan(stage, sources)
        source_keys = [s['source']['key'] for s in sources] if step_pool is None else []
        base_prompt = (STEP_PROMPT if step_pool is None else STEP_SOURCE_PROMPT) + '\n' + STAGE_INSTRUCTIONS.get(stage, '')
        rendered_prompt = step_material_prompt(base_prompt, STAGE_MATERIALS.get(stage, ''), source_keys)

        formatted_sources = []
        for s in sources:
            meta = s['source']
            formatted_sources.append({
                'id': meta['id'],
                'key': meta['key'],
                'profile': meta['profile'],
                'source_state': s['source_state'],
                'use_mode': s['use_mode'],
                'meaning': s.get('meaning', ''),
                'issues_count': sum(len(v) for v in s.get('source_issues', {}).values()),
                **({'original_preview': str(s.get('original_text', ''))[:500]} if step_pool is None
                   else {'step_use': step_pool.get(meta['id'], '')}),
            })
        return {
            'catalog_available': True,
            'stage': stage,
            'zh_title': STAGE_LABELS.get(stage, {}).get('zh', stage),
            'scope': scope,
            'brief': package['brief'],
            'requires': deps,
            'anti_forgetting_guards': _anti_forgetting_notes(stage),
            'continuity_ledger': continuity_ledger,
            'multi_character_coordination': multi_char,
            'joint_material_plan': joint_plan,
            'sources_count': len(formatted_sources),
            'sources': formatted_sources,
            'stage_source_policy': package.get('stage_source_policy'),
            'deferred_reviews_count': len(deferred),
            'queries_executed': selection.get('queries', []),
            'rendered_prompt': rendered_prompt,
            'rendered_prompt_chars': len(rendered_prompt),
        }

    # ---------- 5. Scene Workbench, Live POV Context, Manual Rehearsal & Chapter Records ----------

    def inspect_scene_context(self, project_name: str, scene_id: str, *, branch: str = 'main',
                              char_limit: int = 24000) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            scope = scene_scope(store, scene_id, branch)
            work = build_story_context(store, scene_id, scope, int(char_limit))
            pkg_json = canonical(work.package)
            total_chars = len(work.prompt) + len(pkg_json)
            items_breakdown = [
                {
                    'key': item['source'],
                    'reason': item['reason'],
                    'chars': len(item['text']),
                    'content': item['text'],
                }
                for item in work.package.get('items', ())
            ]
            return {
                'scene_id': scene_id,
                'scope': asdict(work.scope),
                'disclosure': list(work.disclosure),
                'char_limit': int(char_limit),
                'prompt_chars': len(work.prompt),
                'package_chars': len(pkg_json),
                'total_chars': total_chars,
                'usage_ratio': round(total_chars / max(1, int(char_limit)), 4),
                'prompt': work.prompt,
                'writing_source_keys': list(work.writing_source_keys),
                'items': items_breakdown,
                'selection': work.selection,
                'predecessor_drafts': [asdict(r) for r in work.predecessor_drafts],
                'card_refs': list(work.card_refs),
            }

    def scene_workbench(self, project_name: str, scene_id: str, *, branch: str = 'main') -> dict[str, Any]:
        with self._open_store(project_name) as store:
            sc = store.get('scene', scene_id)
            ch = store.get('chapter', sc.chapter_id)
            drafts = [asdict(d) for d in store.drafts(scene_id)]
            runs = [
                asdict(r) for r in store.list('run')
                if r.scene_id == scene_id
            ]
            deltas: list[dict[str, Any]] = []
            if drafts:
                placeholders = ','.join('?' for _ in drafts)
                for drow in store.connection.execute(
                    f'SELECT id FROM state_deltas WHERE draft_id IN ({placeholders}) ORDER BY rowid DESC',
                    tuple(d['id'] for d in drafts),
                ):
                    delta = read_delta(store, drow['id'])
                    findings = [asdict(f) for f in check_delta(store, delta)]
                    deltas.append({'delta': asdict(delta), 'check_findings': findings})
            context_preview = None
            context_error = None
            if store.managed_story():
                try:
                    context_preview = self.inspect_scene_context(project_name, scene_id, branch=branch)
                except Exception as exc:
                    context_error = str(exc)
            return {
                'scene': {'id': sc.id, 'chapter_id': sc.chapter_id, 'chapter_index': ch.index,
                          'chapter_title': ch.title, 'index': sc.index, 'card': json.loads(sc.card_json)},
                'drafts': drafts,
                'runs': runs,
                'deltas': deltas,
                'context_preview': context_preview,
                'context_error': context_error,
            }

    def get_draft(self, project_name: str, scene_id: str, draft_id: str) -> dict[str, Any]:
        """Return a single draft by ID for the Zen Reader / Diff View."""
        with self._open_store(project_name) as store:
            draft = store.get('draft', draft_id)
            if draft.scene_id != scene_id:
                raise ValueError('草稿不属于当前场景')
            return asdict(draft)

    def save_manual_draft(self, project_name: str, scene_id: str, text: str) -> dict[str, Any]:
        if not text.strip():
            raise ValueError('草稿正文不能为空')
        with self._open_store(project_name) as store:
            run_id = uuid4().hex
            started = now()
            store.add_run(Run(
                run_id, scene_id, 'write', 'author', 'manual-studio', '{}',
                canonical({'source': 'studio_manual_author'}),
                canonical({'messages': []}), '', 'error', '{}', started, '',
            ))
            run, draft = store.finish_run(run_id, GenResult(
                text=text, finish_reason='complete', usage={'source': 'author'}, request_id=f'manual:{run_id}', raw={'author': True},
            ))
            return {'run': asdict(run), 'draft': asdict(draft) if draft else None}

    def save_manual_delta(self, project_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            draft_id = str(payload['draft_id'])
            draft = store.get('draft', draft_id)
            branch = str(payload.get('branch') or 'main')
            head = current_head(store, branch)
            sc = store.get('scene', draft.scene_id)
            binding = json.loads(sc.card_json).get('story') or {}
            story_order = int(payload.get('story_order', binding.get('story_order', 1)))
            delta_id = str(payload.get('id') or f'delta-manual-{uuid4().hex[:10]}')
            scope = {
                'id': f'manifest-{delta_id}',
                'branch_id': head.branch_id,
                'base_revision': head.revision,
                'story_order': story_order,
            }
            settings = {
                'provider': 'author', 'model': 'manual', 'params': {},
                'prompt_version': 'manual-state-v1', 'base_url': None, 'timeout': None, 'stream': False,
            }
            manifest_id = freeze_delta_input(store, draft_id, scope, settings)
            digest = draft_digest(draft)
            normalized_ops: list[dict[str, Any]] = []
            for raw_op in payload.get('operations', []):
                if isinstance(raw_op, dict) and isinstance(raw_op.get('evidence'), list):
                    ev_list = [
                        {
                            'draft_id': ev.get('draft_id', draft_id),
                            'text_sha256': ev.get('text_sha256', digest),
                            'start': ev['start'],
                            'end': ev['end'],
                        }
                        if isinstance(ev, dict) and 'start' in ev and 'end' in ev else ev
                        for ev in raw_op['evidence']
                    ]
                    normalized_ops.append({**raw_op, 'evidence': ev_list})
                else:
                    normalized_ops.append(raw_op)
            delta = save_delta(store, delta_id, draft_id, manifest_id, normalized_ops)
            findings = [asdict(f) for f in check_delta(store, delta)]
            return {'delta': asdict(delta), 'findings': findings}

    def accept_scene_delta(self, project_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            branch = str(payload.get('branch') or 'main')
            head = current_head(store, branch)
            scene_id = str(payload['scene_id'])
            draft_id = str(payload['draft_id'])
            delta_id = str(payload['delta_id'])
            delta = read_delta(store, delta_id)
            from nw.acceptance import record_story_decision
            decision_id = record_story_decision(
                store,
                action='accept',
                targets={'branch_id': branch, 'scene_id': scene_id, 'draft_id': draft_id,
                         'delta_id': delta_id, 'manifest_id': delta.manifest_id},
                reason=str(payload.get('reason') or '客户端审核通过并接收正文与状态增量'),
            )
            req = AcceptanceRequest(
                branch_id=branch,
                scene_id=scene_id,
                draft_id=draft_id,
                delta_id=delta_id,
                manifest_id=delta.manifest_id,
                decision_id=decision_id,
            )
            new_head = accept_batch(store, [req], head, f'studio-accept:{uuid4().hex[:10]}')
            return {'head': asdict(new_head), 'decision_id': decision_id}

    def inspect_chapter_ledger(self, project_name: str, chapter_idx: int, *, branch: str = 'main') -> dict[str, Any]:
        with self._open_store(project_name) as store:
            if not store.managed_story():
                return {'managed_story': False}
            head = current_head(store, branch)
            st = chapter_state(store, head, int(chapter_idx))
            summ = chapter_summary(store, head, int(chapter_idx))
            idx_list = chapter_index(store, head)
            return {'managed_story': True, 'head': asdict(head), 'chapter_state': st, 'summary': summ, 'chapter_index': idx_list}

    def record_chapter_summary(self, project_name: str, chapter_idx: int, summary_text: str, *,
                               comparison: str | None = None, branch: str = 'main') -> dict[str, Any]:
        with self._open_store(project_name) as store:
            head = current_head(store, branch)
            current = chapter_summary(store, head, int(chapter_idx))
            body: dict[str, Any] = {'input_sha256': current['input_sha256'], 'summary': summary_text.strip()}
            if comparison and comparison.strip():
                body['comparison'] = comparison.strip()
            return chapter_summary(store, head, int(chapter_idx), body)

    def _list_plans(self, store: Store) -> list[dict[str, Any]]:
        rows = store.connection.execute(
            "SELECT id, status, validation, reason, started_at, ended_at FROM task_calls WHERE kind='plan' ORDER BY rowid DESC LIMIT 30"
        ).fetchall()
        plans: list[dict[str, Any]] = []
        for row in rows:
            entry = dict(row)
            if row['validation'] == 'VALID':
                try:
                    prop = show_plan(store, row['id'])
                    entry['scope'] = prop.scope
                    entry['candidate_cards'] = [asdict(c) for c in prop.candidate_cards]
                    entry['applied'] = prop.application is not None
                except Exception:
                    pass
            plans.append(entry)
        return plans

    def _list_jobs(self, store: Store) -> list[dict[str, Any]]:
        rows = store.connection.execute('SELECT id FROM novel_jobs ORDER BY rowid DESC LIMIT 30').fetchall()
        return [asdict(show_job(store, row['id'])) for row in rows]

    def create_novel_job(self, project_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            budget_raw = payload.get('budget') or {
                'max_calls': 40, 'context_char_limit': 32000, 'output_limit': 4096, 'max_revisions': 2,
            }
            req = JobRequest(
                mode=payload['mode'],
                budget=Budget(**budget_raw),
                branch_id=str(payload.get('branch_id') or 'main'),
                design_scope=str(payload.get('design_scope') or 'chapter'),
                brief_ref=payload.get('brief_ref', payload.get('brief_version')),
                parent_id=payload.get('parent_id'),
                scene_ids=list(payload.get('scene_ids', ())),
                governance_inputs=dict(payload.get('governance_inputs') or {}),
            )
            ref = start_job(store, req)
            return asdict(show_job(store, ref.id))

    def cancel_novel_job(self, project_name: str, job_id: str) -> dict[str, Any]:
        with self._open_store(project_name) as store:
            return asdict(cancel_job(store, job_id))

    # ---------- 6. 6-Corpus Material Desk & F2 Unified Issue Ledger ----------

    def search_materials(self, *, query: str = '', state: str = '', profile: str = '',
                         stage: str = '', limit: int = 40, offset: int = 0) -> dict[str, Any]:
        desk = self._get_desk()
        if desk is None:
            return {'available': False, 'total': 0, 'items': []}
        q = query.strip().lower()
        matched = []
        for row in desk.rows:
            if state and row['state'] != state:
                continue
            if profile and row['profile'] != profile:
                continue
            stages = route_method(row)['stages']
            if stage and stage not in stages:
                continue
            if q:
                hay = f"{row['id']} {row['key']} {row.get('meaning', '')} {row.get('path', '')}".lower()
                if q not in hay:
                    continue
            matched.append((row, stages))
        total = len(matched)
        page = matched[offset: offset + max(1, min(limit, 100))]
        return {
            'available': True,
            'total': total,
            'offset': offset,
            'limit': limit,
            'items': [
                {
                    'id': r['id'],
                    'key': r['key'],
                    'profile': r['profile'],
                    'state': r['state'],
                    'path': r.get('path', ''),
                    'meaning': r.get('meaning', ''),
                    'stages': list(st),
                }
                for r, st in page
            ],
        }

    def get_material_detail(self, source_id: str) -> dict[str, Any]:
        desk = self._get_desk()
        if desk is None:
            raise ValueError('当前工作区尚未构建资料目录数据库 materials/catalog.db')
        full = desk.read(source_id)
        row = desk.by_id[source_id]
        stages = list(route_method(row)['stages'])
        key = full['source']['key']
        step_usages: dict[str, str] = {}
        for st in stages:
            mat = STAGE_MATERIALS.get(st, '')
            if st == 'writer':
                mat = WRITING_MATERIAL
            elif st == 'review':
                mat = REVIEW_MATERIAL
            if mat:
                rendered = step_material_prompt('BASE', mat, [key])
                if rendered != 'BASE':
                    step_usages[st] = rendered[len('BASE'):].strip()
        semantics = None
        try:
            semantics = desk.semantic_contract(full)
        except Exception:
            semantics = None
        return {
            'source': full['source'],
            'source_state': full['source_state'],
            'use_mode': full['use_mode'],
            'meaning': full.get('meaning', ''),
            'original_text': full.get('original_text', ''),
            'source_issues': full.get('source_issues', {}),
            'routed_stages': stages,
            'step_usages': step_usages,
            'semantic_clauses_count': len(semantics.get('clauses', ())) if isinstance(semantics, dict) else 0,
        }

    def search_f2_ledger(self, *, query: str = '', disposition: str = '', corpus: str = '',
                         limit: int = 50, offset: int = 0) -> dict[str, Any]:
        rows = self._get_ledger()
        q = query.strip().lower()
        disp_filter = disposition.strip().lower()
        corp_filter = corpus.strip().lower()
        matched: list[dict] = []
        corpora = Counter()
        dispositions = Counter()
        for r in rows:
            loc = r.get('source_locator') if isinstance(r.get('source_locator'), dict) else {}
            c_val = str(r.get('corpus') or r.get('source_file') or r.get('path') or loc.get('path') or '未分类')
            d_val = str(r.get('disposition') or r.get('status') or r.get('action') or r.get('severity') or 'unknown')
            corpora[c_val] += 1
            dispositions[d_val] += 1
            if disp_filter and disp_filter not in d_val.lower():
                continue
            if corp_filter and corp_filter not in c_val.lower():
                continue
            if q and q not in json.dumps(r, ensure_ascii=False).lower():
                continue
            matched.append(r)
        return {
            'available': self.ledger_path.is_file(),
            'total': len(matched),
            'offset': offset,
            'limit': limit,
            'facets': {
                'corpora': dict(corpora.most_common(20)),
                'dispositions': dict(dispositions.most_common(20)),
            },
            'items': matched[offset: offset + max(1, min(limit, 100))],
        }

    # ---------- 7. Model Routing & Safe API Configuration ----------

    def get_routing_config(self) -> dict[str, Any]:
        env_checks = {}
        for env_name in ('NW_API_KEY', 'NOVEL_GATEWAY_API_KEY', 'ANTHROPIC_COMPAT_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY'):
            env_checks[env_name] = bool(os.environ.get(env_name))
        current: dict[str, Any] | None = None
        valid = False
        error = None
        if self.config_path.is_file():
            try:
                cfg = load_config(self.config_path)
                valid = True
                if cfg.api_key_env:
                    env_checks[cfg.api_key_env] = bool(os.environ.get(cfg.api_key_env))
                for spec in cfg.stage_models.values():
                    if spec.get('api_key_env'):
                        env_checks[spec['api_key_env']] = bool(os.environ.get(spec['api_key_env']))
                current = {
                    'provider': cfg.provider,
                    'base_url': cfg.base_url,
                    'model': cfg.model,
                    'api_key_env': cfg.api_key_env,
                    'timeout': cfg.timeout,
                    'params': cfg.params,
                    'workspace': str(cfg.workspace),
                    'source_driven': cfg.source_driven,
                    'stage_models': cfg.stage_models,
                }
            except ConfigRequired as exc:
                error = str(exc)
                try:
                    current = tomllib.loads(self.config_path.read_text(encoding='utf-8'))
                except Exception:
                    current = None
        mode = 'configured_ready' if valid else 'offline_sandbox'
        return {
            'mode': mode,
            'valid': valid,
            'error': error,
            'config_path': str(self.config_path),
            'current': current,
            'repository_managed': bool(getattr(self, 'repository_sync', None)
                                       and self.repository_sync.enabled),
            'env_present': env_checks,
            'presets': ROUTING_PRESETS,
            'design_stages': [{'stage': s, **STAGE_LABELS[s]} for s in ORDER],
            'runtime_stages': [{'stage': s, **meta} for s, meta in RUNTIME_STAGE_LABELS.items()],
        }

    def render_config_toml(self, payload: dict[str, Any]) -> str:
        model = payload.get('model') or {}
        provider = str(model.get('provider') or 'openai_compat').strip()
        base_url = str(model.get('base_url') or '').strip()
        model_name = str(model.get('model') or '').strip()
        api_key_env = str(model.get('api_key_env') or '').strip()
        timeout = float(model.get('timeout') or 120)

        if _SECRET_LIKE_RE.match(api_key_env):
            raise ValueError('安全拦截：api_key_env 只能填写环境变量名（如 NOVEL_GATEWAY_API_KEY），严禁直接粘贴密钥明文！')
        if api_key_env and not _ENV_NAME_RE.match(api_key_env):
            raise ValueError('api_key_env 必须是合法的环境变量名（字母/数字/下划线）')
        if not base_url:
            raise ValueError('请填写 API 服务地址')
        if not model_name:
            raise ValueError('请填写模型名称')
        if provider == 'openai_compat' and not api_key_env:
            raise ValueError('请填写保存 API 密钥的环境变量名称')

        lines = [
            '# 由 07_新框架_v0 小说工作流客户端生成（严禁在此文件写入 API Key 明文）',
            '[model]',
            f'provider = {json.dumps(provider)}',
            f'base_url = {json.dumps(base_url)}',
            f'model = {json.dumps(model_name)}',
            f'api_key_env = {json.dumps(api_key_env)}',
            f'timeout = {timeout:g}',
            '',
            '[params]',
        ]
        for k, v in (payload.get('params') or {}).items():
            lines.append(f'{k} = {json.dumps(v)}')
        lines.extend([
            '',
            '[paths]',
            f'workspace = {json.dumps(self.workspace.relative_to(self.config_path.parent).as_posix() if self.workspace.is_relative_to(self.config_path.parent) else str(self.workspace))}',
            '',
            '[workflow]',
            f'source_driven = {"true" if payload.get("source_driven", True) else "false"}',
        ])
        stage_models = payload.get('stage_models') or {}
        if stage_models:
            lines.append('')
            for stage_name, spec in stage_models.items():
                if not spec:
                    continue
                if isinstance(spec, str):
                    lines.append(f'[stage_models.{stage_name}]')
                    lines.append(f'model = {json.dumps(spec)}')
                elif isinstance(spec, dict) and spec.get('model'):
                    sp_env = str(spec.get('api_key_env') or '').strip()
                    if _SECRET_LIKE_RE.match(sp_env):
                        raise ValueError(f'安全拦截：stage_models.{stage_name}.api_key_env 严禁填写密钥明文！')
                    lines.append(f'[stage_models.{stage_name}]')
                    for field in ('provider', 'base_url', 'model', 'api_key_env', 'timeout'):
                        if field in spec and spec[field] not in (None, ''):
                            val = float(spec[field]) if field == 'timeout' else spec[field]
                            lines.append(f'{field} = {json.dumps(val) if not isinstance(val, float) else f"{val:g}"}')
                    if isinstance(spec.get('params'), dict) and spec['params']:
                        lines.append(f'[stage_models.{stage_name}.params]')
                        for pk, pv in spec['params'].items():
                            lines.append(f'{pk} = {json.dumps(pv)}')
        return '\n'.join(lines) + '\n'

    def save_routing_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        toml_text = self.render_config_toml(payload)
        tmp = self.config_path.parent / f'.config_validate_{uuid4().hex[:8]}.toml'
        try:
            tmp.write_text(toml_text, encoding='utf-8')
            load_config(tmp)
        finally:
            tmp.unlink(missing_ok=True)
        self.config_path.write_text(toml_text, encoding='utf-8')
        return {'saved': True, 'toml': toml_text, 'status': self.get_routing_config()}
