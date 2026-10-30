"""Workspace/project export manifest and non-destructive import validation CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from accos import __version__
from accos.kernel.settings import load_settings

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "transfer-manifest.json"
RECORDS_NAME = "records.json"
_SENSITIVE_PARTS = ("credential", "password", "secret")
_MIN_SAFE_PATH_PARTS = 3
_TABLE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_TABLE_METADATA_FIELD_COUNT = 2


def _database_url() -> str:
    configured = load_settings(env_file=ROOT / ".env").required.database_url
    parsed = urlsplit(configured.replace("postgresql+psycopg", "postgresql"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_new_directory(path: Path) -> Path:
    target = path.resolve()
    if (
        target in {Path(target.anchor), Path.home().resolve(), ROOT.resolve()}
        or len(target.parts) < _MIN_SAFE_PATH_PARTS
    ):
        raise ValueError("export target must be an explicit, narrow directory")
    if target.exists() and any(target.iterdir()):
        raise ValueError("export target must not already contain files")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _safe_payload_file(directory: Path, filename: object) -> Path:
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise ValueError("transfer records file must be a simple filename")
    path = (directory / filename).resolve()
    if path.parent != directory.resolve():
        raise ValueError("transfer records file escapes the export directory")
    return path


def _schema_revision(connection: psycopg.Connection[Any]) -> str:
    row = connection.execute(
        "SELECT revision FROM accos.schema_metadata "
        "WHERE component = 'accos-core' AND archived_at IS NULL"
    ).fetchone()
    if row is None:
        raise RuntimeError("schema metadata is missing")
    return str(row["revision"] if isinstance(row, dict) else row[0])


def _tables(connection: psycopg.Connection[Any]) -> list[tuple[str, set[str]]]:
    rows = connection.execute(
        "SELECT table_name, array_agg(column_name::text ORDER BY ordinal_position) AS columns "
        "FROM information_schema.columns WHERE table_schema = 'accos' "
        "GROUP BY table_name ORDER BY table_name"
    ).fetchall()
    tables: list[tuple[str, set[str]]] = []
    for row in rows:
        if isinstance(row, dict):
            name = row.get("table_name")
            columns = row.get("columns")
        elif isinstance(row, (tuple, list)) and len(row) == _TABLE_METADATA_FIELD_COUNT:
            name, columns = row
        else:
            raise RuntimeError("table metadata query returned invalid data")
        if not isinstance(name, str) or not isinstance(columns, list):
            raise RuntimeError("table metadata query returned invalid data")
        tables.append((name, {str(column) for column in columns}))
    return tables


def _json_value(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _safe_row(row: dict[str, object]) -> dict[str, object]:
    return {
        key: "<redacted>" if _sensitive_column(key) else _json_value(value)
        for key, value in row.items()
    }


def _sensitive_column(name: str) -> bool:
    normalized = name.lower()
    return (
        any(part in normalized for part in _SENSITIVE_PARTS)
        or normalized in {"token", "api_key", "access_key"}
        or normalized.endswith(("_token", "_api_key", "_access_key"))
    )


def _read_scoped_table(
    connection: psycopg.Connection[Any],
    table: str,
    columns: set[str],
    workspace_id: UUID,
    project_id: UUID | None,
) -> list[dict[str, object]]:
    if "workspace_id" not in columns:
        return []
    if project_id is None:
        query = sql.SQL("SELECT * FROM accos.{} WHERE workspace_id = %s ORDER BY 1").format(
            sql.Identifier(table)
        )
        rows = connection.execute(query, (workspace_id,)).fetchall()
    elif table == "projects":
        rows = connection.execute(
            "SELECT * FROM accos.projects WHERE workspace_id = %s AND id = %s ORDER BY id",
            (workspace_id, project_id),
        ).fetchall()
    elif "project_id" in columns:
        query = sql.SQL(
            "SELECT * FROM accos.{} WHERE workspace_id = %s AND project_id = %s ORDER BY 1"
        ).format(sql.Identifier(table))
        rows = connection.execute(query, (workspace_id, project_id)).fetchall()
    elif table == "audit_events":
        rows = connection.execute(
            "SELECT * FROM accos.audit_events WHERE workspace_id = %s "
            "AND (resource_id = %s OR payload ->> 'project_id' = %s) ORDER BY sequence",
            (workspace_id, str(project_id), str(project_id)),
        ).fetchall()
    else:
        rows = []
    return [_safe_row(dict(row)) for row in rows]


def export_scope(target: Path, workspace_id: UUID, project_id: UUID | None) -> dict[str, object]:
    destination = _safe_new_directory(target)
    with psycopg.connect(_database_url(), row_factory=dict_row) as connection:
        if project_id is not None:
            project = connection.execute(
                "SELECT 1 FROM accos.projects WHERE workspace_id = %s AND id = %s",
                (workspace_id, project_id),
            ).fetchone()
            if project is None:
                raise ValueError("project does not exist in the selected workspace")
        records = {
            table: rows
            for table, columns in _tables(connection)
            if (rows := _read_scoped_table(connection, table, columns, workspace_id, project_id))
        }
        revision = _schema_revision(connection)
    serialized_records = (
        json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    (destination / RECORDS_NAME).write_bytes(serialized_records)
    asset_references = [
        {
            "asset_id": row["asset_id"],
            "version_number": row["version_number"],
            "object_key": row["object_key"],
            "content_hash": row["content_hash"],
            "size_bytes": row["size_bytes"],
        }
        for row in records.get("asset_versions", [])
    ]
    manifest: dict[str, object] = {
        "format": "accos-scope-export",
        "format_version": 1,
        "created_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "application_version": __version__,
        "schema_revision": revision,
        "scope": {
            "workspace_id": str(workspace_id),
            "project_id": None if project_id is None else str(project_id),
        },
        "records": {
            "file": RECORDS_NAME,
            "sha256": _sha256(serialized_records),
            "counts": {table: len(rows) for table, rows in records.items()},
        },
        "asset_references": asset_references,
        "audit_included": "audit_events" in records,
        "import_policy": "validate_compatibility_and_conflicts_before_write_no_overwrite",
    }
    (destination / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def validate_import(source: Path) -> dict[str, object]:
    directory = source.resolve()
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError("transfer manifest is missing")
    parsed_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(parsed_manifest, dict):
        raise ValueError("transfer manifest must be a JSON object")
    manifest = _validated_manifest(cast("dict[str, Any]", parsed_manifest))
    records_path = _safe_payload_file(directory, manifest["records"]["file"])
    payload = records_path.read_bytes()
    if _sha256(payload) != manifest["records"]["sha256"]:
        raise ValueError("transfer record checksum failed")
    parsed_records = json.loads(payload)
    records = _validated_records(parsed_records, manifest["records"]["counts"])
    conflicts: dict[str, int] = {}
    with psycopg.connect(_database_url()) as connection:
        current_revision = _schema_revision(connection)
        schema_compatible = current_revision == manifest["schema_revision"]
        application_compatible = manifest["application_version"] == __version__
        existing_tables = {table for table, _columns in _tables(connection)}
        for table, rows in records.items():
            identifiers = [row["id"] for row in rows if row.get("id") not in {None, "<redacted>"}]
            if table not in existing_tables or not identifiers:
                continue
            query = sql.SQL("SELECT count(*) FROM accos.{} WHERE id = ANY(%s)").format(
                sql.Identifier(table)
            )
            row = connection.execute(query, (identifiers,)).fetchone()
            if row is None:
                raise RuntimeError("conflict query returned no result")
            count = int(row[0])
            if count:
                conflicts[table] = count
    return {
        "compatible": schema_compatible and application_compatible and not conflicts,
        "schema_compatible": schema_compatible,
        "application_compatible": application_compatible,
        "source_schema_revision": manifest["schema_revision"],
        "target_schema_revision": current_revision,
        "conflicts": conflicts,
        "write_performed": False,
        "policy": "conflicts_never_overwrite_existing_records",
    }


def _validated_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("format") != "accos-scope-export" or manifest.get("format_version") != 1:
        raise ValueError("transfer manifest format is unsupported")
    if not isinstance(manifest.get("application_version"), str) or not isinstance(
        manifest.get("schema_revision"), str
    ):
        raise ValueError("transfer manifest version metadata is invalid")
    scope = manifest.get("scope")
    records = manifest.get("records")
    assets = manifest.get("asset_references")
    if not isinstance(scope, dict) or not isinstance(records, dict) or not isinstance(assets, list):
        raise ValueError("transfer manifest structure is invalid")
    try:
        UUID(str(scope["workspace_id"]))
        project_id = scope.get("project_id")
        if project_id is not None:
            UUID(str(project_id))
    except (KeyError, ValueError) as error:
        raise ValueError("transfer manifest scope is invalid") from error
    if (
        records.get("file") != RECORDS_NAME
        or not isinstance(records.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", records["sha256"]) is None
        or not isinstance(records.get("counts"), dict)
    ):
        raise ValueError("transfer manifest record metadata is invalid")
    if any(
        not isinstance(table, str)
        or _TABLE_NAME.fullmatch(table) is None
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        for table, count in records["counts"].items()
    ):
        raise ValueError("transfer manifest record counts are invalid")
    for asset in assets:
        if (
            not isinstance(asset, dict)
            or not isinstance(asset.get("asset_id"), str)
            or not isinstance(asset.get("version_number"), int)
            or isinstance(asset.get("version_number"), bool)
            or asset["version_number"] < 1
            or not isinstance(asset.get("object_key"), str)
            or not isinstance(asset.get("content_hash"), str)
            or re.fullmatch(r"[0-9a-f]{64}", asset["content_hash"]) is None
            or not isinstance(asset.get("size_bytes"), int)
            or isinstance(asset.get("size_bytes"), bool)
            or asset["size_bytes"] < 0
        ):
            raise ValueError("transfer manifest asset reference is invalid")
    if not isinstance(manifest.get("audit_included"), bool):
        raise ValueError("transfer manifest audit marker is invalid")
    if (
        manifest.get("import_policy")
        != "validate_compatibility_and_conflicts_before_write_no_overwrite"
    ):
        raise ValueError("transfer manifest import policy is invalid")
    return manifest


def _validated_records(
    value: object, expected_counts: dict[str, int]
) -> dict[str, list[dict[str, object]]]:
    if not isinstance(value, dict):
        raise ValueError("transfer records must be a JSON object")
    records: dict[str, list[dict[str, object]]] = {}
    for table, rows in value.items():
        if not isinstance(table, str) or _TABLE_NAME.fullmatch(table) is None:
            raise ValueError("transfer record table name is invalid")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("transfer table rows are invalid")
        records[table] = [cast("dict[str, object]", row) for row in rows]
    counts = {table: len(rows) for table, rows in records.items()}
    if counts != expected_counts:
        raise ValueError("transfer record counts do not match the manifest")
    return records


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export")
    export_parser.add_argument("--target", required=True, type=Path)
    export_parser.add_argument("--workspace-id", required=True, type=UUID)
    export_parser.add_argument("--project-id", type=UUID)
    validate_parser = commands.add_parser("validate-import")
    validate_parser.add_argument("--source", required=True, type=Path)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        if arguments.command == "export":
            result = export_scope(arguments.target, arguments.workspace_id, arguments.project_id)
        else:
            result = validate_import(arguments.source)
    except (ValueError, RuntimeError, OSError, psycopg.Error) as error:
        sys.stderr.write(f"transfer_failed: {type(error).__name__}: {error}\n")
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0 if result.get("compatible", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
