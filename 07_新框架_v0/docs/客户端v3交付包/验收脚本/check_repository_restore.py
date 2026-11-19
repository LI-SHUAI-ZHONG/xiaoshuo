"""Verify a restored checkout through source hashes, material state and real HTTP.

Run after tools/materials_baseline.py restore, using only the Python stdlib.
The check never calls a model or writes novel prose.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / 'src'))

from nw.materials.adjudication import _code_hash, adjudication_status
from nw.materials.source_set import selection_status
from nw.materials.work_catalog import SourceDesk
from nw.studio.api import StudioService
from nw.studio.server import create_studio_server


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(workspace: Path) -> dict:
    package = Path(__file__).parent.parent
    before = json.loads((package / 'protected-baseline.json').read_text(encoding='utf-8'))
    assert _code_hash() == before['adjudication'], 'Core adjudication fingerprint differs'
    assert sha(PROJECT / 'src/nw/materials/phase_routes.py') == before['phase_routes']
    for name, expected in before['originals'].items():
        assert sha(PROJECT.parent / name) == expected, f'Original bytes differ: {name}'
    state = adjudication_status(workspace)['status']
    assert state == 'current', f'Adjudication baseline is {state}'
    selected = selection_status(workspace)
    assert selected is not None and selected['active_file_sources'] == 6
    desk = SourceDesk(workspace)
    states = dict(Counter(row['state'] for row in desk.rows))
    previous = json.loads((package / '资料恢复核验.json').read_text(encoding='utf-8'))
    assert len(desk.rows) == previous['materials'] and states == previous['states']

    # Use the checkout's own server, static assets and material databases.
    service = StudioService(workspace, config_path=PROJECT / 'config.example.toml')
    server = create_studio_server(service, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks = {}
    try:
        for route in ('/', '/js/pages/settings.js', '/icons/studio-brand.ico',
                      '/api/status', '/api/genres'):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=60)
            try:
                connection.request('GET', route)
                response = connection.getresponse()
                payload = response.read()
                assert response.status == 200, (route, response.status, payload[:200])
                checks[route] = response.status
                if route == '/api/status':
                    status = json.loads(payload)
                    assert status['catalog']['total_sources'] == len(desk.rows)
                    assert status['catalog']['has_reviews']
                    assert status['f2_ledger']['available']
                    assert not status['config_valid'], 'Example API configuration must stay blank'
                elif route == '/api/genres':
                    genres = json.loads(payload)
                    assert genres['counts'] == {'main': 35, 'sub': 425}
                    assert len(genres['slots']) == 8
            finally:
                connection.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    return {
        'verified': True,
        'checked_commit': subprocess.check_output(
            ['git', '-C', str(PROJECT), 'rev-parse', 'HEAD'], text=True).strip(),
        'working_copy': str(PROJECT),
        'restored_workspace': str(workspace),
        'source_code_loaded_from': str(Path(sys.modules['nw.studio.api'].__file__).resolve()),
        'original_files_unchanged': len(before['originals']),
        'protected_core_files_unchanged': 21,
        'phase_routes_unchanged': True,
        'active_source_files': selected['active_file_sources'],
        'material_rows': len(desk.rows),
        'material_states': states,
        'adjudication_status': state,
        'http': checks,
        'genre_counts': genres['counts'],
        'model_calls': 0,
        'writes_novel_prose': False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=PROJECT / 'workspace')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check(args.workspace.resolve())
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
