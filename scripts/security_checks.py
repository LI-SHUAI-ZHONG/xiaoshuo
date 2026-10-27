"""Deterministic local security/configuration checks that require no credentials or network."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "infra" / "compose.yaml"
DELIVERY_DOCKERFILES = (
    ROOT / "services" / "core" / "Dockerfile",
    ROOT / "apps" / "studio" / "Dockerfile",
)
_EXACT_PYTHON = re.compile(r"^[A-Za-z0-9_.\[\]-]+==[^\s;]+$")
_EXACT_NODE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
_MAX_UPLOAD_MIB = 10


def _compose_config() -> dict[str, Any]:
    environment_file = ROOT / ".env"
    if not environment_file.is_file():
        environment_file = ROOT / ".env.example"
    docker = shutil.which("docker")
    if docker is None:
        parsed = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("compose configuration must be a mapping")
        return cast("dict[str, Any]", parsed)
    result = subprocess.run(  # noqa: S603 - fixed executable and structured argv.
        [
            docker,
            "compose",
            "--env-file",
            str(environment_file),
            "-f",
            str(COMPOSE),
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise ValueError("rendered compose configuration must be a mapping")
    return cast("dict[str, Any]", parsed)


def _check_compose(configuration: dict[str, Any], failures: list[str]) -> None:
    for name, service in configuration["services"].items():
        image = str(service.get("image", ""))
        if not image or image.endswith(":latest") or ":" not in image.rsplit("/", 1)[-1]:
            failures.append(f"container image is not pinned: {name}")
        security_options = service.get("security_opt", [])
        if "no-new-privileges:true" not in security_options:
            failures.append(f"container lacks no-new-privileges: {name}")
        failures.extend(
            f"container port is not loopback-bound: {name}"
            for port in service.get("ports", [])
            if (
                port.get("host_ip") != "127.0.0.1"
                if isinstance(port, dict)
                else not str(port).startswith("127.0.0.1:")
            )
        )
        if name in {
            "api",
            "migrate",
            "minio-init",
            "postgres-check",
            "redis-check",
            "minio-check",
            "otel-collector",
            "jaeger",
            "prometheus",
            "studio",
            "worker",
        } and not service.get("read_only", False):
            failures.append(f"stateless/tool container root filesystem is writable: {name}")


def _check_delivery_dockerfiles(failures: list[str]) -> None:
    for path in DELIVERY_DOCKERFILES:
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        aliases: set[str] = set()
        external_bases: list[str] = []
        for match in re.finditer(
            r"^FROM\s+(\S+)(?:\s+AS\s+(\S+))?",
            source,
            flags=re.MULTILINE | re.IGNORECASE,
        ):
            base, alias = match.groups()
            if base.lower() not in aliases:
                external_bases.append(base)
            if alias is not None:
                aliases.add(alias.lower())
        if not external_bases or any(
            ":" not in base.rsplit("/", 1)[-1] or base.endswith(":latest")
            for base in external_bases
        ):
            failures.append(f"container base image is not pinned: {relative}")
        if re.search(r"^USER\s+(?:root|0)(?::0)?\s*$", source, flags=re.MULTILINE) or not re.search(
            r"^USER\s+(?!root\b|0(?::0)?\b)\S+", source, flags=re.MULTILINE
        ):
            failures.append(f"delivery image does not declare a non-root user: {relative}")
        if "HEALTHCHECK" not in source:
            failures.append(f"delivery image lacks a health check: {relative}")
        failures.extend(
            f"delivery image lacks {label}: {relative}"
            for label in ("org.opencontainers.image.version", "org.opencontainers.image.revision")
            if label not in source
        )
        if re.search(r"(?i)(?:secret|password|token)\s*=\s*[^$\s\"']+", source):
            failures.append(f"delivery image appears to bake a credential: {relative}")


def _check_dependency_pins(failures: list[str]) -> None:
    for path in (ROOT / "pyproject.toml", ROOT / "services" / "core" / "pyproject.toml"):
        manifest = tomllib.loads(path.read_text(encoding="utf-8"))
        requirements = list(manifest.get("project", {}).get("dependencies", []))
        for group in manifest.get("dependency-groups", {}).values():
            requirements.extend(group)
        if any(_EXACT_PYTHON.fullmatch(str(requirement)) is None for requirement in requirements):
            failures.append(f"Python dependency is not exactly pinned: {path.relative_to(ROOT)}")
    workspace = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    manifests = [workspace]
    manifests.extend(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / "apps").glob("*/package.json")
    )
    manifests.extend(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / "packages").glob("*/package.json")
    )
    for manifest in manifests:
        for section in ("dependencies", "devDependencies"):
            for dependency, version in manifest.get(section, {}).items():
                if str(version).startswith("workspace:"):
                    continue
                if _EXACT_NODE.fullmatch(str(version)) is None:
                    failures.append(f"Node dependency is not exactly pinned: {dependency}")
    uv_lock = ROOT / "uv.lock"
    pnpm_lock = ROOT / "pnpm-lock.yaml"
    if not uv_lock.is_file() or not pnpm_lock.is_file():
        failures.append("dependency lockfile is missing")
    else:
        if "sha256:" not in uv_lock.read_text(encoding="utf-8"):
            failures.append("Python lockfile lacks artifact hashes")
        if "integrity:" not in pnpm_lock.read_text(encoding="utf-8"):
            failures.append("Node lockfile lacks package integrity hashes")


def _check_secret_and_upload_guards(failures: list[str]) -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    if ".env" not in {line.strip() for line in gitignore}:
        failures.append(".env is not ignored")
    compose = COMPOSE.read_text(encoding="utf-8")
    if "replace-with-local" in compose:
        failures.append("compose appears to bake a secret value")
    sensitive_assignment = re.compile(
        r"^\s*(?:[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|ACCESS_KEY|API_KEY)):\s*(.+)$"
    )
    for line in compose.splitlines():
        match_assignment = sensitive_assignment.match(line)
        if match_assignment is not None and "${" not in match_assignment.group(1):
            failures.append("compose contains a literal sensitive environment value")
            break
    assets = (
        ROOT / "services" / "core" / "src" / "accos" / "modules" / "assets" / "application.py"
    ).read_text(encoding="utf-8")
    match = re.search(r"MAX_UPLOAD_BYTES\s*=\s*(\d+)\s*\*\s*1024\s*\*\s*1024", assets)
    if match is None or int(match.group(1)) > _MAX_UPLOAD_MIB:
        failures.append("upload limit is absent or exceeds the 10 MiB baseline")


def main() -> int:
    failures: list[str] = []
    try:
        configuration = _compose_config()
    except (
        OSError,
        ValueError,
        subprocess.SubprocessError,
        yaml.YAMLError,
    ) as error:
        sys.stderr.write(f"security_checks_failed: compose_config: {type(error).__name__}\n")
        return 1
    _check_compose(configuration, failures)
    _check_delivery_dockerfiles(failures)
    _check_dependency_pins(failures)
    _check_secret_and_upload_guards(failures)
    report = {
        "status": "PASS" if not failures else "FAIL",
        "checks": [
            "dependency_pins_and_lockfiles",
            "container_images",
            "container_no_new_privileges",
            "delivery_image_non_root_health_and_labels",
            "stateless_read_only_filesystems",
            "loopback_network_exposure",
            "upload_limit",
            "secret_not_baked",
        ],
        "failures": failures,
    }
    stream = sys.stdout if not failures else sys.stderr
    stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
