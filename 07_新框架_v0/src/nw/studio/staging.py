"""Author-reviewed import and decomposition state machine."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from nw.materials.phase_routes import ORDER
from nw.studio import catalog
from nw.studio.library_util import encode, timestamp

STATES = ('pending_review', 'queued', 'decomposing', 'pending_verify', 'archived', 'rejected')


class StagingMixin:
    def _staging_row(self, ident: str) -> dict:
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM staging_books WHERE id=?', (ident,)).fetchone()
        if row is None:
            raise FileNotFoundError('预存书籍不存在')
        return dict(row)

    def _book_text(self, row: dict) -> str:
        path = (self.root / row['file_path']).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError('预存文件路径越界')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() == row['sha256']:
            return raw.decode('utf-8')
        # Earlier Windows imports expanded LF on write, including the LF in a CRLF pair.
        legacy = raw.replace(b'\r\n', b'\n')
        if hashlib.sha256(legacy).hexdigest() == row['sha256']:
            return legacy.decode('utf-8')
        raise ValueError('预存原文已改变，请重新导入，证据不能沿用')

    def list_staging(self, status: str = '') -> dict:
        if status and status not in STATES:
            raise ValueError('未知预存状态')
        with self.connect() as conn:
            rows = conn.execute('SELECT * FROM staging_books WHERE (?="" OR status=?) ORDER BY updated_at DESC',
                                (status, status)).fetchall()
        return {'books': [self._book(row) for row in rows], 'states': list(STATES)}

    def get_staging(self, ident: str) -> dict:
        row = self._staging_row(ident)
        with self.connect() as conn:
            items = conn.execute('SELECT * FROM decomp_items WHERE book_id=? ORDER BY created_at,id', (ident,)).fetchall()
        return {**self._book(row), 'text': self._book_text(row), 'items': [self._item(r) for r in items]}

    def _detect_types(self, title: str, text: str) -> list[dict]:
        """Report observed keyword matches, never invented probability estimates."""
        with self.connect() as conn:
            knowledge = conn.execute('SELECT * FROM type_kb').fetchall()
        sample = title + '\n' + text
        candidates = []
        for row in knowledge:
            features = json.loads(row['features_json'])
            hits = [feature for feature in features if feature and feature in sample]
            if hits:
                candidates.append({'id': row['type_id'], 'name': catalog.type_map()[row['type_id']]['name'],
                                   'confidence': None, 'matched_features': hits, 'match_count': len(hits),
                                   'method': 'maintained_feature_matches',
                                   'basis': '已维护识别特征的原文匹配；未经作者确认'})
        return sorted(candidates, key=lambda x: (-x['match_count'], x['id']))[:5]

    def import_book(self, body: dict) -> dict:
        text = body.get('text', '')
        filename = str(body.get('filename') or '导入小说.txt')
        if Path(filename).suffix.lower() not in ('.txt', '.md'):
            raise ValueError('初版支持 TXT / Markdown 文件')
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 12 * 1024 * 1024:
            raise ValueError('请导入非空、UTF-8 内容不超过 12 MiB 的小说')
        title = str(body.get('title') or Path(filename).stem).strip()
        if not title or len(title) > 200:
            raise ValueError('书名不能为空或超过 200 字')
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        with self.connect() as conn:
            existing = conn.execute('SELECT * FROM staging_books WHERE sha256=?', (digest,)).fetchone()
        if existing:
            return {**self._book(existing), 'duplicate': True}
        ident = uuid4().hex
        folder = self.root / 'imports'
        folder.mkdir(exist_ok=True)
        target = folder / f'{ident}.txt'
        target.write_bytes(text.encode('utf-8'))
        chapters = []
        for match in re.finditer(r'(?m)^(?:#{1,6}\s+[^\r\n]+|第[〇零一二三四五六七八九十百千万\d]+[卷章回节][^\r\n]*)', text):
            chapters.append({'title': match[0], 'start': match.start()})
        if not chapters:
            chapters = [{'title': '全文', 'start': 0}]
        for index, chapter in enumerate(chapters):
            chapter['end'] = chapters[index + 1]['start'] if index + 1 < len(chapters) else len(text)
        now = timestamp()
        detected = self._detect_types(title, text)
        with self.connect() as conn:
            conn.execute('INSERT INTO staging_books(id,title,file_path,sha256,words,filename,detected_types_json,'
                         'status,created_at,updated_at,chapters_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                         (ident, title, str(target.relative_to(self.root)), digest,
                          len(re.sub(r'\s', '', text)), Path(filename).name, encode(detected),
                          'pending_review', now, now, encode(chapters)))
        return self._book(self._staging_row(ident))

    def review_book(self, ident: str, body: dict) -> dict:
        row = self._staging_row(ident)
        decision = body.get('decision', 'approve')
        if decision not in ('approve', 'reject'):
            raise ValueError('审核决定必须为 approve 或 reject')
        if decision == 'reject':
            with self.connect() as conn:
                conn.execute("UPDATE staging_books SET status='rejected',note=?,updated_at=? WHERE id=?",
                             (str(body.get('note', '')), timestamp(), ident))
            self._refresh_stats()
            return self._book(self._staging_row(ident))
        if row['status'] != 'pending_review':
            raise ValueError('只有待审核书籍可以确认分类')
        types = catalog.canonical_types(body.get('types', body.get('confirmed_types', [])))
        if not types:
            raise ValueError('请确认至少一个类型')
        grade = body.get('grade', 'A')
        if grade not in ('S', 'A', 'B'):
            raise ValueError('质量评级必须为 S / A / B')
        requested = body.get('decompose', True)
        if type(requested) is not bool:
            raise ValueError('是否拆解必须为布尔值')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT status FROM staging_books WHERE id=?', (ident,)).fetchone()[0] != 'pending_review':
                raise ValueError('书籍已经审核，请刷新后查看当前状态')
            conn.execute('UPDATE staging_books SET status=?,confirmed_types_json=?,grade=?,note=?,updated_at=?,'
                         'decomposition_requested=?,progress=? WHERE id=?',
                         ('queued' if requested else 'archived', encode(types), grade, str(body.get('note', '')),
                          timestamp(), int(requested), 0 if requested else 1, ident))
        return self._book(self._staging_row(ident))

    def _validate_item(self, row: dict, item: dict, text: str) -> dict:
        if not isinstance(item, dict):
            raise ValueError('拆解条目必须是对象')
        slot = item.get('slot')
        if slot not in catalog.SLOTS:
            raise ValueError('拆解板块无效')
        option_key = str(item.get('option_key', ''))
        option = catalog.option_map(slot).get(option_key)
        if not option or option.get('selectable') is False:
            raise ValueError(f'请选择真实的资料选项: {option_key}')
        usage = item.get('usage_text', '')
        if not isinstance(usage, str) or not usage.strip() or len(usage) > 4000:
            raise ValueError('用法描述不能为空或超过 4000 字')
        stages = item.get('stages', item.get('stage', catalog.SLOT_STAGES[slot]))
        if not isinstance(stages, list) or not stages or any(s not in ORDER for s in stages):
            raise ValueError('拆解步骤必须来自现有 14 步')
        evidence = item.get('evidence')
        if not isinstance(evidence, dict):
            raise ValueError('拆解必须提供原文证据与定位')
        quote = evidence.get('quote', '')
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 1500:
            raise ValueError('证据必须为 1–1500 字的原文短摘录')
        start = evidence.get('start')
        if start is None:
            start = text.find(quote)
            if start >= 0 and text.find(quote, start + 1) >= 0:
                raise ValueError('相同证据出现多次，请提供 start 字符位置')
        if type(start) is not int or start < 0 or text[start:start + len(quote)] != quote:
            raise ValueError('证据与原文定位不一致')
        end = start + len(quote)
        if 'end' in evidence and evidence['end'] != end:
            raise ValueError('证据 end 与摘录长度不一致')
        return {'slot': slot, 'option_key': option_key, 'type_tags': json.loads(row['confirmed_types_json']),
                'stages': list(dict.fromkeys(stages)), 'usage_text': usage.strip(),
                'evidence': {'quote': quote, 'start': start, 'end': end,
                             'line': text[:start].count('\n') + 1, 'source_sha256': row['sha256']}}

    def _insert_items(self, ident: str, items: list[dict], *, origin: str = 'manual') -> dict:
        row = self._staging_row(ident)
        if row['status'] not in ('queued', 'decomposing', 'pending_verify'):
            raise ValueError('当前状态不能提交拆解')
        if not isinstance(items, list) or not 1 <= len(items) <= 500:
            raise ValueError('每批提交 1–500 条真实拆解条目')
        text = self._book_text(row)
        validated = [self._validate_item(row, item, text) for item in items]
        now = timestamp()
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if (conn.execute('SELECT 1 FROM corpus_structures WHERE book_id=?',(ident,)).fetchone()
                    or conn.execute("SELECT 1 FROM corpus_jobs WHERE book_id=? AND status IN ('pending','running','paused','failed')",(ident,)).fetchone()):
                raise ValueError('该作品已进入多层结构拆解，历史局部条目不能更改制作状态')
            current = conn.execute('SELECT status FROM staging_books WHERE id=?', (ident,)).fetchone()[0]
            if current not in ('queued', 'decomposing', 'pending_verify'):
                raise ValueError('书籍状态已变化，拆解结果未入库')
            for item in validated:
                conn.execute('INSERT INTO decomp_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                             (uuid4().hex, ident, item['slot'], item['option_key'], encode(item['type_tags']),
                              encode(item['stages']), item['usage_text'], encode(item['evidence']),
                              'draft', now, now, origin))
            conn.execute("UPDATE staging_books SET status='pending_verify',progress=1,error='',updated_at=? WHERE id=?", (now, ident))
        from nw.studio.method_migration import migrate_legacy
        migrate_legacy(self)
        return self.get_staging(ident)

    def decompose_book(self, ident: str, body: dict) -> dict:
        if 'items' in body:
            return self._insert_items(ident, body['items'])
        if body not in ({}, {'mode': 'model'}):
            raise ValueError('自动拆解请使用多层结构任务；人工原文批注须提交 items')
        return self.start_corpus_job(ident, {'kind': 'structure',
            'options': {'note': self.get_corpus(ident)['body']['source_extent']['note'] or '参考作品完整性尚未确认'}})

    def verify_book(self, ident: str, body: dict) -> dict:
        row = self._staging_row(ident)
        if row['status'] != 'pending_verify':
            raise ValueError('只有待复核书籍可以批准条目')
        text = self._book_text(row)
        with self.connect() as conn:
            current = {r['id']: dict(r) for r in conn.execute('SELECT * FROM decomp_items WHERE book_id=?', (ident,))}
        approve = body.get('approvals', [])
        discard = body.get('discards', [])
        if not isinstance(approve, list) or not isinstance(discard, list) or set(approve) & set(discard):
            raise ValueError('批准与丢弃列表无效或重复')
        if body.get('approve_all') is True:
            approve = [k for k, v in current.items() if v['status'] == 'draft' and k not in discard]
        edits = body.get('edits', [])
        edited = {}
        for edit in edits:
            item_id = edit.get('id')
            if item_id not in current or current[item_id]['status'] != 'draft':
                raise ValueError('只能修改本书待复核条目')
            edited[item_id] = self._validate_item(row, {**self._item(current[item_id]), **edit}, text)
        if not (approve or discard or edited):
            raise ValueError('没有可复核的历史局部条目；结构审核请打开多层拆解')
        if any(k not in current or current[k]['status'] != 'draft' for k in approve + discard):
            raise ValueError('只能复核本书尚未决定的条目')
        now = timestamp()
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT 1 FROM corpus_structures WHERE book_id=?',(ident,)).fetchone():
                raise ValueError('该作品已有多层结构，请在结构页复核，历史局部条目不能更改结构状态')
            if conn.execute('SELECT status FROM staging_books WHERE id=?', (ident,)).fetchone()[0] != 'pending_verify':
                raise ValueError('书籍状态已变化')
            for item_id in set(approve + discard) | set(edited):
                status = conn.execute('SELECT status FROM decomp_items WHERE id=?', (item_id,)).fetchone()[0]
                if status != 'draft':
                    raise ValueError('条目已由另一操作复核，请刷新后重试')
            for item_id, item in edited.items():
                conn.execute('UPDATE decomp_items SET slot=?,option_key=?,stages_json=?,usage_text=?,evidence_json=?,updated_at=? WHERE id=?',
                             (item['slot'], item['option_key'], encode(item['stages']), item['usage_text'], encode(item['evidence']), now, item_id))
            for ids, status in [(approve, 'approved'), (discard, 'discarded')]:
                for item_id in ids:
                    conn.execute('UPDATE decomp_items SET status=?,updated_at=? WHERE id=? AND status="draft"', (status, now, item_id))
            remaining = conn.execute('SELECT COUNT(*) FROM decomp_items WHERE book_id=? AND status="draft"', (ident,)).fetchone()[0]
            conn.execute('UPDATE staging_books SET status=?,updated_at=? WHERE id=?',
                         ('pending_verify' if remaining else 'archived', now, ident))
        if not remaining:
            self._create_upgrades(ident)
        self._refresh_stats()
        return self.get_staging(ident)
