"""HTTP routes for structured production methods."""
from typing import Any


def get(library: Any, segs: list[str], query: dict) -> dict | None:
    def value(key: str, default: str = '') -> str:
        return query.get(key, [default])[0]

    if segs == ['kb', 'method-catalog']:
        return library.method_catalog()
    if segs == ['kb', 'methods']:
        return library.list_methods(task=value('task'), scope=value('scope'),
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
    return None
