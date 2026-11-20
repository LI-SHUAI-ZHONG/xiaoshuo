"""Match methods to the selected taxonomy without expanding a subgenre to siblings."""
from nw.studio.catalog import canonical_types, type_map


TYPE_PRIORITY = {'subgenre': 0, 'main': 1, 'cross_type': 2}


def type_match(selected: list[str], tagged: list[str]) -> dict | None:
    taxonomy = type_map()
    chosen = set(canonical_types(selected))
    if not tagged:
        return {'level': 'cross_type', 'type_ids': [], 'type_names': []}

    subgenres = {ident for ident in tagged if taxonomy[ident].get('parent_id')}
    # The method catalog stores the inherited main tags alongside their subgenres.
    inherited = {taxonomy[ident]['parent_id'] for ident in subgenres}
    main = set(tagged) - subgenres - inherited
    matches = chosen & subgenres
    level = 'subgenre'
    if not matches:
        matches = chosen & main
        level = 'main'
    if not matches:
        return None
    ids = sorted(matches)
    return {'level': level, 'type_ids': ids, 'type_names': [taxonomy[ident]['name'] for ident in ids]}
