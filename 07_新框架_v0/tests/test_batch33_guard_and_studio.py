"""Regression tests for Batch 33: cross-step guards, joint-material coordination, stage_models, and Studio client."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from nw.config import ConfigRequired, load_config, resolve_stage_runtime
from nw.llm.fake import FakeProvider
from nw.materials.phase_routes import POLICY, REQUIRES
from nw.materials.step_guard import (
    PRIORITY_HIERARCHY,
    build_continuity_ledger,
    build_joint_material_plan,
    validate_cross_step_consistency,
)
from nw.materials.work_contract import compact_session
from nw.novel_flow import _scope_governance_inputs
from nw.novel_store import JobRequest
from nw.studio import StudioService, create_studio_server
from nw.task_models import Budget


def test_continuity_ledger_fills_non_direct_upstream_constraints() -> None:
    products = {
        'type_selection': {
            'products': {
                'selection': [{'id': 'TYPE_SUSPENSE', 'label': '悬疑'}],
                'boundaries': ['单视角限制知情'],
            }
        },
        'type_adaptation': {
            'products': {
                'boundaries': ['禁止机械降神'],
                'adaptations': [{'limits': ['证据链闭合']}],
            }
        },
        'world_design': {
            'products': {
                'members': [{'key': 'world_port', 'body': {'rule': '23点涨潮封栈桥', 'limits': '无法夜渡'}}],
                'limitations': ['通讯盲区'],
                'unknowns': ['失踪船员下落'],
            }
        },
        'character_design': {
            'products': {
                'members': [
                    {'key': 'char_hero', 'body': {'visibility': 'public'}},
                    {'key': 'char_mole', 'body': {'visibility': 'author_only'}},
                ],
                'capabilities': [{'entity': 'old_archive', 'can_act': False}],
            }
        },
        'plot_design': {
            'products': {
                'promise_plan': [{'promise': 'prom_watch', 'plant_event': 'e1', 'payoff_event': 'e3', 'setup': '怀表停在23:15'}],
                'reader_plan': [{'event': 'e2', 'before_emotion': '疑惑', 'after_emotion': '警觉', 'trigger': '证词矛盾'}],
            }
        },
    }
    assert build_continuity_ledger('type_selection', products, [], {}) is None

    st_ledger = build_continuity_ledger('state_transition', products, list(REQUIRES['state_transition']), {})
    assert st_ledger is not None
    assert 'type_guard' in st_ledger
    assert 'world_guard' in st_ledger
    assert st_ledger['entity_guard'] == {'non_public_entities': ['char_mole'], 'cannot_act': ['old_archive']}
    assert 'plot_guard' not in st_ledger  # plot_design is already in REQUIRES['state_transition']

    anc_ledger = build_continuity_ledger('anchor_design', products, list(REQUIRES['anchor_design']), {})
    assert anc_ledger is not None
    assert 'world_guard' in anc_ledger
    assert 'plot_guard' in anc_ledger
    assert anc_ledger['plot_guard']['promises'][0]['promise'] == 'prom_watch'


def test_joint_material_plan_roles_and_consistency_guards() -> None:
    single = [{'source': {'id': 'S1', 'key': '1.1', 'profile': 'character'}, 'source_state': 'design_ready', 'source_issues': {}}]
    assert build_joint_material_plan('character_design', single) is None

    multi = [
        {'source': {'id': 'S1', 'key': '1.1_动机', 'profile': 'character'}, 'source_state': 'design_ready', 'source_issues': {}},
        {'source': {'id': 'S2', 'key': '30.1_世界边界', 'profile': 'world'}, 'source_state': 'design_ready', 'source_issues': {}},
        {'source': {'id': 'S3', 'key': 'AC1.1', 'profile': 'anchor'}, 'source_state': 'reference', 'source_issues': {'gaps': ['局部待补']}},
    ]
    plan = build_joint_material_plan('scene_design', multi)
    assert plan is not None
    assert plan['priority'] == PRIORITY_HIERARCHY
    assert plan['drivers'] == ['1.1_动机']
    assert plan['boundaries'] == ['30.1_世界边界']
    assert plan['anchors_and_expression'] == ['AC1.1']
    assert plan['needs_instantiation_or_clause_guard'] == ['AC1.1']

    with pytest.raises(ValueError, match='conflicting before_state'):
        validate_cross_step_consistency(
            'scene_design',
            {
                'events': [
                    {'scene': 'sc1', 'entity': 'char_a', 'before_state': {'injury': 'none'}},
                    {'scene': 'sc1', 'entity': 'char_a', 'before_state': {'injury': 'severe'}},
                ]
            },
            {},
            {},
        )

    with pytest.raises(ValueError, match='unfilled placeholder'):
        validate_cross_step_consistency(
            'state_transition',
            {'transitions': [{'scene': 'sc1', 'entity': 'char_a', 'after_state': {'injury': 'TODO'}}]},
            {},
            {},
        )

    with pytest.raises(ValueError, match='conflicting after_state'):
        validate_cross_step_consistency(
            'state_transition',
            {
                'transitions': [
                    {'scene': 'sc1', 'entity': 'char_a', 'after_state': {'loc': 'dock'}},
                    {'scene': 'sc1', 'entity': 'char_a', 'after_state': {'loc': 'station'}},
                ]
            },
            {},
            {},
        )


def test_compact_session_strips_audit_bloat_without_mutating_frozen_session() -> None:
    session = {
        'policy': POLICY,
        'id': 'stages:t1',
        'scope': 'chapter',
        'sources': [{'source': {'id': 'S1', 'key': 'K1', 'sha256': 'a' * 64, 'file_sha256': 'b' * 64},
                     'source_state': 'design_ready', 'use_mode': 'method', 'meaning': 'm', 'original_text': 'x' * 500}],
        'semantic_contracts': [{'source_id': 'S1', 'clauses': ['big']}],
        'stages': [
            {
                'stage': 'type_selection',
                'task_id': 'c1',
                'sha256': 'c' * 64,
                'source_ids': ['S1'],
                'inputs': {},
                'semantic_contracts': [{'source_id': 'S1'}],
                'binding_reviews': {'S1': {'huge': True}},
                'source_selection': {'queries': ['q']},
                'deferred_sources': [{'id': 'D1'}],
                'products': {'selection': [{'id': 'T1'}], '_criteria': [{'clause': 'heavy'}]},
            }
        ],
    }
    snap = deepcopy(session)
    compacted = compact_session(session)
    assert session == snap
    assert 'semantic_contracts' not in compacted
    st0 = compacted['stages'][0]
    assert 'binding_reviews' not in st0
    assert 'source_selection' not in st0
    assert '_criteria' not in st0['products']
    assert st0['products']['selection'] == [{'id': 'T1'}]


def test_stage_models_config_and_governance_forwarding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_file = tmp_path / 'config.toml'
    cfg_file.write_text(
        """
