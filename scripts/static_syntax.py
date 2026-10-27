"""Parse Python/JSON/TOML source without importing or executing project code."""

from __future__ import annotations

import ast
import json
import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {"node_modules", ".next", "__pycache__", ".venv", "dist", "build"}


def main() -> int:
    count = 0
    errors: list[str] = []
    for base in (ROOT / "services" / "core", ROOT / "scripts"):
        for directory, subdirs, files in os.walk(base):
            subdirs[:] = [name for name in subdirs if name not in IGNORED]
            for name in files:
                path = Path(directory) / name
                if path.suffix not in {".py", ".json", ".toml"}:
                    continue
                try:
                    content = path.read_text(encoding="utf-8-sig")
                    if path.suffix == ".py":
                        ast.parse(content, filename=str(path.relative_to(ROOT)))
                    elif path.suffix == ".json":
                        json.loads(content)
                    else:
                        tomllib.loads(content)
                    count += 1
                except (SyntaxError, ValueError, UnicodeError) as error:
                    errors.append(f"{path.relative_to(ROOT)}: {error}")
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    print(f"Parsed {count} source files. No project code or tests were executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
