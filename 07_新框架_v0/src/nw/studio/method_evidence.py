"""Resolve exact, source-hashed quotations for method review."""
import hashlib
import json
from typing import Any


def locate(service: Any, body: dict) -> dict:
    quote = body.get('quote')
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 1500:
        raise ValueError('请填写不超过 1500 字的原作短摘录')
    book = service._staging_row(str(body.get('book_id', '')))
    content = service._book_text(book)
    start = body.get('start')
    if start is None:
        start = content.find(quote)
        if start < 0 and '\n' in quote and '\r\n' in content:
            crlf_quote = quote.replace('\r\n', '\n').replace('\n', '\r\n')
            pos = content.find(crlf_quote)
            if pos >= 0:
                if content.find(crlf_quote, pos + 1) >= 0:
                    raise ValueError('摘录出现多次，请填写原文字符起点')
                quote = crlf_quote
                start = pos
        elif start >= 0 and content.find(quote, start + 1) >= 0:
            raise ValueError('摘录出现多次，请填写原文字符起点')
    if type(start) is not int or start < 0 or content[start:start + len(quote)] != quote:
        raise ValueError('证据与原文定位不一致')
    return {'book_id': book['id'], 'start': start, 'end': start + len(quote), 'quote': quote,
            'explanation': str(body.get('explanation', '')).strip()}


def resolve(service: Any, rows: list[dict], *, pins: list[dict] | None = None,
            books: dict | None = None) -> tuple[list[dict], list[dict]]:
    resolved, issues = [], []
    cache = {} if books is None else books
    for index, row in enumerate(rows):
        try:
            if row['book_id'] not in cache:
                book = service._staging_row(row['book_id'])
                content = service._book_text(book)
                cache[row['book_id']] = (book, content)
            book, content = cache[row['book_id']]
            if row['end'] != row['start'] + len(row['quote']) or content[row['start']:row['end']] != row['quote']:
                raise ValueError('证据与原文定位不一致')
            chapters = [c['title'] for c in json.loads(book['chapters_json'])
                        if c['start'] < row['end'] and c['end'] > row['start']]
            pin = {'book_id': book['id'], 'book_title': book['title'], 'source_sha256': book['sha256'],
                'start': row['start'], 'end': row['end'], 'chapters': chapters,
                'quote_sha256': hashlib.sha256(row['quote'].encode('utf-8')).hexdigest()}
            if pins is not None:
                old = next((p for p in pins if p.get('book_id') == row['book_id']
                            and p.get('start') == row['start'] and p.get('end') == row['end']), {})
                if old.get('source_sha256') != book['sha256']:
                    raise ValueError('方法冻结的来源版本与当前原作不一致')
            resolved.append(pin)
            if book['status'] != 'archived':
                issues.append({'field': 'evidence', 'message': f'《{book["title"]}》尚未审核入库或已撤回'})
        except (OSError, ValueError, KeyError) as exc:
            issues.append({'field': 'evidence', 'message': f'第 {index + 1} 处原作证据：{exc}'})
    return resolved, issues
