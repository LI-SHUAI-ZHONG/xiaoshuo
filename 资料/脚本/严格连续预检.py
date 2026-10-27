"""Emit a machine-readable preflight for strict continuous upgrades."""
from __future__ import annotations

import json
from pathlib import Path

import 严格全量资料模型升级 as strict
import 严格全量资料连续编排 as continuous


ROOT = Path(r"D:\小说")
PARENT = "20260816T161500Z-strict-micro-retry-02"


def main() -> int:
    bindings = continuous.load_bindings(ROOT)
    completed = strict.chain_records(ROOT, PARENT)
    pending = continuous.pending_indexes(bindings, completed)
    start, count = continuous.next_window(pending, 10)
    print(json.dumps({
        "baseline": len(bindings),
        "completed": len(completed),
        "next_window": {"start": start, "count": count},
        "first_pending_id": bindings[start]["binding_id"],
        "formal_fact_eligible": False,
        "prose_write_allowed": False,
        "formal_release_allowed": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())