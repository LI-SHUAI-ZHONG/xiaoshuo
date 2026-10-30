"""Audit creative material use and quarantine only explicit approvals."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GOVERNANCE_DIR = Path("文档") / "资料治理"
MANIFEST_FILE = "资料用途清单.json"
APPROVAL_FILE = "待隔离资料批准清单.json"
QUARANTINE_DIR = "隔离资料"
CORE_PATHS = {
    "原始资料/资料库.txt", "原始资料/类型系统.txt", "原始资料/锚点网络.txt",
    "网络完整数据/动态连接完整数据.json", "网络完整数据/静态连接完整数据.json",
    "配置/project_config.json", "配置/项目创作圣经.json", "配置/首章场景创作简报.json",
    "配置/项目创作生产政策.json",
    "文档/证据/小说资料选择清单.json", "文档/证据/project_planning.json",
    "文档/证据/资源注册表.json", "文档/证据/全量资料解释词创作绑定.json",
}
HISTORICAL_PREFIXES = ("文档/归档/", "文档/历史/", "文档/废弃/")
CREATIVE_EVIDENCE_NAMES = {"全量资料正文消费证据.json", "全量资料正文生产编排.json", "全量资料正文消费验证报告.json"}
HISTORICAL_CREATIVE_EVIDENCE_NAMES = {"module_08_scene_beat_cards.json", "module_09_scene_prose.json"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _source_paths(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"source_ref", "source_file", "source_path", "prose_location", "scene_source_selection"}:
                if isinstance(child, dict):
                    child = child.get("file") or child.get("path")
                if isinstance(child, str):
                    found.append(re.sub(r":\d+(?:-\d+)?$", "", child.split("#", 1)[0]))
            else:
                found.extend(_source_paths(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_source_paths(child))
    return found


def _creative_evidence(root: Path) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = defaultdict(list)
    candidates = [path for path in root.rglob("*") if path.is_file() and path.name in CREATIVE_EVIDENCE_NAMES]
    for base in (root / "文档" / "归档", root / "文档" / "历史"):
        if base.is_dir():
            candidates.extend(path for path in base.rglob("*") if path.is_file() and (
                path.name in HISTORICAL_CREATIVE_EVIDENCE_NAMES
                or (path.suffix.lower() in {".md", ".jsonl"} and any(token in path.name.lower() for token in ("正文", "scene", "prose", "beat", "消费")))))
    for evidence_file in candidates:
        relative_evidence = _relative(root, evidence_file)
        try:
            text = evidence_file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        payloads: list[Any] = []
        try:
            payloads = [json.loads(text)]
        except json.JSONDecodeError:
            for line in text.splitlines():
                try:
                    payloads.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        for payload in payloads:
            for candidate in _source_paths(payload):
                normalized = candidate.replace("\\", "/").lstrip("./")
                source = (root / normalized).resolve()
                if source.is_file() and root in source.parents:
                    refs[_relative(root, source)].append(f"正文/场景消费证据:{relative_evidence}")
    return refs


def _broken_snapshots(root: Path) -> list[str]:
    planning = _read_json(root / "文档" / "证据" / "project_planning.json", {})
    snapshot = planning.get("source_snapshot", {}) if isinstance(planning, dict) else {}
    broken = []
    for item in snapshot.get("files", []) if isinstance(snapshot, dict) else []:
        relative, expected = item.get("path"), item.get("sha256")
        path = root / relative if relative else None
        if not path or not path.is_file():
            broken.append(f"蓝图快照缺失：{relative}")
        elif _sha256(path) != expected:
            broken.append(f"蓝图快照哈希不匹配：{relative}")
    return broken


def build_manifest(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    governance = root / GOVERNANCE_DIR
    governance_prefix = f"{GOVERNANCE_DIR.as_posix()}/"
    refs = _creative_evidence(root)
    broken = _broken_snapshots(root)
    files = [path for path in root.rglob("*") if path.is_file() and not _relative(root, path).startswith(governance_prefix)]
    rows = []
    for path in sorted(files, key=lambda item: _relative(root, item)):
        relative = _relative(root, path)
        evidence = sorted(set(refs.get(relative, [])))
        historical = any("文档/归档/" in item or "文档/历史/" in item for item in evidence)
        creative_status = "historical_prose_evidence" if evidence and historical else "current_prose_consumed" if evidence else "not_proven"
        if relative in CORE_PATHS:
            category, disposition, status = "当前创作链依赖", "保留：当前创作链输入或授权基线", "current_pipeline_dependency"
        elif evidence:
            category, disposition = "实际创作使用证据关联资料", "保留：存在正文或场景消费证据"
            status = "historical_prose_evidence" if historical else "current_prose_consumed"
        elif relative.startswith(HISTORICAL_PREFIXES):
            category, disposition, status = "历史资料待审计", "不得仅因归档路径自动隔离", "not_proven"
        elif relative.startswith("脚本/"):
            category, disposition, status = "运行或维护工具", "保留：工具文件不是创作使用证据", "not_proven"
        elif relative.startswith(("文档/", "配置/")):
            category, disposition, status = "说明或治理文件", "保留：说明文件不是资料使用证明", "not_proven"
        else:
            category, disposition, status = "未证实用途", "不得因未发现消费证据而自动隔离", "not_proven"
        rows.append({"path": relative, "sha256": _sha256(path), "bytes": path.stat().st_size, "category": category, "creative_use_status": status, "creative_evidence_status": creative_status, "reference_evidence": evidence, "disposition": disposition})
    manifest = {"schema_version": "creative-material-governance-2.0", "generated_at": _now(), "project_root": str(root), "policy": "只有正文消费证据、场景消费证据或当前创作链明确依赖才能证明资料使用；说明文件、脚本、目录名和时间不构成创作使用证据。", "file_count": len(rows), "current_prose_consumed_file_count": sum(row["creative_evidence_status"] == "current_prose_consumed" for row in rows), "historical_prose_evidence_file_count": sum(row["creative_evidence_status"] == "historical_prose_evidence" for row in rows), "broken_dependency_count": len(broken), "broken_dependencies": broken, "files": rows}
    governance.mkdir(parents=True, exist_ok=True)
    (governance / MANIFEST_FILE).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    template = governance / APPROVAL_FILE
    if not template.exists():
        template.write_text(json.dumps({"schema_version": "creative-material-quarantine-approval-1.0", "policy": "仅填写已人工确认不参与当前或未来创作流程的文件。path 与 sha256 必须与资料用途清单完全一致。", "approved_by": "", "approved_at": "", "items": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def apply_approved_quarantine(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    approval = _read_json(root / GOVERNANCE_DIR / APPROVAL_FILE, {})
    if not isinstance(approval, dict) or not str(approval.get("approved_by") or "").strip() or not str(approval.get("approved_at") or "").strip():
        raise ValueError("隔离批准清单必须填写 approved_by、approved_at 和 items")
    moved = []
    for row in approval.get("items", []):
        relative, expected = str(row.get("path") or ""), str(row.get("sha256") or "")
        source = (root / relative).resolve()
        if not relative or source == root or root not in source.parents or not source.is_file():
            raise ValueError(f"隔离来源不存在或非法：{relative}")
        if _sha256(source) != expected:
            raise ValueError(f"隔离来源哈希不匹配：{relative}")
        if relative in CORE_PATHS or relative.startswith("脚本/"):
            raise ValueError(f"核心资料或脚本不得通过本工具隔离：{relative}")
        target = root / QUARANTINE_DIR / datetime.now(timezone.utc).strftime("%Y%m%d") / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        moved.append({"source": relative, "target": _relative(root, target), "sha256": expected})
    result = {"executed_at": _now(), "approved_by": approval["approved_by"], "moved": moved}
    (root / GOVERNANCE_DIR / "隔离执行记录.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="按实际创作消费证据整理资料；默认只生成审计清单")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply-approved-quarantine", action="store_true")
    args = parser.parse_args()
    result = apply_approved_quarantine(args.project_root) if args.apply_approved_quarantine else build_manifest(args.project_root)
    print(json.dumps({"file_count": result.get("file_count"), "current_prose_consumed_file_count": result.get("current_prose_consumed_file_count"), "historical_prose_evidence_file_count": result.get("historical_prose_evidence_file_count"), "broken_dependency_count": result.get("broken_dependency_count"), "moved_count": len(result.get("moved", []))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())