"""Exercise the shipped ES modules in an isolated Chromium against the real local API."""
import json
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


def chromium():
    paths = [Path(os.environ.get('ProgramFiles', '')) / 'Google/Chrome/Application/chrome.exe',
             Path(os.environ.get('ProgramFiles(x86)', '')) / 'Microsoft/Edge/Application/msedge.exe']
    browser = shutil.which('chromium') or shutil.which('google-chrome') or next((p for p in paths if p.is_file()), None)
    if not browser:
        pytest.skip('A locally installed Chromium is required for the desktop DOM regression')
    return str(browser)


def test_edit_single_technique_and_quote_role_in_desktop_browser(tmp_path,monkeypatch):
    from corpus_fixture import CorpusModel, make_book, runtime, wait_job

    browser=chromium()
    service=StudioService(tmp_path/'workspace',config_path=tmp_path/'missing.toml')
    server=create_studio_server(service,port=0)
    library=server.library
    text='# 第一章 📖\n风一推，门环磕了两声。\n# 第二章\n值夜人打开门看了看。'
    book=make_book(library,text)['id']
    model=CorpusModel()
    monkeypatch.setattr(library,'_corpus_runtime',lambda:(runtime(),model))
    job=library.start_corpus_job(book,{'options':{'extent':'excerpt','note':'只供隔离界面测试'}})
    assert wait_job(library,book,job['id'])['status']=='completed'
    doc=library.get_corpus(book)['body']
    for evidence in doc['evidence']:
        if evidence['quote'].startswith('#'):
            heading,_,body=evidence['quote'].partition('\n')
            evidence.update(start=evidence['start']+len(heading)+1,quote=body)
    detail=next(e for e in doc['events'] if e['granularity']=='detail')
    quote=detail['evidence_ids'][0]
    narration=next(t['id'] for t in doc['threads'] if t['domain']=='narration')
    for key in ('Q_title','Q_title_alias'):
        doc['evidence'].append({'id':key,'start':0,'end':len('# 第一章 📖'),'quote':'# 第一章 📖','explanation':'章名'})
        detail['evidence_ids'].append(key)
    library.save_corpus(book,{'expected_version':1,'body':doc})
    # One test-only page drives the shipped UI in a same-origin iframe. The client
    # still loads its ordinary assets, sends its normal source header and writes
    # through the unmodified HTTP API on a temporary workspace.
    args={'book':book,'thread':narration,'event':detail['id'],'quote':quote}
    script=Path(__file__).with_name('corpus_editor_browser.js').read_text(encoding='utf-8')
    harness=('<meta charset="utf-8"><iframe id="studio" src="/#/staging/'+book+'?tab=evidence"></iframe>'
             '<script>const fixture='+json.dumps(args)+';</script><script>'+script+'</script>').encode()
    done=threading.Event()
    report={}
    handler=server.RequestHandlerClass
    original_get,original_post=handler.do_GET,handler.do_POST

    def get(self):
        if self.path!='/_editor_test':
            return original_get(self)
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(harness)))
        self.end_headers()
        self.wfile.write(harness)

    def post(self):
        if self.path!='/_editor_result':
            return original_post(self)
        report.update(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self._send_json(200,{})
        done.set()

    monkeypatch.setattr(handler,'do_GET',get)
    monkeypatch.setattr(handler,'do_POST',post)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    process=None
    try:
        process=subprocess.Popen([browser,'--headless','--disable-gpu','--disable-background-networking',
                                  '--no-first-run','--disable-extensions',f'--user-data-dir={tmp_path/"browser"}',
                                  f'http://127.0.0.1:{server.server_port}/_editor_test'],
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert done.wait(45),'Browser did not finish the editor round trip'
        assert report=={'status':'reopened'},report
        saved=library.get_corpus(book)
        assert saved['latest_version']==5
        assert next(q for q in saved['body']['evidence'] if q['id']=='Q_title')['text_role']=='heading'
        seq=next(t['details']['passage_sequence'] for t in saved['body']['threads'] if t['id']==narration)
        assert seq['kind']=='sensory_evidence' and [(b['role'],b['evidence_id']) for b in seq['beats']]==[('detail',quote)]
        assert not any('题外文字' in issue['message'] for issue in saved['issues'])
        old=library.get_corpus(book,2)
        assert 'text_role' not in next(q for q in old['body']['evidence'] if q['id']=='Q_title')
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=10)
        server.shutdown()
        server.server_close()
        worker.join(5)


def test_visible_catalog_legacy_bookmark_and_pinned_method(tmp_path,monkeypatch):
    browser = chromium()
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
        for technique in catalog['passage_sequences'].values():
            assert technique['label'] in board
            roles = [technique['roles'][r]+('' if r in technique['required_roles'] else '（原文出现时）')
                     for r in technique['role_order']]
            if technique.get('role_order_flexible'):
                assert ' 与 '.join(roles)+'（按原文先后）' in board
            else:
                assert ' → '.join(roles) in board
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
