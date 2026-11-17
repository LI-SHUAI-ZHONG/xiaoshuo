"""Exact owner context and an audit-only, hash-verified frozen read session."""
from contextlib import ExitStack, closing, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from nw.materials.catalog import _connect
from nw.materials.route_catalog import _FRAGMENTS, _UNITS

_ACTIVE: ContextVar = ContextVar("semantic_audit_read_session", default=None)


def _ro(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


@contextmanager
def _connections(workspace: Path) -> Iterator[tuple]:
    active = _ACTIVE.get()
    if active is not None and active[0] == workspace.resolve():
        yield active[1], active[2]
        return
    with ExitStack() as stack:
        catalog = stack.enter_context(closing(_connect(workspace, write=False)))
        catalog.execute("PRAGMA query_only=ON")
        catalog.execute("BEGIN")
        path = workspace / "materials/adjudication.db"
        review = stack.enter_context(closing(_ro(path))) if path.is_file() else None
        if review is not None:
            review.execute("BEGIN")
        yield catalog, review


def source_context(workspace: Path, source: dict) -> dict:
    """Locate a verified SourceDesk snapshot; never replace originals with guidance."""
    pin = source.get("source", {})
    ident = pin.get("id")
    if not isinstance(ident, str):
        raise ValueError("MATERIAL_SEMANTIC_CATALOG: missing owner identity")
    with _connections(workspace) as (catalog, saved):
        row = catalog.execute(_FRAGMENTS + " WHERE f.id=?", (ident,)).fetchone()
        if row is None:
            row = catalog.execute(_UNITS + " WHERE u.id=?", (ident,)).fetchone()
        if row is None:
            raise ValueError("MATERIAL_SEMANTIC_CATALOG: owner is outside the catalog")
        exact = dict(row)
        for name in ("sha256", "file_sha256", "path"):
            if pin.get(name) != exact[name]:
                raise ValueError("MATERIAL_SEMANTIC_CATALOG: owner locator/hash changed")
        exact["locator"] = exact["locator"] or ""
        review = {}
        if saved is not None:
            found = saved.execute("SELECT payload_json FROM contracts WHERE owner_id=?", (ident,)).fetchone()
            if found is None:
                raise ValueError("MATERIAL_SEMANTIC_CATALOG: owner contract is missing")
            review = json.loads(found[0])
            for ref in review.get("source_refs", []):
                if ref.get("id") == ident and ref.get("sha256") != exact["sha256"]:
                    raise ValueError("MATERIAL_SEMANTIC_CATALOG: adjudication owner hash changed")
    return {"source_ref": exact, "adjudication_contract": deepcopy(review),
            "source_context": {key: exact[key] for key in
                ("family", "layer", "kind", "origin", "source_id", "fragment_id", "fragment_key")}
            | {"adjudication_state": review.get("state", "not_adjudicated"),
               "qualification_authority": "unchanged_source_adjudication_not_compilation"}}


@contextmanager
def audit_source_access(workspace: Path) -> Iterator[dict]:
    """Cache whole immutable fragments only inside this audited batch."""
    import nw.materials.work_catalog as desk_module

    previous = desk_module.show_fragment
    stats = {"fragments_verified": 0, "unit_slices_verified": 0, "fragment_bytes_verified": 0}
    with _connections(workspace) as (catalog, saved):
        cache: dict[str, dict] = {}
        fragment_ids = {row[0] for row in catalog.execute("SELECT id FROM fragments")}

        def fragment(ident: str) -> dict:
            if ident not in cache:
                row = catalog.execute("SELECT id,byte_start,byte_end,sha256,payload,kind FROM fragments WHERE id=?",
                                      (ident,)).fetchone()
                if row is None:
                    raise ValueError("MATERIAL_SEMANTIC_CATALOG: parent fragment is missing")
                data = bytes(row["payload"])
                if sha256(data).hexdigest() != row["sha256"]:
                    raise ValueError("MATERIAL_SEMANTIC_CATALOG: parent fragment hash mismatch")
                if row["kind"] == "quarantined":
                    raise ValueError("MATERIAL_SEMANTIC_CATALOG: fragment is quarantined")
                cache[ident] = dict(row)
                stats["fragments_verified"] += 1
                stats["fragment_bytes_verified"] += len(data)
            return cache[ident]

        def cached_read(current: Path, ident: str) -> dict:
            if current.resolve() != workspace.resolve():
                return previous(current, ident)
            if ident in fragment_ids:
                row = fragment(ident)
                return {"sha256": row["sha256"], "text": bytes(row["payload"]).decode("utf-8")}
            unit = catalog.execute("SELECT fragment_id,byte_start,byte_end,sha256 FROM material_units WHERE id=?",
                                   (ident,)).fetchone()
            if unit is None:
                raise ValueError("MATERIAL_SEMANTIC_CATALOG: source unit is missing")
            parent = fragment(unit["fragment_id"])
            left = unit["byte_start"] - parent["byte_start"]
            right = unit["byte_end"] - parent["byte_start"]
            if not 0 <= left <= right <= len(parent["payload"]):
                raise ValueError("MATERIAL_SEMANTIC_CATALOG: unit is outside its parent")
            raw = bytes(parent["payload"])[left:right]
            if sha256(raw).hexdigest() != unit["sha256"]:
                raise ValueError("MATERIAL_SEMANTIC_CATALOG: source unit hash mismatch")
            stats["unit_slices_verified"] += 1
            return {"sha256": unit["sha256"], "text": raw.decode("utf-8")}

        token = _ACTIVE.set((workspace.resolve(), catalog, saved))
        desk_module.show_fragment = cached_read
        try:
            yield stats
        finally:
            desk_module.show_fragment = previous
            _ACTIVE.reset(token)

