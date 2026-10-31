import json
import os
from pathlib import Path
import subprocess
import sys


def invoke(directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, '-m', 'nw', '--workspace', str(directory), *args],
                          capture_output=True, text=True, encoding='utf-8',
                          env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})


def test_cli_persists_across_processes(tmp_path: Path) -> None:
    def call(*args: str) -> object:
        result = invoke(tmp_path, '--project', 'book', *args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    assert call('init', '--name', '中文项目')['name'] == '中文项目'
    assert call('brief', '--text', '作者需求', '--constraints', '限制')['version'] == 1
    call('bible', 'add', '--kind', 'world', '--name', '世界', '--body', '世界设定')
    assert call('bible', 'list')[0]['body'] == '世界设定'
    chapter = call('outline', 'chapter', '--index', '1', '--title', '第一章')
    card = tmp_path / 'card.json'
    card.write_text('{"目的":"调查","视角人物":"沈砚"}', encoding='utf-8')
    scene = call('outline', 'scene', '--chapter', chapter['id'], '--index', '1', '--card', str(card))
    assert json.loads(call('show', 'scene', scene['id'])['card_json'])['目的'] == '调查'
    assert call('show', 'brief')[0]['text'] == '作者需求'
    assert call('show', 'project')['name'] == '中文项目'
    duplicate = invoke(tmp_path, '--project', 'book', 'init', '--name', '覆盖')
    assert duplicate.returncode != 0
    assert call('show', 'project')['name'] == '中文项目'
    invalid = invoke(tmp_path, '--project', 'book', 'outline', 'chapter', '--index', '0', '--title', '错误')
    assert invalid.returncode != 0
    assert len(call('show', 'chapter')) == 1


def test_cli_missing_project_and_path_escape(tmp_path: Path) -> None:
    for project in ('missing', '../outside', 'CON', 'book.'):
        result = invoke(tmp_path, '--project', project, 'show', 'project')
        assert result.returncode != 0
    assert list(tmp_path.iterdir()) == []
