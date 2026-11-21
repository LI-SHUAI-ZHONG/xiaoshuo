from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
import venv

import pytest

from nw.studio import runtime
from nw.studio.api import StudioService
from nw.studio.repository import RepositorySync
from nw.studio.server import create_studio_server


@pytest.mark.skipif(os.name != 'nt', reason='Windows desktop shortcut')
@pytest.mark.parametrize('use_venv', [False, True])
def test_shortcut_batch_passes_its_checkout_to_the_client(tmp_path, use_venv):
    launcher = runtime.PROJECT / '启动写作客户端.bat'
    project = tmp_path / '含空格 的仓库'
    module = project / 'src/nw'
    module.mkdir(parents=True)
    (module / '__init__.py').touch()
    (project / launcher.name).write_bytes(launcher.read_bytes())
    (module / '__main__.py').write_text(
        'import json, sys\nfrom pathlib import Path\n'
        'Path("argv.json").write_text(json.dumps(sys.argv[1:]), encoding="utf-8")\n', encoding='utf-8')
    if use_venv:
        venv.EnvBuilder(with_pip=False).create(project / '.venv')
    env = {**os.environ, 'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']}
    result = subprocess.run(['cmd.exe', '/d', '/c', launcher.name], cwd=project, env=env,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
    assert result.returncode == 0 and not result.stderr, result.stderr
    assert json.loads((project / 'argv.json').read_text(encoding='utf-8')) == [
        '--config', str(project / 'studio.config.toml'), 'studio', '--host', '127.0.0.1', '--port', '8767', '--open-browser']
    (module / '__main__.py').write_text('raise SystemExit(7)\n', encoding='utf-8')
    assert subprocess.run(result.args, cwd=project, env=env, stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=20).returncode == 7


def test_desktop_reuses_matching_source_and_releases_only_an_idle_stale_backend(tmp_path, monkeypatch):
    project = tmp_path / 'client'
    source = project / 'src/nw/story.py'
    source.parent.mkdir(parents=True)
    source.write_text('# first', encoding='utf-8')
    service = StudioService(tmp_path / 'workspace')
    monkeypatch.setattr('nw.studio.repository.RepositorySync', lambda svc: RepositorySync(svc, project=project))
    server = create_studio_server(service, port=0)
    host, port = server.server_address
    closed = Event()

    def serve():
        try:
            server.serve_forever(poll_interval=.05)
        finally:
            server.server_close()
            closed.set()

    thread = Thread(target=serve, daemon=True)
    thread.start()
    try:
        old = runtime.identity(project, service, runtime.source_digest(project))
        assert runtime.reuse_desktop(host, port, old)
        with monkeypatch.context() as patch:
            patch.setattr(RepositorySync, 'prepare', lambda *_: pytest.fail('occupied port touched the workspace'))
            with pytest.raises(OSError):
                create_studio_server(service, host, port)
        with pytest.raises(ValueError, match='其他仓库'):
            runtime.reuse_desktop(host, port, {**old, 'workspace': str(tmp_path)})
        with pytest.raises(ValueError, match='拆解能力'):
            runtime.reuse_desktop(host, port, {**old, 'corpus_schema': 1})
        source.write_text('# second', encoding='utf-8')
        current = runtime.identity(project, service, runtime.source_digest(project))
        assert current['source_sha256'] != old['source_sha256']
        assert runtime._request(host, port, '/api/repository')[1]['restart_required']
        assert runtime._request(host, port, '/api/pipeline/simulate', {})[0] == 409
        server.production._workers['isolated-test'] = thread
        with pytest.raises(ValueError, match='正在运行'):
            runtime.reuse_desktop(host, port, current)
        del server.production._workers['isolated-test']
        assert not runtime.reuse_desktop(host, port, current)
        assert closed.wait(3)
        replacement = create_studio_server(service, host, port)
        worker = Thread(target=replacement.serve_forever, daemon=True)
        worker.start()
        try:
            assert runtime.reuse_desktop(host, port, current)
            catalog = runtime._request(host, port, '/api/corpus/catalog')[1]
            assert catalog['schema_version'] == current['corpus_schema']
            assert sorted(catalog['domains']) == current['domains']
        finally:
            replacement.shutdown()
            replacement.server_close()
            worker.join(3)
    finally:
        server.shutdown()
        thread.join(3)


def test_shortcut_refuses_the_shared_legacy_server_label():
    class Legacy(BaseHTTPRequestHandler):
        server_version = 'NovelWorkflowStudio/3.0'

        def do_GET(self):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"legacy"}')

    server = ThreadingHTTPServer(('127.0.0.1', 0), Legacy)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(ValueError, match='已有服务缺少新版'):
            runtime.reuse_desktop(*server.server_address, {})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)
