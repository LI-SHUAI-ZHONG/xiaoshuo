"""Bind the 28-H/I gate outcomes to one current execution run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from 运行清单复核 import register_artifact, verify_manifest


def _read(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default
    return value


def build(project_root: str | Path, run_id: str) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    evidence = root / "文档" / "证据"
    run_dir = evidence / "运行" / run_id
    manifest = _read(run_dir / "run_manifest.json", {})
    planning = _read(evidence / "三章金样本" / "三章金样本验证报告.json", {})
    literary = _read(run_dir / "文学审校.json", _read(evidence / "全量资料文学审校报告.json", {}))
    blockers = [
        "当前运行未完成模块 09-11，不能证明正文消费、文学审校或正式交付",
        "当前项目配置 target_chapter_count 不足以证明长篇连续生产",
        "三章规划门属于 draft_only，不是文学质量或发布许可",
    ]
    if manifest.get("run_status") != "passed":
        blockers.insert(0, f"当前运行终态为 {manifest.get('run_status') or 'unknown'}，退出码 {manifest.get('exit_code')}")
    report = {
        "schema_version": "28hi-current-run-acceptance-1.0",
        "run_id": run_id,
        "project_id": _read(root / "配置" / "project_config.json", {}).get("project_id"),
        "run_status": manifest.get("run_status"),
        "h_recovery": {
            "status": "passed" if (run_dir / "run_failure.json").is_file() and manifest.get("run_status") == "failed" else "pending",
            "failure_receipt": str((run_dir / "run_failure.json").relative_to(root)).replace("\\", "/") if (run_dir / "run_failure.json").is_file() else "",
        },
        "i_long_line_quality": {
            "three_chapter_planning_status": planning.get("status", "missing"),
            "literary_review_status": literary.get("status", "literary_review_pending") if isinstance(literary, dict) else "literary_review_pending",
            "delivery_status": "release_blocked",
            "draft_only": True,
            "blockers": blockers,
        },
        "delivery_ready": False,
        "formal_release_allowed": False,
    }
    output = run_dir / "28HI当前运行验收.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The report is successfully persisted even though its business decision is
    # blocked. Keep storage integrity separate from delivery eligibility.
    register_artifact(root, run_id, output, kind="delivery_report", module_id="28HI", status="success", exit_code=0)
    report["manifest_audit"] = verify_manifest(root, run_id)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    report = build(args.project_root, args.run_id)
    print(json.dumps(report, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())