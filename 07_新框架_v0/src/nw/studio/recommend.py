"""Evidence-only recommendations: distinct books, three match tiers, real blanks."""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json

from nw.studio import catalog
from nw.studio.library_util import timestamp


class RecommendationMixin:
    def recommend_length(self, types: list[str]) -> dict:
        """Each complete, approved source casts one vote in the selected genre."""
        from nw.length_settings import WORD_TIERS, book_word_range, nearest_word_tier
        from nw.studio.corpus_catalog import SCHEMA_VERSION

        selected = catalog.canonical_types(types)
        required = set(selected)
        counts = {tier: 0 for tier in WORD_TIERS}
        seen = set()
        if required:
            with self.connect() as conn:
                rows = conn.execute("""
                    SELECT b.file_path, b.sha256, b.confirmed_types_json, v.body_json, v.body_sha256
                    FROM staging_books b JOIN corpus_structures h ON h.book_id=b.id
                    JOIN corpus_structure_versions v ON v.book_id=h.book_id AND v.version=h.approved_version
                    JOIN corpus_structure_reviews r ON r.book_id=v.book_id AND r.version=v.version
                    LEFT JOIN corpus_jobs j ON j.id=v.job_id
                    WHERE b.status!='rejected' AND r.decision='approve' AND v.source_sha256=b.sha256
                    AND json_extract(v.body_json,'$.schema_version')=?
                    AND json_extract(v.body_json,'$.source_extent.status')='complete'
                    AND coalesce(json_extract(j.runtime_json,'$.provider'),'') NOT IN ('fake','test-only')
                    AND trim(b.title) NOT LIKE '[FAKE]%' AND trim(b.filename) NOT LIKE '[FAKE]%'
                """, (SCHEMA_VERSION,))
                for row in rows:
                    tags = json.loads(row['confirmed_types_json'])
                    if not required.issubset(tags):
                        continue
                    # The review applies to these exact structure and source bytes.
                    if sha256(row['body_json'].encode('utf-8')).hexdigest() != row['body_sha256']:
                        continue
                    try:
                        text = self._book_text(row)
                    except (OSError, ValueError):
                        continue
                    if text.lstrip().startswith('[FAKE]'):
                        continue
                    # Whitespace variants of an imported work still cast one vote.
                    prose = ''.join(text.split())
                    identity = sha256(prose.encode('utf-8')).digest()
                    if identity in seen:
                        continue
                    seen.add(identity)
                    tier = nearest_word_tier(len(prose))
                    if tier is not None:
                        counts[tier] += 1
        eligible = sum(counts.values())
        top_count = max(counts.values())
        leaders = [tier for tier, votes in counts.items() if votes and votes == top_count]
        if not required:
            status = 'no_types'
        elif not seen:
            status = 'no_samples'
        elif not leaders:
            status = 'outside_tiers'
        else:
            status = 'recommended' if len(leaders) == 1 else 'tied'
        tiers = []
        for tier in WORD_TIERS:
            lower, upper = book_word_range(tier)
            tiers.append({'target_words': tier, 'min_words': lower, 'max_words': upper})
        return {'types': selected, 'tiers': tiers, 'counts': {str(k): v for k, v in counts.items()},
                'status': status, 'recommended_tier': leaders[0] if len(leaders) == 1 else None,
                'leading_tiers': leaders, 'sample_count': len(seen), 'eligible_count': eligible,
                'outside_count': len(seen) - eligible}

    def _approved_items(self, slot: str = '') -> list[dict]:
        if slot and slot not in catalog.SLOTS:
            raise ValueError('未知板块')
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT d.*,b.title AS book_title FROM decomp_items d JOIN staging_books b ON b.id=d.book_id "
                "WHERE d.status='approved' AND b.status='archived' AND (?='' OR d.slot=?) "
                "ORDER BY d.updated_at DESC,d.id", (slot, slot)).fetchall()
        return [self._item(r) for r in rows]

    def _tiers(self, types: list[str]) -> list[tuple[str, set[str]]]:
        selected = catalog.canonical_types(types)
        if not selected:
            return [('exact', set())]
        mapping = catalog.type_map()
        primary = selected[0]
        child = next((t for t in selected if mapping[t].get('parent_id') == primary), None)
        result = [('exact', set(selected))]
        if child and {primary, child} != result[-1][1]:
            result.append(('subgenre', {primary, child}))
        if {primary} != result[-1][1]:
            result.append(('main', {primary}))
        return result

    def _aggregate(self, rows: list[dict], level: str) -> list[dict]:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for item in rows:
            grouped[item['option_key']].append(item)
        with self.connect() as conn:
            adopts = {r['option_key']: r['n'] for r in conn.execute(
                'SELECT option_key,COUNT(*) AS n FROM reviewed_adoptions GROUP BY option_key')}
        results = []
        for key, items in grouped.items():
            books = {i['book_id']: {'id': i['book_id'], 'title': i['book_title']} for i in items}
            examples = []
            for item in items:
                if not any(ex['book_id'] == item['book_id'] for ex in examples):
                    examples.append({**item['evidence'], 'book_id': item['book_id'], 'item_id': item['id']})
                if len(examples) == 2:
                    break
            results.append({'option_key': key, 'key': key, 'slot': items[0]['slot'], 'name': items[0]['name'],
                            'corpus_count': len(books), 'adopt_count': adopts.get(key, 0),
                            'books': list(books.values()), 'level': level, 'rec_level': level,
                            'examples': examples, 'item_ids': [i['id'] for i in items],
                            'updated_at': max(i['updated_at'] for i in items)})
        return sorted(results, key=lambda r: (r['corpus_count'], r['adopt_count'], r['updated_at'], r['option_key']), reverse=True)

    def recommend(self, slot: str, types: list[str] | None = None) -> dict:
        rows = self._approved_items(slot)
        selected = catalog.canonical_types(types or [])
        recommendations = []
        seen = set()
        for level, tags in self._tiers(selected):
            matches = [r for r in rows if tags.issubset(r['type_tags'])]
            for item in self._aggregate(matches, level):
                if item['option_key'] not in seen:
                    recommendations.append({**item, 'rank': len(recommendations) + 1})
                    seen.add(item['option_key'])
                if len(recommendations) == 3:
                    break
            if len(recommendations) == 3:
                break
        recommendations.extend([None] * (3 - len(recommendations)))
        return {'slot': slot, 'types': selected, 'recommendations': recommendations,
                'source': 'legacy_decomp_items', 'eligible_for_new_design': False}

    def freeze_references(self, choices: list[dict], types: list[str]) -> list[dict]:
        """Freeze only selected, approved, same-type uses, never entire chapters."""
        keys = {str(c.get('option_key') or c.get('key') or '') for c in choices}
        rows = self._approved_items()
        references = []
        for key in sorted(keys):
            candidates = [r for r in rows if r['option_key'] == key]
            for level, tags in self._tiers(types):
                matched = [r for r in candidates if tags.issubset(r['type_tags'])]
                if not matched:
                    continue
                seen_books: set[str] = set()
                for item in matched:
                    if item['book_id'] in seen_books:
                        continue
                    seen_books.add(item['book_id'])
                    references.append({k: item[k] for k in ('id', 'book_id', 'slot', 'option_key', 'stages',
                                                            'usage_text', 'evidence', 'status', 'type_tags')})
                    references[-1]['usage_text'] = item['usage_text'][:2000]
                    references[-1]['evidence'] = {**item['evidence'], 'quote': item['evidence']['quote'][:400],
                                                 'end': item['evidence']['start'] + len(item['evidence']['quote'][:400])}
                    references[-1]['rec_level'] = level
                    if len(references) == 64:
                        return references
                    if len(seen_books) == 3:
                        break
                break
        return references

    reference_snapshot = freeze_references

    def record_adoption(self, novel_id: str, scene_id: str, option_keys: list[str], reviewed_ref: str) -> None:
        """Internal hook; caller must verify the scene's accepted review record."""
        if not novel_id or not scene_id or not reviewed_ref:
            raise ValueError('采用计数需要小说、场景及已通过审稿的记录')
        valid = catalog.option_map()
        if any(key not in valid for key in option_keys):
            raise ValueError('采用记录含未知选项')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            has_production = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='novel_deletions'").fetchone()
            if has_production and conn.execute('SELECT 1 FROM novel_deletions WHERE novel_id=?', (novel_id,)).fetchone():
                return
            conn.executemany('INSERT OR IGNORE INTO reviewed_adoptions VALUES(?,?,?,?,?)',
                             [(novel_id, scene_id, key, reviewed_ref, timestamp()) for key in set(option_keys)])
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        rows = self._approved_items()
        groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
        for row in rows:
            for type_id in row['type_tags']:
                groups[(row['option_key'], row['slot'], type_id)].add(row['book_id'])
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            adopts = {r['option_key']: r['n'] for r in conn.execute(
                'SELECT option_key,COUNT(*) AS n FROM reviewed_adoptions GROUP BY option_key')}
            conn.execute('DELETE FROM usage_stats')
            conn.executemany('INSERT INTO usage_stats VALUES(?,?,?,?,?,?)',
                             [(*key, len(books), adopts.get(key[0], 0), timestamp()) for key, books in groups.items()])

    def items(self, slot: str = '', types: list[str] | None = None) -> dict:
        selected = set(catalog.canonical_types(types or []))
        rows = [r for r in self._approved_items(slot) if selected.issubset(r['type_tags'])]
        return {'items': rows, 'stats': self._aggregate(rows, 'exact'), 'slots': list(catalog.SLOTS),
                'source': 'legacy_decomp_items', 'eligible_for_new_design': False}
