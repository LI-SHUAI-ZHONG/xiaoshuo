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
        elif segs == ['wizard', 'setup-profile']:
            from nw.studio.wizard_setup import setup_profile_for_types
            types = [t for t in first(query, 'types').split(',') if t]
            tw_raw = first(query, 'target_words')
            tw_val = int(tw_raw) if tw_raw.isdigit() else None
            data = setup_profile_for_types(types or None, library=lib, target_words=tw_val)
        elif segs == ['wizard', 'preferences']:
            data = app.wizard_preferences()
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
                elif action == 'voice-spec':
                    data = app.voice_spec(ident)
                elif action == 'craft-specs':
                    data = app.craft_specs(ident)
                elif action == 'style-reference':
                    data = app.style_reference(ident)
                elif action == 'cold-reads':
                    data = app.cold_reads(ident, first(query, 'scene'))
                elif action == 'serial-health':
                    data = app.serial_health(ident)
                elif action == 'overrides':
                    data = app.overrides(ident, first(query, 'scene'), first(query, 'status', 'active'))
                elif action == 'craft-evolution':
                    data = app.craft_evolution(ident, first(query, 'scene'))
                elif action == 'doctor':
                    data = app.doctor(ident, repair_cache=first(query, 'repair_cache') in ('1', 'true'))
                elif action == 'briefing':
                    data = app.scene_briefing(ident, first(query, 'scene'))
                elif action == 'forecasts':
                    data = app.forecasts(ident)
                elif action == 'deslop':
                    data = app.analyze_deslop(ident, first(query, 'scene'), first(query, 'draft'))
                elif action == 'manuscript-imports':
                    data = app.manuscript_imports(ident)
                elif action == 'author-memory':
                    data = app.author_memory(ident, first(query, 'stage'))
                elif action == 'publish-preflight':
                    data = app.publish_preflight(ident, {
                        'platform': first(query, 'platform', 'fanqie'),
                        'quote_mode': first(query, 'quote_mode', 'keep'),
                    })
                elif action == 'book-audit':
                    mw = first(query, 'min_words')
                    data = app.book_audit(ident, min_words=(int(mw) if mw.isdigit() else 1800))
                elif action == 'fact-ledger':
                    data = app.fact_ledger(ident, category=first(query, 'category'), status=first(query, 'status'))
                elif action == 'calibration-anchor':
                    data = app.calibration_anchor(ident)
                elif action == 'continuation':
                    data = app.continuation(ident)
                elif action == 'finish-check':
                    data = app.finish_check(ident)
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
        elif len(segs) == 3 and segs[0] == 'staging' and segs[2] == 'anatomy':
            data = lib.get_book_anatomy(segs[1])
        elif segs == ['radar']:
            data = lib.radar_overview(platform=first(query, 'platform'))
        elif segs == ['radar', 'playbooks']:
            types = [t for t in first(query, 'types').split(',') if t]
            data = lib.radar_playbooks(
                scale=first(query, 'scale', 'long'),
                experience=first(query, 'experience', 'beginner'),
                types=types or None,
            )
        elif len(segs) == 3 and segs[:2] == ['radar', 'snapshots']:
            data = lib.radar_snapshot_detail(segs[2])
        elif len(segs) == 3 and segs[:2] == ['kb', 'types']:
            data = lib.get_type(segs[2])
        elif segs == ['kb', 'items']:
            data = lib.items(first(query, 'slot'), first(query, 'types').split(',') if first(query, 'types') else [])
        elif segs == ['kb', 'upgrades']:
            data = lib.upgrades(first(query, 'status'))
        elif segs == ['kb', 'voice-fingerprints']:
            from nw.voice_specs import VOICE_KNOBS, recommend_voice_bases
            types = [t for t in first(query, 'types').split(',') if t]
            data = {
                'fingerprints': lib.voice_fingerprints(
                    types=types or None,
                    status=first(query, 'status', 'approved'),
                    include_incompatible=first(query, 'all') in ('1', 'true'),
                ),
                'voice_bases': recommend_voice_bases(types or None),
                'knobs': VOICE_KNOBS,
            }
        elif segs == ['kb', 'craft-fingerprints']:
            from nw.craft_specs import recommend_all_craft_setup
            types = [t for t in first(query, 'types').split(',') if t]
            dom = first(query, 'domain') or None
            tw_raw = first(query, 'target_words')
            tw_val = int(tw_raw) if tw_raw.isdigit() else None
            data = {
                'domain': dom,
                'fingerprints': lib.craft_fingerprints(
                    domain=dom,
                    types=types or None,
                    status=first(query, 'status', 'approved'),
                    include_incompatible=first(query, 'all') in ('1', 'true'),
                ),
                'setup': recommend_all_craft_setup(types or None, target_words=tw_val, library=lib),
            }
        elif segs == ['kb', 'verified-excerpts']:
            types = [t for t in first(query, 'types').split(',') if t]
            data = {
                'excerpts': lib.list_verified_excerpts(
                    types=types or None,
                    scene_function=first(query, 'scene_function'),
                ),
            }
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
                elif action == 'voice-spec':
                    data = app.save_voice_spec(ident, body)
                elif action == 'craft-specs':
                    dom = str(body.get('domain') or '').strip() if isinstance(body, dict) else ''
                    data = app.save_craft_spec(ident, dom, body)
                elif action == 'style-reference':
                    data = app.save_style_reference(ident, body)
                elif action == 'cold-reads':
                    data = app.run_cold_read(ident, body)
                elif action == 'overrides':
                    data = app.record_soft_override(ident, body)
                elif action == 'volume-summaries':
                    data = app.save_volume_summary_record(ident, body)
                elif action == 'forecasts':
                    data = app.create_forecast(ident, body)
                elif action == 'deslop':
                    data = app.run_deslop(ident, body)
                elif action == 'manuscript-imports':
                    data = app.analyze_manuscript_import(ident, body)
                elif action == 'author-memory':
                    data = app.save_author_memory(ident, body)
                elif action == 'style-whitelist':
                    data = app.save_style_whitelist(ident, body)
                elif action == 'publish-preflight':
                    data = app.publish_preflight(ident, body)
                elif action == 'ab-judge':
                    data = app.run_ab_blind_judge(ident, body)
                elif action == 'fact-ledger':
                    data = app.save_fact_ledger_entry(ident, body)
                elif action == 'calibration-anchor':
                    data = app.save_calibration_anchor(ident, body)
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
            elif len(segs) == 4 and action == 'craft-specs':
                data = app.save_craft_spec(ident, segs[3], body)
            elif len(segs) == 4 and action == 'serial-health' and segs[3] == 'telemetry':
                data = app.save_chapter_telemetry(ident, body)
            elif len(segs) == 4 and action == 'craft-evolution':
                evo_actions = {
                    'accept-contrast': app.accept_evolution_contrast,
                    'remove-contrast': app.remove_evolution_contrast,
                    'promote': app.promote_evolution_rule,
                    'pin-baseline': app.pin_evolution_baseline,
                }
                if segs[3] in evo_actions:
                    data = evo_actions[segs[3]](ident, body)
            elif len(segs) == 5 and action == 'overrides' and segs[4] == 'revoke':
                data = app.revoke_soft_override(ident, segs[3])
            elif len(segs) == 5 and action == 'forecasts' and segs[4] == 'select':
                data = app.select_forecast(ident, segs[3], body)
            elif len(segs) == 5 and action == 'manuscript-imports' and segs[4] == 'apply':
                data = app.apply_manuscript_import(ident, segs[3], body)
            elif len(segs) == 5 and action == 'fact-ledger' and segs[4] == 'delete':
                data = app.delete_fact_ledger_entry(ident, segs[3])
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
            elif len(segs) == 5 and action == 'chapters' and segs[4] == 'summary':
                data = app.save_chapter_summary(ident, int(segs[3]), body)
            elif len(segs) == 6 and action == 'chapters' and segs[4] == 'reviews':
                data = app.save_chapter_review(ident, int(segs[3]), segs[5], body)
        elif segs == ['staging']:
            data, status = lib.import_book(body), 201
        elif len(segs) == 3 and segs[0] == 'staging':
            if segs[2] == 'anatomy':
                if body.get('use_llm'):
                    cfg, prov = app._runtime()
                    data = lib.run_book_anatomy(segs[1], body, provider=prov, model=cfg.model, params=dict(cfg.params))
                else:
                    data = lib.run_book_anatomy(segs[1], body)
            elif segs[2]=='verify' or (segs[2]=='decompose' and 'items' in body):
                raise ValueError('历史局部条目只读。新分析和复核请打开本书的多层结构拆解。')
            else:
                actions = {'review': lib.review_book, 'decompose': lib.decompose_book, 'reclassify': lib.reclassify_book}
                if segs[2] in actions:
                    data = actions[segs[2]](segs[1], body)
        elif len(segs) == 2 and segs[0] == 'radar':
            if segs[1] == 'fetch':
                data = lib.radar_fetch_live(body)
            elif segs[1] == 'import':
                data, status = lib.radar_import_chart(body), 201
            elif segs[1] == 'diff':
                data = lib.radar_diff_snapshots(body)
            elif segs[1] == 'topics':
                if body.get('use_llm'):
                    cfg, prov = app._runtime()
                    data = lib.radar_generate_topics(body, provider=prov, model=cfg.model, params=dict(cfg.params))
                else:
                    data = lib.radar_generate_topics(body)
            elif segs[1] == 'title-workshop':
                if body.get('use_llm'):
                    cfg, prov = app._runtime()
                    data = lib.radar_title_workshop(body, provider=prov, model=cfg.model, params=dict(cfg.params))
                else:
                    data = lib.radar_title_workshop(body)
        elif len(segs) == 3 and segs[:2] == ['kb', 'types']:
            data = lib.save_type(segs[2], body)
        elif len(segs) == 3 and segs[:2] == ['kb', 'upgrades']:
            raise ValueError('历史升级记录只读。新方法请从本书已批准的现行结构提炼并审核。')
        elif segs == ['kb', 'verified-excerpts']:
            data, status = lib.add_verified_excerpt(body), 201
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
