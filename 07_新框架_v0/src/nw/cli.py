"""Local project commands, context providers and blind comparisons."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

from nw.store import Store
from nw.config import ConfigRequired, ROOT, load_config, make_provider
from nw.generation import write_scene, review_draft
from nw.flow.engine import FlowEngine
from nw.experiments.ab import Experiment


def decide_interactively(node: str, payload: dict) -> str:
    print(json.dumps({'node': node, 'data': payload}, ensure_ascii=False, indent=2), file=sys.stderr)
    prompt = ('接受 accept / 退回修订 revise / 暂停 pause: ' if node == 'N5'
              else '确认 confirm / 暂停 pause: ')
    print(prompt, end='', file=sys.stderr, flush=True)
    try:
        return input().strip().lower()
    except EOFError:
        return 'pause'


def project_directory(workspace: Path, name: str) -> Path:
    """Require a single Windows-compatible directory name inside workspace."""
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{n}' for p in ('COM', 'LPT') for n in range(1, 10)}
    if (not name or name in ('.', '..') or name.endswith((' ', '.'))
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.split('.')[0].upper() in reserved):
        raise ValueError('Invalid project directory name')
    root = workspace.resolve()
    directory = (root / name).resolve()
    if directory.parent != root:
        raise ValueError('Project directory must stay inside workspace')
    return directory


def dispatch(store: Store, args: argparse.Namespace) -> Any:
    if args.command == 'init':
        return store.init_project(args.name)
    store.project()
    if args.command == 'ab':
        experiment = Experiment(store)
        if args.action == 'start':
            return experiment.start(args.scene, args.provider_instance, args.settings.model, args.settings.params,
                                    a=args.a, b=args.b, seed=args.seed)
        if args.action == 'choose':
            return experiment.choose(args.choice, args.experiment)
        if args.action == 'show':
            return experiment.view(args.experiment)
        return experiment.reveal(args.experiment)
    if args.command == 'review':
        return review_draft(store, args.draft, args.provider_instance, args.settings.model, args.settings.params)
    if args.command == 'flow':
        notes = json.loads(args.notes.read_text(encoding='utf-8')) if args.action == 'run' else None
        def decide(node: str, payload: dict) -> str:
            if args.yes:
                return 'accept' if node == 'N5' else 'confirm'
            return decide_interactively(node, payload)
        return FlowEngine(store, args.provider_instance, args.settings.model, args.settings.params, args.context).run(
            args.scene, decide, notes=notes, resume=args.action == 'resume',
            retry_failed=getattr(args, 'retry_failed', False))
    if args.command == 'write':
        run, draft = write_scene(store, args.scene, args.provider_instance, args.settings.model, args.settings.params, context_name=args.context)
        return {'run': asdict(run), 'draft': asdict(draft) if draft else None}
    if args.command == 'accept':
        return store.accept(args.draft)
    if args.command == 'runs':
        return [dict(asdict(run), response=store.run_output(run.id)) for run in store.list('run')]
    if args.command == 'brief':
        return store.add_brief(args.text, args.constraints)
    if args.command == 'bible':
        if args.action == 'list':
            return store.bible()
        return store.add_bible(args.kind, args.name, args.body)
    if args.command == 'outline':
        if args.action == 'chapter':
            return store.add_chapter(args.index, args.title)
        return store.add_scene(args.chapter, args.index, args.card.read_text(encoding='utf-8'))
    if args.record_id:
        if args.kind == 'run':
            return dict(asdict(store.get('run', args.record_id)), response=store.run_output(args.record_id))
        return store.get(args.kind, args.record_id)
    if args.kind == 'project':
        return store.project()
    return store.list(args.kind)


def main(argv: list[str] | None = None) -> int:
    """Execute a storage command and print UTF-8 compatible JSON records."""
    parser = argparse.ArgumentParser(
        prog="python -m nw",
        description="Novel-writing framework v0 (M4 context and A/B).",
        epilog="fake is available only through the isolated automated test API.",
    )
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--config', type=Path, default=ROOT / 'config.toml')
    parser.add_argument('--project', help='project directory name')
    commands = parser.add_subparsers(dest='command')
    ab = commands.add_parser('ab').add_subparsers(dest='action', required=True)
    start = ab.add_parser('start')
    start.add_argument('--scene', required=True)
    start.add_argument('--a', default='minimal')
    start.add_argument('--b', default='rules_pack')
    start.add_argument('--seed', type=int)
    start.add_argument('--provider', choices=['ollama', 'openai_compat'])
    for action in ('choose', 'reveal', 'show'):
        command = ab.add_parser(action)
        command.add_argument('--experiment', help='defaults to latest experiment')
        if action == 'choose':
            command.add_argument('choice', type=int, choices=[1, 2])
    review = commands.add_parser('review')
    review.add_argument('--draft', required=True)
    review.add_argument('--provider', choices=['ollama', 'openai_compat'])
    flow = commands.add_parser('flow').add_subparsers(dest='action', required=True)
    for action in ('run', 'resume'):
        command = flow.add_parser(action)
        command.add_argument('--scene', required=True)
        command.add_argument('--context', default='minimal')
        command.add_argument('--provider', choices=['ollama', 'openai_compat'])
        command.add_argument('--yes', action='store_true', help='explicitly confirm all gates and accept the first complete reviewed draft')
        if action == 'run':
            command.add_argument('--notes', type=Path, required=True, help='UTF-8 JSON author state notes to record after acceptance')
        else:
            command.add_argument('--retry-failed', action='store_true', help='explicitly retry failed/unknown calls as new Runs; completed calls are reused')
    write = commands.add_parser('write')
    write.add_argument('--scene', required=True)
    write.add_argument('--context', default='minimal')
    write.add_argument('--provider', choices=['ollama', 'openai_compat'])
    accept = commands.add_parser('accept')
    accept.add_argument('--draft', required=True)
    commands.add_parser('runs')
    init = commands.add_parser('init', help='create a project')
    init.add_argument('--name', required=True)
    brief = commands.add_parser('brief', help='append a brief version')
    brief.add_argument('--text', required=True)
    brief.add_argument('--constraints', default='')
    bible = commands.add_parser('bible').add_subparsers(dest='action', required=True)
    add = bible.add_parser('add')
    add.add_argument('--kind', choices=['world', 'character', 'style', 'taboo'], required=True)
    add.add_argument('--name', required=True)
    add.add_argument('--body', required=True)
    bible.add_parser('list')
    outline = commands.add_parser('outline').add_subparsers(dest='action', required=True)
    chapter = outline.add_parser('chapter')
    chapter.add_argument('--index', type=int, required=True)
    chapter.add_argument('--title', required=True)
    scene = outline.add_parser('scene')
    scene.add_argument('--chapter', required=True)
    scene.add_argument('--index', type=int, required=True)
    scene.add_argument('--card', type=Path, required=True, help='UTF-8 JSON object file')
    show = commands.add_parser('show')
    show.add_argument('kind', choices=['project', 'brief', 'bible', 'chapter', 'scene', 'draft', 'run', 'accepted', 'note'])
    show.add_argument('record_id', nargs='?')
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if not args.project:
        parser.error('--project is required')
    try:
        settings = None
        needs_model = args.command in ('write', 'review', 'flow') or (args.command == 'ab' and args.action == 'start')
        if needs_model or args.config.exists():
            settings = load_config(args.config)
        if needs_model:
            args.settings = settings
            args.provider_instance = make_provider(settings, args.provider)
        args.workspace = args.workspace or (settings.workspace if settings else ROOT / 'workspace')
        directory = project_directory(args.workspace, args.project)
        with Store(directory, create=args.command == 'init') as store:
            result = dispatch(store, args)
        def serialize(item: Any) -> Any:
            return item if isinstance(item, dict) else asdict(item)
        data = [serialize(item) for item in result] if isinstance(result, list) else serialize(result)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        if args.command == 'write' and result['run']['finish_reason'] != 'complete':
            return 1
        if args.command == 'review' and result.finish_reason != 'complete':
            return 1
        if args.command == 'ab' and args.action in ('start', 'show') and result['status'] != 'READY':
            return 1
        if args.command == 'flow' and result['status'] != 'DONE':
            return 1
        return 0
    except ConfigRequired as exc:
        print(f'CONFIG_REQUIRED: {exc}', file=sys.stderr)
        return 2
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
