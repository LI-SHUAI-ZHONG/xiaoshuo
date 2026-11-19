from pathlib import Path
import os
import sys
PROJECT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(PROJECT / 'src'))
from nw.studio.api import StudioService
from nw.studio.server import create_studio_server

root = Path(os.environ.get('STUDIO_BROWSER_ROOT', str(PROJECT / 'build' / 'client-v3-browser' / 'library')))
service = StudioService(root, config_path=root / 'unconfigured.toml')
server = create_studio_server(service, host='127.0.0.1', port=18765)
print('Studio v3 isolated browser verification on 18765', flush=True)
try:
    server.serve_forever()
finally:
    server.server_close()