[model]
provider = "ollama"
base_url = "http://127.0.0.1:11434"
model = "gemini-4-carbon"
timeout = 120

[params]
temperature = 0.2

[stage_models]
write = "claude-opus-5-5"

[stage_models.expression_design]
model = "claude-opus-5-5"
params = { temperature = 0.65 }
""",
        encoding='utf-8',
    )
    cfg = load_config(cfg_file)
    assert cfg.stage_models['write']['model'] == 'claude-opus-5-5'
    assert cfg.stage_models['expression_design']['params'] == {'temperature': 0.65}

    # FakeProvider stays isolated in unit tests
    fake = FakeProvider()
    resolved_cfg, resolved_prov = resolve_stage_runtime(cfg, fake, 'write')
    assert resolved_prov is fake
    assert resolved_cfg is cfg

    req = JobRequest(
        mode='design',
        budget=Budget(max_calls=10, context_char_limit=16000, output_limit=2048, max_revisions=1),
        design_scope='chapter',
        brief_ref=1,
        governance_inputs={
            'book': {'type_selection': {'confirmed': True}, 'scene_design': {'ignored': True}},
            'detail': {'scene_design': {'confirmed': True}},
        },
    )
    assert _scope_governance_inputs(req.governance_inputs, 'book') == {'type_selection': {'confirmed': True}}
    assert _scope_governance_inputs(req.governance_inputs, 'chapter') == {'scene_design': {'confirmed': True}}


def test_studio_http_end_to_end_offline_rehearsal(tmp_path: Path) -> None:
    ws = tmp_path / 'ws'
    cfg_path = tmp_path / 'studio_config.toml'
    ledger_path = tmp_path / 'F2.jsonl'
    ledger_path.write_text(
        json.dumps({'source_key': '板块78', 'disposition': 'blocked', 'reason': '时间双轴待补'}, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )
    service = StudioService(workspace=ws, config_path=cfg_path, ledger_path=ledger_path)
    server = create_studio_server(service, host='127.0.0.1', port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        req = Request(f'http://127.0.0.1:{port}{path}', data=data, method=method,
                      headers={'Content-Type': 'application/json'} if data else {})
        try:
            with urlopen(req, timeout=10) as resp:
                raw = resp.read().decode('utf-8')
                ctype = resp.headers.get('Content-Type', '')
                return resp.status, (json.loads(raw) if 'application/json' in ctype else raw)
        except HTTPError as err:
            return err.code, json.loads(err.read().decode('utf-8'))

    try:
        code, html = call('GET', '/')
        # v3 explicitly replaces the v2 product title; keep the real HTTP check.
        assert code == 200 and '小说生产客户端' in html

        code, status = call('GET', '/api/status')
        assert code == 200 and status['api_mode'] == 'offline_sandbox'
        assert status['f2_ledger']['total_issues'] == 1

        # 1. Create project & Brief
        code, created = call('POST', '/api/projects', {
            'dir_name': 'harbor_demo',
            'title': '《潮痕测试》',
            'brief_text': '基层刑警在旧港追查沉船真相',
            'constraints': '单章单POV；限制知情',
        })
        assert code == 201 and created['project']['name'] == '《潮痕测试》'

        # 2. Save & approve character + world + scene cards
        code, char_card = call('POST', '/api/projects/harbor_demo/cards', {
            'card_id': 'char_lin',
            'kind': 'character',
            'body': {'name': '林沉', 'role': '刑警', 'want': '查明沉船真相', 'visibility': 'public'},
            'auto_approve': True,
        })
        assert code == 200 and char_card['status'] == 'approved'

        code, sc_card = call('POST', '/api/projects/harbor_demo/cards', {
            'card_id': 'sc_dock_01',
            'kind': 'scene',
            'body': {'title': '雨夜栈桥', 'goal': '核对涨潮水位', 'pov': 'char_lin',
                     'characters': ['char_lin'], 'story_time': '1', 'visibility': 'author_only'},
            'auto_approve': True,
        })
        assert code == 200 and sc_card['status'] == 'approved'

        # 3. Adopt story state machine (includes approved cards on main@r0)
        code, head = call('POST', '/api/projects/harbor_demo/adopt', {
            'entities': ['char_lin'],
            'predicates': ['location'],
            'include_approved_cards': True,
        })
        assert code == 200 and head == {'branch_id': 'main', 'revision': 0}

        # 4. Create chapter & scene bound to sc_dock_01
        code, ch = call('POST', '/api/projects/harbor_demo/chapters', {'index': 1, 'title': '第一章 夜潮'})
        assert code == 200
        code, sc = call('POST', '/api/projects/harbor_demo/scenes', {
            'chapter_id': ch['id'],
            'index': 1,
            'card': {'title': '雨夜栈桥', 'story': {'scene_ref': {'card_id': 'sc_dock_01', 'version': 1}, 'story_order': 1}},
        })
        assert code == 200

        # 5. Live POV context inspection (zero API calls)
        code, ctx = call('GET', f"/api/projects/harbor_demo/scenes/{sc['id']}/context?char_limit=16000")
        assert code == 200, ctx
        keys = [it['key'] for it in ctx['items']]
        assert 'brief' in keys and 'scene:sc_dock_01' in keys and 'pov:char_lin' in keys

        # 6. Manual draft -> StateDelta -> check_delta -> accept_batch -> chapter summary
        draft_text = '林沉踩上三号栈桥湿滑的木板，咸腥海风裹着夜雨扑面而来。怀表指针死死停在二十三点十五分。'
        code, saved_draft = call('POST', f"/api/projects/harbor_demo/scenes/{sc['id']}/draft", {'text': draft_text})
        assert code == 200
        draft_id = saved_draft['draft']['id']

        code, delta_res = call('POST', f"/api/projects/harbor_demo/scenes/{sc['id']}/delta", {
            'draft_id': draft_id,
            'operations': [{
                'op': 'set',
                'entity_id': 'char_lin',
                'predicate': 'location',
                'holder': 'WORLD',
                'claim': 'fact',
                'story_order': 1,
                'disclosure_order': [1, 1, 1],
                'expected_old': None,
                'new_value': '三号栈桥',
                'evidence': [{'draft_id': draft_id, 'start': 0, 'end': 14}],
            }],
        })
        assert code == 200 and delta_res['findings'] == []

        code, acc = call('POST', f"/api/projects/harbor_demo/scenes/{sc['id']}/accept", {
            'draft_id': draft_id,
            'delta_id': delta_res['delta']['id'],
        })
        assert code == 200 and acc['head'] == {'branch_id': 'main', 'revision': 1}
        assert (ws / 'harbor_demo' / '正文' / 'ch01_s01.md').read_text(encoding='utf-8') == draft_text

        code, summ = call('POST', '/api/projects/harbor_demo/chapters/1/summary', {
            'summary': '林沉夜探三号栈桥，确认停摆怀表指向23:15。',
        })
        assert code == 200 and summ['status'] == 'recorded'

        code, matrix = call('GET', '/api/projects/harbor_demo/state-matrix?story_order=5')
        assert code == 200 and matrix['matrix'][0]['cells']['WORLD'][0]['value'] == '三号栈桥'

        # 7. Pipeline dry-run & routing security guard
        code, bp = call('GET', '/api/pipeline/blueprint?scope=chapter')
        assert code == 200 and len(bp['design_steps']) == 14

        code, sim = call('POST', '/api/pipeline/simulate', {'scope': 'chapter', 'stage': 'anchor_design', 'project_name': 'harbor_demo'})
        assert code == 200 and 'plot_guard' in sim['continuity_ledger']

        code, bad_cfg = call('POST', '/api/config/preview', {
            'model': {'provider': 'openai_compat', 'base_url': 'https://api.example.com/v1',
                      'model': 'claude-opus-5-5', 'api_key_env': 'sk-secret1234567890abcdef'},
        })
        assert code == 400 and '严禁' in bad_cfg['error']

        code, saved_cfg = call('POST', '/api/config/save', {
            'model': {'provider': 'ollama', 'base_url': 'http://127.0.0.1:11434', 'model': 'gemini-4-carbon', 'timeout': 120},
            'params': {'temperature': 0.3},
            'stage_models': {'write': {'model': 'claude-opus-5-5'}},
        })
        assert code == 200 and saved_cfg['saved'] is True
        loaded = load_config(cfg_path)
        assert loaded.stage_models['write']['model'] == 'claude-opus-5-5'
    finally:
        server.shutdown()
        server.server_close()


def test_studio_live_catalog_joint_material_simulation() -> None:
    real_ws = Path(__file__).resolve().parents[1] / 'workspace'
    if not (real_ws / 'materials/adjudication.db').is_file():
        pytest.skip('Real catalog not present')
    svc = StudioService(workspace=real_ws)
    status = svc.system_status()
    assert status['catalog']['available'] is True
    assert status['catalog']['total_sources'] > 20000

    sim = svc.simulate_step_materials(
        scope='chapter',
        stage='character_design',
        brief_text='一部现实向刑侦悬疑小说，主角在追查旧港沉船案时发现昔日师父隐瞒关键证词，师徒信任与职责正面冲突。',
        constraints='第三人称单视角限制知情；情感克制，靠具体动作与试错代价呈现人物弧线。',
    )
    assert sim['catalog_available'] is True
    assert sim['sources_count'] >= 1
    assert sim['rendered_prompt_chars'] > 200
    if sim['sources_count'] >= 2:
        assert sim['joint_material_plan'] is not None
        assert sim['joint_material_plan']['priority'] == PRIORITY_HIERARCHY

    first_id = sim['sources'][0]['id']
    detail = svc.get_material_detail(first_id)
    assert detail['source']['id'] == first_id
    assert 'character_design' in detail['routed_stages']
