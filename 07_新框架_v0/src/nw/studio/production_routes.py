"""HTTP translation for the production client, keeping the original API compatible."""
import json
from typing import Any
from urllib.parse import quote


def first(query: dict, key: str, default: str = '') -> str:
    return query.get(key, [default])[0]


class ProductionRoutes:
    def __init__(self, production: Any, library: Any) -> None:
        self.production, self.library = production, library

    def get(self, handler: Any, segs: list[str], query: dict) -> bool:
        lib, app = self.library, self.production
        data = None
        if segs == ['genres']:
            data = lib.genres()
        elif segs == ['recommend']:
            data = lib.recommend(first(query, 'slot', 'genre'), first(query, 'types').split(',') if first(query, 'types') else [])
        elif segs == ['options']:
            data = lib.options(first(query, 'slot', 'tone'), first(query, 'parent'))
        elif segs == ['novels']:
            data = app.list(first(query, 'status'))
        elif len(segs) >= 2 and segs[0] == 'novels':
            ident = segs[1]
            if len(segs) == 2:
                data = app.detail(ident)
            elif len(segs) == 3:
                action = segs[2]
                if action == 'progress':
                    data = app.progress(ident)
                elif action == 'branches':
                    data = app.branch_status(ident)
                elif action == 'gates':
                    data = app.gates(ident)
                elif action == 'timeline':
                    data = app.timeline(ident)
                elif action == 'quality':
                    data = app.quality(ident, first(query, 'scene'))
                elif action == 'export':
                    text, filename = app.export(ident, first(query, 'fmt', 'txt'), first(query, 'scope', 'book'))
                    raw = text.encode('utf-8')
                    handler.send_response(200)
                    handler.send_header('Content-Type', 'text/plain; charset=utf-8')
                    handler.send_header('Content-Disposition', f"attachment; filename*=UTF-8''{quote(filename)}")
                    handler.send_header('Content-Length', str(len(raw)))
                    handler.end_headers()
                    handler.wfile.write(raw)
                    return True
                elif action == 'events':
                    self.events(handler, ident)
                    return True
        elif segs == ['staging']:
            data = lib.list_staging(first(query, 'status'))
        elif len(segs) == 2 and segs[0] == 'staging':
            data = lib.get_staging(segs[1])
        elif len(segs) == 3 and segs[:2] == ['kb', 'types']:
            data = lib.get_type(segs[2])
        elif segs == ['kb', 'items']:
            data = lib.items(first(query, 'slot'), first(query, 'types').split(',') if first(query, 'types') else [])
        elif segs == ['kb', 'upgrades']:
            data = lib.upgrades(first(query, 'status'))
        if data is None:
            return False
        handler._send_json(200, data)
        return True

    def post(self, handler: Any, segs: list[str], body: dict) -> bool:
        lib, app = self.library, self.production
        data, status = None, 200
        if segs == ['novels']:
            data, status = app.create(body), 201
        elif len(segs) >= 3 and segs[0] == 'novels':
            ident, action = segs[1:3]
            if len(segs) == 3:
                if action == 'run':
                    data = app.run(ident, body)
                elif action == 'retry':
                    data = app.run(ident, body, retry=True)
                elif action == 'pause':
                    data = app.pause(ident)
                elif action == 'cancel':
                    data = app.cancel(ident)
                elif action == 'finish':
                    data = app.finish(ident)
            elif len(segs) == 4 and action == 'gates':
                data = app.decide(ident, segs[3], body)
            elif len(segs) == 4 and action == 'branches':
                branch_actions = {'fork': app.fork_branch, 'select': app.select_branch, 'promote': app.promote_branch}
                if segs[3] in branch_actions:
                    data = branch_actions[segs[3]](ident, body)
        elif segs == ['staging']:
            data, status = lib.import_book(body), 201
        elif len(segs) == 3 and segs[0] == 'staging':
            actions = {'review': lib.review_book, 'decompose': lib.decompose_book, 'verify': lib.verify_book}
            if segs[2] in actions:
                data = actions[segs[2]](segs[1], body)
        elif len(segs) == 3 and segs[:2] == ['kb', 'types']:
            data = lib.save_type(segs[2], body)
        elif len(segs) == 3 and segs[:2] == ['kb', 'upgrades']:
            data = lib.review_upgrade(segs[2], body)
        if data is None:
            return False
        handler._send_json(status, data)
        return True

    def events(self, handler: Any, ident: str) -> None:
        initial = self.production.progress(ident)
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        handler.send_header('Cache-Control', 'no-cache')
        handler.send_header('Connection', 'close')
        handler.send_header('X-Accel-Buffering', 'no')
        handler.end_headers()
        previous = None
        ticks = 0
        try:
            while not handler.server.studio_shutdown.is_set():
                progress = initial if previous is None else self.production.progress(ident)
                raw = json.dumps(progress, ensure_ascii=False, separators=(',', ':'))
                if raw != previous:
                    handler.wfile.write(f'event: progress\ndata: {raw}\n\n'.encode('utf-8'))
                    handler.wfile.flush()
                    previous = raw
                elif ticks % 30 == 0:
                    handler.wfile.write(b': keep-alive\n\n')
                    handler.wfile.flush()
                ticks += 1
                handler.server.studio_shutdown.wait(0.35)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            handler.close_connection = True
