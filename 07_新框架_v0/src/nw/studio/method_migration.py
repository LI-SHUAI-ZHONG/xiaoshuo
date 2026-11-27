"""Additive library migration: preserve legacy rows, create incomplete drafts."""
from typing import Any
from uuid import uuid4

from nw.studio.library_util import encode, timestamp
from nw.studio.method_contract import draft

SCHEMA = '''
CREATE TABLE IF NOT EXISTS method_schema (version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO method_schema VALUES(1);
CREATE TABLE IF NOT EXISTS production_methods (
 id TEXT PRIMARY KEY, latest_version INTEGER NOT NULL, approved_version INTEGER,
 origin_item_id TEXT UNIQUE REFERENCES decomp_items(id),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS production_method_versions (
 method_id TEXT NOT NULL REFERENCES production_methods(id), version INTEGER NOT NULL,
 body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL, evidence_json TEXT NOT NULL,
 legacy_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
 PRIMARY KEY(method_id,version));
CREATE TABLE IF NOT EXISTS production_method_reviews (
 method_id TEXT NOT NULL, version INTEGER NOT NULL, decision TEXT NOT NULL,
 note TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(method_id,version),
 FOREIGN KEY(method_id,version) REFERENCES production_method_versions(method_id,version));
'''


def migrate_legacy(service: Any) -> int:
    import hashlib
    count = 0
    with service.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        rows = conn.execute("SELECT d.* FROM decomp_items d LEFT JOIN production_methods m "
                            "ON m.origin_item_id=d.id WHERE m.id IS NULL AND d.status!='discarded' ORDER BY d.created_at,d.id").fetchall()
        for raw in rows:
            old = service._item(raw)
            evidence = old['evidence']
            # The legacy scope and applicability are unknown, not inferred from its slot.
            body, _ = draft({'title': old['name'][:120], 'type_tags': old['type_tags'],
                'operations': [{'key': 'operation_1', 'instruction': old['usage_text'],
                                'input_keys': [], 'output_keys': []}],
                'evidence': [{'book_id': old['book_id'], 'start': evidence['start'], 'end': evidence['end'],
                    'quote': evidence['quote'], 'explanation': '旧条目原作证据；方法结构仍待补齐与审核。'}]})
            ident, now, serialized = uuid4().hex, timestamp(), encode(body)
            conn.execute('INSERT INTO production_methods VALUES(?,?,NULL,?,?,?)', (ident, 1, old['id'], now, now))
            pins = [{'book_id': old['book_id'], 'start': evidence['start'], 'end': evidence['end'],
                     'source_sha256': evidence.get('source_sha256', '')}]
            conn.execute('INSERT INTO production_method_versions VALUES(?,?,?,?,?,?,?)',
                (ident, 1, serialized, hashlib.sha256(serialized.encode('utf-8')).hexdigest(),
                 encode(pins), encode(dict(raw)), now))
            count += 1
    return count
