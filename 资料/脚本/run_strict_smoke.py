"""Run the strict smoke profile through the authoritative execution pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from 执行管道 import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--project-id")
    parser.add_argument("--genres", nargs="+")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    results = run_pipeline(
        project_root=args.project_root,
        project_id=args.project_id,
        genres=args.genres,
        run_id=args.run_id,
    )
    print(json.dumps(results, ensure_ascii=False))
    return 0 if results and all(row.get("status") == "success" for row in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())