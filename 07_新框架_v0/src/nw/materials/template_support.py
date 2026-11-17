"""Small pure helpers for project-specific template contracts."""
from collections.abc import Iterable


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError('MATERIAL_STAGE: ' + reason)


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def content(value: object) -> bool:
    labels = {'对象', '行动', '动作', '障碍', '应对', '结果', '关注重点', '激活条件',
              'object', 'action', 'obstacle', 'response', 'result', 'activation_condition'}
    return (text(value) and value.strip().casefold() not in labels
            and not any(token in value for token in ('<填写', '待填写', '写出实际', '<fill')))


def strings(value: object, *, nonempty: bool = False) -> bool:
    return isinstance(value, list) and (not nonempty or bool(value)) and all(text(item) for item in value)


def references(value: object, allowed: Iterable[str], *, nonempty: bool = True) -> bool:
    return (strings(value, nonempty=nonempty) and len(value) == len(set(value))
            and set(value) <= set(allowed))


def rows(value: dict, key: str, fields: set[str]) -> list[dict]:
    result = value.get(key)
    require(isinstance(result, list), key + ' must be an explicit list')
    require(all(isinstance(row, dict) and set(row) == fields for row in result),
            key + ' has invalid product fields')
    return result


def identified(value: dict, key: str, fields: set[str], reserved: Iterable[str] = ()) -> list[dict]:
    result = rows(value, key, fields)
    seen = set(reserved)
    for row in result:
        require(text(row['id']) and row['id'] not in seen, key + ' needs distinct actual IDs')
        seen.add(row['id'])
    return result


def product(products: dict, stage: str) -> dict:
    return products.get(stage, {}).get('products', {})


def members(products: dict, context: dict, kinds: set[str], local: Iterable[dict] = ()) -> set[str]:
    result = {row['card_id'] for row in context.get('approved_cards', []) if row['kind'] in kinds}
    for record in products.values():
        result.update(row['key'] for row in record.get('products', {}).get('members', []) if row['kind'] in kinds)
    result.update(row['key'] for row in local if row['kind'] in kinds)
    return result


def source_ids(sources: list[dict]) -> set[str]:
    return {row['source']['id'] for row in sources}


def capabilities(products: dict) -> dict[str, dict]:
    return {row['entity']: row for row in product(products, 'character_design').get('capabilities', [])}


def events(products: dict) -> dict[str, dict]:
    result = {row['id']: row for row in product(products, 'plot_design').get('event_nodes', [])}
    result.update({row['id']: row for row in product(products, 'event_design').get('candidates', [])})
    return result


def waiting(value: dict, sources: list[dict]) -> None:
    seen = set()
    applied = {ident for row in value.get('candidates', []) for ident in row['source_ids']}
    for row in rows(value, 'waiting', {'source_id', 'missing', 'reason'}):
        ident = row['source_id']
        require(text(ident) and ident in source_ids(sources) and ident not in seen | applied
                and strings(row['missing'], nonempty=True) and content(row['reason']),
                'waiting must identify missing inputs without claiming an actual use')
        seen.add(ident)
