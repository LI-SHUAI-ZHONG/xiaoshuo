"""Compile common wire schemas without loading the app, settings, ORM or adapters."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "core" / "src"))

from pydantic.json_schema import models_json_schema  # noqa: E402

from accos.kernel.shared_contracts import CONTRACT_VERSION, SHARED_CONTRACTS  # noqa: E402


def main() -> int:
    _, definitions = models_json_schema(
        [(model, "validation") for model in SHARED_CONTRACTS],
        ref_template="#/components/schemas/{model}",
    )
    document = {
        "openapi": "3.1.0",
        "info": {
            "title": "ACCOS shared value contracts (not implemented HTTP endpoints)",
            "version": CONTRACT_VERSION,
        },
        "paths": {},
        "components": {"schemas": definitions["$defs"]},
    }
    target = ROOT / "packages" / "api-client" / "shared-contracts.json"
    target.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("Generated shared value schemas; no application or test was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
