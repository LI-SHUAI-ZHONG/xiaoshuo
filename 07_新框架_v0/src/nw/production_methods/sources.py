"""Read existing library revisions without migrating or mutating a live library."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from nw.production_methods.matching import TYPE_PRIORITY, type_match
from nw.studio import corpus_catalog
from nw.studio.corpus_store import CorpusMixin
from nw.studio.method_store import MethodMixin
from nw.studio.staging import StagingMixin
from nw.studio.method_catalog import CAST_OUTPUTS, PROGRESS_OUTPUTS, TASKS
from nw.task_models import canonical,content_sha256


def story_context(document: dict, instance: dict, citations: list[dict]) -> dict:
    """Resolve the IDs in the selected observation without copying the rest of the book."""
    characters={p['id']:p for p in document['characters']}
    people={person for row in instance['threads']+instance['events'] for person in row['characters']}
    units={u['id']:u for u in document['units']}
    locations={e['unit_id'] for e in instance['events']}
    for selected, records, parent in ((people,characters,'canonical_id'),(locations,units,'parent_id')):
        pending=list(selected)
        while pending:
            target=records.get(pending.pop(),{}).get(parent)
            if target and target not in selected:
                selected.add(target)
                pending.append(target)
    cited_ids={key for part in ('threads','events','links') for row in instance[part] for key in row['evidence_ids']}
    quotes={(e['start'],e['end'],e['quote']) for e in citations if e['book_id']==instance['book_id']}
    return {'participants':[{k:p[k] for k in ('id','name','canonical_id')} for p in characters.values() if p['id'] in people],
            'units':[{k:u[k] for k in ('id','level','title','parent_id')} for u in units.values() if u['id'] in locations],
            'evidence':[{k:e[k] for k in ('id','start','end')} for e in document['evidence']
                        if e['id'] in cited_ids and (e['start'],e['end'],e['quote']) in quotes]}


class MethodReader(MethodMixin,CorpusMixin,StagingMixin):
    def __init__(self,workspace: Path) -> None:
        self.workspace=workspace.resolve();self.root=self.workspace/'library';self.db_path=self.root/'library.db'

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        if not self.db_path.is_file():raise ValueError('METHOD_DESIGN_REQUIRED: 请先导入参考作品、完成结构拆解并批准方法')
        db=sqlite3.connect(self.db_path.as_uri()+'?mode=ro',uri=True,timeout=20);db.row_factory=sqlite3.Row
        try:yield db
        finally:db.close()

    def approved(self, *, current_only: bool = False) -> list[dict]:
        with self.connect() as conn:
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'production_methods' not in tables:return []
            if current_only:
                if not {'corpus_method_origins','corpus_structures','corpus_structure_versions'} <= tables:
                    return []
                heads=conn.execute("""SELECT m.* FROM production_methods m
                    JOIN corpus_method_origins o ON o.method_id=m.id AND o.method_version=m.approved_version
                    JOIN corpus_structures s ON s.book_id=o.book_id AND s.approved_version=o.structure_version
                    JOIN corpus_structure_versions v ON v.book_id=s.book_id AND v.version=s.approved_version
                    WHERE json_extract(v.body_json,'$.schema_version')=? ORDER BY m.id""",
                    (corpus_catalog.SCHEMA_VERSION,)).fetchall()
            else:
                heads=conn.execute('SELECT * FROM production_methods WHERE approved_version IS NOT NULL ORDER BY id').fetchall()
            books = {}
            return [self._method_row(dict(row),row['approved_version'],conn,books) for row in heads]

    def snapshot(self,row: dict, *, structure: dict | None = None) -> dict:
        origin=row['structure_origin']
        if not origin:raise ValueError('METHOD_DESIGN_REQUIRED: 方法尚无已批准的多层拆解依据')
        if structure is None:
            with self.connect() as conn:structure=self._corpus_row(origin['book_id'],origin['structure_version'],conn)
        body=structure['body'];basis=origin['basis']
        instance={'book_id':origin['book_id'],'version':structure['version'],'body_sha256':structure['body_sha256'],
            'source_sha256':structure['source_sha256'],'source_extent':body['source_extent'],'overview':body['overview'],
            **{section:[r for r in body[section] if r['id'] in basis[key]]
               for section,key in [('threads','thread_ids'),('events','event_ids'),('links','link_ids')]}}
        result={key:deepcopy(row[key]) for key in ('id','version','body_sha256','body','evidence_locations','structure_origin')}
        if origin.get('observation_domains'):
            instance['source_context']=story_context(body, instance, row['body']['evidence'])
        result['instance']=instance;result['snapshot_sha256']=content_sha256(result)
        return result

    def current_methods(self) -> list[dict]:
        return [row for row in self.approved(current_only=True) if row['current_for_production']]

    def world_source(self, row: dict, types: list[str]) -> tuple[dict, dict] | None:
        """Only a corresponding novel and an evidenced rule affecting a real event qualify."""
        origin = row['structure_origin']
        book = self._staging_row(origin['book_id'])
        tags = json.loads(book['confirmed_types_json'])
        source_match = type_match(types, tags)
        if not source_match or source_match['level'] == 'cross_type':
            return None
        with self.connect() as conn:
            structure = self._corpus_row(origin['book_id'], origin['structure_version'], conn)
        # v2 availability includes the library's rule-to-event citation and output checks.
        # Historical v1 methods remain readable, but their tags alone cannot supply new rules.
        if not row['available'] or structure['body'].get('schema_version', 1) < 2:
            return None
        return self.snapshot(row, structure=structure), {**source_match, 'source_type_ids': tags}

    def verify(self,pin: dict, *, require_current: bool = True, world_types: list[str] | None = None,
               source_type_match: dict | None = None) -> None:
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
        if world_types is None:
            actual = self.snapshot(row)
        else:
            source = self.world_source(row, world_types)
            if source is None or source[1] != source_type_match:
                raise ValueError('STALE_PROJECT_METHOD: 原作类型、世界规则结构或原文证据已改变')
            actual = source[0]
        if 'source_context' not in pin['instance'] and 'source_context' in actual['instance']:
            # Frozen gates created before source IDs were expanded have a different exact digest.
            del actual['instance']['source_context']
            actual.pop('snapshot_sha256')
            actual['snapshot_sha256']=content_sha256(actual)
        if canonical(actual)!=canonical(pin):raise ValueError('STALE_PROJECT_METHOD: 冻结的拆解实例或原文证据已改变')


def matching_methods(reader: MethodReader, types: list[str]) -> list[tuple[dict, dict]]:
    methods = []
    for row in reader.current_methods():
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


def enabled_outputs(body: dict, stage: str, package: dict) -> bool:
    from nw.materials import cast_demands, chapter_progress
    fields={o['field'] for o in body['outputs'] if o['stage']==stage}
    if fields & CAST_OUTPUTS.get(stage,set()) and package.get('cast_demand_policy')!=cast_demands.POLICY:
        return False
    if fields & PROGRESS_OUTPUTS.get(stage,set()):
        if package.get('chapter_progress_policy') not in chapter_progress.POLICIES:
            return False
        if 'continuations' in fields and not chapter_progress.chapter_openings(
                package.get('chapter_handoff',{}), package['chapter_progress_policy']):
            return False
    return True


def task_routes(reader: MethodReader, package: dict) -> dict:
    """Pin the actual output stage for a task when the library serves it later in the workflow."""
    from nw.materials.phase_routes import phase_order
    policy=package['production_method_policy']
    scope=package['scope']
    tasks=set(policy['tasks'])
    if policy.get('world_selection')=='ai':
        tasks.discard('world_rules')
    if not tasks or not reader.db_path.is_file():
        return {}
    available={}
    preferred=policy.get('preferred_methods',{})
    for row,_ in matching_methods(reader,policy['type_ids']):
        body=row['body']
        for stage in {o['stage'] for o in body['outputs']}:
            covered=stage_tasks(body,stage,scope) & tasks
            if covered and enabled_outputs(body,stage,package):
                for task in covered:
                    available.setdefault(task,{}).setdefault(stage,set()).add((row['id'],row['version']))
    order=phase_order(scope)
    routes={}
    for task, stages in available.items():
        preferred_stages={s for s,versions in stages.items() if any(preferred.get(k)==v for k,v in versions)}
        routes[task]=next(s for s in order if s in (preferred_stages or stages))
    return routes


def relevant(reader: MethodReader, policy: dict, stage: str, scope: str, types: list[str], *, package: dict | None = None) -> list[dict]:
    tasks = set(policy['tasks'])
    production_scope = 'chapter' if scope == 'replan' else scope
    if not policy.get('preferred_methods') and not any(stage in TASKS[task]['stages'] and production_scope in TASKS[task]['scopes'] for task in tasks):
        return []
    if not tasks:
        return []
    preferred = policy.get('preferred_methods', {})
    return [reader.snapshot(row) for row, _ in matching_methods(reader, types)
            if (applicable := stage_tasks(row['body'], stage, scope))
            and enabled_outputs(row['body'],stage,package or {})
            and (applicable & tasks or preferred.get(row['id']) == row['version'])]
