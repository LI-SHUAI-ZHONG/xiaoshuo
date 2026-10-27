"""T001–T003: baseline recovery and rejected architecture/contract violations.

Written during construction; scheduled for execution at stage 45 only.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from accos.kernel.shared_contracts import (
    CapabilityStatus,
    ContentRef,
    DataOwner,
    RuntimePackageFile,
    RuntimePackageManifest,
    SourceSpan,
    package_relative_path,
)
from scripts.check_import_boundaries import boundary_violations
from scripts.check_table_ownership import inspect_sources
from scripts.source_baseline import create_baseline, digest, restore_baseline, safe_source_name

ID = UUID("11111111-1111-4111-8111-111111111111")


def test_source_only_recovery_preserves_bytes_and_excludes_private_data(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "README.md").write_bytes("原始\r\n资料\n".encode())
    for name in (
        ".env",
        "infra/.data/tools/example.py",
        "apps/studio/node_modules/sdk/index.js",
        "services/core/.env.local",
        "infra/credentials/provider.json",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture-private", encoding="utf-8")
    output = root / ".construction/baselines/first"
    result = create_baseline(root, output)
    assert result["file_count"] == 1
    assert result["restore_test_status"] == "NOT_RUN"
    target = tmp_path / "recovered"
    assert restore_baseline(output / "source.zip", target) == 1
    assert (target / "README.md").read_bytes() == (root / "README.md").read_bytes()
    assert not (target / ".env").exists()
    with pytest.raises(FileExistsError):
        restore_baseline(output / "source.zip", target)
    with pytest.raises(FileExistsError):
        create_baseline(root, output)


@pytest.mark.parametrize(
    "path",
    [
        "../README.md",
        "C:/README.md",
        "/README.md",
        "apps/studio/.env",
        "infra/.data/data.json",
        "services/core/credentials/key.json",
        "scripts/../../.env",
    ],
)
def test_baseline_name_rejects_runtime_credentials_and_traversal(path: str) -> None:
    assert not safe_source_name(path)


def test_recovery_refuses_tampered_archive_before_creating_target(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "README.md").write_text("fixture", encoding="utf-8")
    output = root / ".construction/baselines/first"
    create_baseline(root, output)
    archive = output / "source.zip"
    with zipfile.ZipFile(archive, "a") as bundle:
        bundle.writestr("files/../escaped.txt", "fixture")
    target = tmp_path / "recovered"
    with pytest.raises(ValueError, match="hash"):
        restore_baseline(archive, target)
    (output / "source.zip.sha256").write_text(digest(archive.read_bytes()), encoding="ascii")
    with pytest.raises(ValueError, match="Unexpected archive"):
        restore_baseline(archive, target)
    assert not target.exists()
    assert not (tmp_path / "escaped.txt").exists()


def test_cross_owner_imports_are_rejected_but_public_ports_are_allowed() -> None:
    assert list(
        boundary_violations("accos.modules.novel.application", "accos.modules.memory.domain")
    )
    assert list(
        boundary_violations(
            "accos.adapters.projects.persistence", "accos.adapters.identity.persistence"
        )
    )
    assert list(
        boundary_violations(
            "accos.entrypoints.api.v1.router", "accos.adapters.projects.persistence"
        )
    )
    assert not list(
        boundary_violations("accos.modules.novel.application", "accos.modules.memory.public")
    )
    assert not list(
        boundary_violations(
            "accos.adapters.projects.persistence", "accos.adapters.persistence.models"
        )
    )


def test_registered_table_cannot_move_to_another_owner_or_be_written_through_raw_sql(
    tmp_path: Path,
) -> None:
    own = tmp_path / "services/core/src/accos/adapters/projects/persistence.py"
    own.parent.mkdir(parents=True)
    own.write_text('class Project:\n    __tablename__ = "projects"\n', encoding="utf-8")
    registry: dict[str, Any] = {
        "tables": [
            {
                "table": "projects",
                "owner": "projects",
                "declaration": own.relative_to(tmp_path).as_posix(),
            }
        ],
        "read_only_exceptions": [],
    }
    assert inspect_sources(tmp_path, registry) == []
    illegal = tmp_path / "services/core/src/accos/adapters/models/persistence.py"
    illegal.parent.mkdir(parents=True)
    illegal.write_text(
        'class Wrong:\n    __tablename__ = "projects"\ntext("UPDATE accos.projects SET name=:name")\n',
        encoding="utf-8",
    )
    errors = inspect_sources(tmp_path, registry)
    assert any("duplicate table" in error for error in errors)
    assert any("belongs to projects" in error for error in errors)
    assert any("forbidden SQL write" in error for error in errors)


def test_content_reference_and_spans_reject_false_sizes_and_ranges() -> None:
    with pytest.raises(ValidationError):
        ContentRef(
            asset_id=ID, asset_version_id=ID, sha256="hash", media_type="text/plain", byte_length=-1
        )
    with pytest.raises(ValidationError):
        SourceSpan(start=5, end=2)


def test_capability_verification_requires_evidence_and_is_separate_from_configuration() -> None:
    data = {
        "capability": "writing",
        "enabled": True,
        "implementation": "implemented",
        "implementation_version": "1.0.0",
        "configuration": "missing",
        "health": "unknown",
        "verification": "untested",
        "data": "empty",
    }
    status = CapabilityStatus.model_validate(data)
    assert status.configuration == "missing"
    assert status.implementation == "implemented"
    with pytest.raises(ValidationError, match="evidence"):
        CapabilityStatus.model_validate({**data, "verification": "verified"})


@pytest.mark.parametrize("path", ["../secret", "C:/x", "/x", "a\\b", "NUL.json", "a./b", "a//b"])
def test_runtime_packages_reject_nonportable_or_traversing_paths(path: str) -> None:
    with pytest.raises(ValueError):
        package_relative_path(path)


def test_runtime_entrypoints_must_belong_to_hashed_manifest() -> None:
    file = RuntimePackageFile(path="prompt.md", sha256="a" * 64, byte_length=1, kind="prompt")
    with pytest.raises(ValidationError, match="manifested"):
        RuntimePackageManifest(
            package_id="writer.fixture",
            version="1.0.0",
            owner=DataOwner.MODELS,
            package_type="prompt",
            minimum_contract_version="1.0.0",
            files=(file,),
            entrypoints={"main": "unlisted.md"},
        )


def test_legacy_migration_files_match_registered_hashes() -> None:
    root = Path(__file__).resolve().parents[3]
    registry = json.loads((root / "docs/contracts/migrations.json").read_text(encoding="utf-8"))
    for revision in registry["revisions"]:
        assert digest((root / revision["path"]).read_bytes()) == revision["sha256"]
