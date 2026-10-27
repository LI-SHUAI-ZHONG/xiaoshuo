"""Synchronize binding permission projections from the audited authorization ledger."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from 全量资料输入与正文授权 import authorized_bindings


BINDINGS_FILE = "全量资料解释词创作绑定.json"


def sync(root: str | Path) -> dict[str, int]:
    root = Path(root).expanduser().resolve()
    path = root / "文档" / "证据" / BINDINGS_FILE
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict) or not isinstance(document.get("records"), list):
        raise ValueError("全量资料解释词创作绑定缺失或无法解析")
    records = document["records"]
    if not all(isinstance(row, dict) for row in records):
        raise ValueError("全量资料解释词创作绑定包含非对象记录")
    grants = authorized_bindings(root, records)
    changed = 0
    for row in records:
        grant = grants.get(row.get("binding_id"))
        eligible = bool(grant and grant.get("model_input_eligible") is True)
        prose_allowed = bool(grant and grant.get("prose_write_allowed") is True)
        if row.get("model_input_eligible") != eligible or row.get("prose_write_allowed") != prose_allowed:
            changed += 1
        row["model_input_eligible"] = eligible
        row["prose_write_allowed"] = prose_allowed
        if grant:
            row["use_authorization"] = grant
        else:
            row.pop("use_authorization", None)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"binding_count": len(records), "authorized_binding_count": len(grants), "changed_count": changed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    print(json.dumps(sync(parser.parse_args().project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())