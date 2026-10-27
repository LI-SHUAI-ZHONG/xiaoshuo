"""Create source-only recovery archives; never read runtime data or credentials.

Creation is an operational backup, not a project test. Recovery is deliberately
limited to a new directory; exercising it belongs to final acceptance (T001).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORIES = (
    ".github",
    ".vscode",
    "apps",
    "docs",
    "infra",
    "packages",
    "scripts",
    "services",
    "tests",
    "执行",
    "后续执行",
    "content-packs",
)
ROOT_FILES = (
    ".dependency-cruiser.cjs",
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    ".gitattributes",
    ".gitignore",
    ".node-version",
    ".npmrc",
    ".pre-commit-config.yaml",
    ".prettierignore",
    ".prettierrc.json",
    ".python-version",
    "AGENTS.md",
    "README.md",
    "eslint.config.mjs",
    "package.json",
    "playwright.config.ts",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "pyfang.toml",
    "pyproject.toml",
    "tsconfig.json",
    "uv.lock",
    "vitest.config.ts",
    "创作搭建.txt",
    "改进资料.txt",
    "执行.txt",
)
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".next",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".turbo",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".import_linter_cache",
        ".pnpm-store",
        "coverage",
        "htmlcov",
        "dist",
        "build",
        "test-results",
        "playwright-report",
        "artifacts",
        "evidence",
        "logs",
        "data",
        "uploads",
        "credentials",
        "secrets",
        ".secrets",
        "backups",
        ".construction",
        ".data",
        ".cache",
        "volumes",
        "minio-data",
        ".tools",
        ".toolchain",
    }
)
SOURCE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".typed",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".sql",
        ".mako",
        ".md",
        ".txt",
        ".csv",
        ".html",
        ".css",
        ".scss",
        ".svg",
        ".ps1",
        ".sh",
        ".lock",
        ".conf",
        ".cfg",
        ".example",
        ".sample",
        ".template",
    }
)
SPECIAL_FILES = frozenset({"Dockerfile", ".dockerignore", ".gitignore", ".npmrc"})
PROTECTED_INPUTS = frozenset({"创作搭建.txt", "改进资料.txt", "执行.txt"})


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_source_name(relative: str) -> bool:
    """An explicit allowlist applies to both creation and recovery."""
    path = PurePosixPath(relative)
    windows_devices = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{number}" for number in range(10)),
        *(f"lpt{number}" for number in range(10)),
    }
    if (
        not relative
        or "\\" in relative
        or ":" in relative
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.split("/"))
        or any(ord(char) < 32 for char in relative)
        or any(
            part.endswith((".", " "))
            or part.split(".", maxsplit=1)[0].casefold() in windows_devices
            for part in path.parts
        )
    ):
        return False
    if len(path.parts) == 1:
        return relative in ROOT_FILES
    if path.parts[0] not in SOURCE_DIRECTORIES:
        return False
    if any(
        part.lower() in EXCLUDED_DIRECTORIES or part.startswith(".tmp") for part in path.parts[:-1]
    ):
        return False
    name = path.name.lower()
    if name.startswith(".env") and name != ".env.example":
        return False
    if any(word in name for word in ("credential", "secret", "private-key", "id_rsa")):
        # Source programs about credentials are valid; credential DATA is not.
        if path.suffix not in {".py", ".ts", ".tsx", ".mjs", ".md"}:
            return False
    return path.suffix in SOURCE_SUFFIXES or path.name in SPECIAL_FILES


def source_files(root: Path) -> list[Path]:
    files = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for directory in SOURCE_DIRECTORIES:
        base = root / directory
        if not base.exists():
            continue
        if base.is_symlink() or base.is_junction():
            raise ValueError(f"Source directory is a link: {directory}")
        for current, subdirs, names in os.walk(base, followlinks=False):
            current_path = Path(current)
            subdirs[:] = sorted(
                name
                for name in subdirs
                if name.lower() not in EXCLUDED_DIRECTORIES and not name.startswith(".tmp")
            )
            for name in subdirs:
                candidate = current_path / name
                if candidate.is_symlink() or candidate.is_junction():
                    raise ValueError(f"Source directory is a link: {candidate.relative_to(root)}")
            files.extend(
                current_path / name
                for name in sorted(names)
                if safe_source_name((current_path / name).relative_to(root).as_posix())
            )
    for path in files:
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Source file is a link or outside the repository: {path.name}")
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def create_baseline(root: Path, output: Path) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    permitted = root / ".construction" / "baselines"
    if not output.is_relative_to(permitted) or output == permitted:
        raise ValueError("Baseline output must be a new child of .construction/baselines")
    if output.exists():
        raise FileExistsError("A baseline is immutable; choose a new output directory")
    files = source_files(root)
    output.mkdir(parents=True, exist_ok=False)
    entries: list[dict[str, object]] = []
    archive = output / "source.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            entries.append(
                {
                    "path": relative,
                    "bytes": len(data),
                    "sha256": digest(data),
                    "protected": relative in PROTECTED_INPUTS
                    or relative.startswith("执行/")
                    or relative.startswith("docs/handoffs/"),
                }
            )
            bundle.writestr(f"files/{relative}", data)
        manifest: dict[str, object] = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "source_root": str(root),
            "kind": "source_only_no_runtime_data",
            "git_restore_available": False,
            "restore_test_status": "NOT_RUN",
            "excludes": sorted(EXCLUDED_DIRECTORIES),
            "files": entries,
        }
        serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        bundle.writestr("manifest.json", serialized)
    (output / "manifest.json").write_text(serialized, encoding="utf-8", newline="\n")
    archive_hash = digest(archive.read_bytes())
    (output / "source.zip.sha256").write_text(archive_hash + "  source.zip\n", encoding="ascii")
    return {
        "directory": str(output),
        "file_count": len(entries),
        "archive_sha256": archive_hash,
        "restore_test_status": "NOT_RUN",
    }


def restore_baseline(archive: Path, target: Path) -> int:
    """Restore to an absent directory only, validating every archive member first."""
    archive = archive.resolve(strict=True)
    target = target.resolve()
    if target.exists():
        raise FileExistsError("Recovery never overwrites a directory; use a new target")
    expected = archive.with_suffix(".zip.sha256").read_text(encoding="ascii").split()[0]
    if digest(archive.read_bytes()) != expected:
        raise ValueError("Archive hash does not match the recorded baseline")
    with zipfile.ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        if manifest.get("schema_version") != 1:
            raise ValueError("Unsupported baseline manifest")
        entries = manifest["files"]
        names = [entry["path"] for entry in entries]
        if len(set(name.casefold() for name in names)) != len(names):
            raise ValueError("Duplicate or case-colliding baseline path")
        if set(bundle.namelist()) != {"manifest.json", *(f"files/{name}" for name in names)}:
            raise ValueError("Unexpected archive members")
        if len(bundle.namelist()) != len(names) + 1:
            raise ValueError("Duplicate archive member")
        for entry in entries:
            name = entry["path"]
            if not safe_source_name(name) or not (target / name).resolve().is_relative_to(target):
                raise ValueError("Unsafe or excluded baseline path")
            member = bundle.getinfo(f"files/{name}")
            if stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("Archive links are forbidden")
            if member.file_size != entry["bytes"]:
                raise ValueError("Baseline size mismatch")
            data = bundle.read(member)
            if digest(data) != entry["sha256"]:
                raise ValueError("Baseline content hash mismatch")
        target.mkdir(parents=True, exist_ok=False)
        for entry in entries:
            destination = target / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(bundle.read(f"files/{entry['path']}"))
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--output", type=Path, required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument("--target", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.command == "create":
        print(json.dumps(create_baseline(ROOT, arguments.output), ensure_ascii=False))
    else:
        count = restore_baseline(arguments.archive, arguments.target)
        print(json.dumps({"restored_files": count, "target": str(arguments.target.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
