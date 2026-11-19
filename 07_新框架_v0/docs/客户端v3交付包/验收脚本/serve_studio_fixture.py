"""Visibly FAKE, isolated browser acceptance. Never use a production workspace."""
from pathlib import Path
import json
import os
import sys
PROJECT = Path(__file__).resolve().parents[3]

repo = PROJECT
sys.path[:0] = [str(repo / 'src'), str(repo / 'tests')]
from nw.config import Config
from nw.store import Store
from nw.story_state import adopt_story
from nw.studio.api import StudioService
from nw.studio.server import create_studio_server
from test_material_phase_flow import template_catalog, PhaseModel
from test_material_stage_roundtrip import StageModel
from story_fixture import baseline

workspace = PROJECT / 'build' / 'client-v3-browser' / os.environ.get('STUDIO_FIXTURE_NAME', 'production')
workspace.mkdir(parents=True,exist_ok=True)
template_catalog(workspace)
if not (workspace / 'test-book').exists():
    with Store(workspace / 'test-book', create=True, test_mode=True) as store:
        store.init_project('[FAKE] 浏览器制作验收')
        store.add_brief('[FAKE] 调查封条和钥匙的来源，仅用于客户端隔离测试。')
        adopt_story(store, baseline(), {})

class IsolatedStudio(StudioService):
    def _open_store(self, project_name, *, create=False):
        return Store(self.workspace / project_name, create=create, test_mode=True)

class ClientModel(PhaseModel, StageModel):
    def generate(self, messages, **params):
        result = super().generate(messages, **params)
        if '{"operations"' in messages[0]['content']:
            raw = json.loads(result.text)
            for op in raw['operations']:
                op.setdefault('expected_old', None)
            result.text = json.dumps(raw, ensure_ascii=False)
        return result

studio = IsolatedStudio(workspace, config_path=workspace / 'missing.toml')
port = int(os.environ.get('STUDIO_FIXTURE_PORT', '18766'))
server = create_studio_server(studio, port=port)
production = server.production
production.test_mode = True
model = ClientModel('client-browser-fixture')
config = Config('fake', 'http://localhost', 'isolated-browser-test', '', 5, {}, workspace, source_driven=True)
production.runtime_factory = lambda: (config, model)
novel = production.list()['novels'][0]
if not novel['job_id']:
    production.run(novel['id'], {'mode': 'design', 'scope': 'book'})
print(json.dumps({'url': f'http://127.0.0.1:{port}/#/studio/' + novel['id'], 'isolated': True}, ensure_ascii=False), flush=True)
try:
    server.serve_forever()
finally:
    server.server_close()
