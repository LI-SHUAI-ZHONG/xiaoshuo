"""Match the desktop shortcut to the code and checkout actually serving requests."""
from __future__ import annotations

import hashlib
from http.client import HTTPConnection, HTTPException
import json
from pathlib import Path
import time


PROJECT = Path(__file__).resolve().parents[3]


def source_digest(project: Path) -> str:
    source = project / 'src'
    files = [p for p in source.rglob('*') if p.suffix in {'.py', '.js', '.css', '.html', '.json', '.jsonl', '.toml', '.ico', '.svg'}]
    files.extend(path for path in (project / 'pyproject.toml', project / 'studio.repository.toml') if path.is_file())
    total = hashlib.sha256()
    for path in sorted(files):
        total.update(path.relative_to(project).as_posix().encode('utf-8') + b'\0')
        total.update(hashlib.sha256(path.read_bytes()).digest())
    return total.hexdigest()


def identity(project: Path, service, digest: str) -> dict:
    from nw.materials.story_policies import current
    from nw.studio.corpus_catalog import DOMAINS, SCHEMA_VERSION

    return {'project': str(project.resolve()), 'workspace': str(service.workspace),
            'config_path': str(service.config_path), 'source_sha256': digest,
            'corpus_schema': SCHEMA_VERSION, 'domains': sorted(DOMAINS), 'story_policies': current()}


def _request(host: str, port: int, path: str, body: dict | None = None) -> tuple[int, dict]:
    connection = HTTPConnection(host, port, timeout=4)
    try:
        if body is None:
            connection.request('GET', path)
        else:
            connection.request('POST', path, json.dumps(body).encode('utf-8'), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        data = json.loads(response.read(65536))
        return response.status, data if isinstance(data, dict) else {}
    finally:
        connection.close()


def reuse_desktop(host: str, port: int, expected: dict) -> bool:
    """Return True only for the same live workflow. An idle stale peer may release the port."""
    if port == 0 or host not in ('localhost', '127.0.0.1', '::1'):
        return False
    try:
        status, running = _request(host, port, '/api/runtime')
    except ConnectionRefusedError:
        return False
    except (OSError, HTTPException, ValueError) as exc:
        raise ValueError('端口上的服务未返回客户端版本。请检查已有启动窗口再打开桌面快捷方式。') from exc
    if status != 200 or not running.get('source_sha256'):
        raise ValueError('已有服务缺少新版运行标识。请在原客户端启动终端按 Ctrl+C 正常退出，再双击桌面快捷方式。')
    if any(not running.get(k) or Path(running[k]) != Path(expected[k]) for k in ('project', 'workspace', 'config_path')):
        raise ValueError('当前端口由其他仓库、工作区或配置使用，请检查已打开的客户端。')
    if running['source_sha256'] == expected['source_sha256'] and not running.get('restart_required'):
        if any(running.get(k) != expected[k] for k in ('corpus_schema', 'domains', 'story_policies')):
            raise ValueError('运行中的拆解能力或制作校验与仓库声明不同，请从原启动终端重启客户端。')
        return True
    status, reply = _request(host, port, '/api/runtime/reload', {
        'loaded': running['source_sha256'], 'target': expected['source_sha256']})
    if status != 200 or not reply.get('closing'):
        raise ValueError(reply.get('error') or '已有客户端尚未结束，请稍后再打开快捷方式。')
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            status, peer = _request(host, port, '/api/runtime')
        except ConnectionRefusedError:
            return False
        except (ConnectionResetError, HTTPException):
            pass
        else:
            if status == 200 and all(peer.get(k) == v for k, v in expected.items()) and not peer.get('restart_required'):
                return True
        time.sleep(.1)
    raise ValueError('旧客户端正在退出，端口仍在使用。请稍后再打开快捷方式。')
