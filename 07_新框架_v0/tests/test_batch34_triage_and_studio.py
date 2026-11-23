"""Batch 34 — 专项测试：F2台账分类处理、前端修复与管道完整性验证。"""
import json
import os
import pathlib
import threading
from http.server import HTTPServer

import pytest

# ── F2 台账结项验证 ──────────────────────────────────────────────

LEDGER = pathlib.Path(os.environ.get(
    'NOVEL_LEDGER',
    str(pathlib.Path(__file__).resolve().parents[1] / 'workspace' / 'materials' / 'F2_统一问题台账.jsonl'),
))


@pytest.fixture(scope='module')
def ledger_data():
    """加载 F2 台账全部条目。"""
    if not LEDGER.is_file():
        pytest.skip('F2 台账文件不存在')
    items = []
    for line in LEDGER.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def test_ledger_total_count(ledger_data):
    """台账总条目数不减少。"""
    assert len(ledger_data) >= 2532


def test_ledger_no_unknown_status(ledger_data):
    """台账中不出现未知状态。"""
    valid = {'open', 'resolved', 'discarded', 'recovered_via_verified_archive'}
    for item in ledger_data:
        assert item['status'] in valid, f"{item['issue_id']} has unknown status {item['status']}"


def test_batch34_resolved_have_resolution(ledger_data):
    """Batch 34 结项的条目必须有 resolution 字段。"""
    for item in ledger_data:
        res = item.get('resolution')
        if item['status'] == 'resolved' and isinstance(res, dict) and res.get('batch') == '34':
            assert 'decision' in res, f"{item['issue_id']} missing resolution.decision"
            assert 'date' in res, f"{item['issue_id']} missing resolution.date"


def test_batch34_discarded_have_resolution(ledger_data):
    """Batch 34 废弃的条目必须有 resolution 字段。"""
    for item in ledger_data:
        if item['status'] == 'discarded' and item.get('resolution', {}).get('batch') == '34':
            assert 'decision' in item['resolution'], f"{item['issue_id']} missing resolution.decision"


def test_open_count_decreased(ledger_data):
    """开放条目数应从 1684 减少。"""
    open_count = sum(1 for item in ledger_data if item['status'] == 'open')
    assert open_count < 1684, f"Open count {open_count} not decreased from 1684"


# ── Studio 前端修复验证 ──────────────────────────────────────────

def test_app_js_switch_tab_has_catch():
    """v3 replaces the six legacy tabs with one error-handled module router.

    Migration: docs/客户端v3初版验收.md records the replaced v2 contracts.
    """
    js_path = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'nw' / 'studio' / 'static' / 'js' / 'app.js'
    js = js_path.read_text(encoding='utf-8')
    assert 'hashchange' in js
    assert 'catch' in js, '路由加载失败必须向作者显示错误'


def test_app_js_json_parse_has_friendly_error():
    """JSON.parse 调用应有友好的错误提示。"""
    js_path = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'nw' / 'studio' / 'static' / 'app.js'
    if not js_path.is_file():
        pytest.skip('app.js 不存在')
    js = js_path.read_text(encoding='utf-8')
    # The deltaOpsJson parse should be wrapped
    assert '格式不正确' in js, 'JSON.parse 友好错误消息缺失'


def test_server_path_traversal_check(tmp_path, monkeypatch):
    """v3: nested modules are served; prefix-sharing sibling paths stay private.

    Replaces the unsafe v2 assertion requiring str.startswith(STATIC_DIR).
    """
    from http.client import HTTPConnection
    from nw.studio import server as module
    from nw.studio.api import StudioService

    static = tmp_path / 'static'
    (static / 'js').mkdir(parents=True)
    (static / 'index.html').write_text(
        '<meta name="studio-source" content="__STUDIO_SOURCE_SHA256__">', encoding='utf-8')
    (static / 'js' / 'app.js').write_text('export const safe = true;', encoding='utf-8')
    sibling = tmp_path / 'static-private'
    sibling.mkdir()
    (sibling / 'secret.txt').write_text('DO_NOT_DISCLOSE_93742', encoding='utf-8')
    monkeypatch.setattr(module, 'STATIC_DIR', static.resolve())
    server = module.create_studio_server(StudioService(tmp_path / 'workspace'), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for path, expected in [('/js/app.js', 200), ('/../static-private/secret.txt', 404),
                               ('/%2e%2e/static-private/secret.txt', 404),
                               ('/%2e%2e%2fstatic-private%2fsecret.txt', 404)]:
            connection = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            connection.request('GET', path)
            response = connection.getresponse()
            assert response.status == expected, path
            assert b'DO_NOT_DISCLOSE_93742' not in response.read(), path
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_api_ledger_cache_invalidation():
    """api.py 台账缓存应有 mtime 失效机制。"""
    api_path = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'nw' / 'studio' / 'api.py'
    if not api_path.is_file():
        pytest.skip('api.py 不存在')
    code = api_path.read_text(encoding='utf-8')
    assert '_ledger_mtime' in code, '台账缓存应包含 mtime 字段'
    assert 'st_mtime' in code, '台账缓存应使用 st_mtime 检测文件变更'


# ── 管道结构完整性验证 ──────────────────────────────────────────

def test_phase_routes_requires_all_14_steps():
    """phase_routes.py REQUIRES 应包含全部 14 步。"""
    from nw.materials.phase_routes import REQUIRES
    expected_steps = [
        'type_selection', 'type_adaptation', 'world_design', 'character_design',
        'static_relations', 'plot_design', 'event_design', 'action_design',
        'scene_design', 'state_transition', 'state_propagation', 'anchor_design',
        'expression_design', 'bind_scope',
    ]
    for step in expected_steps:
        assert step in REQUIRES, f'步骤 {step} 不在 REQUIRES 中'


def test_step_guard_imports():
    """step_guard.py 三大功能可正常导入。"""
    from nw.materials.step_guard import (
        build_continuity_ledger,
        build_joint_material_plan,
        validate_cross_step_consistency,
    )
    assert callable(build_continuity_ledger)
    assert callable(build_joint_material_plan)
    assert callable(validate_cross_step_consistency)


def test_write_prompt_starts_correctly():
    """WRITE_PROMPT 保持向后兼容的开头。"""
    from nw.context.story import WRITE_PROMPT
    assert WRITE_PROMPT.startswith('按作者约束和本场任务写正文'), f'WRITE_PROMPT 开头已变更: {WRITE_PROMPT[:40]}'
