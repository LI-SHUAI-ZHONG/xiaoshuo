"""Audit Cline sessions overlapping 2026-08-20 through 2026-08-27.

The audit is read-only with respect to Cline storage. It records evidence
levels instead of treating assistant plans as completed repository changes.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SESSIONS = Path(r"C:\Users\li\.cline\data\sessions")
DEFAULT_START = "2026-08-20T00:00:00+00:00"
DEFAULT_END = "2026-08-28T00:00:00+00:00"
OUTPUT_JSON = Path("文档") / "证据" / "历史会话核对_20260820_20260827.json"
OUTPUT_MD = Path("文档") / "证据" / "历史会话核对_20260820_20260827.md"
SIGNALS = {
    "proposed": ("计划", "目标", "要求", "方案", "准备", "应当"),
    "written": ("已修改", "已写入", "已修复", "补丁已", "修改内容", "文件已"),
    "tested": ("测试通过", "回归通过", "py_compile 通过", "tests", "Ran ", "验证结果"),
    "rejected": ("禁止", "不应", "被否定", "拒绝", "不能作为", "不再使用"),
    "unverified": ("未验证", "无法确认", "未完成", "不能声称", "命令中断", "终端未返回"),
}
PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/][^\"\n<>|]*|(?:脚本|配置|文档|原始资料|网络完整数据|正文|docs)[\\/][^\"\n<>|]+)")
KEYWORDS = ("资料", "执行管道", "创作", "类型", "场景", "正文", "质量", "人物", "动态网络", "静态网络", "锚点", "高质量", "完整")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(content_text(item) for item in content)
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    return ""


def session_texts(document: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    users: list[str] = []
    assistant: list[str] = []
    tool_inputs: list[str] = []
    for message in document.get("messages", []):
        if not isinstance(message, dict):
            continue
        if message.get("role") == "user":
            value = content_text(message.get("content")).strip()
            if value:
                users.append(value)
        elif message.get("role") == "assistant":
            value = content_text(message.get("content")).strip()
            if value:
                assistant.append(value)
            for item in message.get("content", []):
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_inputs.append(json.dumps(item.get("input", {}), ensure_ascii=False))
    return users, assistant, tool_inputs


def classify(text: str) -> list[str]:
    result = []
    for label, words in SIGNALS.items():
        if any(word.lower() in text.lower() for word in words):
            result.append(label)
    return result or ["unverified"]


def snippet(value: str, limit: int = 700) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit] + ("…" if len(value) > limit else "")


def paths_from(values: list[str]) -> list[str]:
    found: set[str] = set()
    for value in values:
        for match in PATH_RE.findall(value):
            normalized = match.replace("\\", "/").rstrip(".,;:")
            if any(token in normalized for token in ("小说", "原始资料", "执行管道", "配置", "文档", "正文", "脚本")):
                found.add(normalized)
    return sorted(found)[:80]


def audit(sessions_root: str | Path, project_root: str | Path) -> dict[str, Any]:
    root = Path(sessions_root).expanduser().resolve()
    project = Path(project_root).expanduser().resolve()
    start = parse_time(DEFAULT_START)
    end = parse_time(DEFAULT_END)
    if start is None or end is None:
        raise ValueError("历史核对日期边界无效")
    rows: list[dict[str, Any]] = []
    for metadata_path in sorted(root.glob("*/*.json")):
        if metadata_path.name.endswith(".messages.json") or metadata_path.name.endswith(".compaction.json"):
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(metadata, dict):
            continue
        started = parse_time(metadata.get("started_at"))
        ended = parse_time(metadata.get("ended_at")) or started
        if started is None or ended is None or ended < start or started >= end:
            continue
        messages_path = Path(str(metadata.get("messages_path") or metadata_path.with_name(metadata_path.stem + ".messages.json")))
        if not messages_path.is_file():
            messages_path = metadata_path.parent / f"{metadata.get('session_id', metadata_path.stem)}.messages.json"
        users: list[str] = []
        assistant: list[str] = []
        tool_inputs: list[str] = []
        if messages_path.is_file():
            try:
                document = json.loads(messages_path.read_text(encoding="utf-8-sig"))
                users, assistant, tool_inputs = session_texts(document)
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass
        all_text = "\n".join(users + assistant + tool_inputs)
        relevant = any(word in all_text for word in KEYWORDS)
        if not relevant:
            continue
        categories = sorted(set(classify("\n".join(assistant[-8:] + users))))
        rows.append({
            "session_id": metadata.get("session_id") or metadata_path.parent.name,
            "started_at": metadata.get("started_at"),
            "ended_at": metadata.get("ended_at"),
            "status": metadata.get("status"),
            "exit_code": metadata.get("exit_code"),
            "overlap_days": sorted({item[:10] for item in (metadata.get("started_at", ""), metadata.get("ended_at", "")) if isinstance(item, str)}),
            "prompt": snippet(str(metadata.get("prompt") or ""), 900),
            "message_file": str(messages_path),
            "user_request_snippets": [snippet(item, 900) for item in users[:4]],
            "final_assistant_snippets": [snippet(item, 900) for item in assistant[-4:]],
            "evidence_categories": categories,
            "referenced_paths": paths_from(tool_inputs + users + assistant),
            "tool_use_count": len(tool_inputs),
            "message_count": len(users) + len(assistant),
        })
    rows.sort(key=lambda row: (str(row.get("started_at")), str(row.get("session_id"))))
    category_counts = Counter(category for row in rows for category in row["evidence_categories"])
    current_files = {
        "pipeline": (project / "脚本" / "执行管道.py").is_file(),
        "raw_source_count": sum((project / "原始资料" / name).is_file() for name in ("资料库.txt", "类型系统.txt", "类型连接.txt", "静态网络.txt", "动态网络.txt", "锚点网络.txt")),
        "current_project_config": (project / "配置" / "project_config.json").is_file(),
    }
    report = {
        "schema_version": "cline-history-material-audit-1.0",
        "window": {"start": DEFAULT_START, "end_exclusive": DEFAULT_END, "meaning": "覆盖 8 月 20 日至 27 日，包含首尾日期"},
        "sessions_root": str(root),
        "project_root": str(project),
        "selection_rule": "按会话 started_at/ended_at 与日期窗口相交筛选；文件名和修改时间不作为主依据。",
        "evidence_policy": "用户要求和助手计划只能标为 proposed；只有消息中的实际写入/命令结果/测试证据才可分别标为 written/tested；含未验证或失败描述的结论保留 unverified。",
        "session_count": len(rows),
        "category_counts": dict(sorted(category_counts.items())),
        "current_repository_snapshot": current_files,
        "sessions": rows,
        "historical_conclusions": [
            {"status": "adopted", "claim": "步骤 08 应按当前剧情条件和上游产物调度，不按 scene index、固定 profile 或 round-robin 绑定资料。", "sources": ["1787205053922_24344", "1787206948361_7sgdd", "1787211376420_wzidl"]},
            {"status": "adopted", "claim": "步骤 09 只能消费步骤 08 的 action_chain/node_contracts；步骤 10 只能检查实际采用资料的正文证据。", "sources": ["1787205053922_24344", "1787206948361_7sgdd", "1787399544817_5ptkw"]},
            {"status": "adopted", "claim": "角色原始资料必须区分已证实、难转写、冲突、未确认和不适用，不能用项目草案反推原始人物事实。", "sources": ["1787386869425_spbiw"]},
            {"status": "adopted", "claim": "系统具备资料与质量门框架，但单章、draft_only、缺少作者确认和真实正文消费证据时，不能宣称可稳定产出高质量长篇或正式发布。", "sources": ["1787700079073_0693x", "1787399544817_5ptkw", "1787813355286_skwkp"]},
            {"status": "unverified", "claim": "任何完整管道成功、全量资料已进入正文或商业化质量达标的说法，必须以同一 run_id 的实际产物、正文证据、质量报告和发布批准重新证明。", "sources": ["1787206948361_7sgdd", "1787399544817_5ptkw", "1787700079073_0693x"]},
        ],
    }
    return report


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Cline 历史会话资料核对",
        "",
        f"窗口：{report['window']['start']} 至 2026-08-27（结束边界 {report['window']['end_exclusive']}）",
        f"相关会话：{report['session_count']} 个",
        "",
        "## 证据规则",
        "",
        report["evidence_policy"],
        "",
        "## 历史结论",
        "",
    ]
    for item in report["historical_conclusions"]:
        lines.append(f"- **{item['status']}**：{item['claim']}（会话：{', '.join(item['sources'])}）")
    lines.extend(["", "## 会话清单", "", "| 会话 | 开始 | 结束 | 状态 | 证据分类 |", "|---|---|---|---|---|"])
    for row in report["sessions"]:
        lines.append(f"| `{row['session_id']}` | {row['started_at']} | {row['ended_at']} | {row['status']} | {', '.join(row['evidence_categories'])} |")
    lines.extend(["", "## 当前仓库核对", "", f"- 执行管道存在：`{report['current_repository_snapshot']['pipeline']}`", f"- 六大原始资料存在数量：`{report['current_repository_snapshot']['raw_source_count']}/6`", f"- 当前项目配置存在：`{report['current_repository_snapshot']['current_project_config']}`", "- 详细会话摘要、用户要求片段、最终结论片段和引用路径见同名 JSON 报告。", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="只读核对指定日期范围内的 Cline 历史会话")
    parser.add_argument("--sessions-root", default=DEFAULT_SESSIONS)
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    report = audit(args.sessions_root, args.project_root)
    project = Path(args.project_root).expanduser().resolve()
    json_path = project / OUTPUT_JSON
    md_path = project / OUTPUT_MD
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": "completed", "session_count": report["session_count"], "category_counts": report["category_counts"], "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
