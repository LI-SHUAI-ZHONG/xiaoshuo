"""Run the minimal project evidence-to-design pipeline."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=str(Path(__file__).parent))
    args = parser.parse_args()
    project = Path(args.project).resolve()
    config = json.loads((project / "config" / "type_commitment.json").read_text(encoding="utf-8"))
    adoptions = load_jsonl(project / "docs" / "evidence" / "library_adoption.jsonl")
    chains = load_jsonl(project / "docs" / "evidence" / "chain_consumption.jsonl")
    adoption_ids = {item["entry_id"] for item in adoptions if item.get("status") == "adopted"}
    bound_ids = {entry_id for chain in chains for entry_id in chain.get("source_entry_ids", []) if chain.get("status") == "bound"}
    decisions = []
    for task_path in sorted((project / "design_tasks").glob("*.md")):
        text = task_path.read_text(encoding="utf-8")
        task_match = re.search(r"任务ID：([^\r\n]+)", text)
        declared_match = re.search(r"声明使用条目：([^\r\n]+)", text)
        if not task_match or not declared_match:
            raise ValueError(f"Missing task declaration in {task_path}")
        task_id = task_match.group(1).strip()
        declared_ids = [value.strip() for value in declared_match.group(1).split("、")]
        for item in adoptions:
            if item.get("entry_id") in declared_ids and item.get("status") == "adopted":
                decisions.append({
                    "project_id": config["project_id"],
                    "task_id": task_id,
                    "entry_id": item["entry_id"],
                    "decision": item["influenced_decision"][0],
                    "confidence": item["confidence"],
                    "source_ref": item["source_ref"],
                    "chain_bound": item["entry_id"] in bound_ids,
                })
    if not decisions:
        raise ValueError("No adopted design decisions found")
    output = project / config["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        for decision in decisions:
            stream.write(json.dumps(decision, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"status": "PASS", "project_id": config["project_id"], "adopted_records": len(adoptions), "bound_chains": len(chains), "design_decisions": len(decisions), "output": output.relative_to(project).as_posix()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())