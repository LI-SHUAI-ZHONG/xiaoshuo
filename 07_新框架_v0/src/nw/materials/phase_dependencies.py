"""Schedule direct method references only after an actual upstream use."""
from nw.materials.phase_routes import ORDER, route_method
from nw.materials.work_catalog import SourceDesk


def deferred_source_ids(desk: SourceDesk, stage: str, products: dict, studied_sources: list[dict]) -> list[str]:
    positions = {name: index for index, name in enumerate(ORDER)}
    current = positions.get(stage)
    if current is None:
        return []
    originals = {row['source']['id']: row for row in studied_sources if row.get('source', {}).get('id')}
    result = []
    seen = set()
    for origin, record in products.items():
        if origin not in positions or positions[origin] >= current:
            continue
        for use in record.get('products', {}).get('_uses', []):
            source = originals.get(use.get('source_id'), {})
            for ident in source.get('related_sources', []):
                if ident in seen:
                    continue
                seen.add(ident)
                meta = desk.by_id.get(ident)
                if meta is not None and stage in route_method(meta)['stages']:
                    result.append(ident)
    return result
