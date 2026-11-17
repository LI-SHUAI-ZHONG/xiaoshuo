"""Expose one pinned complete material version to every operational catalog read."""
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from nw.task_models import content_sha256

POLICY='single-material-version-v1'
FAMILIES={'library','types','type_links','static','dynamic','anchors'}
_HASH=re.compile(r'[0-9a-f]{64}')


def require(ok: bool,reason: str) -> None:
    if not ok:raise ValueError('MATERIAL_SOURCE_SET: '+reason)


def _selection(db: sqlite3.Connection,workspace: Path) -> dict | None:
    path=workspace/'materials/active_source_set.json'
    registered=db.execute("SELECT 1 FROM main.sqlite_master WHERE type='table' AND name='source_set_selection'").fetchone()
    if not path.is_file():
        require(not registered,'selected version configuration is missing; multi-version fallback is disabled')
        return None
    try:data=json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError,UnicodeError,OSError) as exc:
        raise ValueError('MATERIAL_SOURCE_SET: cannot read the selected version configuration') from exc
    require(isinstance(data,dict) and data.get('policy')==POLICY and
        isinstance(data.get('version_name'),str) and bool(data['version_name'].strip()),'invalid version selection')
    require(data.get('sha256')==content_sha256({k:v for k,v in data.items() if k!='sha256'}),
        'selected version configuration changed')
    require(bool(registered),'selected version is not registered in this catalog')
    marker=db.execute('SELECT policy,sha256 FROM main.source_set_selection WHERE singleton=1').fetchone()
    require(marker is not None and tuple(marker)==(POLICY,data['sha256']),'selected version registration changed')
    entries=data.get('sources')
    require(isinstance(entries,list) and len(entries)==6 and all(isinstance(e,dict) for e in entries),
        'the selected version must contain the six material families')
    require(all(all(isinstance(e.get(k),str) for k in ('id','path','family','file_sha256')) for e in entries),
        'invalid selected source version fields')
    require({e.get('family') for e in entries}==FAMILIES and len({e.get('id') for e in entries})==6,
        'selected version has missing or repeated material families')
    for entry in entries:
        require(all(isinstance(entry.get(k),str) and _HASH.fullmatch(entry[k]) for k in ('id','file_sha256')),
            'invalid selected source version pin')
        row=db.execute('SELECT path,family,file_sha256,layer,status FROM main.sources WHERE id=?',(entry['id'],)).fetchone()
        require(row is not None and tuple(row)==(entry.get('path'),entry['family'],entry['file_sha256'],'baseline','INDEXED'),
            'selected source is missing or its exact version changed')
    return data


def apply_source_set(db: sqlite3.Connection,workspace: Path) -> None:
    selection=_selection(db,workspace)
    if selection is None:return
    # IDs are validated SHA256 strings. DDL creates no implicit DML transaction,
    # so existing callers can still BEGIN their frozen read transactions.
    ids=','.join("'"+e['id']+"'" for e in selection['sources'])
    db.execute(f'CREATE TEMP VIEW sources AS SELECT * FROM main.sources WHERE id IN ({ids})')
    db.execute('CREATE TEMP VIEW fragments AS SELECT f.* FROM main.fragments f JOIN temp.sources s ON s.id=f.source_id')
    tables={r[0] for r in db.execute("SELECT name FROM main.sqlite_master WHERE type='table'")}
    if 'material_units' in tables:
        db.execute('CREATE TEMP VIEW material_units AS SELECT u.* FROM main.material_units u JOIN temp.fragments f ON f.id=u.fragment_id')
    if 'unit_checkpoints' in tables:
        db.execute('CREATE TEMP VIEW unit_checkpoints AS SELECT u.* FROM main.unit_checkpoints u JOIN temp.sources s ON s.id=u.source_id')


def selection_status(workspace: Path) -> dict | None:
    path=workspace/'materials/catalog.db'
    if not path.is_file():return None
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        selection=_selection(db,workspace)
        if selection is None:return None
        count=db.execute('SELECT count(*) FROM sources').fetchone()[0]
    return {'policy':POLICY,'version_name':selection['version_name'],'sha256':selection['sha256'],
        'active_file_sources':6,'excluded_from_operation':count-6,'sources':selection['sources'],
        'archive_files_deleted':False,'item_semantics_verified_by_selection':False}
