"""[FAKE] Isolated source-structure browser fixture; GitHub sync stays disabled."""
import argparse
import json
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'src'),str(PROJECT/'tests')]

from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
from corpus_fixture import SOURCE,CorpusModel,make_book,runtime,wait_job


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--port',type=int,default=18769)
    args=parser.parse_args();workspace=args.workspace.resolve()
    if not workspace.is_relative_to((PROJECT/'build').resolve()):
        raise ValueError('隔离夹具只允许使用本项目build目录')
    studio=StudioService(workspace,config_path=workspace/'missing.toml')
    server=create_studio_server(studio,port=args.port)
    assert not server.repository.enabled
    library=server.library;provider=CorpusModel()
    library._corpus_runtime=lambda:(runtime(),provider)
    book=make_book(library)
    retry=make_book(library,SOURCE+'[FAKE] 第二本仅验证未知调用续接。\n')
    if not library.list_corpus_jobs(retry['id'])['jobs']:
        provider.fail_at=2
        started=library.start_corpus_job(retry['id'],{'options':{'extent':'excerpt','note':'[FAKE] 中断续接'}})
        assert wait_job(library,retry['id'],started['id'])['status']=='paused'
    provider.fail_at=None
    metadata={'base':f'http://127.0.0.1:{server.server_port}','book_id':book['id'],'retry_book_id':retry['id'],
              'isolated':True,'provider':'[FAKE] local test double','github_sync':False}
    (workspace/'browser.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False),flush=True)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=='__main__':main()
