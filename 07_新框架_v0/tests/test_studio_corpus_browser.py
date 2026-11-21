"""Exercise the shipped ES modules in an isolated Chromium against the real local API."""
import os
from pathlib import Path
import shutil
import subprocess
import threading

import pytest

from corpus_fixture import start_analysis
from nw.studio.api import StudioService
from nw.studio.corpus_catalog import corpus_catalog
from nw.studio.server import create_studio_server
from test_studio_methods import method_body


def test_visible_catalog_legacy_bookmark_and_pinned_method(tmp_path,monkeypatch):
    paths = [Path(os.environ.get('ProgramFiles', '')) / 'Google/Chrome/Application/chrome.exe',
             Path(os.environ.get('ProgramFiles(x86)', '')) / 'Microsoft/Edge/Application/msedge.exe']
    browser = shutil.which('chromium') or shutil.which('google-chrome') or next((p for p in paths if p.is_file()), None)
    if not browser:
        pytest.skip('A locally installed Chromium is required for the desktop DOM regression')
    service = StudioService(tmp_path / 'workspace', config_path=tmp_path / 'missing.toml')
    server = create_studio_server(service, port=0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    def render(route):
        result = subprocess.run([str(browser), '--headless', '--disable-gpu', '--disable-background-networking',
                                 '--no-first-run', '--disable-extensions', f'--user-data-dir={tmp_path / "browser"}',
                                 '--virtual-time-budget=4000', '--dump-dom',
                                 f'http://127.0.0.1:{server.server_port}/#/{route}'],
                                capture_output=True, timeout=35, check=True)
        return result.stdout.decode('utf-8')

    try:
        catalog = corpus_catalog()
        board = render('staging')
        assert '暂无作品' in board and '现行拆解条目' in board
        for domain, fields in catalog['domain_details'].items():
            assert f'data-analysis-domain="{domain}"' in board
            assert all(label in board for label in fields.values())
        atlas=render('atlas/GENRE_XUANYI?tab=cast')
        assert '已确认的阵容样本为 0 部' in atlas
        assert 'type="number"' not in atlas

        library = server.library
        book,job,_ = start_analysis(library,monkeypatch)
        assert job['status']=='completed', job['error']
        detail = render(f'staging/{book["id"]}?view=legacy')
        assert 'id="startCorpus"' in detail and 'id="autoDecompose"' not in detail
        assert 'data-domain-observations="cast_entry"' in detail
        distribution=render(f'staging/{book["id"]}?tab=distribution')
        observed=library.get_corpus(book['id'])['statistics']['cast_distribution']
        assert observed['unique_count']==1
        assert f'覆盖文本内去重出场 {observed["unique_count"]} 人' in distribution
        assert [c['first_count'] for c in observed['chapters']]==[1,0]
        assert [c['returning_count'] for c in observed['chapters']]==[0,1]
        for chapter in observed['chapters']:
            assert chapter['title'] in distribution
            for ident in chapter['observation_ids']:
                assert f'data-chapter-observation="{ident}"' in distribution

        from test_studio_cast_samples import add_reference
        pending_book = add_reference(library,'渡口待核',['GENRE_XUANYI'])
        document = library.get_corpus(pending_book)['body']
        next(t for t in document['threads'] if t['id']=='rb')['status']='uncertain'
        library.save_corpus(pending_book,{'expected_version':1,'body':document,'reviewed_units':['c00001','c00002']})
        library.review_corpus(pending_book,{'version':2,'decision':'approve','note':'老许的出场待核','accept_limitations':True})
        reference = render(f'staging/{pending_book}?tab=distribution')
        assert '已确认出场至少 1 人，1 章待核' in reference and 'data-chapter-observation="rb"' in reference
        atlas = render('atlas/GENRE_XUANYI?tab=cast')
        assert '全书上限未确定' in atlas and '第 1 章 · 已确认出场 1 人 · 待核人物 1 人' in atlas

        body = method_body(library)
        first = library.save_method({'body': body, 'expected_version': 0})
        library.save_method({'body': {**body, 'title': '[FAKE] 后续草稿'}, 'expected_version': 1}, first['id'])
        pinned = render(f'kb/items?method={first["id"]}&version=1')
        assert f'id="drawerTitle">{body["title"]}</h2>' in pinned
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
