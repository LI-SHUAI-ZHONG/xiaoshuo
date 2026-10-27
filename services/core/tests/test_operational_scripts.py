from __future__ import annotations

# The operational CLIs intentionally keep their implementation private; these tests exercise
# those safety boundaries directly without widening the production command surface.
# ruff: noqa: SLF001
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from scripts import (
    ci_secret_scan,
    project_transfer,
    recovery,
    release_manifest,
    security_checks,
    verify_images,
)

from accos import __version__

if TYPE_CHECKING:
    from accos.kernel.settings import RuntimeSettings


def _checksum(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _backup_fixture(directory: Path) -> dict[str, object]:
    database = b"fixture-database"
    stored_object = b"fixture-object"
    objects = directory / recovery.OBJECTS_DIR
    objects.mkdir(parents=True)
    (directory / recovery.DATABASE_DUMP).write_bytes(database)
    (objects / "fixture.bin").write_bytes(stored_object)
    manifest: dict[str, object] = {
        "format": "accos-backup",
        "format_version": 1,
        "created_at": "2026-09-18T00:00:00Z",
        "application_version": __version__,
        "schema_revision": "0012_extension_graph_projection",
        "database": {
            "logical_name": "accos",
            "file": recovery.DATABASE_DUMP,
            "bytes": len(database),
            "sha256": _checksum(database),
            "table_counts": {"projects": 1},
        },
        "object_storage": {
            "bucket": "fixture-bucket",
            "versioning_required": True,
            "objects": [
                {
                    "key": "fixture/object.bin",
                    "version_id": "fixture-version",
                    "last_modified": "2026-09-18T00:00:00Z",
                    "delete_marker": False,
                    "etag": "fixture-etag",
                    "size": len(stored_object),
                    "file": "fixture.bin",
                    "sha256": _checksum(stored_object),
                    "content_type": "application/octet-stream",
                }
            ],
        },
    }
    (directory / recovery.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def _transfer_fixture(
    directory: Path,
    *,
    application_version: str = __version__,
    with_identifier: bool = False,
) -> dict[str, object]:
    record: dict[str, object] = {"name": "fixture-project"}
    if with_identifier:
        record["id"] = str(uuid4())
    records = {"projects": [record]}
    payload = (json.dumps(records, sort_keys=True) + "\n").encode()
    (directory / project_transfer.RECORDS_NAME).write_bytes(payload)
    manifest: dict[str, object] = {
        "format": "accos-scope-export",
        "format_version": 1,
        "created_at": "2026-09-18T00:00:00Z",
        "application_version": application_version,
        "schema_revision": "0012_extension_graph_projection",
        "scope": {"workspace_id": str(uuid4()), "project_id": None},
        "records": {
            "file": project_transfer.RECORDS_NAME,
            "sha256": _checksum(payload),
            "counts": {"projects": 1},
        },
        "asset_references": [],
        "audit_included": False,
        "import_policy": "validate_compatibility_and_conflicts_before_write_no_overwrite",
    }
    (directory / project_transfer.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_recovery_manifest_verification_tamper_and_path_guards(tmp_path: Path) -> None:
    backup = tmp_path / "fixture-backup"
    backup.mkdir()
    manifest = _backup_fixture(backup)

    assert recovery.verify_backup(backup) == manifest

    object_file = backup / recovery.OBJECTS_DIR / "fixture.bin"
    object_file.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="object backup checksum"):
        recovery.verify_backup(backup)
    object_file.write_bytes(b"fixture-object")

    manifest["object_storage"]["objects"][0]["file"] = "../fixture.bin"  # type: ignore[index]
    (backup / recovery.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="simple filename"):
        recovery.verify_backup(backup)

    with pytest.raises(ValueError, match="explicit, narrow"):
        recovery._safe_new_directory(Path(tmp_path.anchor))
    with pytest.raises(ValueError, match="manifest"):
        recovery._safe_source_directory(tmp_path / "missing")


@pytest.mark.parametrize(
    ("database", "prefix"),
    [
        ("accos", "accos-restore/fixture"),
        ("accos_restore_fixture", "fixture"),
        ("accos_restore_fixture", "accos-restore/../fixture"),
    ],
)
def test_recovery_restore_targets_are_narrow(database: str, prefix: str) -> None:
    with pytest.raises(ValueError):
        recovery._validate_restore_targets(database, prefix)


def test_postgres_tool_uses_local_binary_with_explicit_connection_limits() -> None:
    settings = SimpleNamespace(
        required=SimpleNamespace(
            database_url="postgresql+psycopg://fixture:fixture-secret@127.0.0.1:55432/accos"
        )
    )
    completed = subprocess.CompletedProcess(["pg_dump"], 0, b"fixture", b"")
    with (
        patch("scripts.recovery.shutil.which", return_value="C:/fixture/pg_dump.exe"),
        patch.object(recovery, "_settings", return_value=settings),
        patch("scripts.recovery.subprocess.run", return_value=completed) as run,
    ):
        assert recovery._run_postgres_tool(["pg_dump", "-d", "accos"]) is completed

    arguments = run.call_args.args[0]
    environment = run.call_args.kwargs["env"]
    assert arguments[-4:] == ["--host", "127.0.0.1", "--port", "55432"]
    assert environment["PGPASSWORD"] == "fixture-secret"


def test_versioned_object_backup_and_restore_integrity(
    tmp_path: Path, runtime_settings: RuntimeSettings
) -> None:
    source_item = SimpleNamespace(
        object_name="fixture/object.bin",
        version_id="source-version",
        last_modified=None,
        is_delete_marker=False,
        etag="fixture-etag",
        size=len(b"fixture-object"),
    )
    response = MagicMock()
    response.read.return_value = b"fixture-object"
    client = MagicMock()
    client.get_bucket_versioning.return_value.status = "Enabled"
    client.list_objects.return_value = iter((source_item,))
    client.get_object.return_value = response
    client.stat_object.return_value.content_type = "application/octet-stream"

    with patch.object(recovery, "_minio", return_value=client):
        records = recovery._backup_objects(runtime_settings, tmp_path)
    assert records[0]["sha256"] == _checksum(b"fixture-object")
    assert (tmp_path / recovery.OBJECTS_DIR / records[0]["file"]).read_bytes() == b"fixture-object"

    client.list_objects.return_value = iter(())
    client.put_object.return_value.version_id = "restored-version"
    manifest = {"object_storage": {"objects": records}}
    with patch.object(recovery, "_minio", return_value=client):
        assert (
            recovery._restore_objects(runtime_settings, tmp_path, manifest, "accos-restore/fixture")
            == 1
        )
    assert client.put_object.call_args.kwargs["metadata"] == {
        "sha256": _checksum(b"fixture-object"),
        "accos-source-version": "source-version",
    }

    client.get_bucket_versioning.return_value.status = "Suspended"
    with (
        patch.object(recovery, "_minio", return_value=client),
        pytest.raises(RuntimeError, match="versioning"),
    ):
        recovery._backup_objects(runtime_settings, tmp_path / "disabled")


def test_restore_refuses_overwrite_and_validates_database_integrity(
    tmp_path: Path, runtime_settings: RuntimeSettings
) -> None:
    backup = tmp_path / "restore-source"
    backup.mkdir()
    _backup_fixture(backup)
    completed = subprocess.CompletedProcess(["pg_restore"], 0, b"", b"")
    patches = (
        patch.object(recovery, "_settings", return_value=runtime_settings),
        patch.object(recovery, "_database_exists", return_value=False),
        patch.object(recovery, "_create_database"),
        patch.object(recovery, "_run_postgres_tool", return_value=completed),
        patch.object(recovery, "_restore_objects", return_value=1),
        patch.object(recovery, "_table_counts", return_value={"projects": 1}),
        patch.object(recovery, "_schema_revision", return_value="0012_extension_graph_projection"),
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        result = recovery.restore(
            backup,
            "accos_restore_fixture1",
            "accos-restore/fixture1",
        )
    assert result["table_counts"] == {"projects": 1}
    assert result["object_versions"] == 1

    with (
        patch.object(recovery, "_settings", return_value=runtime_settings),
        patch.object(recovery, "_database_exists", return_value=True),
        pytest.raises(ValueError, match="already exists"),
    ):
        recovery.restore(backup, "accos_restore_fixture2", "accos-restore/fixture2")


def test_project_export_manifest_contains_assets_audit_and_checksum(tmp_path: Path) -> None:
    workspace_id = uuid4()
    asset_id = uuid4()
    connection = MagicMock()
    connector = MagicMock()
    connector.return_value.__enter__.return_value = connection

    def scoped_rows(
        _connection: object,
        table: str,
        _columns: set[str],
        _workspace_id: object,
        _project_id: object,
    ) -> list[dict[str, object]]:
        if table == "asset_versions":
            return [
                {
                    "asset_id": str(asset_id),
                    "version_number": 1,
                    "object_key": "fixture/object.bin",
                    "content_hash": "a" * 64,
                    "size_bytes": 14,
                    "input_tokens": 7,
                    "provider_token": "must-redact",
                }
            ]
        return [{"id": str(uuid4()), "event_type": "fixture.event"}]

    with (
        patch("scripts.project_transfer.psycopg.connect", connector),
        patch.object(project_transfer, "_database_url", return_value="fixture"),
        patch.object(
            project_transfer,
            "_tables",
            return_value=[
                ("asset_versions", {"workspace_id"}),
                ("audit_events", {"workspace_id"}),
            ],
        ),
        patch.object(project_transfer, "_read_scoped_table", side_effect=scoped_rows),
        patch.object(
            project_transfer,
            "_schema_revision",
            return_value="0012_extension_graph_projection",
        ),
    ):
        manifest = project_transfer.export_scope(tmp_path / "export", workspace_id, None)

    records = json.loads((tmp_path / "export" / project_transfer.RECORDS_NAME).read_text())
    assert manifest["audit_included"] is True
    assert manifest["asset_references"][0]["asset_id"] == str(asset_id)  # type: ignore[index]
    assert records["asset_versions"][0]["input_tokens"] == 7
    assert records["asset_versions"][0]["provider_token"] == "must-redact"
    assert manifest["records"]["sha256"] == _checksum(  # type: ignore[index]
        (tmp_path / "export" / project_transfer.RECORDS_NAME).read_bytes()
    )


def test_project_transfer_reads_dictionary_table_metadata() -> None:
    connection = MagicMock()
    connection.execute.return_value.fetchall.return_value = [
        {
            "table_name": "projects",
            "columns": ["id", "workspace_id", "project_id"],
        }
    ]

    assert project_transfer._tables(connection) == [
        ("projects", {"id", "workspace_id", "project_id"})
    ]

    connection.execute.return_value.fetchall.return_value = [("projects", ["id"])]
    assert project_transfer._tables(connection) == [("projects", {"id"})]

    connection.execute.return_value.fetchall.return_value = [{"table_name": "projects"}]
    with pytest.raises(RuntimeError, match="invalid data"):
        project_transfer._tables(connection)


def test_project_transfer_includes_project_root_record() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    connection = MagicMock()
    connection.execute.return_value.fetchall.return_value = [
        {"id": project_id, "workspace_id": workspace_id, "name": "fixture-project"}
    ]

    records = project_transfer._read_scoped_table(
        connection,
        "projects",
        {"id", "workspace_id"},
        workspace_id,
        project_id,
    )

    assert records == [
        {
            "id": str(project_id),
            "workspace_id": str(workspace_id),
            "name": "fixture-project",
        }
    ]


def test_import_validation_is_read_only_and_blocks_incompatibility_and_conflicts(
    tmp_path: Path,
) -> None:
    source = tmp_path / "transfer"
    source.mkdir()
    manifest = _transfer_fixture(source)
    connection = MagicMock()
    connector = MagicMock()
    connector.return_value.__enter__.return_value = connection

    with (
        patch("scripts.project_transfer.psycopg.connect", connector),
        patch.object(project_transfer, "_database_url", return_value="fixture"),
        patch.object(
            project_transfer,
            "_schema_revision",
            return_value="0012_extension_graph_projection",
        ),
        patch.object(project_transfer, "_tables", return_value=[("projects", {"id"})]),
    ):
        result = project_transfer.validate_import(source)
    assert result["compatible"] is True
    assert result["write_performed"] is False

    manifest["application_version"] = "incompatible-version"
    (source / project_transfer.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    with (
        patch("scripts.project_transfer.psycopg.connect", connector),
        patch.object(project_transfer, "_database_url", return_value="fixture"),
        patch.object(
            project_transfer,
            "_schema_revision",
            return_value="0012_extension_graph_projection",
        ),
        patch.object(project_transfer, "_tables", return_value=[]),
    ):
        incompatible = project_transfer.validate_import(source)
    assert incompatible["compatible"] is False
    assert incompatible["application_compatible"] is False

    manifest["records"]["counts"] = {"projects": 2}  # type: ignore[index]
    (source / project_transfer.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="counts"):
        project_transfer.validate_import(source)

    conflict_source = tmp_path / "conflict"
    conflict_source.mkdir()
    _transfer_fixture(conflict_source, with_identifier=True)
    connection.execute.return_value.fetchone.return_value = (1,)
    with (
        patch("scripts.project_transfer.psycopg.connect", connector),
        patch.object(project_transfer, "_database_url", return_value="fixture"),
        patch.object(
            project_transfer,
            "_schema_revision",
            return_value="0012_extension_graph_projection",
        ),
        patch.object(project_transfer, "_tables", return_value=[("projects", {"id"})]),
    ):
        conflict = project_transfer.validate_import(conflict_source)
    assert conflict["compatible"] is False
    assert conflict["conflicts"] == {"projects": 1}


def test_security_runtime_checks_and_failure_reporting(capsys: pytest.CaptureFixture[str]) -> None:
    configuration = security_checks._compose_config()
    failures: list[str] = []
    security_checks._check_compose(configuration, failures)
    security_checks._check_delivery_dockerfiles(failures)
    security_checks._check_dependency_pins(failures)
    security_checks._check_secret_and_upload_guards(failures)
    assert failures == []

    insecure = {
        "services": {
            "fixture": {
                "image": "fixture:latest",
                "ports": ["8000:8000"],
                "security_opt": [],
            }
        }
    }
    security_checks._check_compose(insecure, failures)
    assert any("not pinned" in item for item in failures)
    assert any("no-new-privileges" in item for item in failures)
    assert any("loopback" in item for item in failures)

    with (
        patch.object(security_checks, "_compose_config", side_effect=ValueError("fixture")),
        patch.object(sys, "argv", ["security_checks.py"]),
    ):
        assert security_checks.main() == 1
    assert "security_checks_failed" in capsys.readouterr().err


def test_stage23_secret_image_and_release_guards(tmp_path: Path) -> None:
    clean = tmp_path / "clean.txt"
    clean.write_text("fixture-token-placeholder", encoding="utf-8")
    leaked = tmp_path / "leaked.txt"
    leaked.write_text("AKIA" + "1234567890ABCDEF", encoding="utf-8")
    with patch.object(ci_secret_scan, "ROOT", tmp_path):
        findings = ci_secret_scan.scan((clean, leaked))
    assert findings == [{"kind": "aws_access_key", "line": 1, "path": "leaked.txt"}]

    safe_image = {
        "Config": {
            "Env": ["PATH=/usr/bin", "ACCOS_ENV=fixture"],
            "Healthcheck": {"Test": ["CMD", "fixture"]},
            "Labels": {
                "org.opencontainers.image.revision": "fixture-revision",
                "org.opencontainers.image.version": "0.1.0-skeleton",
            },
            "User": "10001:10001",
        }
    }
    with patch.object(verify_images, "_inspect", return_value=safe_image):
        assert (
            verify_images.verify_image(
                "fixture-image",
                expected_version="0.1.0-skeleton",
                expected_revision="fixture-revision",
            )
            == []
        )
    unsafe_image = {
        "Config": {
            "Env": ["ACCOS_API_TOKEN=fixture-secret"],
            "Healthcheck": {},
            "Labels": {},
            "User": "root",
        }
    }
    with patch.object(verify_images, "_inspect", return_value=unsafe_image):
        failures = verify_images.verify_image(
            "fixture-image",
            expected_version="0.1.0-skeleton",
            expected_revision="fixture-revision",
        )
    assert len(failures) == 5

    with patch.object(release_manifest, "_image_digest", return_value="sha256:" + "0" * 64):
        manifest = release_manifest.build_manifest(
            revision="fixture-revision",
            version="0.1.0-skeleton",
            images=("fixture-image",),
            created_at=datetime(2026, 9, 18, tzinfo=UTC),
        )
    assert manifest["real_provider_calls"] is False
    assert manifest["images"] == [
        {"content_digest": "sha256:" + "0" * 64, "reference": "fixture-image"}
    ]
    assert len(manifest["dependency_manifests"]) == 3


def test_recovery_postgres_tool_mode_rejects_invalid_or_missing_local_tool() -> None:
    with (
        patch.dict(os.environ, {"ACCOS_POSTGRES_TOOL_MODE": "invalid"}),
        pytest.raises(ValueError, match="must be"),
    ):
        recovery._run_postgres_tool(["pg_dump", "fixture"])
    with (
        patch.dict(os.environ, {"ACCOS_POSTGRES_TOOL_MODE": "local"}),
        patch("scripts.recovery.shutil.which", return_value=None),
        pytest.raises(FileNotFoundError, match="pg_dump"),
    ):
        recovery._run_postgres_tool(["pg_dump", "fixture"])
