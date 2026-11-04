"""Version-specific dependency edges and changes to legacy inputs."""
from dataclasses import asdict
import json
from typing import Any

from nw.store import Store, now
from nw.task_models import Ref, content_sha256


def _key(ref: Ref) -> tuple[str, str, int, str]:
    return ref.kind, ref.id, ref.version, ref.sha256


def add_dependency(store: Store, consumer: Ref, producer: Ref) -> None:
    store.connection.execute(
        'INSERT INTO artifact_dependencies VALUES (?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
        (*_key(consumer), *_key(producer)))


def find_impacts(store: Store, changed_refs: list[Ref]) -> list[Ref]:
    seen = set(changed_refs)
    queue = list(changed_refs)
    result = []
    for ref in queue:
        rows = store.connection.execute(
            '''SELECT consumer_kind,consumer_id,consumer_version,consumer_sha256 FROM artifact_dependencies
               WHERE producer_kind=? AND producer_id=? AND producer_version=? AND producer_sha256=?
               ORDER BY consumer_kind,consumer_id,consumer_version''', _key(ref))
        for row in rows:
            consumer = Ref(*row)
            if consumer not in seen:
                seen.add(consumer)
                queue.append(consumer)
                result.append(consumer)
    return result


def legacy_ref(kind: str, ident: str, record: Any, *, version: int | None = None) -> Ref:
    return Ref(kind, ident, version if version is not None else record.version, content_sha256(asdict(record)))


def outline_ref(store: Store) -> Ref:
    rows = [asdict(row) for kind in ('chapter', 'scene') for row in store.list(kind)]
    return Ref('outline', store.project().id, len(rows) + 1, content_sha256(rows))


def verify_legacy_ref(store: Store, ref: Ref) -> Ref:
    if ref.kind == 'brief':
        project = store.project()
        matches = any(legacy_ref('brief', project.id, row) == ref for row in store.briefs())
    elif ref.kind == 'bible':
        matches = any(legacy_ref('bible', json.dumps([row.kind, row.name], ensure_ascii=False), row) == ref
                      for row in store.bible())
    elif ref.kind == 'outline':
        matches = outline_ref(store) == ref or store.connection.execute(
            'SELECT 1 FROM story_invalidations WHERE producer_kind=? AND producer_id=? '
            'AND producer_version=? AND producer_sha256=?', _key(ref)).fetchone() is not None
    else:
        matches = False
    if not matches:
        raise ValueError(f'Frozen {ref.kind} reference does not match a recorded version and hash')
    return ref


def invalidate_input(store: Store, ref: Ref) -> None:
    store.connection.execute('INSERT INTO story_invalidations VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING',
                             (*_key(ref), now()))


def check_inputs_current(store: Store, refs: list[Ref]) -> None:
    for ref in refs:
        invalid = store.connection.execute(
            '''SELECT 1 FROM story_invalidations WHERE producer_kind=? AND producer_id=?
               AND producer_version=? AND producer_sha256=?''', _key(ref)).fetchone()
        if invalid:
            raise ValueError(f'STALE_INPUT: {ref.kind} {ref.id} version {ref.version}')
