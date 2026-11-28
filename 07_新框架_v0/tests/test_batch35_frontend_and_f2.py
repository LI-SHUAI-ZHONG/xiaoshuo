"""Batch 35 regression tests: TEMP redirect, F2 ledger processing, and frontend enhancements."""
import json
import os
import pathlib
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ── P0: conftest.py TEMP redirect ──

def test_conftest_exists_and_redirects_temp():
    """conftest.py should redirect TEMP to D: drive."""
    conftest = ROOT / 'conftest.py'
    assert conftest.is_file(), 'conftest.py not found'
    text = conftest.read_text(encoding='utf-8')
    assert 'TEMP' in text
    assert 'tmptest' in text or 'TMP' in text


def test_tempfile_uses_d_drive():
    """tempfile.tempdir should point to D: after conftest runs."""
    # conftest.py should have already set this via pytest_configure
    td = tempfile.gettempdir()
    # On this machine, D: should be the temp dir
    assert 'D:' in td or 'tmptest' in td or os.environ.get('TEMP', '').startswith('D:'), \
        f'TEMP not on D: drive: {td}'


# ── P1: F2 ledger batch 35 processing ──

def test_f2_ledger_batch35_resolved_count():
    """After Batch 35, resolved count should be >= 2320."""
    ledger = ROOT / 'workspace' / 'materials' / 'F2_统一问题台账.jsonl'
    if not ledger.is_file():
        return  # workspace is gitignored
    resolved = 0
    for line in ledger.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get('status') == 'resolved':
            resolved += 1
    assert resolved >= 2320, f'Expected ≥2320 resolved, got {resolved}'


def test_f2_ledger_open_count_is_zero():
    """After Batch 38 authoritative completion, all 117 previously open items are resolved (open == 0)."""
    ledger = ROOT / 'workspace' / 'materials' / 'F2_统一问题台账.jsonl'
    if not ledger.is_file():
        return
    rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
    open_count = sum(1 for obj in rows if obj.get('status') == 'open')
    resolved_count = sum(1 for obj in rows if obj.get('status') == 'resolved')
    assert open_count == 0, f'Expected 0 open after Batch 38, got {open_count}'
    assert resolved_count >= 2437, f'Expected ≥2437 resolved after Batch 38, got {resolved_count}'


def test_f2_batch35_resolutions_have_correct_model():
    """All Batch 35 resolutions should reference gemini-4-carbon."""
    ledger = ROOT / 'workspace' / 'materials' / 'F2_统一问题台账.jsonl'
    if not ledger.is_file():
        return
    for line in ledger.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        res = obj.get('resolution')
        if isinstance(res, dict) and res.get('batch') == '35':
            assert res.get('model') == 'gemini-4-carbon', \
                f'{obj["issue_id"]}: model={res.get("model")}'


# ── P2: Frontend enhancements ──

def test_zen_reader_html_present():
    """v3 renders reader/diff inside the actual Studio module, not a hidden shell.

    See docs/客户端v3初版验收.md for the explicit migration of old DOM contracts.
    """
    html = (ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js' / 'pages' / 'studio.js').read_text(encoding='utf-8')
    assert 'zenReaderContainer' in html
    assert 'zenDiffContainer' in html
    assert 'btnZenDiff' in html
    assert 'btnZenRead' in html


def test_svg_graph_html_present():
    """v3 replaces the old graph panel with readable design output cards."""
    js = (ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js' / 'ui.js').read_text(encoding='utf-8')
    assert 'readable' in js
    assert 'design-card' in js
    assert 'esc(' in js


def test_job_stepper_html_present():
    """v3 production tree replaces the old Job Stepper drawer."""
    root = ROOT / 'src' / 'nw' / 'studio' / 'static' / 'js'
    js = '\n'.join(path.read_text(encoding='utf-8') for path in root.rglob('*.js'))
    assert '/progress' in js
    assert 'ProgressTree' in js
    assert 'EventSource' in js


def test_app_js_zen_reader_functions():
    """app.js should contain Zen Reader diff and read functions."""
    js = (ROOT / 'src' / 'nw' / 'studio' / 'static' / 'app.js').read_text(encoding='utf-8')
    assert 'renderZenDiff' in js
    assert 'renderZenRead' in js
    assert 'simpleDiff' in js
    assert 'populateZenSelects' in js


def test_app_js_svg_graph_function():
    """app.js should contain the SVG relationship graph renderer."""
    js = (ROOT / 'src' / 'nw' / 'studio' / 'static' / 'app.js').read_text(encoding='utf-8')
    assert 'renderRelationshipGraph' in js
    assert 'node-character' in js or 'node-circle' in js


def test_app_js_job_stepper_function():
    """app.js should contain the Job Stepper Drawer renderer."""
    js = (ROOT / 'src' / 'nw' / 'studio' / 'static' / 'app.js').read_text(encoding='utf-8')
    assert 'refreshJobDrawer' in js
    assert 'JOB_STEPS' in js


def test_styles_css_has_zen_and_graph_styles():
    """styles.css should contain styles for Zen Reader, SVG graph, and job stepper."""
    css = (ROOT / 'src' / 'nw' / 'studio' / 'static' / 'styles.css').read_text(encoding='utf-8')
    assert '.zen-reader-container' in css
    assert '.svg-graph-container' in css
    assert '.job-stepper-content' in css
    assert '.diff-add' in css
    assert '.node-circle' in css


def test_api_get_draft_method_exists():
    """api.py should have a get_draft method."""
    api_text = (ROOT / 'src' / 'nw' / 'studio' / 'api.py').read_text(encoding='utf-8')
    assert 'def get_draft(' in api_text


def test_api_list_jobs_method_exists():
    """api.py should have a list_jobs method."""
    api_text = (ROOT / 'src' / 'nw' / 'studio' / 'api.py').read_text(encoding='utf-8')
    assert 'def list_jobs(' in api_text


def test_server_draft_route_exists():
    """server.py should route GET for individual drafts."""
    srv_text = (ROOT / 'src' / 'nw' / 'studio' / 'server.py').read_text(encoding='utf-8')
    assert 'get_draft' in srv_text


def test_server_jobs_route_exists():
    """server.py should route GET for jobs list."""
    srv_text = (ROOT / 'src' / 'nw' / 'studio' / 'server.py').read_text(encoding='utf-8')
    assert 'list_jobs' in srv_text
