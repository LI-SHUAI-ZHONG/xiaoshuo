"""Length recommendations use the reviewed complete source and a distinct work as the voting unit."""
import http.client
import json
import threading

import pytest

from nw.studio.api import StudioService
from nw.studio.corpus_catalog import DOMAINS, FIELDS, OVERVIEW
from nw.studio.corpus_index import empty_document
from nw.studio.library import LibraryService
from nw.studio.server import create_studio_server


def reference(library, text, title, types, extent='complete', *, approve=True):
    book = library.import_book({'title': title, 'filename': title + '.txt', 'text': text})
    ident = book['id']
    library.review_book(ident, {'types': types, 'decompose': False})
    if extent is None:
        return ident
    body = empty_document(text, extent=extent, note='已核对本次导入文本的起止范围')
    body['overview'] = {field: '核对已导入范围' for field in OVERVIEW}
    body['evidence'] = [{'id': 'e1', 'start': 0, 'end': 1, 'quote': text[0], 'explanation': '原作开头'}]
    event = dict.fromkeys(FIELDS['events'], '')
    event.update(id='opening', unit_id='c00001', granularity='overview', story_order=1,
                 summary='核对开头', result='读到开头', characters=[], parent_event_ids=[], evidence_ids=['e1'])
    body['events'] = [event]
    body['domains'] = [{'domain': domain, 'status': 'not_observed', 'explanation': '正文没有该结构',
                        'evidence_ids': ['e1']} for domain in DOMAINS]
    saved = library.save_corpus(ident, {'expected_version': 0, 'body': body, 'reviewed_units': ['c00001']})
    if approve:
        library.review_corpus(ident, {'version': saved['version'], 'decision': 'approve', 'note': '已复核全文结构',
                                      'accept_limitations': True})
    return ident


def test_five_tiers_only_vote_for_matching_reviewed_complete_sources(tmp_path):
    lib = LibraryService(tmp_path)
    genre = lib.genres()['genres'][0]
    main, child, sibling = genre['id'], genre['children'][0]['id'], genre['children'][1]['id']
    assert lib.recommend_length([])['status'] == 'no_types'
    assert len(lib.recommend_length([])['tiers']) == 5
    assert lib.recommend_length([child])['status'] == 'no_samples'
    reference(lib, '短文', '短文样本', [child])
    assert lib.recommend_length([child])['status'] == 'outside_tiers'

    reference(lib, '甲' * 300000, '甲本', [child])
    reference(lib, '甲 ' * 300000, '甲本换行本', [child])
    reference(lib, '乙' * 400000, '乙本', [child])
    reference(lib, '丙' * 400000, '未确认全文', [child], 'unknown')
    reference(lib, '丁' * 400000, '摘录', [child], 'excerpt')
    reference(lib, '戊' * 400000, '仅归档', [child], None)
    reference(lib, '己' * 400000, '[FAKE] 隔离样本', [child])
    reference(lib, '[FAKE] ' + '庚' * 400000, '明确标记的测试文本', [child])
    reference(lib, '辛' * 400000, '另一子类', [sibling])
    pending = reference(lib, '壬' * 400000, '壬本', [child], approve=False)

    tied = lib.recommend_length([child])
    assert (tied['sample_count'], tied['eligible_count'], tied['outside_count']) == (3, 2, 1)
    assert tied['leading_tiers'] == [300000, 500000] and tied['recommended_tier'] is None
    assert tied['status'] == 'tied'
    assert lib.recommend_length([main])['recommended_tier'] == 500000
    assert lib.recommend_length([child, sibling])['status'] == 'no_samples'

    lib.review_corpus(pending, {'version': 1, 'decision': 'approve', 'note': '已确认原文', 'accept_limitations': True})
    recommended = lib.recommend_length([child])
    assert recommended['status'] == 'recommended' and recommended['recommended_tier'] == 500000
    assert recommended['counts']['500000'] == 2

    structure = lib.get_corpus(pending)
    structure['body']['source_extent'] = {'status': 'excerpt', 'note': '复核范围为摘录'}
    update = lib.save_corpus(pending, {'expected_version': 1, 'body': structure['body'], 'reviewed_units': ['c00001']})
    assert lib.recommend_length([child]) == recommended
    lib.review_corpus(pending, {'version': update['version'], 'decision': 'approve', 'note': '范围已修正',
                                'accept_limitations': True})
    assert LibraryService(tmp_path).recommend_length([child])['status'] == 'tied'
    structure['body']['source_extent'] = {'status': 'complete', 'note': '已重新对照完整原作'}
    lib.save_corpus(pending, {'expected_version': 2, 'body': structure['body'], 'reviewed_units': ['c00001']})
    lib.review_corpus(pending, {'version': 3, 'decision': 'approve', 'note': '来源核实', 'accept_limitations': True})
    assert lib.recommend_length([child]) == recommended

    row = lib._staging_row(pending)
    source_path = lib.root / row['file_path']
    source_path.write_text('外部替换文本', encoding='utf-8')
    assert lib.recommend_length([child])['status'] == 'tied'
    source_path.write_text('壬' * 400000, encoding='utf-8')
    lib.review_book(pending, {'decision': 'reject'})
    assert lib.recommend_length([child])['status'] == 'tied'


def test_import_preserves_literal_offsets_and_reads_historical_windows_encoding(tmp_path):
    lib = LibraryService(tmp_path)
    original = '第一章\r\n甲\n乙\r丙。'
    book = lib.import_book({'text': original, 'filename': '段落.txt'})
    assert lib.get_staging(book['id'])['text'] == original
    row = lib._staging_row(book['id'])
    path = lib.root / row['file_path']
    assert path.read_bytes() == original.encode('utf-8')
    path.write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    assert lib.get_staging(book['id'])['text'] == original
    path.write_bytes(path.read_bytes() + b'!')
    with pytest.raises(ValueError, match='原文已改变'):
        lib.get_staging(book['id'])


def test_http_import_upper_tier_source_and_count_without_guessing_its_extent(tmp_path):
    api = StudioService(tmp_path, config_path=tmp_path / 'absent.toml', projects_root=tmp_path / 'books')
    server = create_studio_server(api, port=0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=30)
    try:
        text = '𠮷' * 2250000 + '\r\n'
        payload = json.dumps({'text': text, 'filename': '边界.txt'}, ensure_ascii=False).encode()
        assert len(payload) > 8 * 1024 * 1024
        client.request('POST', '/api/staging', body=payload, headers={'Content-Type': 'application/json'})
        response = client.getresponse()
        added = json.loads(response.read())
        assert response.status in (200, 201), added
        assert added['words'] == 2250000
        client.request('GET', '/api/recommendations/length?types=GENRE_XUANYI')
        response = client.getresponse()
        result = json.loads(response.read())
        assert response.status == 200 and result['status'] == 'no_samples'
        assert result['tiers'][-1]['max_words'] == 2250000
        client.request('POST', '/api/novels', headers={'Content-Type': 'application/json',
                                                     'Content-Length': str(len(payload))})
        response = client.getresponse()
        assert response.status == 400 and '8MB' in json.loads(response.read())['error']
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
