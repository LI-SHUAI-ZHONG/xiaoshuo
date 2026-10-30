"""Create the immutable local release-candidate artifact manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _image_digest(reference: str) -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker CLI is unavailable")
    result = subprocess.run(  # noqa: S603 - resolved executable and structured argv.
        [docker, "image", "inspect", "--format", "{{.Id}}", reference],
        capture_output=True,
        check=True,
        text=True,
    )
    digest = result.stdout.strip()
    if not digest.startswith("sha256:"):
        raise ValueError(f"image {reference} did not expose a content digest")
    return digest


def build_manifest(
    *, revision: str, version: str, images: tuple[str, ...], created_at: datetime
) -> dict[str, Any]:
    files = (
        ROOT / "uv.lock",
        ROOT / "pnpm-lock.yaml",
        ROOT / "packages" / "api-client" / "openapi.snapshot.json",
    )
    return {
        "schema_version": "accos.release-manifest.v1",
        "version": version,
        "source_revision": revision,
        "created_at": created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "real_provider_calls": False,
        "images": [
            {"content_digest": _image_digest(reference), "reference": reference}
            for reference in images
        ],
        "dependency_manifests": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--image", action="append", default=[])
    arguments = parser.parse_args()
    images = tuple(cast("list[str]", arguments.image))
    if not images:
        parser.error("at least one --image is required")
    manifest = build_manifest(
        revision=arguments.revision,
        version=arguments.version,
        images=images,
        created_at=datetime.now(UTC),
    )
    output = cast("Path", arguments.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps({"output": str(output), "status": "PASS"}, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
