"""v3 migration of the former v2 frontend contract tests.

The six-tab, giant-single-file assertions are intentionally replaced. See
`docs/客户端v3初版验收.md`; no ledger/backend coverage was removed.
"""
from html.parser import HTMLParser
import base64
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / 'src' / 'nw' / 'studio' / 'static'


class Shell(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def shell():
    result = Shell()
    result.feed((STATIC / 'index.html').read_text(encoding='utf-8'))
    return result


def test_html_loads_only_the_v3_module_entrypoint():
    scripts = [attrs for tag, attrs in shell().tags if tag == 'script']
    assert scripts == [{'type': 'module', 'src': '/js/app.js'}]
    assert (STATIC / 'js' / 'app.js').is_file()


def test_shell_contains_unique_accessible_regions():
    tags = shell().tags
    ids = [attrs['id'] for _, attrs in tags if 'id' in attrs]
    assert len(ids) == len(set(ids)), 'Duplicate IDs make controls target the wrong region'
    assert {'activityBar', 'sidebar', 'contentArea', 'bottomPanel', 'inspector', 'statusConnection'} <= set(ids)
    assert any(tag == 'nav' and attrs.get('aria-label') for tag, attrs in tags)
    assert any(tag == 'main' for tag, _ in tags)
    assert any(attrs.get('aria-live') == 'polite' for _, attrs in tags)


def test_shell_loads_all_local_styles_and_mobile_viewport():
    tags = shell().tags
    styles = [attrs['href'] for tag, attrs in tags if tag == 'link' and attrs.get('rel') == 'stylesheet']
    assert styles
    assert all(href.startswith('/css/') and (STATIC / href.lstrip('/')).is_file() for href in styles)
    assert any(tag == 'meta' and attrs.get('name') == 'viewport' and 'device-width' in attrs['content'] for tag, attrs in tags)


def test_search_and_notifications_are_real_dialogs():
    tags = shell().tags
    dialogs = {attrs.get('id') for tag, attrs in tags if tag == 'dialog'}
    assert {'searchOverlay', 'notificationPanel', 'modalBackdrop', 'drawer'} <= dialogs


@pytest.mark.parametrize('page', ['home', 'studio', 'library', 'book', 'atlas', 'kb', 'staging', 'settings'])
def test_production_pages_are_modules(page):
    text = (STATIC / 'js' / 'pages' / f'{page}.js').read_text(encoding='utf-8')
    assert re.search(r'\bexport\b', text)
    assert 'innerHTML' in text or 'render' in text


def test_all_static_module_dependencies_exist():
    for path in (STATIC / 'js').rglob('*.js'):
        source = path.read_text(encoding='utf-8')
        for specifier in re.findall(r'(?:from\s*|import\s*\()\s*[\"\']([^\"\']+)[\"\']', source):
            assert specifier.startswith(('.', '/')), f'Runtime third-party dependency: {path}: {specifier}'
            target = STATIC / specifier.lstrip('/') if specifier.startswith('/') else path.parent / specifier
            assert target.resolve().is_relative_to(STATIC.resolve()) and target.is_file(), f'{path}: {specifier}'


def node_run(source):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is an optional local JS verification tool, not a runtime dependency')
    result = subprocess.run([node, '--input-type=module'], input=source, encoding='utf-8', capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_every_es_module_parses_without_a_build_step():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node not installed')
    for path in (STATIC / 'js').rglob('*.js'):
        result = subprocess.run([node, '--input-type=module', '--check'], input=path.read_text(encoding='utf-8'), encoding='utf-8', capture_output=True, timeout=10)
        assert result.returncode == 0, f'{path}: {result.stderr}'


def test_api_adapter_sends_json_and_propagates_errors():
    source = base64.b64encode((STATIC / 'js' / 'api.js').read_bytes()).decode('ascii')
    node_run(f'''
import assert from 'node:assert/strict';
const {{api, ApiError}} = await import('data:text/javascript;base64,{source}');
let seen;
globalThis.fetch = async (url, options) => {{ seen = {{url, options}}; return {{ok:true, json:async()=>({{id:'saved'}})}}; }};
assert.equal((await api.post('/novels', {{title:'甲'}})).id, 'saved');
assert.equal(seen.url, '/api/novels');
assert.equal(seen.options.headers['Content-Type'], 'application/json');
assert.deepEqual(JSON.parse(seen.options.body), {{title:'甲'}});
globalThis.fetch = async () => ({{ok:false, status:400, json:async()=>({{error:'必须审核证据'}})}});
await assert.rejects(api.post('/staging/x/verify', {{}}), e => e instanceof ApiError && e.status===400 && e.message==='必须审核证据');
globalThis.fetch = async () => ({{ok:true, status:200, json:async()=>{{throw new Error('invalid')}}}});
await assert.rejects(api.get('/novels'));
''')


def test_theme_and_mobile_layout_use_the_v3_styles():
    css = '\n'.join(path.read_text(encoding='utf-8') for path in (STATIC / 'css').rglob('*.css'))
    assert 'data-theme="light"' in css or "data-theme='light'" in css
    assert '--accent' in css and '--font-serif' in css
    assert '959px' in css or '960px' in css
    assert 'prefers-reduced-motion' in css


def test_packaged_client_includes_nested_assets():
    import tomllib
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    patterns = data['tool']['setuptools']['package-data']['nw.studio']
    assert 'static/js/pages/*.js' in patterns
    assert 'static/js/components/*.js' in patterns
    assert 'static/css/*.css' in patterns
