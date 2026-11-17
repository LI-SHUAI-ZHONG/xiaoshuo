"""Full original-clause fidelity audit and versioned discovery-only metadata."""
from collections import Counter
from contextlib import ExitStack, closing
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from nw.materials.catalog import _connect
from nw.materials import source_semantics
from nw.materials.source_semantics import compile_semantics
from nw.materials.semantic_fields import _BULLET, _EMPTY, _LABEL, _LABELS, _META, anchor_cells
from nw.materials.source_context import audit_source_access, source_context
from nw.materials.work_catalog import SourceDesk
from nw.task_models import canonical, content_sha256

POLICY = "semantic-source-catalog-v1"
_SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
CREATE TABLE semantic_sources (
 owner_id TEXT PRIMARY KEY, source_ref_json TEXT NOT NULL, source_text_sha256 TEXT NOT NULL,
 semantic_contract_sha256 TEXT NOT NULL, obligation_count INTEGER NOT NULL,
 execution_stages_json TEXT NOT NULL, semantic_disposition TEXT NOT NULL,
 source_state TEXT NOT NULL, field_dispositions_json TEXT NOT NULL, contract_json TEXT NOT NULL
);
"""


def _fingerprint(workspace: Path) -> dict:
    folder = Path(__file__).parent
    names = ("source_semantics.py", "semantic_fields.py", "source_context.py",
             "semantic_catalog.py", "work_catalog.py", "type_adjudication.py", "binding_reviews.py",
             "catalog.py", "source_set.py", "work_knowledge.py")
    code = sha256(b"".join(name.encode() + (folder / name).read_bytes() for name in names)).hexdigest()
    with closing(_connect(workspace, write=False)) as catalog:
        sources = [tuple(row) for row in catalog.execute(
            "SELECT id,path,file_sha256,family,layer,status FROM sources ORDER BY id")]
        counts = [catalog.execute("SELECT count(*) FROM " + table).fetchone()[0]
                  for table in ("fragments", "material_units")]
        path = workspace / "materials/adjudication.db"
        adjudication = {}
        if path.is_file():
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as saved:
                adjudication = {key: json.loads(value) for key, value in saved.execute("SELECT * FROM metadata")}
                owners = [row[0] for row in saved.execute("SELECT owner_id FROM contracts ORDER BY owner_id")]
        else:
            owners = [row[0] for row in catalog.execute("""SELECT id FROM fragments
                WHERE kind NOT IN ('library_upgrade','quarantined') UNION SELECT id FROM material_units
                WHERE kind IN ('record','embedded_entry','embedded_block') AND origin='source' ORDER BY id""")]
    files = {}
    from nw.materials.binding_reviews import BUNDLED,ROOT,WORKFLOWS
    for path in (BUNDLED,workspace/'materials/workflow_binding_reviews.json'):
        if path.is_file():files[str(path)]=sha256(path.read_bytes()).hexdigest()
    for name in sorted(WORKFLOWS):
        path=ROOT/name
        if path.is_file():files[name]=sha256(path.read_bytes()).hexdigest()
    for name in ("catalog.db", "catalog.db-wal", "adjudication.db", "adjudication.db-wal"):
        path = workspace / "materials" / name
        if path.is_file():
            stat = path.stat()
            files[name] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    return {"policy": POLICY, "compiler_policy": source_semantics.POLICY, "code_sha256": code,
            "source_set_sha256": content_sha256(sources), "owner_set_sha256": content_sha256(owners),
            "owner_count": len(owners), "indexed_counts": counts, "adjudication": adjudication,
            "input_files": files}


def _owner_scope_matches(fingerprint: dict, current: set[str], isolated: set[str] | frozenset[str]) -> bool:
    # Writing and work knowledge are disjoint, but together must cover the full catalog.
    owners = sorted(current | isolated)
    return (not current & isolated and len(owners) == fingerprint['owner_count']
            and content_sha256(owners) == fingerprint['owner_set_sha256'])


def _relative(locator: str, owner: str) -> str:
    if owner and not locator.startswith(owner.rstrip("/") + "/"):
        raise ValueError("clause locator is outside owner")
    return locator[len(owner.rstrip("/")):] if owner else locator


def _value_at(value: object, pointer: str) -> object:
    for key in pointer.lstrip("/").split("/") if pointer else []:
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def _fields(text: str, original: object, clauses: set[str], owner: str) -> list[dict]:
    ledger = []
    if isinstance(original, (dict, list)):
        def walk(value: object, path: str = "", metadata: bool = False) -> None:
            if isinstance(value, dict) and value:
                for key, child in value.items():
                    walk(child, path + "/" + key.replace("~", "~0").replace("/", "~1"), metadata or key in _META)
                return
            if isinstance(value, list) and value:
                for index, child in enumerate(value):
                    walk(child, path + "/" + str(index), metadata)
                return
            status = ("original_metadata" if metadata else "source_clause" if path in clauses
                      else "empty_container" if isinstance(value, (dict, list))
                      else "empty_value" if value is None or isinstance(value, str) and value.strip() in _EMPTY
                      else "unaccounted_field")
            ledger.append({"locator": path, "disposition": status})
        walk(original)
        return ledger
    cells = anchor_cells(text)
    if cells:
        return [{"locator": f"cell/{i}", "disposition": "source_clause" if f"cell/{i}" in clauses
                 else "original_metadata" if i in (0, 4) else "empty_value"} for i in range(5)]
    pos = 0
    navigation = False
    for line in text.splitlines(keepends=True):
        body = line.strip()
        match = _LABEL.match(line.rstrip("\r\n"))
        if match:
            label = match[1] or match[2]
            navigation = label in _LABELS and _LABELS[label] is None
        spans = [path for path in clauses if path.startswith("text/")]
        covered = any((lambda pair: int(pair[0]) < pos + len(line) and pos < int(pair[1]))(
            path[5:].split(":")) for path in spans)
        formatting = re.fullmatch(r"[^。！？:：\r\n]{0,16}规则[:：]", body.replace("\\", "").replace("*", ""))
        empty=_BULLET.sub('',(match[3] if match else line.rstrip('\r\n'))).strip() in _EMPTY
        status = ("source_clause" if covered else "whitespace" if not body else "heading" if
                  re.match(r"^#{1,6}\s", body) else "navigation_label" if navigation else
                  "section_label" if match and not match[3].strip() else "formatting" if formatting
                  else "empty_value" if empty else "unaccounted_text")
        ledger.append({"locator": f"text/{pos}:{pos+len(line)}", "disposition": status})
        pos += len(line)
    return ledger


def _audit_record(source: dict, context: dict, contract: dict) -> dict:
    text = source["original_text"]
    digest = content_sha256(text)
    pin = context["source_ref"]
    owner = pin.get("locator", "").rstrip("/")
    errors = []
    if contract.get("sha256") != content_sha256({k:v for k,v in contract.items() if k != "sha256"}):
        errors.append("compiled contract hash mismatch")
    if contract.get("source_id") != pin["id"] or contract.get("source_text_sha256") != digest:
        errors.append("compiled owner/text identity mismatch")
    for field in ("id", "sha256", "file_sha256", "byte_start", "byte_end", "line_start", "line_end", "locator"):
        if contract.get("source_ref", {}).get(field) != pin[field]:
            errors.append("compiled source locator mismatch: " + field)
    try:
        original = json.loads(text) if text.lstrip().startswith(("{", "[")) else text
    except ValueError:
        original = text
    paths = set()
    seen = set()
    for item in contract["obligations"]:
        ref = item["source_ref"]
        left, right = ref.get("text_start"), ref.get("text_end")
        valid = type(left) is int and type(right) is int and 0 <= left < right <= len(text)
        if not valid:
            errors.append("invalid clause span")
            continue
        raw = text[left:right]
        if (ref.get("id") != pin["id"] or ref.get("source_text_sha256") != digest
                or ref.get("text_basis") != "original_text"
                or ref.get("clause_sha256") != sha256(raw.encode("utf-8")).hexdigest()):
            errors.append("clause identity/hash mismatch")
        try:
            path = _relative(item["locator"], owner)
            if not isinstance(original,(dict,list)):path=path.lstrip('/')
            paths.add(path)
            actual = json.loads(raw) if isinstance(original, (dict, list)) else raw
            if actual != item["value"] or isinstance(original, (dict, list)) and _value_at(original, path) != item["value"]:
                errors.append("clause original value mismatch")
        except (ValueError, KeyError, TypeError, IndexError):
            errors.append("clause JSON pointer/value is invalid")
        if item["id"] in seen or item["check_mode"] not in {"deterministic", "semantic_review"}:
            errors.append("duplicate clause or unknown check mode")
        seen.add(item["id"])
    fields = _fields(text, original, paths, owner)
    errors.extend(x["disposition"] + ": " + x["locator"] for x in fields
                  if x["disposition"].startswith("unaccounted"))
    return {"source_id": pin["id"], "source_ref": pin, "source_state": source["source_state"],
            "source_text_sha256": digest, "contract": contract, "field_dispositions": fields,
            "fidelity_errors": errors, "semantic_effects_verified": 0}


def _issue_counts(issues: dict) -> Counter:
    counts: Counter = Counter()
    for section, entries in issues.items():
        for item in entries if isinstance(entries, list) else [entries] if entries else []:
            counts[section + ":" + (str(item.get("kind", "unspecified")) if isinstance(item, dict) else "reported")] += 1
    return counts


def audit_semantic_sources(workspace: Path, *, write_index: bool = False,
                           details_path: Path | None = None) -> dict:
    """Compile and account for every current owner; fidelity is not semantic success."""
    fingerprint = _fingerprint(workspace)
    totals: Counter = Counter()
    stages: Counter = Counter()
    dispositions: Counter = Counter()
    states: Counter = Counter()
    fields: Counter = Counter()
    issues: Counter = Counter()
    with ExitStack() as stack:
        details = stack.enter_context(Path(details_path).open("x", encoding="utf-8")) if details_path else None
        if details:
            details.write('{"rows":[')
        index_path = None
        saved = None
        if write_index:
            index_path = workspace / "materials" / f"semantic-index-{content_sha256(fingerprint)[:16]}-{uuid4().hex}.db"
            saved = stack.enter_context(closing(sqlite3.connect(index_path)))
            saved.executescript(_SCHEMA)
        with audit_source_access(workspace) as read_stats:
            desk = SourceDesk(workspace)
            isolated = desk.work_knowledge_only_ids
            if len(desk.by_id) != len(desk.rows) or not _owner_scope_matches(fingerprint, set(desk.by_id), isolated):
                raise ValueError("MATERIAL_SEMANTIC_CATALOG: owner set changed")
            for position in desk.rows:
                source = desk.read(position["id"])
                context = source_context(workspace, source)
                contract = compile_semantics(source, context)
                row = _audit_record(source, context, contract)
                if details:
                    details.write(("," if totals["source_contracts"] else "") + canonical(row))
                totals["source_contracts"] += 1
                totals["source_clause_count"] += len(contract["obligations"])
                totals["deterministic_clause_count"] += sum(x["check_mode"] == "deterministic" for x in contract["obligations"])
                totals["native_or_semantic_review_count"] += sum(x["check_mode"] == "semantic_review" for x in contract["obligations"])
                totals["fidelity_failures"] += len(row["fidelity_errors"])
                stages.update(contract["stages"])
                dispositions[contract["disposition"]] += 1
                states[source["source_state"]] += 1
                fields.update(x["disposition"] for x in row["field_dispositions"])
                issues.update(_issue_counts(contract["source_issues"]))
                if saved is not None:
                    saved.execute("INSERT INTO semantic_sources VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (position["id"], canonical(context["source_ref"]), contract["source_text_sha256"],
                         contract["sha256"], len(contract["obligations"]), canonical(contract["stages"]),
                         contract["disposition"], source["source_state"], canonical(row["field_dispositions"]),
                         canonical(contract)))
        if _fingerprint(workspace) != fingerprint:
            raise ValueError("MATERIAL_SEMANTIC_CATALOG: inputs changed during audit")
        summary = {key: totals[key] for key in ("source_contracts", "source_clause_count",
            "deterministic_clause_count", "native_or_semantic_review_count", "fidelity_failures")}
        summary.update(policy=POLICY, status="SOURCE_FIDELITY_FAILED" if totals["fidelity_failures"] else
            "COMPILED_SOURCE_FIDELITY_AUDITED", semantic_effects_verified=0, execution_qualification_changed=False,
            work_knowledge_only_count=len(isolated),
            source_issue_counts=dict(issues), source_dispositions=dict(dispositions), source_states=dict(states),
            explicit_stage_assignments=dict(stages), field_disposition_counts=dict(fields),
            read_verification=dict(read_stats), index_path=str(index_path) if index_path else None,
            details_path=str(details_path) if details_path else None, fingerprint=fingerprint,
            authority="source_fidelity_and_discovery_only_not_applicability_prose_or_state_verification")
        if details:
            details.write('],"summary":' + canonical(summary) + "}\n")
        if saved is not None:
            saved.executemany("INSERT INTO metadata VALUES (?,?)", [(key, canonical(value)) for key, value in
                {"fingerprint": fingerprint, "summary": summary, "work_knowledge_only_ids": sorted(isolated),
                 "complete": not totals["fidelity_failures"]}.items()])
            saved.commit()
            if saved.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("MATERIAL_SEMANTIC_CATALOG: new index integrity failed")
    return summary


def load_semantic_metadata(workspace: Path) -> dict:
    """Load matching lightweight discovery data; missing/stale/incomplete means {}."""
    paths = sorted((workspace / "materials").glob("semantic-index-*.db"),
                   key=lambda path: path.stat().st_mtime_ns, reverse=True)
    if not paths:
        return {}
    try:
        expected = _fingerprint(workspace)
    except (OSError, sqlite3.Error, ValueError):
        return {}
    for path in paths:
        try:
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
                meta = {key: json.loads(value) for key, value in db.execute("SELECT * FROM metadata")}
                if meta.get("complete") is not True or meta.get("fingerprint") != expected:
                    continue
                result = {}
                for ident, text_sha, digest, count, raw_stages, disposition, state in db.execute("""
                    SELECT owner_id,source_text_sha256,semantic_contract_sha256,obligation_count,
                           execution_stages_json,semantic_disposition,source_state FROM semantic_sources"""):
                    stages = json.loads(raw_stages)
                    if not isinstance(stages, list) or any(not isinstance(stage, str) for stage in stages):
                        raise ValueError("invalid cached execution stages")
                    result[ident] = {"execution_stages": stages, "semantic_disposition": disposition,
                        "semantic_contract_sha256": digest, "semantic_source_text_sha256": text_sha,
                        "semantic_obligation_count": count, "source_state": state,
                        "semantic_metadata_authority": "discovery_only_not_execution_qualification"}
                isolated = set(meta['work_knowledge_only_ids'])
                if (len(result) == meta['summary']['source_contracts']
                        and len(isolated) == meta['summary']['work_knowledge_only_count']
                        and _owner_scope_matches(expected, set(result), isolated)):
                    return result
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            continue
    return {}

