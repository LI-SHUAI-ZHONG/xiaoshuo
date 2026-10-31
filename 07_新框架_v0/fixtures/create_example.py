"""Create the author-draft example only; never calls a model or exports prose."""
import argparse
import json
from pathlib import Path
from nw.cli import project_directory
from nw.config import ROOT
from nw.store import Store


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=ROOT / 'workspace')
    parser.add_argument('--project', default='chaohen')
    args = parser.parse_args()
    data = json.loads((Path(__file__).parent / 'chaohen_minimal.json').read_text(encoding='utf-8'))
    with Store(project_directory(args.workspace, args.project), create=True) as store:
        store.init_project(data['name'])
        store.add_brief(data['brief'], data['constraints'])
        for entry in data['bible']:
            store.add_bible(**entry)
        chapter = store.add_chapter(1, data['scene']['title'])
        scene = store.add_scene(chapter.id, 1, json.dumps(data['scene'], ensure_ascii=False))
        print(json.dumps({'scene_id': scene.id}))

if __name__ == '__main__':
    main()
