"""Audit absorbed material snapshots without writing any original file."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGETS = ("资料库.txt", "静态网络.txt", "动态网络.txt", "锚点网络.txt", "类型系统.txt", "类型连接.txt")
POLLUTION = (
    "源文件", "生成时间", "条目总数", "source_file", "source_refs", "sha256", "upgrade_id",
    "binding_id", "status", "permitted_use", "prose_write_allowed", "```", "好。懂了",
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig", errors="replace").splitlines()


def audit_pair(original: Path, snapshot: Path) -> dict[str, Any]:
    base = lines(original)
    candidate = lines(snapshot)
    base_counts = Counter(base)
    additions: list[str] = []
    remaining = base_counts.copy()
    for line in candidate:
        if remaining[line]:
            remaining[line] -= 1
        else:
            additions.append(line)
    nonempty = [line for line in additions if line.strip()]
    pollution_hits = Counter(marker for marker in POLLUTION if any(marker in line for line in nonempty))
    rule_like = [line for line in nonempty if re.search(r"定义|条件|指令|约束|依赖|关联|判定|修正|调用|规则", line)]
    return {
        "original": str(original),
        "snapshot": str(snapshot),
        "original_sha256": digest(original),
        "snapshot_sha256": digest(snapshot),
        "original_lines": len(base),
        "snapshot_lines": len(candidate),
        "estimated_added_lines": len(nonempty),
        "estimated_added_rule_like_lines": len(rule_like),
        "pollution_markers": dict(pollution_hits),
        "sample_added_lines": nonempty[:30],
        "snapshot_safe_for_direct_writeback": False,
    }


def run(root: str | Path, run_id: str) -> dict[str, Any]:
    project = Path(root).resolve()
    output = project / "文档" / "合并升级" / run_id
    if output.exists() or Path(run_id).name != run_id:
        raise ValueError("run_id 非法或输出目录已存在")
    output.mkdir(parents=True)
    original_root = project / "原始资料"
    snapshot_roots = {
        "raw_transfer": project / "文档" / "合并升级" / "raw-material-transfer-20260818T051048Z" / "原始资料",
        "classified_transfer": project / "文档" / "合并升级" / "classified-upgrade-transfer-20260818T052359Z" / "原始资料",
        "absorbed": project / "文档" / "合并升级" / "material-absorption-20260818T054129Z" / "当前资料备份",
    }
    reports = []
    for kind, snapshot_root in snapshot_roots.items():
        for target in TARGETS:
            original = original_root / target
            snapshot = snapshot_root / target
            if original.exists() and snapshot.exists():
                report = audit_pair(original, snapshot)
                report["snapshot_kind"] = kind
                reports.append(report)
                (output / f"{kind}-{target}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "six-primary-material-snapshot-diff-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "review_only": True,
        "original_sources_modified": False,
        "report_count": len(reports),
        "reports": [f"{row['snapshot_kind']}-{Path(row['snapshot']).name}.json" for row in reports],
        "polluted_snapshot_count": sum(bool(row["pollution_markers"]) for row in reports),
        "direct_writeback_allowed": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="审查六主资料吸收快照与当前原版的差异")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.project_root, args.run_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())