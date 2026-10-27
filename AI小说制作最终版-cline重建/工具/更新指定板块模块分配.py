# -*- coding: utf-8 -*-
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "docs" / "library_index.jsonl"

module_by_prefix = {
    "137": "11",
    "138": "05",
    "155.1": "07",
    "155.2": "05",
    "155.3": "07",
    "156.1": "09",
    "156.2": "09",
    "156.3": "09",
    "156.4": "09",
    "156.5": "09",
    "157.1": "10",
    "157.2": "07",
    "158.1": "06",
    "158.2": "06",
    "158.3": "06",
    "159.1": "09",
    "159.2": "09",
    "159.3": "09",
    "160.1": "06",
    "160.2": "06",
    "161.1": "09",
    "161.2": "09",
    "162.1": "11",
    "162.2": "10",
}

records = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
changes = []
matched = set()
for record in records:
    prefix = record["entry_id"].split("_", 1)[0]
    if prefix not in module_by_prefix:
        continue
    new_module = module_by_prefix[prefix]
    old_module = record.get("assigned_to_module")
    record["assigned_to_module"] = new_module
    matched.add(prefix)
    changes.append({"entry_id": record["entry_id"], "old": old_module, "new": new_module})

missing = sorted(set(module_by_prefix) - matched)
path.write_text(
    "\n".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records) + "\n",
    encoding="utf-8",
)
print(json.dumps({"total_records": len(records), "modified_count": len(changes), "missing_prefixes": missing, "changes": changes}, ensure_ascii=False, indent=2))