"""HTTP translation for the production client, keeping the original API compatible."""
from contextlib import nullcontext
import json
from dataclasses import asdict
from typing import Any
from urllib.parse import quote
from nw.studio import catalog, method_routes, corpus_routes


def first(query: dict, key: str, default: str = '') -> str:
    return query.get(key, [default])[0]


class ProductionRoutes:
    def __init__(self, production: Any, library: Any, *, data_lock: Any = None) -> None:
        self.production, self.library, self.data_lock = production, library, data_lock

    def get(self, handler: Any, segs: list[str], query: dict) -> bool:
        lib, app = self.library, self.production
        data = corpus_routes.get(lib, segs, query)
        if data is None:
            data = method_routes.get(lib, segs, query)
        if data is not None:
            handler._send_json(200, data)
            return True
        if segs == ['genres']:
            data = {**lib.genres(), 'selection_limits': catalog.wizard_selection_limits(),
                    'default_budget': asdict(app.budget())}
        elif segs == ['kb', 'review-queue']:
            from nw.studio.review_queue import review_queue
            data = review_queue(lib)
        elif segs == ['recommend']:
            data = lib.recommend(first(query, 'slot', 'genre'), first(query, 'types').split(',') if first(query, 'types') else [])
        elif segs == ['recommendations', 'length']:
            data = lib.recommend_length(first(query, 'types').split(',') if first(query, 'types') else [])
        elif segs == ['recommendations', 'cast']:
            from nw.studio.cast_samples import genre_cast_samples
            data = genre_cast_samples(lib, first(query, 'types').split(',') if first(query, 'types') else [])
        elif segs == ['options']:
            types = [t for t in first(query, 'types').split(',') if t]
            data = lib.options(first(query, 'slot', 'world'), first(query, 'parent'), types=types or None)
        elif segs == ['novel-cache']:
            data = app.novel_cache()
        elif segs == ['novels']:
            data = app.list(first(query, 'status'))
        elif len(segs) >= 2 and segs[0] == 'novels':
            ident = segs[1]
            if len(segs) == 2:
                data = app.detail(ident)
            elif len(segs) == 3:
                action = segs[2]
                if action == 'methods':
                    data = app.method_usage(ident)
                elif action == 'progress':
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
        data, status = corpus_routes.post(lib, segs, body), 200
        if data is None:
            data = method_routes.post(lib, segs, body)
        if data is not None:
            handler._send_json(201 if segs == ['kb', 'methods'] else 200, data)
            return True
        if segs == ['novels']:
            data, status = app.create(body), 201
        elif segs == ['novel-cache', 'clear']:
            data = app.clear_novel_cache()
        elif len(segs) >= 3 and segs[0] == 'novels':
            ident, action = segs[1:3]
            if len(segs) == 3:
                if action == 'trash':
                    data = app.trash_novel(ident)
                elif action == 'length':
                    data = app.configure_length(ident, body)
                elif action == 'methods':
                    data = app.configure_methods(ident,body)
                elif action == 'run':
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
            elif len(segs) == 5 and action == 'gates' and segs[4] == 'refresh':
                data = app.refresh_methods(ident, segs[3], body)
            elif len(segs) == 4 and action == 'branches':
                branch_actions = {'fork': app.fork_branch, 'select': app.select_branch, 'promote': app.promote_branch}
                if segs[3] in branch_actions:
                    data = branch_actions[segs[3]](ident, body)
            elif len(segs) == 5 and action == 'scenes' and segs[4] == 'accept':
                data = app.accept_scene(ident, segs[3], body)
        elif segs == ['staging']:
            data, status = lib.import_book(body), 201
        elif len(segs) == 3 and segs[0] == 'staging':
            if segs[2]=='verify' or (segs[2]=='decompose' and 'items' in body):
                raise ValueError('历史局部条目只读。新分析和复核请打开本书的多层结构拆解。')
            actions = {'review': lib.review_book, 'decompose': lib.decompose_book, 'reclassify': lib.reclassify_book}
            if segs[2] in actions:
                data = actions[segs[2]](segs[1], body)
        elif len(segs) == 3 and segs[:2] == ['kb', 'types']:
            data = lib.save_type(segs[2], body)
        elif len(segs) == 3 and segs[:2] == ['kb', 'upgrades']:
            raise ValueError('历史升级记录只读。新方法请从本书已批准的现行结构提炼并审核。')
        if data is None:
            return False
        handler._send_json(status, data)
        return True

    def events(self, handler: Any, ident: str) -> None:
        def read_progress() -> dict:
            with (self.data_lock or nullcontext()):
                return self.production.progress(ident)

        initial = read_progress()
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
                progress = initial if previous is None else read_progress()
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
        except Exception:
            pass
        finally:
            handler.close_connection = True
