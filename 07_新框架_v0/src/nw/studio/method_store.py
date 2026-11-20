"""Maintain immutable method revisions, separate from original source rules."""
import hashlib
import json
from typing import Any
from uuid import uuid4

from nw.studio.catalog import canonical_types
from nw.studio.library_util import encode, timestamp
from nw.studio.method_catalog import SCOPES, TASKS, method_catalog
from nw.studio.method_contract import completeness, draft, text
from nw.studio.method_evidence import locate, resolve


def digest(body: dict) -> str:
    return hashlib.sha256(encode(body).encode('utf-8')).hexdigest()


class MethodMixin:
    def method_catalog(self) -> dict:
        return method_catalog()

    def locate_method_evidence(self, body: dict) -> dict:
        return locate(self, body)

    def _method_head(self, ident: str, conn: Any) -> dict:
        row = conn.execute('SELECT * FROM production_methods WHERE id=?', (ident,)).fetchone()
        if row is None:
            raise FileNotFoundError('生产方法不存在')
        return dict(row)

    def _method_row(self, head: dict, version: int, conn: Any, books: dict | None = None) -> dict:
        raw = conn.execute('SELECT * FROM production_method_versions WHERE method_id=? AND version=?',
                           (head['id'], version)).fetchone()
        if raw is None:
            raise FileNotFoundError('方法版本不存在')
        body = json.loads(raw['body_json'])
        if digest(body) != raw['body_sha256']:
            raise ValueError('方法版本完整性校验失败，请核对仓库资料')
        review = conn.execute('SELECT * FROM production_method_reviews WHERE method_id=? AND version=?',
                              (head['id'], version)).fetchone()
        pins = json.loads(raw['evidence_json'])
        resolved, unavailable = resolve(self, body['evidence'], pins=pins, books=books)
        from nw.studio.corpus_methods import origin_status
        origin, origin_issues = origin_status(self, head['id'], version, body, conn)
        unavailable += origin_issues
        issues = completeness(body)
        state = {'approve': 'approved', 'reject': 'rejected'}.get(review['decision'], 'draft') if review else 'draft'
        return {'id': head['id'], 'version': version, 'latest_version': head['latest_version'],
            'approved_version': head['approved_version'], 'body': body, 'body_sha256': raw['body_sha256'],
            'status': 'source_unavailable' if state == 'approved' and unavailable else state,
            'review_state': state, 'review': dict(review) if review else None,
            'available': state == 'approved' and not issues and not unavailable,
            'issues': issues, 'source_issues': unavailable, 'evidence_locations': resolved,
            'origin_item_id': head['origin_item_id'], 'legacy': json.loads(raw['legacy_json']),
            'structure_origin': origin,
            'created_at': raw['created_at'], 'updated_at': head['updated_at'],
            'authority': 'reference_method', 'missing_input_policy': 'return_design',
            'runtime_integration': 'project_design_and_review' if origin else 'requires_approved_structure'}

    def get_method(self, ident: str, version: int | None = None) -> dict:
        with self.connect() as conn:
            head = self._method_head(ident, conn)
            if version is not None and (type(version) is not int or version < 1):
                raise ValueError('版本须为正整数')
            result = self._method_row(head, version or head['latest_version'], conn)
            history = conn.execute('SELECT v.version,v.body_sha256,v.created_at,r.decision '
                'FROM production_method_versions v LEFT JOIN production_method_reviews r '
                'ON r.method_id=v.method_id AND r.version=v.version '
                'WHERE v.method_id=? ORDER BY v.version DESC', (ident,)).fetchall()
        result['history'] = [dict(row) for row in history]
        return result

    def save_method(self, request: dict, ident: str | None = None) -> dict:
        if not isinstance(request, dict) or set(request) - {'body', 'expected_version'}:
            raise ValueError('方法保存请求无效')
        body, _ = draft(request.get('body'))
        pins, source_issues = resolve(self, body['evidence'])
        if len(pins) != len(body['evidence']):
            raise ValueError('；'.join(row['message'] for row in source_issues))
        if len(encode(body).encode('utf-8')) > 96 * 1024:
            raise ValueError('方法内容超过 96 KiB，请按独立用途拆成多条方法')
        expected = request.get('expected_version')
        if type(expected) is not int or expected < 0:
            raise ValueError('保存须提供当前版本，新方法为 0')
        now = timestamp()
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            legacy = '{}'
            if ident is not None:
                head = self._method_head(ident, conn)
                if head['latest_version'] != expected:
                    raise ValueError('方法已更新，请刷新后以当前版本保存')
                version = expected + 1
                legacy = conn.execute('SELECT legacy_json FROM production_method_versions WHERE method_id=? '
                                      'AND version=?', (ident, expected)).fetchone()[0]
                conn.execute('UPDATE production_methods SET latest_version=?,updated_at=? WHERE id=?',
                             (version, now, ident))
            else:
                if expected != 0:
                    raise ValueError('新方法的当前版本须为 0')
                ident, version = uuid4().hex, 1
                conn.execute('INSERT INTO production_methods VALUES(?,?,NULL,NULL,?,?)', (ident, version, now, now))
            conn.execute('INSERT INTO production_method_versions VALUES(?,?,?,?,?,?,?)',
                (ident, version, encode(body), digest(body), encode(pins), legacy, now))
            if version > 1:
                from nw.studio.corpus_methods import inherit_origin
                inherit_origin(conn, ident, expected, version)
        return self.get_method(ident)

    def review_method(self, ident: str, body: dict) -> dict:
        version, decision = body.get('version'), body.get('decision')
        if type(version) is not int or version < 1 or decision not in ('approve', 'reject'):
            raise ValueError('请指定方法版本和批准/退回决定')
        note = text(body.get('note', ''), '审核说明')
        if not note:
            raise ValueError('请记录审核依据或退回原因')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            head = self._method_head(ident, conn)
            if version != head['latest_version']:
                raise ValueError('方法已更新，只能审核当前版本')
            current = self._method_row(head, version, conn)
            if current['review']:
                raise ValueError('该方法版本已审核；修订须保存新版本')
            if decision == 'approve':
                issues = current['issues'] + current['source_issues']
                if issues:
                    raise ValueError('方法尚不能批准：' + '；'.join(row['message'] for row in issues))
            conn.execute('INSERT INTO production_method_reviews VALUES(?,?,?,?,?)',
                         (ident, version, decision, note, timestamp()))
            if decision == 'approve':
                conn.execute('UPDATE production_methods SET approved_version=?,updated_at=? WHERE id=?',
                             (version, timestamp(), ident))
        return self.get_method(ident)

    def list_methods(self, *, task: str = '', scope: str = '', types: list[str] | None = None,
                     status: str = '', q: str = '', limit: int = 40, offset: int = 0) -> dict:
        states = ('draft', 'approved', 'rejected', 'source_unavailable')
        if task and task not in TASKS or scope and scope not in SCOPES or status and status not in states:
            raise ValueError('方法筛选条件无效')
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
            raise ValueError('分页须为 1–100 条且起点非负')
        selected = set(canonical_types(types or []))
        query = text(q, '搜索词', 200).casefold()
        result, books = [], {}
        with self.connect() as conn:
            heads = conn.execute('SELECT * FROM production_methods ORDER BY updated_at DESC,id').fetchall()
            pending = conn.execute('SELECT COUNT(*) FROM production_methods WHERE origin_item_id IS NOT NULL '
                                   'AND approved_version IS NULL').fetchone()[0]
            for raw in heads:
                head = dict(raw)
                version = head['approved_version'] if status in ('approved', 'source_unavailable') else head['latest_version']
                if version is None:
                    continue
                row = self._method_row(head, version, conn, books)
                method = row['body']
                if task and task not in method['tasks'] or scope and scope not in method['scopes']:
                    continue
                # Exact selected type tags must all be covered, unless explicitly cross-type.
                if selected and method['type_tags'] and not selected <= set(method['type_tags']):
                    continue
                if status and row['status'] != status:
                    continue
                if query and query not in encode(method).casefold():
                    continue
                result.append(row)
        return {'methods': result[offset:offset + limit], 'total': len(result), 'limit': limit, 'offset': offset,
            'legacy_pending_count': pending, 'runtime_integration': 'not_connected',
            'missing_input_policy': 'return_design',
            'note': '已批准表示方法库审核通过；尚未接通本项目卡生成，不表示文学效果已验证。'}
