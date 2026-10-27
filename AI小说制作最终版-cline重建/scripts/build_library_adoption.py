"""Build entry-level adoption records for capability-library entries 1-10."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(r"D:\AI小说制作最终版-cline重建")
INDEX = ROOT / "docs" / "library_index.jsonl"
OUTPUT = ROOT / "docs" / "library_adoption.jsonl"
EVIDENCE_ROOTS = (
    ROOT / "04_综合设计",
    ROOT / "05_正文",
    ROOT / "06_测试验证",
)
RETROSPECTIVE_MARKERS = (
    "retrospective_reconstruction",
    "retrospective_regression_manifest",
)


def load_index() -> list[dict]:
    entries: list[dict] = []
    with INDEX.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {INDEX}:{line_number}") from exc
            match = re.match(r"^(\d+)\.", entry.get("entry_id", ""))
            if match and 1 <= int(match.group(1)) <= 10:
                entries.append(entry)
    return entries


def evidence_files() -> list[Path]:
    files: list[Path] = []
    for root in EVIDENCE_ROOTS:
        if root.exists():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}
            )
    return sorted(files)


def adopted_evidence(entry_id: str, paths: list[Path]) -> list[dict]:
    evidence: list[dict] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if entry_id not in text:
            continue
        if any(marker in text for marker in RETROSPECTIVE_MARKERS):
            continue
        evidence.append({"path": path.relative_to(ROOT).as_posix()})
    return evidence


def main() -> None:
    entries = load_index()
    paths = evidence_files()
    records: list[dict] = []
    for entry in entries:
        entry_id = entry["entry_id"]
        evidence = adopted_evidence(entry_id, paths)
        records.append(
            {
                "entry_id": entry_id,
                "status": "adopted" if evidence else "not_adopted",
                "evidence": evidence,
                "reason": (
                    "在综合设计或章节计划中发现精确条目级证据。"
                    if evidence
                    else "未发现综合设计或章节计划中的精确条目级采用证据。"
                ),
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    not_adopted = [record["entry_id"] for record in records if record["status"] == "not_adopted"]
    adopted_count = len(records) - len(not_adopted)
    print(f"01-10 板块总条目数：{len(records)}")
    print(f"已采用条目数：{adopted_count}")
    print(f"未采用条目数：{len(not_adopted)}")
    print("未采用条目编号列表：" + ("、".join(not_adopted) if not_adopted else "无"))


if __name__ == "__main__":
    main()