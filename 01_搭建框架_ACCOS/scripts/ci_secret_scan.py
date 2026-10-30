"""Small deterministic secret scan used before network-backed CI scanners."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT = Path(__file__).resolve().parents[1]
MAX_SCANNED_FILE_BYTES = 5_000_000
SKIPPED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "infra/.data",
        "node_modules",
    }
)
PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "openai_api_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "private_key": re.compile(r"-----BEGIN " + r"(?:EC |OPENSSH |PGP |RSA )?PRIVATE KEY-----"),
}


def _tracked_files() -> tuple[Path, ...]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required for the repository secret scan")
    result = subprocess.run(  # noqa: S603 - resolved executable and structured argv.
        [git, "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    return tuple(ROOT / line for line in result.stdout.splitlines() if line)


def _is_skipped(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return any(relative == part or relative.startswith(f"{part}/") for part in SKIPPED_PARTS)


def scan(paths: Iterable[Path]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in paths:
        if not path.is_file() or _is_skipped(path) or path.stat().st_size > MAX_SCANNED_FILE_BYTES:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(source.splitlines(), start=1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        {
                            "kind": name,
                            "line": line_number,
                            "path": path.relative_to(ROOT).as_posix(),
                        }
                    )
    return findings


def main() -> int:
    findings = scan(_tracked_files())
    report = {"findings": findings, "status": "PASS" if not findings else "FAIL"}
    stream = sys.stdout if not findings else sys.stderr
    stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
