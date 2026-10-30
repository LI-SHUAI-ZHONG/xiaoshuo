"""Materialize every exported historical improvement into a verifiable material ledger.

The six original source files remain immutable.  This command records their
current hashes and maps each historical window to an auditable material-facing
outcome: a normalized view, a runtime contract, pending field evidence, or an
explicit non-material/non-applicable disposition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "historical-improvement-materialization-1.0"
SOURCE_FILES = {
    "资料库": "原始资料/资料库.txt",
    "类型系统": "原始资料/类型系统.txt",
    "类型连接": "原始资料/类型连接.txt",
    "静态网络": "原始资料/静态网络.txt",
    "动态网络": "原始资料/动态网络.txt",
    "锚点网络": "原始资料/锚点网络.txt",
}
OUTPUT_ROOT = Path("文档/证据/历史改进资料化")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _record(number: int, title: str, category: str, targets: list[str], action: str, status: str, evidence: list[str], blocker: str | None = None) -> dict[str, Any]:
    return {
        "history_id": f"{number:03d}",
        "history_window": f"文档/归档/历史恢复与改进/改进方法/Cline聊天记录_2026-08-11至2026-08-27/{number:03d}_*.md",
        "title": title,
        "material_category": category,
        "material_targets": targets,
        "material_improvement": action,
        "status": status,
        "evidence_paths": evidence,
        "raw_source_writeback_allowed": False,
        "formal_fact_eligible": False,
        "blocker": blocker,
    }


def _records() -> list[dict[str, Any]]:
    normalized = ["文档/证据/全量资料治理/全量检查报告.json", "文档/证据/全量资料治理/全量修正账本.jsonl"]
    runtime = ["脚本/执行管道.py", "脚本/资料消费审计.py", "脚本/场景创作激活.py"]
    records = [
        _record(1, "资料库完整盘点与 11 模块分配", "资料索引", ["资料库"], "将全部可解析资料库条目建立为带来源定位的规范化索引；模块分配属于运行路由，不改写资料事实。", "materialized_normalized_view", normalized),
        _record(2, "精确模块重分配", "资料索引", ["资料库"], "保留条目身份并在派生索引中承载模块路由；禁止以名称近似替换资料条目。", "materialized_normalized_view", normalized),
        _record(3, "核心资料镜像", "资料完整性", list(SOURCE_FILES), "以六类主资料哈希快照验证镜像/副本完整性；缺失文件不得用替代文件补齐。", "materialized_hash_snapshot", normalized),
        _record(4, "11 步流程定位", "资料消费合同", list(SOURCE_FILES), "把流程说明与资料运行入口分离，资料改进落点为可执行来源注册与消费合同。", "materialized_runtime_contract", runtime),
        _record(5, "世界设定与静态关系读取", "资料结构化", ["资料库", "静态网络"], "通过规范化视图保留世界设定、静态关系和来源定位，避免将历史模块输出作为资料事实。", "materialized_normalized_view", normalized),
        _record(6, "全资料可运行性与消费审计", "资料治理", list(SOURCE_FILES), "生成六类资料的对象级规范化视图、问题账本和来源哈希；不可解析或缺字段项保持 pending。", "materialized_normalized_view", normalized),
        _record(7, "全量零模型预检", "资料准入", list(SOURCE_FILES), "资料级改进仅准备预检、哈希、唯一性和来源覆盖；项目采用与正文消费保持未启动。", "requires_current_preflight", normalized, "需要当前全量绑定预检的完整可复核运行结果。"),
        _record(8, "字段级融合预览", "资料融合", list(SOURCE_FILES), "建立字段级融合的待证据队列；没有候选字段值、来源与派生规则的映射不得合并。", "pending_field_evidence", ["文档/证据/资料融合版本", *normalized], "历史候选不具备正式字段变更合同。"),
        _record(9, "模型超时与模块 09 进度", "运行资料证据", ["资料库", "动态网络", "锚点网络"], "资料改进落点是 run_id 下逐段来源记录、检查点和错误区分，不把模型/降级结果写入原始资料。", "requires_current_runtime_evidence", runtime, "缺少当前同一 run_id 的完整模块 06-11 证据。"),
        _record(10, "运行目录统一", "运行资料证据", list(SOURCE_FILES), "同一 run_id 的资料快照、场景选择、进度与审校报告必须位于同一运行目录。", "requires_current_runtime_evidence", runtime, "未复核当前端到端运行目录一致性。"),
        _record(11, "确定性锚点补全分支", "资料消费合同", ["锚点网络", "动态网络"], "锚点只能由实际场景条件和来源记录采用，不能以段落序号循环分配。", "requires_current_runtime_evidence", runtime, "未复核当前模块 09 实际执行结果。"),
        _record(12, "章节级质量门", "资料消费合同", ["资料库", "动态网络", "锚点网络"], "段落长度规则不构成资料事实；资料采用必须保留章节级场景条件、来源和语义效果。", "requires_current_runtime_evidence", runtime, "缺少当前章节级消费与质量证据。"),
        _record(13, "资料包驱动章节创作", "资料消费合同", list(SOURCE_FILES), "完整资料到 chapter/scene/beat 的资料包应保留输入哈希、选择理由和段落效果；当前只登记合同，不授权正文。", "requires_current_runtime_evidence", runtime, "未取得逐条双授权与完整消费证据。"),
        _record(14, "步骤八条件化调度", "资料调度", list(SOURCE_FILES), "未触发资料保持 deferred/not_applicable；步骤八只编排前置资料和场景条件，不写正文。", "materialized_runtime_contract", runtime),
        _record(15, "步骤八真实调度验证", "资料调度", list(SOURCE_FILES), "将前置产物、场景调度、正文验证的断层列为可审计合同，防止仅字段存在被误报为资料消费。", "materialized_runtime_contract", runtime),
        _record(16, "生产能力门记录", "资料准入", list(SOURCE_FILES), "保留资料生产能力报告作为运行期风险信号；移除启动阻断不改变资料资格或交付资格。", "materialized_runtime_contract", runtime),
        _record(17, "前置产物到创作的传递", "资料消费合同", list(SOURCE_FILES), "将资料分为继承事实、条件触发规则、表达方法、审校规则和治理信息，未触发资料不强行采用。", "materialized_runtime_contract", runtime),
        _record(18, "角色资料创作可用性审查", "角色资料治理", ["资料库", "动态网络", "静态网络", "锚点网络", "类型系统", "类型连接"], "已纳入原始资料范围与排除规则；具体人物逐维审查必须基于原始定位，不能使用项目草案补写。", "requires_source_review", normalized, "缺少可复核的逐角色原始资料审查报告。"),
        _record(19, "01-08、10-11 资料规则链路", "资料消费合同", list(SOURCE_FILES), "保留资料规则到模块的传递/激活/消费审计边界；历史模块 09 路由动作不作为正文或资料完成证据。", "materialized_runtime_contract", runtime, "端到端模块 06-11 尚未当前复核。"),
        _record(20, "全步骤生产能力审查", "资料准入", list(SOURCE_FILES), "将 input_only/draft_only、人物实体、长线连续性和消费证据缺口保持为资料准入阻断。", "materialized_runtime_contract", runtime, "不存在可证明平台发布或长线生产能力的当前证据。"),
        _record(21, "无项目改进", "不适用", [], "该窗口没有资料读取、资料修改或资料要求，明确登记为不适用。", "not_applicable", []),
        _record(22, "路径恢复与回归核验", "资料完整性", list(SOURCE_FILES), "当前六类资料哈希快照提供存在性基线；历史补丁重放和历史全量回归不以日志文本视为已完成。", "requires_replay_evidence", normalized, "缺少逐日成功回执、状态哈希和 final_state.files。"),
        _record(23, "聊天记录导出", "不适用", [], "聊天记录只作为方法来源；不构成资料改进或资料事实。", "not_applicable", []),
    ]
    return records


def build(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    output = root / OUTPUT_ROOT
    output.mkdir(parents=True, exist_ok=True)
    sources = {}
    for kind, relative in SOURCE_FILES.items():
        path = root / relative
        sources[kind] = {"path": relative, "exists": path.is_file(), "sha256": _sha256(path) if path.is_file() else None, "bytes": path.stat().st_size if path.is_file() else 0}
    records = _records()
    if len(records) != 23 or {row["history_id"] for row in records} != {f"{index:03d}" for index in range(1, 24)}:
        raise ValueError("历史改进记录必须完整覆盖 001 至 023")
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "policy": "原始六类资料不可由历史聊天结论直接覆盖；确定性结构化改进写入证据视图，字段事实写回必须另有哈希锁定的人工批准变更集。",
        "source_snapshots": sources,
        "history_record_count": len(records),
        "status_counts": dict(sorted(Counter(row["status"] for row in records).items())),
        "raw_source_writeback_allowed_count": 0,
        "formal_fact_eligible_count": 0,
        "records": records,
    }
    (output / "历史改进资料化清单.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    (output / "历史改进资料化报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 历史改进资料化执行矩阵", "", "原始六类资料保持不覆盖。每条历史记录均已转换为资料视图、消费合同、待证据项或不适用结论。", "", "| 记录 | 资料目标 | 资料改进状态 | 写回原始资料 | 阻断 |", "|---|---|---|---|---|"]
    for row in records:
        lines.append(f"| {row['history_id']} | {'、'.join(row['material_targets']) or '无'} | {row['status']} | 否 | {row['blocker'] or '无'} |")
    (output / "历史改进资料化执行矩阵.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="将 001-023 历史改进转换为可验证的资料改进矩阵")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = build(args.project_root)
    print(json.dumps({"history_record_count": report["history_record_count"], "status_counts": report["status_counts"], "raw_source_writeback_allowed_count": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())