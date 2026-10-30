"""Verify release-image metadata without starting the images."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any, cast

_SENSITIVE_ENVIRONMENT = ("ACCESS_KEY", "API_KEY", "PASSWORD", "SECRET", "TOKEN")


def _inspect(reference: str) -> dict[str, Any]:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker CLI is unavailable")
    result = subprocess.run(  # noqa: S603 - resolved executable and structured argv.
        [docker, "image", "inspect", reference],
        capture_output=True,
        check=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise ValueError(f"unexpected image inspection result for {reference}")
    return cast("dict[str, Any]", payload[0])


def verify_image(reference: str, *, expected_version: str, expected_revision: str) -> list[str]:
    image = _inspect(reference)
    configuration = cast("dict[str, Any]", image.get("Config") or {})
    user = str(configuration.get("User") or "")
    failures: list[str] = []
    if not user or user.lower() == "root" or user.split(":", maxsplit=1)[0] == "0":
        failures.append(f"{reference}: image user is root or unspecified")
    healthcheck = cast("dict[str, Any]", configuration.get("Healthcheck") or {})
    if not healthcheck.get("Test"):
        failures.append(f"{reference}: health check is missing")
    labels = cast("dict[str, str]", configuration.get("Labels") or {})
    if labels.get("org.opencontainers.image.version") != expected_version:
        failures.append(f"{reference}: version label mismatch")
    if labels.get("org.opencontainers.image.revision") != expected_revision:
        failures.append(f"{reference}: revision label mismatch")
    for item in cast("list[str]", configuration.get("Env") or []):
        name, separator, value = item.partition("=")
        if separator and value and any(marker in name.upper() for marker in _SENSITIVE_ENVIRONMENT):
            failures.append(f"{reference}: sensitive environment value is baked: {name}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("images", nargs="+")
    arguments = parser.parse_args()
    failures = [
        failure
        for image in arguments.images
        for failure in verify_image(
            image,
            expected_version=arguments.version,
            expected_revision=arguments.revision,
        )
    ]
    report = {"failures": failures, "status": "PASS" if not failures else "FAIL"}
    stream = sys.stdout if not failures else sys.stderr
    stream.write(json.dumps(report, sort_keys=True) + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
