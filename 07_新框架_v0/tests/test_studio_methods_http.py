"""Real HTTP requests exercise method editing, evidence checks and version review."""
import http.client
import json
import threading

import pytest

from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
from test_studio_methods import SOURCE


@pytest.fixture
def client(tmp_path):
    studio = StudioService(tmp_path / 'isolated-http', config_path=tmp_path / 'missing.toml')
    server = create_studio_server(studio, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(method, path, body=None, origin=None):
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        connection.request(method, path, json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None,
                           headers)
        response = connection.getresponse()
        result = response.status, response.read().decode('utf-8')
        connection.close()
        if path.startswith('/api/'):
            return result[0], json.loads(result[1])
        return result
    try:
        yield request
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_method_endpoints_preserve_complete_versions_and_require_real_evidence(client):
    status, catalog = client('GET', '/api/kb/method-catalog')
    assert status == 200 and len(catalog['tasks']) == 21
    status, empty = client('GET', '/api/kb/methods')
    assert status == 200 and empty['methods'] == []
    status, book = client('POST', '/api/staging', {'title': '[FAKE] HTTP证据', 'filename': 'http.md', 'text': SOURCE})
    assert status == 201
    assert client('POST', f'/api/staging/{book["id"]}/review', {'types': ['GENRE_XUANYI'], 'decompose': False})[0] == 200
    status, evidence = client('POST', '/api/kb/method-evidence', {'book_id': book['id'], 'quote': '测试选择与后果。',
                                                               'explanation': '[FAKE] HTTP原文定位'})
    assert status == 200 and evidence['start'] == SOURCE.index('测试选择与后果。')
    body = {'title': '[FAKE] HTTP方法', 'tasks': ['world_rules'], 'scopes': ['book'],
        'applicability': ['[FAKE] 有类型边界'],
        'prerequisites': [{'key': 'i1', 'input_kind': 'type_adaptation', 'artifact': '[FAKE] 边界', 'requirement': '[FAKE] 已批准'}],
        'operations': [{'key': 'p1', 'instruction': '[FAKE] 定义限制', 'input_keys': ['i1'], 'output_keys': ['o1']}],
        'outputs': [{'key': 'o1', 'stage': 'world_design', 'field': 'members', 'artifact_kind': 'world', 'description': '[FAKE] 世界规则卡'}],
        'downstream': [{'output_key': 'o1', 'consumer': 'character_design', 'usage': '[FAKE] 约束人物能力'}],
        'acceptance': [{'output_key': 'o1', 'check': '[FAKE] 核对能力边界', 'evidence_required': '[FAKE] 实际世界与人物卡'}],
        'evidence': [evidence], 'non_applicability': ['[FAKE] 未批准适配时先补设计']}
    status, saved = client('POST', '/api/kb/methods', {'body': body, 'expected_version': 0})
    assert status == 201 and saved['issues'] == []
    ident = saved['id']
    status, approved = client('POST', f'/api/kb/methods/{ident}/review', {'version': 1, 'decision': 'approve', 'note': '[FAKE] 证据及引用已核对'})
    assert status == 200 and approved['available']
    assert client('GET', '/api/kb/methods?task=world_rules&scope=book&status=approved')[1]['total'] == 1
    body['title'] += '第二版'
    status, revised = client('POST', f'/api/kb/methods/{ident}', {'body': body, 'expected_version': 1})
    assert status == 200 and revised['version'] == 2
    assert client('GET', f'/api/kb/methods/{ident}?version=1')[1]['body']['title'] == '[FAKE] HTTP方法'
    assert client('POST', f'/api/kb/methods/{ident}', {'body': body, 'expected_version': 1})[0] == 400
    assert client('POST', '/api/kb/method-evidence', {'book_id': book['id'], 'quote': '[FAKE] 原文不存在'})[0] == 400


def test_invalid_filters_unknown_versions_and_mutation_origins_are_explicit(client):
    for path in ('/api/kb/methods?scope=unknown', '/api/kb/methods?limit=1000',
                 '/api/kb/methods?offset=-1', '/api/kb/methods?limit=nan'):
        assert client('GET', path)[0] == 400
    assert client('GET', '/api/kb/methods/nonexistent')[0] == 404
    assert client('POST', '/api/kb/methods', {'body': {}, 'expected_version': 0}, 'https://untrusted.example')[0] == 403


def test_new_ui_modules_are_served_by_the_same_client(client):
    status, code = client('GET', '/js/pages/methods.js')
    assert status == 200 and 'export async function renderMethods' in code
    status, kb = client('GET', '/js/pages/kb.js')
    assert status == 200 and "await renderMethods(ctx)" in kb and "page==='legacy'" in kb
