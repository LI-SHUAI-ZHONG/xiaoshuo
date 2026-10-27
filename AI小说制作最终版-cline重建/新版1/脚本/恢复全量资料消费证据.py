"""Restore current model candidate evidence from archived records and batch prose."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


PREFIX = "RPL-20260814-01"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [value for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip() and isinstance(value := json.loads(line), dict)]


def _paragraphs(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.replace("\\n", "\n").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def restore(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    plan = _read_json(evidence / "全量资料正文生产编排.json", {})
    archive = {
        row["consumption_id"]: row
        for row in _jsonl(evidence / "全量资料升级档案.jsonl")
        if str(row.get("consumption_id", "")).startswith(PREFIX)
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in plan.get("records", []):
        if isinstance(row, dict) and row.get("consumption_id") in archive:
            grouped[str(row["batch_id"])].append(row)
    records: list[dict[str, Any]] = []
    output = root / "正文" / "全量资料升级" / "批次"
    for batch_id, rows in grouped.items():
        prose_path = output / f"{batch_id}.md"
        paragraphs = _paragraphs(prose_path)
        if len(paragraphs) != len(rows):
            raise ValueError(f"{batch_id} 段落数量与已审计档案不一致：正文={len(paragraphs)}，档案={len(rows)}")
        lines = [f"# 全量资料自动升级 {batch_id}", ""]
        prose_file = prose_path.relative_to(root).as_posix()
        for index, (row, paragraph) in enumerate(zip(rows, paragraphs)):
            upgrade = archive[row["consumption_id"]]["upgrade"]
            records.append({
                "consumption_id": row["consumption_id"], "binding_id": row["binding_id"], "source_id": row["source_id"], "scene_id": row["scene_id"],
                "prose_file": prose_file, "prose_location": f"{prose_file}#lines[{len(lines) + 1}]", "paragraph": paragraph,
                "paragraph_sha256": hashlib.sha256(paragraph.encode("utf-8")).hexdigest(),
                "quality_status": "automatic_draft_requires_semantic_editorial_review", "literary_review_status": "pending_human_literary_review",
                "generation": {"provider": "ollama", "model": "qwen2.5:7b", "generation_strategy": "four_stage_model_prose_recovered_from_archive"},
                "trigger": upgrade["applied_trigger"], "action": upgrade["applied_action"],
                "observable_result": upgrade["applied_result"], "cost_or_change": upgrade["applied_cost_or_change"],
                "semantic_support": "将来源语义转化为异常、具体行动、可观察变化与持续代价。",
            })
            lines.extend([paragraph, ""])
        prose_path.write_text("\n".join(lines), encoding="utf-8")
    document = {
        "schema_version": "full-source-prose-consumption-evidence-1.1", "records": records,
        "generated_batches": sorted(grouped),
        "generation_policy": "从已审计升级档案与已写入批次正文恢复的模型候选；未经语义和文学审校，不得标记为正文已实现。",
    }
    (evidence / "全量资料正文消费证据.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"restored_count": len(records), "batches": sorted(grouped)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.project_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())