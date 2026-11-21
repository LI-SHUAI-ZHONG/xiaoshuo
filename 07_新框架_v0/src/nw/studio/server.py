"""Stdlib HTTP server for the Novel Workflow Studio (zero third-party dependencies)."""
from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sqlite3
import threading
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit
import webbrowser

from nw.studio.api import StudioService
from nw.studio import runtime

STATIC_DIR = (Path(__file__).resolve().parent / 'static').resolve()
_MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
}


def _first(query: dict[str, list[str]], key: str, default: str = '') -> str:
    vals = query.get(key)
    return vals[0] if vals else default


def create_studio_server(service: StudioService, host: str = '127.0.0.1', port: int = 8765) -> ThreadingHTTPServer:
    from nw.studio.library import LibraryService
    from nw.studio.production import ProductionService
    from nw.studio.production_routes import ProductionRoutes
    from nw.studio.repository import RepositorySync
    repository = RepositorySync(service)
    running = runtime.identity(repository.project, service, repository.loaded_source)

    class StudioHandler(BaseHTTPRequestHandler):
        server_version = 'NovelWorkflowStudio/3.0'

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, status: int, data: Any) -> None:
            raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True

        def _read_json(self, limit_mib: int = 8) -> dict[str, Any]:
            length = int(self.headers.get('Content-Length', '0') or '0')
            if length <= 0:
                return {}
            if length > limit_mib * 1024 * 1024:
                raise ValueError(f'请求体超过 {limit_mib}MB 上限')
            raw = self.rfile.read(length).decode('utf-8')
            val = json.loads(raw) if raw.strip() else {}
            if not isinstance(val, dict):
                raise ValueError('JSON 请求体必须是对象')
            return val

        def _serve_static(self, rel_path: str) -> None:
            name = 'index.html' if rel_path in ('', '/') else unquote(rel_path).lstrip('/')
            target = (STATIC_DIR / name).resolve()
            if not (target.is_relative_to(STATIC_DIR) and target.is_file()):
                self._send_json(HTTPStatus.NOT_FOUND, {'error': f'未找到静态资源: {name}'})
                return
            data = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', _MIME_TYPES.get(target.suffix.lower(), 'application/octet-stream'))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True

        def do_GET(self) -> None:
            if self.path.startswith('/api/') and not urlsplit(self.path).path.endswith('/events'):
                with repository.data_lock:
                    self._get()
            else:
                self._get()

        def _get(self) -> None:
            parts = urlsplit(self.path)
            path = parts.path
            query = parse_qs(parts.query)
            if not path.startswith('/api/'):
                self._serve_static(path)
                return
            try:
                segs = [unquote(s) for s in path.strip('/').split('/')][1:]
                if segs == ['runtime']:
                    return self._send_json(200, {**running, 'restart_required': repository.check_running_source()})
                if segs == ['repository']:
                    repository.check_running_source()
                    return self._send_json(200, repository.status())
                if routes.get(self, segs, query):
                    return
                if segs == ['status']:
                    return self._send_json(200, service.system_status())
                if segs == ['projects']:
                    return self._send_json(200, {'projects': service.list_projects()})
                if len(segs) == 2 and segs[0] == 'projects':
                    return self._send_json(200, service.project_overview(segs[1]))
                if len(segs) == 3 and segs[0] == 'projects' and segs[2] == 'cards':
                    return self._send_json(200, {'cards': service.list_cards(segs[1])})
                if len(segs) == 3 and segs[0] == 'projects' and segs[2] == 'jobs':
                    return self._send_json(200, service.list_jobs(segs[1]))
                if len(segs) == 3 and segs[0] == 'projects' and segs[2] == 'state-matrix':
                    rev_str = _first(query, 'revision')
                    disc_str = _first(query, 'disclosure')
                    disc = [int(x) for x in disc_str.split(',')] if disc_str else None
                    return self._send_json(200, service.inspect_state_matrix(
                        segs[1],
                        branch=_first(query, 'branch', 'main'),
                        revision=int(rev_str) if rev_str else None,
                        story_order=int(_first(query, 'story_order', '999999')),
                        disclosure=disc,
                    ))
                if len(segs) == 5 and segs[0] == 'projects' and segs[2] == 'scenes' and segs[4] == 'workbench':
                    return self._send_json(200, service.scene_workbench(
                        segs[1], segs[3], branch=_first(query, 'branch', 'main'),
                    ))
                if len(segs) == 6 and segs[0] == 'projects' and segs[2] == 'scenes' and segs[4] == 'drafts':
                    return self._send_json(200, service.get_draft(segs[1], segs[3], segs[5]))
                if len(segs) == 5 and segs[0] == 'projects' and segs[2] == 'scenes' and segs[4] == 'context':
                    return self._send_json(200, service.inspect_scene_context(
                        segs[1], segs[3],
                        branch=_first(query, 'branch', 'main'),
                        char_limit=int(_first(query, 'char_limit', '24000')),
                    ))
                if len(segs) == 5 and segs[0] == 'projects' and segs[2] == 'chapters' and segs[4] == 'ledger':
                    return self._send_json(200, service.inspect_chapter_ledger(
                        segs[1], int(segs[3]), branch=_first(query, 'branch', 'main'),
                    ))
                if segs == ['pipeline', 'blueprint']:
                    return self._send_json(200, service.pipeline_blueprint(_first(query, 'scope', 'chapter')))
                if segs == ['materials', 'search']:
                    return self._send_json(200, service.search_materials(
                        query=_first(query, 'q'),
                        state=_first(query, 'state'),
                        profile=_first(query, 'profile'),
                        stage=_first(query, 'stage'),
                        limit=int(_first(query, 'limit', '40')),
                        offset=int(_first(query, 'offset', '0')),
                    ))
                if segs == ['materials', 'detail']:
                    return self._send_json(200, service.get_material_detail(_first(query, 'id')))
                if segs == ['ledger', 'search']:
                    return self._send_json(200, service.search_f2_ledger(
                        query=_first(query, 'q'),
                        disposition=_first(query, 'disposition'),
                        corpus=_first(query, 'corpus'),
                        limit=int(_first(query, 'limit', '50')),
                        offset=int(_first(query, 'offset', '0')),
                    ))
                if segs == ['config', 'routing']:
                    return self._send_json(200, service.get_routing_config())
                self._send_json(404, {'error': f'未知 API 路径: {path}'})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True
            except FileNotFoundError as exc:
                self._send_json(404, {'error': str(exc)})
            except (ValueError, KeyError, sqlite3.Error) as exc:
                self._send_json(400, {'error': str(exc)})
            except Exception as exc:
                self._send_json(500, {'error': f'内部错误: {exc}'})

        def do_POST(self) -> None:
            if urlsplit(self.path).path in ('/api/repository/sync', '/api/runtime/reload'):
                return self._post()
            try:
                with repository.mutation():
                    self._post()
            except ValueError as exc:
                self._send_json(409, {'error': str(exc)})

        def _post(self) -> None:
            parts = urlsplit(self.path)
            path = parts.path
            if not path.startswith('/api/'):
                self._send_json(405, {'error': '仅 API 支持 POST'})
                return
            try:
                origin = self.headers.get('Origin')
                if origin:
                    source = urlsplit(origin)
                    target = urlsplit('http://' + self.headers.get('Host', ''))
                    if (source.scheme != 'http' or source.hostname not in ('localhost', '127.0.0.1', '::1')
                            or source.netloc.lower() != target.netloc.lower()):
                        return self._send_json(403, {'error': '只接受本地客户端的同源操作'})
                if self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/json':
                    return self._send_json(415, {'error': '请使用 application/json 请求体'})
                segs = [unquote(s) for s in path.strip('/').split('/')][1:]
                body = self._read_json(24 if segs == ['staging'] else 8)
                if segs == ['runtime', 'reload']:
                    if self.client_address[0] not in ('127.0.0.1', '::1'):
                        return self._send_json(403, {'error': '请从本机桌面快捷方式重新打开客户端。'})
                    try:
                        repository.release_for_reload(body)
                    except ValueError as exc:
                        return self._send_json(409, {'error': str(exc)})
                    self._send_json(200, {'closing': True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                if segs == ['repository', 'sync']:
                    return self._send_json(202, repository.trigger())
                if routes.post(self, segs, body):
                    return
                if segs == ['projects']:
                    return self._send_json(201, service.create_project(
                        str(body['dir_name']),
                        str(body.get('title') or body['dir_name']),
                        brief_text=str(body.get('brief_text') or ''),
                        constraints=str(body.get('constraints') or ''),
                    ))
                if len(segs) == 3 and segs[0] == 'projects':
                    proj = segs[1]
                    act = segs[2]
                    if act == 'brief':
                        return self._send_json(200, service.save_brief(proj, str(body['text']), str(body.get('constraints') or '')))
                    if act == 'bible':
                        return self._send_json(200, service.save_bible(proj, str(body['kind']), str(body['name']), str(body['body'])))
                    if act == 'chapters':
                        return self._send_json(200, service.create_chapter(proj, int(body['index']), str(body['title'])))
                    if act == 'scenes':
                        return self._send_json(200, service.create_scene(proj, str(body['chapter_id']), int(body['index']), body['card']))
                    if act == 'adopt':
                        return self._send_json(200, service.adopt_project_story(proj, body))
                    if act == 'fork':
                        return self._send_json(200, service.fork_branch(proj, str(body.get('branch') or 'main'), int(body['revision']), str(body['name'])))
                    if act == 'cards':
                        return self._send_json(200, service.save_author_card(proj, body))
                    if act == 'jobs':
                        return self._send_json(200, service.create_novel_job(proj, body))
                if len(segs) == 4 and segs[0] == 'projects' and segs[2] == 'cards':
                    proj = segs[1]
                    if segs[3] == 'decide':
                        return self._send_json(200, service.decide_project_card(
                            proj, str(body['card_id']), int(body['version']), str(body['decision']), str(body.get('reason') or ''),
                        ))
                    if segs[3] == 'link':
                        return self._send_json(200, service.add_card_link(
                            proj, str(body['source_id']), int(body['source_version']),
                            str(body['relation']), str(body['target_id']), int(body['target_version']),
                        ))
                if len(segs) == 4 and segs[0] == 'projects' and segs[2] == 'jobs' and segs[3] == 'cancel':
                    return self._send_json(200, service.cancel_novel_job(segs[1], str(body['job_id'])))
                if len(segs) == 5 and segs[0] == 'projects' and segs[2] == 'scenes':
                    proj, scene_id, act = segs[1], segs[3], segs[4]
                    if act == 'draft':
                        return self._send_json(200, service.save_manual_draft(
                            proj, scene_id, str(body['text']), branch=str(body.get('branch', 'main'))))
                    if act == 'delta':
                        return self._send_json(200, service.save_manual_delta(proj, body))
                    if act == 'accept':
                        return self._send_json(200, service.accept_scene_delta(proj, {**body, 'scene_id': scene_id}))
                if len(segs) == 5 and segs[0] == 'projects' and segs[2] == 'chapters' and segs[4] == 'summary':
                    return self._send_json(200, service.record_chapter_summary(
                        segs[1], int(segs[3]), str(body['summary']),
                        comparison=body.get('comparison'), branch=str(body.get('branch') or 'main'),
                    ))
                if segs == ['pipeline', 'simulate']:
                    return self._send_json(200, service.simulate_step_materials(
                        scope=str(body.get('scope') or 'chapter'),
                        stage=str(body.get('stage') or 'character_design'),
                        brief_text=str(body.get('brief_text') or ''),
                        constraints=str(body.get('constraints') or ''),
                        project_name=body.get('project_name'),
                        simulate_prior_products=bool(body.get('simulate_prior_products', True)),
                    ))
                if segs == ['config', 'preview']:
                    return self._send_json(200, {'toml': service.render_config_toml(body)})
                if segs == ['config', 'save']:
                    return self._send_json(200, service.save_routing_config(body))
                self._send_json(404, {'error': f'未知 POST API 路径: {path}'})
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True
            except FileNotFoundError as exc:
                self._send_json(404, {'error': str(exc)})
            except (ValueError, KeyError, sqlite3.Error) as exc:
                self._send_json(400, {'error': str(exc)})
            except Exception as exc:
                self._send_json(500, {'error': f'内部错误: {exc}'})

    class StudioServer(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = not hasattr(socket, 'SO_EXCLUSIVEADDRUSE')

        def server_bind(self) -> None:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

        def shutdown(self) -> None:
            self.studio_shutdown.set()
            super().shutdown()

        def server_close(self) -> None:
            self.studio_shutdown.set()
            repository.close()
            super().server_close()

    server = StudioServer((host, int(port)), StudioHandler, bind_and_activate=False)
    server.studio_shutdown = threading.Event()
    try:
        server.server_bind()
        server.server_activate()
        repository.prepare()
        service.repository_sync = repository
        library = LibraryService(service.workspace, config_path=service.config_path, ledger_path=service.ledger_path)
        production = ProductionService(service, library)
        routes = ProductionRoutes(production, library)
        repository.attach(production, library)
        server.production = production
        server.library = library
        server.repository = repository
        repository.start()
    except BaseException:
        server.server_close()
        raise
    return server


def run_studio(workspace: Path | None = None, *, config_path: Path | None = None,
               host: str = '127.0.0.1', port: int = 8765, open_browser: bool = False) -> None:
    service = StudioService(workspace=workspace, config_path=config_path)
    if open_browser and runtime.reuse_desktop(host, port, runtime.identity(
            runtime.PROJECT, service, runtime.source_digest(runtime.PROJECT))):
        webbrowser.open(f'http://{host}:{port}/')
        return
    httpd = create_studio_server(service, host=host, port=port)
    actual_host, actual_port = httpd.server_address[:2]
    url = f'http://{actual_host}:{actual_port}/'
    print(f'小说创作工作流客户端已启动: {url}')
    print(f'工作区路径: {service.workspace}')
    print('v3 生产客户端：立项、制作台、书架、图鉴、知识库与预存库。模型密钥仅从环境读取。按 Ctrl+C 停止。')
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
