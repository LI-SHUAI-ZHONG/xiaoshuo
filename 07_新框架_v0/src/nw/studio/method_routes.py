"""HTTP routes for structured production methods."""
from typing import Any


def get(library: Any, segs: list[str], query: dict) -> dict | None:
    def value(key: str, default: str = '') -> str:
        return query.get(key, [default])[0]

    if segs == ['kb', 'method-catalog']:
        return library.method_catalog()
    if segs == ['kb', 'step-blueprint']:
        from nw.studio.step_material_blueprint import build_step_blueprint
        return build_step_blueprint(library)
    if segs == ['kb', 'world-blueprint']:
        from nw.studio.world_materials import world_blueprint
        types = [t for t in value('types').split(',') if t]
        return world_blueprint(library, types)
    if segs == ['kb', 'character-blueprint']:
        from nw.studio.character_materials import character_blueprint
        types = [t for t in value('types').split(',') if t]
        return character_blueprint(library, types)
    if segs == ['kb', 'plot-blueprint']:
        from nw.studio.plot_materials import plot_blueprint
        types = [t for t in value('types').split(',') if t]
        return plot_blueprint(library, types)
    if segs == ['kb', 'execution-blueprint']:
        from nw.studio.execution_materials import execution_blueprint
        types = [t for t in value('types').split(',') if t]
        return execution_blueprint(library, types)
    if segs == ['kb', 'craft-blueprint']:
        from nw.studio.craft_materials import craft_blueprint
        types = [t for t in value('types').split(',') if t]
        return craft_blueprint(library, types)
    if segs == ['kb', 'handoff-audit']:
        from nw.studio.downstream_handoff import audit_downstream_handoff
        types = [t for t in value('types').split(',') if t]
        hierarchy = value('planning_hierarchy', '1') in ('1', 'true', 'True')
        tasks_raw = value('tasks')
        active_tasks = [t for t in tasks_raw.split(',') if t] if tasks_raw else None
        return audit_downstream_handoff(
            library,
            types=types,
            book_id=value('book_id'),
            planning_hierarchy=hierarchy,
            active_tasks=active_tasks,
        )
    if segs == ['kb', 'approved-structures']:
        from nw.studio.corpus_methods import approved_structures_summary
        return {'structures': approved_structures_summary(library)}
    if segs == ['kb', 'method-recommendations']:
        from nw.production_methods.sources import MethodReader
        from nw.studio.catalog import canonical_types
        from nw.studio.method_recommendations import recommendations
        types = canonical_types(value('types').split(',') if value('types') else [])
        selected = value('selected').split(',') if value('selected') else []
        hierarchy = value('planning_hierarchy') in ('1', 'true', 'True')
        raw_limit = value('limit')
        limit = 3
        if raw_limit:
            try:
                limit = int(raw_limit)
            except ValueError as exc:
                raise ValueError('推荐数量上限须为整数') from exc
            if not 1 <= limit <= 24:
                raise ValueError('推荐数量上限须在 1–24 之间')
        return recommendations(MethodReader(library.workspace), value('slot'), types, selected,
                               planning_hierarchy=hierarchy, limit=limit)
    if segs == ['kb', 'methods']:
        return library.list_methods(task=value('task'), scope=value('scope'), stage=value('stage'),
            types=value('types').split(',') if value('types') else [], status=value('status'),
            q=value('q'), limit=int(value('limit', '40')), offset=int(value('offset', '0')))
    if len(segs) == 3 and segs[:2] == ['kb', 'methods']:
        return library.get_method(segs[2], int(value('version')) if value('version') else None)
    return None


def post(library: Any, segs: list[str], body: dict) -> dict | None:
    if segs == ['kb', 'method-evidence']:
        return library.locate_method_evidence(body)
    if segs == ['kb', 'methods']:
        return library.save_method(body)
    if len(segs) == 3 and segs[:2] == ['kb', 'methods']:
        return library.save_method(body, segs[2])
    if len(segs) == 4 and segs[:2] == ['kb', 'methods'] and segs[3] == 'review':
        return library.review_method(segs[2], body)
    if len(segs) == 4 and segs[:2] == ['kb', 'methods'] and segs[3] == 'origin':
        return library.bind_method_origin(segs[2], body)
    return None
