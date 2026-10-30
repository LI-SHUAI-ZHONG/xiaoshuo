"""Safe PostgreSQL + versioned object-storage backup, restore, verify, and drill CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
from minio import Minio
from minio.error import MinioException
from psycopg import sql
from urllib3 import PoolManager, Timeout

from accos import __version__
from accos.kernel.settings import RuntimeSettings, load_settings

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "infra" / "compose.yaml"
MANIFEST_NAME = "backup-manifest.json"
DATABASE_DUMP = "postgres.dump"
OBJECTS_DIR = "objects"
_RESTORE_DATABASE = re.compile(r"^accos_(?:restore|drill)_[a-z0-9_]{6,80}$")
_RESTORE_PREFIX = re.compile(r"^accos-(?:restore|drill)/[a-z0-9-]{6,80}$")
_MIN_SAFE_PATH_PARTS = 3


def _settings() -> RuntimeSettings:
    return load_settings(env_file=ROOT / ".env")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_new_directory(path: Path) -> Path:
    target = path.resolve()
    forbidden = {Path(target.anchor), Path.home().resolve(), ROOT.resolve()}
    if target in forbidden or len(target.parts) < _MIN_SAFE_PATH_PARTS:
        raise ValueError("backup target must be an explicit, narrow directory")
    if target.exists() and any(target.iterdir()):
        raise ValueError("backup target must not already contain files")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _safe_source_directory(path: Path) -> Path:
    source = path.resolve()
    forbidden = {Path(source.anchor), Path.home().resolve(), ROOT.resolve()}
    if (
        source in forbidden
        or len(source.parts) < _MIN_SAFE_PATH_PARTS
        or not source.is_dir()
        or not (source / MANIFEST_NAME).is_file()
    ):
        raise ValueError("backup source does not contain a manifest")
    return source


def _safe_child(directory: Path, filename: object, *, label: str) -> Path:
    if not isinstance(filename, str) or not filename or Path(filename).name != filename:
        raise ValueError(f"{label} must be a simple filename")
    child = (directory / filename).resolve()
    if child.parent != directory.resolve():
        raise ValueError(f"{label} escapes the backup directory")
    return child


def _database_parts(settings: RuntimeSettings) -> tuple[str, str]:
    parsed = urlsplit(settings.required.database_url)
    user = parsed.username or ""
    database = parsed.path.lstrip("/")
    if not user or not database:
        raise ValueError("database URL must contain an explicit user and database")
    return user, database


def _database_url(settings: RuntimeSettings, database: str) -> str:
    parsed = urlsplit(settings.required.database_url.replace("postgresql+psycopg", "postgresql"))
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database}", parsed.query, ""))


def _run_postgres_tool(
    arguments: list[str], *, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    mode = os.environ.get("ACCOS_POSTGRES_TOOL_MODE", "auto").lower()
    if mode not in {"auto", "compose", "local"}:
        raise ValueError("ACCOS_POSTGRES_TOOL_MODE must be auto, compose, or local")
    executable = shutil.which(arguments[0])
    if mode != "compose" and executable is not None:
        parsed = urlsplit(_settings().required.database_url)
        environment = os.environ.copy()
        if parsed.password:
            environment["PGPASSWORD"] = parsed.password
        local_arguments = [
            executable,
            *arguments[1:],
            "--host",
            parsed.hostname or "127.0.0.1",
            "--port",
            str(parsed.port or 5432),
        ]
        return subprocess.run(  # noqa: S603 - resolved executable and structured argv.
            local_arguments,
            cwd=ROOT,
            env=environment,
            input=input_bytes,
            capture_output=True,
            check=True,
        )
    if mode == "local":
        raise FileNotFoundError(f"PostgreSQL client tool is unavailable: {arguments[0]}")
    command = [
        "docker",
        "compose",
        "--env-file",
        str(ROOT / ".env"),
        "-f",
        str(COMPOSE),
        "exec",
        "-T",
        "postgres",
        *arguments,
    ]
    return subprocess.run(  # noqa: S603 - fixed executable and structured argv.
        command,
        cwd=ROOT,
        input=input_bytes,
        capture_output=True,
        check=True,
    )


def _table_counts(database_url: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'accos' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        for (table_name,) in cursor.fetchall():
            cursor.execute(
                sql.SQL("SELECT count(*) FROM accos.{}").format(sql.Identifier(table_name))
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("table count query returned no result")
            counts[str(table_name)] = int(row[0])
    return counts


def _schema_revision(database_url: str) -> str:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT revision FROM accos.schema_metadata "
            "WHERE component = 'accos-core' AND archived_at IS NULL"
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("schema metadata is missing")
    return str(row[0])


def _minio(settings: RuntimeSettings) -> Minio:
    parsed = urlsplit(settings.required.s3_endpoint)
    return Minio(
        parsed.netloc,
        access_key=settings.required.s3_access_key,
        secret_key=settings.required.s3_secret_key,
        secure=settings.optional.s3_use_ssl,
        region=settings.optional.s3_region,
        http_client=PoolManager(
            timeout=Timeout(
                connect=settings.resilience.timeout_seconds,
                read=settings.resilience.timeout_seconds,
            ),
            retries=False,
        ),
    )


def _backup_objects(settings: RuntimeSettings, target: Path) -> list[dict[str, Any]]:
    client = _minio(settings)
    bucket = settings.required.s3_bucket
    if client.get_bucket_versioning(bucket).status != "Enabled":
        raise RuntimeError("object storage bucket versioning must be enabled before backup")
    result: list[dict[str, Any]] = []
    objects_dir = target / OBJECTS_DIR
    objects_dir.mkdir(parents=True, exist_ok=True)
    for item in client.list_objects(bucket, recursive=True, include_version=True):
        version_id = item.version_id or "null"
        record: dict[str, Any] = {
            "key": item.object_name,
            "version_id": version_id,
            "last_modified": (
                None
                if item.last_modified is None
                else item.last_modified.astimezone(UTC).isoformat().replace("+00:00", "Z")
            ),
            "delete_marker": bool(item.is_delete_marker),
            "etag": item.etag,
            "size": int(item.size or 0),
        }
        if not item.is_delete_marker:
            response = client.get_object(bucket, item.object_name, version_id=item.version_id)
            try:
                data = bytes(response.read())
            finally:
                response.close()
                response.release_conn()
            metadata = client.stat_object(bucket, item.object_name, version_id=item.version_id)
            filename = _sha256(f"{item.object_name}\0{version_id}".encode()) + ".bin"
            (objects_dir / filename).write_bytes(data)
            record.update(
                {
                    "file": filename,
                    "sha256": _sha256(data),
                    "content_type": metadata.content_type or "application/octet-stream",
                }
            )
        result.append(record)
    return result


def backup(target: Path) -> dict[str, Any]:
    settings = _settings()
    destination = _safe_new_directory(target)
    user, database = _database_parts(settings)
    dump = _run_postgres_tool(
        [
            "pg_dump",
            "-U",
            user,
            "-d",
            database,
            "--format=custom",
            "--no-owner",
            "--no-acl",
        ]
    ).stdout
    (destination / DATABASE_DUMP).write_bytes(dump)
    database_url = _database_url(settings, database)
    objects = _backup_objects(settings, destination)
    manifest: dict[str, Any] = {
        "format": "accos-backup",
        "format_version": 1,
        "created_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "application_version": __version__,
        "schema_revision": _schema_revision(database_url),
        "database": {
            "logical_name": database,
            "file": DATABASE_DUMP,
            "bytes": len(dump),
            "sha256": _sha256(dump),
            "table_counts": _table_counts(database_url),
        },
        "object_storage": {
            "bucket": settings.required.s3_bucket,
            "versioning_required": True,
            "objects": objects,
        },
    }
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (destination / MANIFEST_NAME).write_text(serialized, encoding="utf-8", newline="\n")
    return manifest


def verify_backup(source: Path) -> dict[str, Any]:
    backup_dir = _safe_source_directory(source)
    parsed = json.loads((backup_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("backup manifest must be a JSON object")
    manifest = _validated_manifest(cast("dict[str, Any]", parsed))
    database = manifest["database"]
    dump = _safe_child(backup_dir, database["file"], label="database backup file").read_bytes()
    if len(dump) != database["bytes"] or _sha256(dump) != database["sha256"]:
        raise ValueError("database backup checksum failed")
    for item in manifest["object_storage"]["objects"]:
        if item["delete_marker"]:
            continue
        data = _safe_child(
            backup_dir / OBJECTS_DIR,
            item["file"],
            label="object backup file",
        ).read_bytes()
        if len(data) != item["size"] or _sha256(data) != item["sha256"]:
            raise ValueError("object backup checksum failed")
    return manifest


def _validated_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("format") != "accos-backup" or manifest.get("format_version") != 1:
        raise ValueError("backup manifest format is unsupported")
    if not isinstance(manifest.get("application_version"), str) or not isinstance(
        manifest.get("schema_revision"), str
    ):
        raise ValueError("backup manifest version metadata is invalid")
    database = manifest.get("database")
    object_storage = manifest.get("object_storage")
    if not isinstance(database, dict) or not isinstance(object_storage, dict):
        raise ValueError("backup manifest storage metadata is invalid")
    if (
        database.get("file") != DATABASE_DUMP
        or not isinstance(database.get("bytes"), int)
        or database["bytes"] < 0
        or not _is_checksum(database.get("sha256"))
    ):
        raise ValueError("backup manifest database metadata is invalid")
    counts = database.get("table_counts")
    if not isinstance(counts, dict) or any(
        not isinstance(name, str)
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        for name, count in counts.items()
    ):
        raise ValueError("backup manifest table counts are invalid")
    objects = object_storage.get("objects")
    if object_storage.get("versioning_required") is not True or not isinstance(objects, list):
        raise ValueError("backup manifest object storage metadata is invalid")
    for item in objects:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("key"), str)
            or not item["key"]
            or not isinstance(item.get("last_modified"), (str, type(None)))
        ):
            raise ValueError("backup manifest object entry is invalid")
        if not isinstance(item.get("version_id"), str) or not isinstance(
            item.get("delete_marker"), bool
        ):
            raise ValueError("backup manifest object version entry is invalid")
        if (
            not isinstance(item.get("size"), int)
            or isinstance(item.get("size"), bool)
            or item["size"] < 0
        ):
            raise ValueError("backup manifest object size is invalid")
        if not item["delete_marker"] and (
            not isinstance(item.get("file"), str)
            or not _is_checksum(item.get("sha256"))
            or not isinstance(item.get("content_type"), str)
        ):
            raise ValueError("backup manifest object payload metadata is invalid")
    return manifest


def _is_checksum(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _validate_restore_targets(database: str, object_prefix: str) -> None:
    if _RESTORE_DATABASE.fullmatch(database) is None:
        raise ValueError("restore database must use the accos_restore_/accos_drill_ prefix")
    if _RESTORE_PREFIX.fullmatch(object_prefix) is None or ".." in object_prefix:
        raise ValueError("restore object prefix must be an explicit accos-restore/accos-drill path")


def _database_exists(settings: RuntimeSettings, database: str) -> bool:
    with (
        psycopg.connect(_database_url(settings, "postgres")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
        return cursor.fetchone() is not None


def _create_database(settings: RuntimeSettings, database: str) -> None:
    with psycopg.connect(_database_url(settings, "postgres"), autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))


def _restore_objects(
    settings: RuntimeSettings,
    backup_dir: Path,
    manifest: dict[str, Any],
    object_prefix: str,
) -> int:
    client = _minio(settings)
    bucket = settings.required.s3_bucket
    if next(client.list_objects(bucket, prefix=object_prefix + "/", recursive=True), None):
        raise ValueError("restore object prefix is not empty")
    objects = sorted(
        manifest["object_storage"]["objects"], key=lambda item: item["last_modified"] or ""
    )
    restored_versions = 0
    for item in objects:
        target_key = f"{object_prefix}/{item['key']}"
        if item["delete_marker"]:
            client.remove_object(bucket, target_key)
            restored_versions += 1
            continue
        data = _safe_child(
            backup_dir / OBJECTS_DIR,
            item["file"],
            label="object backup file",
        ).read_bytes()
        written = client.put_object(
            bucket,
            target_key,
            BytesIO(data),
            len(data),
            content_type=item["content_type"],
            metadata={
                "sha256": item["sha256"],
                "accos-source-version": item["version_id"],
            },
        )
        response = client.get_object(bucket, target_key, version_id=written.version_id)
        try:
            restored = bytes(response.read())
        finally:
            response.close()
            response.release_conn()
        if _sha256(restored) != item["sha256"]:
            raise RuntimeError("restored object checksum does not match the backup manifest")
        restored_versions += 1
    return restored_versions


def restore(source: Path, database: str, object_prefix: str) -> dict[str, Any]:
    _validate_restore_targets(database, object_prefix)
    backup_dir = _safe_source_directory(source)
    manifest = verify_backup(backup_dir)
    settings = _settings()
    if _database_exists(settings, database):
        raise ValueError("restore database already exists; overwrite is forbidden")
    _create_database(settings, database)
    user, _source_database = _database_parts(settings)
    dump = _safe_child(
        backup_dir,
        manifest["database"]["file"],
        label="database backup file",
    ).read_bytes()
    _run_postgres_tool(
        ["pg_restore", "-U", user, "-d", database, "--no-owner", "--no-acl"],
        input_bytes=dump,
    )
    restored_object_versions = _restore_objects(settings, backup_dir, manifest, object_prefix)
    restored_counts = _table_counts(_database_url(settings, database))
    if restored_counts != manifest["database"]["table_counts"]:
        raise RuntimeError("restored database table counts do not match the backup manifest")
    restored_revision = _schema_revision(_database_url(settings, database))
    if restored_revision != manifest["schema_revision"]:
        raise RuntimeError("restored database schema revision does not match the backup manifest")
    return {
        "database": database,
        "object_prefix": object_prefix,
        "schema_revision": restored_revision,
        "table_counts": restored_counts,
        "object_versions": restored_object_versions,
    }


def _drop_drill_database(settings: RuntimeSettings, database: str) -> None:
    if not database.startswith("accos_drill_"):
        raise ValueError("only generated drill databases may be removed")
    with psycopg.connect(_database_url(settings, "postgres"), autocommit=True) as connection:
        connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (database,),
        )
        connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))


def _clear_drill_prefix(settings: RuntimeSettings, prefix: str) -> None:
    if not prefix.startswith("accos-drill/"):
        raise ValueError("only generated drill object prefixes may be removed")
    client = _minio(settings)
    bucket = settings.required.s3_bucket
    for item in client.list_objects(
        bucket, prefix=prefix + "/", recursive=True, include_version=True
    ):
        client.remove_object(bucket, item.object_name, version_id=item.version_id)


def drill(target: Path) -> dict[str, Any]:
    started = time.perf_counter()
    suffix = uuid4().hex[:12]
    database = f"accos_drill_{suffix}"
    prefix = f"accos-drill/{suffix}"
    backup_dir = _safe_new_directory(target)
    settings = _settings()
    result: dict[str, Any]
    try:
        backup_started = time.perf_counter()
        manifest = backup(backup_dir)
        backup_seconds = time.perf_counter() - backup_started
        first_restore = restore(backup_dir, database, prefix)

        with psycopg.connect(_database_url(settings, database)) as connection:
            connection.execute("DELETE FROM accos.schema_metadata")
            connection.commit()
        if _table_counts(_database_url(settings, database)) == manifest["database"]["table_counts"]:
            raise RuntimeError("drill destruction did not alter isolated technical data")

        _drop_drill_database(settings, database)
        _clear_drill_prefix(settings, prefix)
        restore_started = time.perf_counter()
        final_restore = restore(backup_dir, database, prefix)
        restore_seconds = time.perf_counter() - restore_started
        result = {
            "status": "PASS",
            "completed_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "rpo_target_hours": 24,
            "rto_target_hours": 4,
            "backup_seconds": round(backup_seconds, 3),
            "restore_seconds": round(restore_seconds, 3),
            "total_seconds": round(time.perf_counter() - started, 3),
            "schema_revision": manifest["schema_revision"],
            "database_table_count": len(final_restore["table_counts"]),
            "object_versions": final_restore["object_versions"],
            "integrity": {
                "database_counts_match": True,
                "object_checksums_match": True,
                "destructive_test_isolated": True,
            },
            "first_restore": first_restore,
        }
        (backup_dir / "drill-result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return result
    finally:
        if _database_exists(settings, database):
            _drop_drill_database(settings, database)
        _clear_drill_prefix(settings, prefix)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--target", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--source", type=Path, required=True)
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--source", type=Path, required=True)
    restore_parser.add_argument("--database-target", required=True)
    restore_parser.add_argument("--object-prefix", required=True)
    drill_parser = subparsers.add_parser("drill")
    drill_parser.add_argument("--target", type=Path, required=True)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        if arguments.command == "backup":
            result = backup(arguments.target)
        elif arguments.command == "verify":
            result = verify_backup(arguments.source)
        elif arguments.command == "restore":
            result = restore(
                arguments.source,
                arguments.database_target,
                arguments.object_prefix,
            )
        else:
            result = drill(arguments.target)
    except (
        ValueError,
        RuntimeError,
        OSError,
        subprocess.SubprocessError,
        psycopg.Error,
        MinioException,
    ) as error:
        sys.stderr.write(f"recovery_failed: {type(error).__name__}: {error}\n")
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
