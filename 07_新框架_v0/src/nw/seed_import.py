"""Import a small, hash-pinned batch without mutating the source files."""
from dataclasses import asdict
import json
from pathlib import Path, PurePosixPath
from typing import Any

from nw.cards import CardConflict, _append, _card_values, _link
from nw.sources import _Source, _insert_span, _insert_version, _load_source, _span, text_sha256
from nw.store import Store
from nw.story_models import CardRef, SourceRef


def _object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate seed field: {key}')
        result[key] = value
    return result


def _json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_object)
    if not isinstance(data, dict):
        raise ValueError('Seed file must contain a JSON object')
    return data


def _relative(value: str) -> Path:
    if not isinstance(value, str) or '\\' in value or ':' in value:
        raise ValueError('Seed path must be repository-relative')
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or '..' in path.parts:
        raise ValueError('Seed path must be repository-relative')
    return Path(*path.parts)


def _seed_cards(data: dict, rules_only: bool) -> dict[str, dict]:
    cards = {}
    if data.get('schema_version') != 1 or not isinstance(data.get('cards'), list):
        raise ValueError('Invalid seed card file')
    for card in data['cards']:
        if (not isinstance(card, dict) or set(card) != {'card_id','kind','status','origin','body','sources'} or
                not isinstance(card['card_id'], str) or not card['card_id'] or card['card_id'] in cards or
                card['status'] != 'proposal' or
                (card['origin'] != 'repository' and not
                 (rules_only and card['kind'] == 'rule' and card['origin'] == 'author')) or
                not isinstance(card['sources'], list) or (card['origin'] == 'repository' and not card['sources']) or
                not all(isinstance(key, str) and key for key in card['sources'])):
            raise ValueError('Invalid or duplicate proposal seed card')
        cards[card['card_id']] = card
    return {key: card for key, card in cards.items() if not rules_only or card['kind'] == 'rule'}


def _prepare_sources(data: dict, root: Path, wanted: set[str]) -> tuple[list[_Source], dict[str, tuple[SourceRef, str]]]:
    files, results, keys = [], {}, set()
    for entry in data['sources']:
        if not isinstance(entry, dict) or not isinstance(entry.get('spans'), list):
            raise ValueError('Invalid seed source entry')
        selected = []
        for span in entry['spans']:
            if (not isinstance(span, dict) or set(span) != {'key','start_line','end_line','sha256'} or
                    not isinstance(span['key'], str) or not span['key'] or span['key'] in keys):
                raise ValueError('Invalid or duplicate seed span key')
            keys.add(span['key'])
            if span['key'] in wanted:
                selected.append(span)
        if not selected:
            continue
        source = _load_source(_relative(entry['path']), root)
        if source.status != 'READY':
            from nw.sources import SourceQuarantined
            raise SourceQuarantined(source.id, source.status)
        if source.relative_path != entry['path'] or text_sha256(source.text) != entry.get('normalized_sha256'):
            raise ValueError(f'Seed file hash or path mismatch: {source.relative_path}')
        files.append(source)
        lines = source.lines()
        for item in selected:
            ref, text = _span(source, lines, item['start_line'], item['end_line'])
            if ref.span_sha256 != item['sha256']:
                raise ValueError(f"Seed span hash mismatch: {item['key']}")
            results[item['key']] = (ref, text)
    if results.keys() != wanted:
        raise ValueError('Seed card references a missing source span')
    return files, results


def _seed_card(store: Store, card: dict) -> CardRef:
    ident, kind, origin, body, refs = _card_values(store, card)
    row = store.connection.execute('SELECT * FROM cards WHERE card_id=? AND version=1', (ident,)).fetchone()
    if row is None:
        return _append(store, card, None)
    if (row['kind'], row['origin'], row['body_json'], row['source_refs_json']) != (kind, origin, body, refs):
        raise CardConflict(f'Seed would replace existing card {ident}; use a new version explicitly')
    return CardRef(ident, 1)


def import_manifest(store: Store, path: Path, *, root: Path | None, rules_only: bool = False) -> list[CardRef]:
    data = _json(path)
    if data.get('schema_version') != 1 or not isinstance(data.get('sources'), list):
        raise ValueError('Invalid seed manifest')
    parent = path.resolve().parent
    card_path = (parent / _relative(data.get('cards_file'))).resolve()
    if not card_path.is_relative_to(parent):
        raise ValueError('Seed card path is outside the manifest directory')
    card_data = _json(card_path)
    cards = _seed_cards(card_data, rules_only)
    links = card_data.get('links', [])
    if not isinstance(links, list):
        raise ValueError('Invalid seed links')
    all_ids = {card['card_id'] for card in card_data['cards']}
    for link in links:
        if (not isinstance(link, dict) or set(link) != {'from','to','relation'} or
                not all(isinstance(link[k], str) for k in ('from','to','relation')) or
                not {link['from'],link['to']} <= all_ids):
            raise ValueError('Seed link references an unknown card')
    wanted = {key for card in cards.values() for key in card['sources']}
    files, spans = _prepare_sources(data, root or Path(__file__).resolve().parents[3], wanted)
    with store.connection:
        store.connection.execute('BEGIN IMMEDIATE')
        for source in files:
            _insert_version(store, source)
        for ref, text in spans.values():
            _insert_span(store, ref, text)
        refs = {}
        for key, entry in cards.items():
            card = {k: v for k, v in entry.items() if k != 'sources'}
            card['source_refs'] = [asdict(spans[k][0]) for k in entry['sources']]
            refs[key] = _seed_card(store, card)
        for link in links:
            if link['from'] in refs and link['to'] in refs:
                _link(store, refs[link['from']], refs[link['to']], link['relation'])
        return list(refs.values())
