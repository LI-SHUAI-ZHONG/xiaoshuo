"""Read existing library revisions without migrating or mutating a live library."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from typing import Iterator

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
            return [self._method_row(dict(row),row['approved_version'],conn) for row in heads]

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

    def verify(self,pin: dict) -> None:
        saved={k:v for k,v in pin.items() if k!='snapshot_sha256'}
        if content_sha256(saved)!=pin.get('snapshot_sha256'):raise ValueError('STALE_PROJECT_METHOD: 方法快照已被改写')
        row=self.get_method(pin['id'],pin['version'])
        if not row['available'] or row['approved_version']!=pin['version'] or row['body_sha256']!=pin['body_sha256']:
            raise ValueError('STALE_PROJECT_METHOD: 方法、原作或批准版本已改变，请补设计并重建任务')
        if canonical(self.snapshot(row))!=canonical(pin):raise ValueError('STALE_PROJECT_METHOD: 冻结的拆解实例或原文证据已改变')


def relevant(reader: MethodReader,policy: dict,stage: str,scope: str,types: list[str]) -> list[dict]:
    scope='chapter' if scope=='replan' else scope
    from nw.studio.catalog import genres
    parents={child['id']:parent['id'] for parent in genres() for child in parent['children']}
    allowed=set(types)|{parents[t] for t in types if t in parents}
    result=[]
    for row in reader.approved():
        body=row['body']
        if not row['available'] or not row['structure_origin'] or scope not in body['scopes']:continue
        if not set(body['tasks'])&set(policy['tasks']):continue
        if body['type_tags'] and not set(body['type_tags'])&allowed:continue
        if not any(o['stage']==stage for o in body['outputs']):continue
        if not any(stage in TASKS[t]['stages'] for t in set(body['tasks'])&set(policy['tasks'])):continue
        result.append(reader.snapshot(row))
    return result
