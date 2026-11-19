"""Verify automatic recovery using only a clean Git checkout, never a model."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / 'src'))

from nw.materials.adjudication import adjudication_status
from nw.materials.work_catalog import SourceDesk
from nw.studio.api import StudioService
from nw.studio.repository import RepositorySync
from nw.studio.repository_data import digest, load_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    service = StudioService(PROJECT / 'workspace')
    manager = RepositorySync(service)
    assert manager.enabled and manager.git is not None, manager.status()
    manager.prepare()
    assert not manager.restore_required, manager.status()
    assert service.config_path == PROJECT / 'studio.config.toml'
    manifest = load_manifest(PROJECT / 'studio_data/runtime')
    assert manifest is not None
    assert all(digest(service.workspace / entry['path']) == entry['sha256'] for entry in manifest['entries'])
    desk = SourceDesk(service.workspace)
    assert len(desk.rows) == 22941
    assert adjudication_status(service.workspace)['status'] == 'current'
    module = Path(sys.modules['nw.studio.api'].__file__).resolve()
    assert module.is_relative_to(PROJECT / 'src')
    result = {'verified': True, 'checked_commit': subprocess.check_output(
        ['git', '-C', str(PROJECT), 'rev-parse', 'HEAD'], text=True).strip(),
        'github_url': manager.git.url, 'branch': manager.git.branch,
        'source_code_loaded_from': str(module), 'config_path': str(service.config_path),
        'workspace': str(service.workspace), 'automatic_material_recovery': True,
        'material_rows': len(desk.rows), 'adjudication_status': 'current',
        'automatic_novel_recovery': True, 'restored_novel_files': len(manifest['entries']),
        'all_novel_file_hashes_match': True, 'formal_novels': len(service.list_projects()),
        'runtime_snapshot': manifest['content_sha256'], 'model_calls': 0,
        'github_background_worker_started': False}
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
