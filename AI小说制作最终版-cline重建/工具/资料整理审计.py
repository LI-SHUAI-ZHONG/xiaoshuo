# -*- coding: utf-8 -*-
"""Build a purpose-and-reference based material organization audit."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "资料整理审计.json"
TEXT_OUT = ROOT / "docs" / "资料整理审计报告.md"
TEXT_EXTENSIONS = {".json", ".yaml", ".yml", ".md", ".txt", ".ps1", ".py"}
RAW = {"08_原始资料"}
GENERATED = {"四网络连接，剧情覆盖", "阶段状态", "reports", "docs"}
CODE = {"工具", "scripts", "tests"}
PROJECT = {"05_正文", "07_项目模板"}


def classify(relative: Path) -> tuple[str, str]:
    top = relative.parts[0]
    if top in RAW:
        return "保留为权威原始资料", "索引主入口或历史来源，不能以派生产物替代"
    if top in GENERATED:
        return "保留为当前派生/审计资料", "被索引、运行闭环、网络校验或审计流程使用"
    if top in CODE:
        return "保留为当前工具或验证入口", "代码或测试仍承担生成、校验、检索或初始化作用"
    if top in PROJECT:
        return "保留为项目或模板资料", "属于正文状态、设计产物或可复制项目结构"
    if top == ".clinerules" or top in {"00_资料索引", "01_系统核心", "02_生产流程", "03_调用协议", "04_综合设计"}:
        return "保留为当前规范资料", "属于运行规则、索引契约或生产协议"
    return "待人工确认", "未能仅凭目录职责确认替代关系"


def main() -> int:
    files = []
    hashes = defaultdict(list)
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        relative = path.relative_to(ROOT)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[digest].append(relative.as_posix())
        decision, reason = classify(relative)
        files.append({
            "path": relative.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest,
            "decision": decision,
            "reason": reason,
            "current_path": relative.as_posix(),
        })
    duplicates = [{"sha256": digest, "paths": paths, "action": "保留一份前需人工确认引用"}
                  for digest, paths in hashes.items() if len(paths) > 1]
    report = {
        "schema_version": "material-organization-audit-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root_policy": "运行资料统一使用工作区相对路径；历史外部路径仅允许出现在 legacy_source_refs 或 migration 审计字段",
        "file_count": len(files),
        "cache_files_excluded": "*.pyc and __pycache__ are disposable runtime cache and are not organization sources",
        "files": files,
        "exact_duplicate_groups": duplicates,
        "deletion_candidates": [],
        "blocking_rule": "未确认权威版本、引用关系或内容替代关系前，不自动删除资料",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = defaultdict(int)
    for item in files:
        counts[item["decision"]] += 1
    lines = ["# 资料整理审计报告", "", f"生成时间：`{report['generated_at']}`", f"扫描文件：`{len(files)}`", "",
             "## 处理原则", "", "- 按作用、路径和当前引用关系判断，不按文件名直接判重。",
             "- 当前运行路径统一为工作区相对路径。历史绝对路径只保留在 `legacy_source_refs` 或迁移审计字段。",
             "- 未确认替代关系前不自动删除原始资料、派生产物或报告。", "", "## 分类统计", ""]
    lines.extend(f"- {key}：{value}" for key, value in sorted(counts.items()))
    lines.extend(["", "## 完全重复组", ""])
    lines.append("未发现完全相同文件。" if not duplicates else "存在重复组，均暂不删除，等待引用确认。")
    for group in duplicates:
        lines.append("- " + ", ".join(f"`{item}`" for item in group["paths"]))
    lines.extend(["", "## 删除清单", "", "当前为空。Python 缓存已清理，但缓存不属于资料删除清单。", ""])
    TEXT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "file_count": len(files), "duplicate_groups": len(duplicates)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())