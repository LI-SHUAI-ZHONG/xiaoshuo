"""Editable type knowledge and independently versioned, approved upgrades."""
from __future__ import annotations

import json
import re
from uuid import uuid4

from nw.studio import catalog
from nw.studio.library_util import encode, timestamp


class KnowledgeMixin:
    def get_type(self, ident: str) -> dict:
        original = catalog.type_map().get(ident)
        if not original:
            raise FileNotFoundError('类型不存在')
        with self.connect() as conn:
            stored = conn.execute('SELECT * FROM type_kb WHERE type_id=?', (ident,)).fetchone()
        result = {'type_id': ident, 'id': ident, 'name': original['name'],
                  'definition': original.get('definition', ''), 'includes': [], 'excludes': [],
                  'features': [], 'examples': [], 'counterexamples': [], 'version': 0,
                  'source_ref': original['source_ref']}
        if stored:
            result.update(definition=stored['definition'], version=stored['version'], updated_at=stored['updated_at'])
            for field, column in [('includes', 'includes'), ('excludes', 'excludes'), ('features', 'features_json'),
                                   ('examples', 'examples_json'), ('counterexamples', 'counterexamples_json')]:
                result[field] = json.loads(stored[column])
        return result

    def save_type(self, ident: str, body: dict) -> dict:
        current = self.get_type(ident)
        definition = body.get('definition', current['definition'])
        if not isinstance(definition, str) or len(definition) > 10000:
            raise ValueError('类型定义须为不超过 10000 字的文本')
        fields = {}
        for name in ('includes', 'excludes', 'features', 'examples', 'counterexamples'):
            value = body.get(name, current[name])
            if isinstance(value, str):
                value = [part.strip() for part in value.splitlines() if part.strip()]
            if not isinstance(value, list) or len(value) > 100 or any(not isinstance(v, str) or len(v) > 1000 for v in value):
                raise ValueError(f'{name} 必须是最多 100 条短文本的列表')
            fields[name] = list(dict.fromkeys(v.strip() for v in value if v.strip()))
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT version FROM type_kb WHERE type_id=?', (ident,)).fetchone()
            version = row['version'] if row else 0
            if body.get('version', current['version']) != version:
                raise ValueError('类型知识已更新，请刷新后再保存')
            conn.execute('INSERT INTO type_kb VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(type_id) DO UPDATE SET '
                         'definition=excluded.definition,includes=excluded.includes,excludes=excluded.excludes,'
                         'features_json=excluded.features_json,examples_json=excluded.examples_json,'
                         'counterexamples_json=excluded.counterexamples_json,version=excluded.version,updated_at=excluded.updated_at',
                         (ident, definition.strip(), encode(fields['includes']), encode(fields['excludes']),
                          encode(fields['features']), encode(fields['examples']), encode(fields['counterexamples']),
                          version + 1, timestamp()))
        return self.get_type(ident)

    def _open_gaps(self) -> list[dict]:
        if self.ledger_path is None or not self.ledger_path.is_file():
            return []
        rows = []
        for line in self.ledger_path.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('status') == 'open' and re.search(r'missing|truncat|缺义|截断|缺失', encode(row)):
                rows.append(row)
        return rows

    def _create_upgrades(self, book_id: str) -> None:
        rows = [r for r in self._approved_items() if r['book_id'] == book_id]
        options = catalog.option_map()
        gaps = self._open_gaps()
        with self.connect() as conn:
            for item in rows:
                option = options[item['option_key']]
                ref = option.get('source_ref', {})
                target = f'{ref.get("file", "")}#{ref.get("section", ref.get("original_line", ""))}'
                matching = [g for g in gaps if option['name'] in encode(g.get('source_locator', {}))]
                if matching:
                    kind = 'fill'
                    reason = '对应开放缺口 ' + ', '.join(str(g.get('issue_id', '')) for g in matching[:3]) + '；按台账关联初筛，候选待人工语义核对'
                elif option.get('description'):
                    kind = 'enhance'
                    reason = '同一选项已有定义；按同选项关联初筛，候选待人工语义核对，尚未判定是否同义增强'
                else:
                    kind = 'new'
                    reason = '当前选项没有可用定义，提议新增独立用法；候选待人工语义核对，不宣称已修复原件'
                conn.execute('INSERT OR IGNORE INTO upgrade_candidates VALUES(?,?,?,?,?,?,?,?)',
                             (uuid4().hex, item['id'], target, kind, 'pending', reason, timestamp(), None))

    def upgrades(self, status: str = '') -> dict:
        if status and status not in ('pending', 'approved', 'rejected'):
            raise ValueError('升级候选状态无效')
        with self.connect() as conn:
            rows = conn.execute('SELECT u.*,d.usage_text,d.option_key,d.slot,d.evidence_json,b.title AS book_title,'
                                'b.status AS book_status FROM upgrade_candidates u JOIN decomp_items d ON d.id=u.decomp_item_id '
                                'JOIN staging_books b ON b.id=d.book_id WHERE (?="" OR u.status=?) ORDER BY u.created_at DESC',
                                (status, status)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item['evidence'] = json.loads(item.pop('evidence_json'))
            item['available'] = item['book_status'] == 'archived'
            result.append(item)
        return {'upgrades': result, 'scope': 'new_books_only'}

    def review_upgrade(self, ident: str, body: dict) -> dict:
        decision = body.get('decision')
        if decision not in ('approve', 'reject'):
            raise ValueError('升级决定必须为 approve 或 reject')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            candidate = conn.execute('SELECT * FROM upgrade_candidates WHERE id=?', (ident,)).fetchone()
            if not candidate:
                raise FileNotFoundError('升级候选不存在')
            if candidate['status'] != 'pending':
                raise ValueError('该升级候选已处理')
            source = conn.execute('SELECT d.*,b.status AS book_status FROM decomp_items d JOIN staging_books b ON b.id=d.book_id '
                                  'WHERE d.id=?', (candidate['decomp_item_id'],)).fetchone()
            if decision == 'approve' and (source['status'] != 'approved' or source['book_status'] != 'archived'):
                raise ValueError('只有已入库、已批准的拆解可以升级')
            now = timestamp()
            conn.execute('UPDATE upgrade_candidates SET status=?,decided_at=? WHERE id=?',
                         ('approved' if decision == 'approve' else 'rejected', now, ident))
            if decision == 'approve':
                item = self._item(source)
                snapshot = {k: item[k] for k in ('id', 'book_id', 'slot', 'option_key', 'stages', 'usage_text', 'evidence', 'status', 'type_tags')}
                snapshot.update(target_source_key=candidate['target_source_key'], kind=candidate['kind'])
                conn.execute('INSERT INTO upgrade_versions(candidate_id,snapshot_json,created_at) VALUES(?,?,?)',
                             (ident, encode(snapshot), now))
        return next(r for r in self.upgrades()['upgrades'] if r['id'] == ident)

    def approved_upgrades(self, types: list[str] | None = None) -> dict:
        """Snapshot valid upgrades only. Existing books keep their frozen version."""
        with self.connect() as conn:
            rows = conn.execute("SELECT v.* FROM upgrade_versions v JOIN upgrade_candidates u ON u.id=v.candidate_id "
                                "JOIN decomp_items d ON d.id=u.decomp_item_id JOIN staging_books b ON b.id=d.book_id "
                                "WHERE u.status='approved' AND d.status='approved' AND b.status='archived' ORDER BY v.version").fetchall()
            version = conn.execute('SELECT COALESCE(MAX(version),0) FROM upgrade_versions').fetchone()[0]
        all_items = [{**json.loads(row['snapshot_json']), 'version': row['version']} for row in rows]
        items = all_items
        if types is not None:
            selected = catalog.canonical_types(types)
            primary = selected[0] if selected else None
            items = [item for item in items if primary and primary in item['type_tags']]
        # An upgrade collection is a source layer, not an unlimited prompt appendix.
        selected_items = []
        per_option: dict[str, set[str]] = {}
        for item in reversed(items):
            books = per_option.setdefault(item['option_key'], set())
            if len(books) >= 3 or item['book_id'] in books:
                continue
            books.add(item['book_id'])
            evidence = item['evidence']
            quote = evidence['quote'][:400]
            selected_items.append({**item, 'usage_text': item['usage_text'][:2000],
                                   'evidence': {**evidence, 'quote': quote, 'end': evidence['start'] + len(quote)}})
            if len(selected_items) >= 64:
                break
        return {'version': version, 'items': selected_items, 'scope': 'new_books_only',
                'index': [{'id': item['id'], 'version': item['version'], 'slot': item['slot'],
                           'option_key': item['option_key'], 'type_tags': item['type_tags']} for item in all_items],
                'available_count': len(all_items), 'applicable_count': len(items),
                'selection_policy': 'same_primary_type; latest; max_3_books_per_option; max_64_items'}

    upgrade_snapshot = approved_upgrades
