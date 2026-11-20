"""Read existing library revisions without migrating or mutating a live library."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from nw.production_methods.matching import TYPE_PRIORITY, type_match
from nw.studio.corpus_store import CorpusMixin
from nw.studio.method_store import MethodMixin
from nw.studio.staging import StagingMixin
from nw.studio.method_catalog import TASKS
from nw.task_models import canonical,content_sha256


class MethodReader(MethodMixin,CorpusMixin,StagingMixin):
    def __init__(self,workspace: Path) -> None:
        self.workspace=workspace.resolve();self.root=self.workspace/'library';self.db_path=self.root/'library.db'

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        if not self.db_path.is_file():raise ValueError('METHOD_DESIGN_REQUIRED: 请先导入参考作品、完成结构拆解并批准方法')
        db=sqlite3.connect(self.db_path.as_uri()+'?mode=ro',uri=True,timeout=20);db.row_factory=sqlite3.Row
        try:yield db
        finally:db.close()

    def approved(self) -> list[dict]:
        with self.connect() as conn:
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'production_methods' not in tables:return []
            heads=conn.execute('SELECT * FROM production_methods WHERE approved_version IS NOT NULL ORDER BY id').fetchall()
            books = {}
            return [self._method_row(dict(row),row['approved_version'],conn,books) for row in heads]

    def snapshot(self,row: dict) -> dict:
        origin=row['structure_origin']
        if not origin:raise ValueError('METHOD_DESIGN_REQUIRED: 方法尚无已批准的多层拆解依据')
        with self.connect() as conn:structure=self._corpus_row(origin['book_id'],origin['structure_version'],conn)
        body=structure['body'];basis=origin['basis']
        instance={'book_id':origin['book_id'],'version':structure['version'],'body_sha256':structure['body_sha256'],
            'source_sha256':structure['source_sha256'],'source_extent':body['source_extent'],'overview':body['overview'],
            **{section:[r for r in body[section] if r['id'] in basis[key]]
               for section,key in [('threads','thread_ids'),('events','event_ids'),('links','link_ids')]}}
        result={key:deepcopy(row[key]) for key in ('id','version','body_sha256','body','evidence_locations','structure_origin')}
        result['instance']=instance;result['snapshot_sha256']=content_sha256(result)
        return result

    def verify(self,pin: dict, *, require_current: bool = True) -> None:
        saved={k:v for k,v in pin.items() if k!='snapshot_sha256'}
        if content_sha256(saved)!=pin.get('snapshot_sha256'):raise ValueError('STALE_PROJECT_METHOD: 方法快照已被改写')
        try:
            row=self.get_method(pin['id'],pin['version'])
        except FileNotFoundError as exc:
            raise ValueError('STALE_PROJECT_METHOD: 已选方法版本不存在，请刷新候选') from exc
        if require_current and row['approved_version']!=pin['version']:
            raise ValueError('STALE_PROJECT_METHOD: 方法已有不同的批准版本，请刷新候选后重新确认')
        if not row['available'] or row['body_sha256']!=pin['body_sha256']:
            raise ValueError('STALE_PROJECT_METHOD: 已选方法或原作证据失效，请核对资料后重新确认')
        if canonical(self.snapshot(row))!=canonical(pin):raise ValueError('STALE_PROJECT_METHOD: 冻结的拆解实例或原文证据已改变')


def matching_methods(reader: MethodReader, types: list[str]) -> list[tuple[dict, dict]]:
    methods = []
    for row in reader.approved():
        if row['available'] and row['structure_origin']:
            match = type_match(types, row['body']['type_tags'])
            if match:
                methods.append((row, match))
    methods.sort(key=lambda item: item[0]['review']['created_at'], reverse=True)
    methods.sort(key=lambda item: TYPE_PRIORITY[item[1]['level']])
    return methods


def stage_tasks(body: dict, stage: str, scope: str) -> set[str]:
    scope = 'chapter' if scope == 'replan' else scope
    if scope not in body['scopes'] or not any(output['stage'] == stage for output in body['outputs']):
        return set()
    return {task for task in body['tasks'] if scope in TASKS[task]['scopes'] and stage in TASKS[task]['stages']}


def relevant(reader: MethodReader, policy: dict, stage: str, scope: str, types: list[str]) -> list[dict]:
    tasks = set(policy['tasks'])
    if not tasks:
        return []
    preferred = policy.get('preferred_methods', {})
    return [reader.snapshot(row) for row, _ in matching_methods(reader, types)
            if (applicable := stage_tasks(row['body'], stage, scope))
            and (applicable & tasks or preferred.get(row['id']) == row['version'])]
