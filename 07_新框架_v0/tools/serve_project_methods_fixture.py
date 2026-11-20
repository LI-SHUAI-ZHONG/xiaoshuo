"""[FAKE] Isolated browser fixture for concrete method execution and author gates."""
import argparse
import json
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'src'),str(PROJECT/'tests')]

import pytest
from nw.config import Config
from nw.novel_store import JobRequest,start_job
from nw.production_methods.policy import normalize
from nw.store import Store
from nw.story_state import adopt_story
from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
from nw.task_models import Budget
from project_methods_fixture import seed_method,template_catalog,ProjectModel
from story_fixture import baseline


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--port',type=int,default=18770)
    args=parser.parse_args();workspace=args.workspace.resolve()
    if not workspace.is_relative_to((PROJECT/'build').resolve()):raise ValueError('Only an isolated build workspace is allowed')
    workspace.mkdir(parents=True,exist_ok=True)
    template_catalog(workspace);patch=pytest.MonkeyPatch();_,method=seed_method(workspace,patch)
    studio=StudioService(workspace,config_path=workspace/'missing.toml');server=create_studio_server(studio,port=args.port)
    assert not server.repository.enabled
    app=server.production;app.test_mode=True;model=ProjectModel()
    cfg=Config('fake','http://localhost','[FAKE] browser-project-methods','',5,{},workspace,source_driven=False)
    app.runtime_factory=lambda:(cfg,model)
    ident='[FAKE]-method-browser';directory='[FAKE]-method-browser-story'
    policy=normalize({'tasks':['hook']},types=['GENRE_XUANYI'])
    app.db.add(ident,directory,'[FAKE] 本项目制作方法验收',{'title':'[FAKE] 本项目制作方法验收','genre_ids':['GENRE_XUANYI'],'production_methods':policy})
    novel=app.db.get(ident)
    if not novel['job_id']:
        with Store(workspace/directory,create=True,test_mode=True) as store:
            store.init_project('[FAKE] 本项目制作方法验收');store.add_brief('[FAKE] 查出旧印与登记者之间的关系，调查过程须承担代价。')
            adopt_story(store,baseline(),{})
            job=start_job(store,JobRequest('design',design_scope='book',budget=Budget(80,200000,6000),production_method_policy=policy))
        app.db.update(ident,job_id=job.id)
        app.run(ident,{})
    data={'base':f'http://127.0.0.1:{server.server_port}','novel_id':ident,'method_id':method['id'],
          'isolated':True,'github_sync':False,'model':'[FAKE] local test double'}
    (workspace/'browser.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();patch.undo()


if __name__=='__main__':main()
