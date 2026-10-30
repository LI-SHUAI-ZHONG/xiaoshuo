"""Build and validate the source-bounded golden three-chapter planning sample.

This gate deliberately creates planning evidence only.  It never edits prose,
and it refuses to represent draft-usable or candidate material as confirmed
story fact.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHAPTER_BLUEPRINTS = (
    {
        "chapter_id": "1",
        "title": "第七码",
        "progression": "发现异常",
        "chapter_goal": "确认第七息回亮不是自身修炼误差，并取得能复核的旧域指向。",
        "obstacle": "检测与档案制度会把异常归为误差，公开追问将危及沈砚和协助者的晋升资格。",
        "choice": "沈砚放弃当场争辩，以掌心节拍、缺页与禁线反应保存可复核证据，并用内门木牌打开旧域缝隙。",
        "consequence": "晋升资格作废；许照微因协助被记过；陆昭与沈砚的信任出现裂口。",
        "state_change": "从怀疑异常到确认镇潮阵正在向旧域输送灵息。",
        "chapter_state_before": "仅怀疑检测异常，尚无可复核的阵法指向。",
        "chapter_state_after": "确认镇潮阵向旧域输送灵息，并失去正常申诉资格。",
        "progression_target": "把个人怀疑推进为可复核的阵法异常。",
        "irreversible_change": "晋升资格作废，沈砚只能在规则外追查。",
        "suspense_handoff": "父亲节拍打开的旧域缝隙中究竟回应着谁？",
        "information_units": ["第七息与镇潮阵同步", "缺页刻痕指向旧域", "禁线吸收灵息"],
        "next_action_interface": "带着父亲留下的节拍进入旧域，查明回响对应的人与阵眼。",
        "scenes": (
            ("1-S1", "检测场", "完成检测并辨明异常来源", "异常会被直接记为修行不稳", "第七息回亮且指向旧域", "保留节拍和刻痕方向", "放弃复测，线索只能私下追查"),
            ("1-S2", "档案廊", "取得潮期的历史记录", "低阶权限只能看到被删改的卷宗", "缺页与检测石有同样刻痕", "接受许照微的薄页", "许照微被记过，沈砚欠下人情"),
            ("1-S3", "旧域外廊", "验证禁线用途", "擅入将永失晋升资格，巡夜逼近", "禁线吸入灵息而非隔绝灾息", "以木牌换取短暂缝隙", "资格作废，必须进入旧域"),
        ),
    },
    {
        "chapter_id": "2",
        "title": "西廊残名",
        "progression": "追查并付代价",
        "chapter_goal": "在旧域西廊确认回响与被抹除名册之间的对应关系，并带出可交叉验证的残页。",
        "obstacle": "旧域回声会侵蚀沈砚与至亲有关的记忆；陆昭拒绝再为他的越界承担药额风险。",
        "choice": "沈砚让许照微在外记录阵纹，独自追听回响，宁可遗失一段父亲记忆也不带走无法复核的结论。",
        "consequence": "他取得残名与阵纹拓印，却记不起父亲教节拍时说过的最后一句话；陆昭转而向执律堂求稳。",
        "state_change": "从确认输送存在到确认旧域中有人以神识维持阵法。",
        "chapter_state_before": "确认镇潮阵向旧域输送灵息，并失去正常申诉资格。",
        "chapter_state_after": "确认旧域有人以神识维持阵法，并失去一段父亲记忆。",
        "progression_target": "把阵法异常推进为具体的人员与名册证据。",
        "irreversible_change": "父亲记忆出现不可逆缺失，陆昭转向执律堂。",
        "suspense_handoff": "轮值编号将在下一次检测前变化，原始名册能否及时找到？",
        "information_units": ["旧域存在神识回应", "残名与阵纹可交叉验证", "轮值编号将变化"],
        "previous_action_interface": "带着父亲留下的节拍进入旧域，查明回响对应的人与阵眼。",
        "next_action_interface": "残页上的轮值编号将在下一次检测前变化，必须在执律堂封锁前找到原始名册。",
        "scenes": (
            ("2-S1", "旧域西廊", "找到回响源头", "回声诱导沈砚重复父亲的节拍", "墙内有与检测同期变化的神识回应", "记下回应顺序而不触碰阵眼", "失去一段父亲相关记忆"),
            ("2-S2", "西廊库室", "取得可复核的名册证据", "库室只在潮息间隙开启", "残名与许照微兄长的记录相互矛盾", "留下拓印并带走编号", "警铃记录了闯入痕迹"),
            ("2-S3", "外廊出口", "安全带出证据", "陆昭要求停止并保住药额", "执律堂已按编号调阅检测名单", "沈砚把拓印交给许照微分存", "陆昭选择向执律堂报告异常"),
        ),
    },
    {
        "chapter_id": "3",
        "title": "封台之前",
        "progression": "证据升级且被迫行动",
        "chapter_goal": "在下一轮检测封台前完成证据链交叉验证，并阻止陆昭成为新的灵息供给。",
        "obstacle": "执律堂已控制档案与检测场；公开残页会先暴露许照微，沉默则让陆昭按时进入抽取。",
        "choice": "沈砚放弃等待完整名册，在检测场以节拍、拓印和陆昭读数建立可见证据，并破坏一次抽取流程。",
        "consequence": "陆昭暂时脱离抽取，但沈砚成为违规者；闻执衡取得残页并以旧域再开为由启动追捕。",
        "state_change": "从私人取证转为公开行动，证据由单点异象升级为人、阵纹与实时读数的链条。",
        "chapter_state_before": "确认旧域有人以神识维持阵法，并失去一段父亲记忆。",
        "chapter_state_after": "公开阻断一次抽取，证据链闭合，沈砚被迫逃入旧域。",
        "progression_target": "把私人证据推进为公开可见的实时因果链。",
        "irreversible_change": "抽取流程被破坏，沈砚被定为违规者并携钥逃亡。",
        "suspense_handoff": "半枚阵钥将把沈砚带向救人、守阵还是第三种方法？",
        "information_units": ["编号拓印读数同向", "陆昭正在被抽取", "导流刻槽通向旧域"],
        "previous_action_interface": "残页上的轮值编号将在下一次检测前变化，必须在执律堂封锁前找到原始名册。",
        "next_action_interface": "在追捕抵达前带着半枚阵钥返回旧域，决定救人、守阵或寻找第三种方法。",
        "scenes": (
            ("3-S1", "藏卷阁外", "拼合证据链", "原始名册被执律堂调走", "编号、拓印和潮期读数指向同一轮值", "让许照微只交出可公开部分", "她的身份暴露风险上升"),
            ("3-S2", "检测场", "确认陆昭正被抽取", "封台倒计时，陆昭不愿失去药额", "第七息读数与西廊阵纹同步", "沈砚请求陆昭延迟按石并当众复测", "两人必须在众目下站到同一边"),
            ("3-S3", "封台阵前", "阻断当次抽取", "闻执衡以潮灾风险要求立即封台", "阵法会把异常读数导向旧域", "沈砚击碎导流刻槽并留下拓印", "被定为违规者，只能携钥逃入旧域"),
        ),
    },
)


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _source_levels(report: dict[str, Any]) -> dict[str, str]:
    return {str(row.get("source")): str(row.get("usage_level")) for row in report.get("sources", []) if isinstance(row, dict)}


def _evidence(levels: dict[str, str]) -> list[dict[str, str]]:
    # These are design inputs, not assertions upgraded into verified facts.
    requested = (
        ("SB-WORLD-001", "项目创作圣经.json:world.power_system", "项目创作圣经", "世界规则、代价与公开谎言"),
        ("SB-CHAR-001", "项目创作圣经.json:characters", "项目创作圣经", "人物动机、冲突与可承担代价"),
        ("SB-ARC-001", "项目创作圣经.json:series_arc[0]", "项目创作圣经", "卷一承诺与转折边界"),
        ("DYN-001", "网络完整数据/动态连接完整数据.json", "动态网络.txt", "状态变化只能落为行动与可观察后果"),
        ("STA-001", "网络完整数据/静态连接完整数据.json", "静态网络.txt", "权限、资源与关系边界"),
        ("ANC-001", "原始资料/锚点网络.txt", "锚点网络.txt", "用可感知物件和空间落实异常"),
    )
    return [{"source_id": source_id, "source_ref": ref, "evidence_level": levels.get(source_name, "derived"), "decision_impact": impact, "direct_fact_allowed": False} for source_id, ref, source_name, impact in requested]


def build_artifacts(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    evidence_dir = root / "文档" / "证据"
    levels = _source_levels(_read(evidence_dir / "来源质量自主分析报告.json", {}))
    selected = _evidence(levels)
    manifests = []
    for blueprint in CHAPTER_BLUEPRINTS:
        scenes = [{"scene_id": scene_id, "location": location, "goal": goal, "obstacle": obstacle, "new_information": info, "choice": choice, "consequence": consequence, "required_prose_evidence": ["目标", "阻碍或新信息", "人物选择", "可观察后果", "状态变化"]} for scene_id, location, goal, obstacle, info, choice, consequence in blueprint["scenes"]]
        manifests.append({
            "schema_version": "chapter-execution-manifest-2.0",
            "chapter_id": blueprint["chapter_id"], "title": blueprint["title"], "status": "derived_planning_candidate",
            "target_characters": {"minimum": 2000, "maximum": 2500}, "progression": blueprint["progression"],
            "chapter_state_before": blueprint["chapter_state_before"], "chapter_state_after": blueprint["chapter_state_after"],
            "progression_target": blueprint["progression_target"], "irreversible_change": blueprint["irreversible_change"],
            "suspense_handoff": blueprint["suspense_handoff"], "information_units": blueprint["information_units"],
            "chapter_decision": {key: blueprint[key] for key in ("chapter_goal", "obstacle", "choice", "consequence", "state_change", "chapter_state_before", "chapter_state_after", "progression_target", "irreversible_change", "suspense_handoff", "information_units", "next_action_interface") if key in blueprint} | ({"previous_action_interface": blueprint["previous_action_interface"]} if "previous_action_interface" in blueprint else {}),
            "selected_evidence": selected,
            "fact_boundary": "仅可将项目创作圣经中的作者草案和 draft_usable 来源转为带来源标识的草稿设计；不得作为已确认项目事实、不得混入 candidate/unconfirmed 内容。",
            "exclusions": ["candidate、blocked 或无 source_ref 的资料不得进入正文", "来源定义、资料 ID、元数据和规则原文不得出现在正文", "未通过跨章连续性和场景闭环验证不得写入正文"],
            "scenes": scenes,
            "validation_criteria": ["每场具备目标、阻碍或新信息、选择、后果", "全章具备可观察状态变化和下一章行动接口", "字数在 2000-2500 中文字符", "证据链不得越过 draft_usable 的事实边界"],
        })
    report = validate_artifacts(manifests)
    output_dir = evidence_dir / "三章金样本"
    output_dir.mkdir(parents=True, exist_ok=True)
    for manifest in manifests:
        (output_dir / f"章节_{manifest['chapter_id']}_execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    task_table = {"schema_version": "golden-three-chapter-task-table-1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "policy": "先通过章节设计闸门，再以每批 6 条资料生成决策包；决策包未经复核不得改写正文。", "micro_batch_size": 6, "chapters": [{"chapter_id": item["chapter_id"], "progression": item["progression"], "goal": item["chapter_decision"]["chapter_goal"], "next_action_interface": item["chapter_decision"]["next_action_interface"]} for item in manifests]}
    (output_dir / "三章金样本任务表.json").write_text(json.dumps(task_table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    micro_batches = build_micro_batch_queue(_read(evidence_dir / "全量资料正文生产编排.json", {}), levels)
    (output_dir / "资料决策微批次.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in micro_batches), encoding="utf-8")
    report["micro_batch_size"] = 6
    report["micro_batch_count"] = len(micro_batches)
    report["micro_batch_policy"] = "每批只能产生资料选择和章节决策候选；禁止生成或覆盖正文。"
    (output_dir / "三章金样本验证报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def validate_artifacts(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    if len(manifests) != 3:
        errors.append("金样本必须恰有三章")
    prior_interface = ""
    for index, manifest in enumerate(manifests):
        decision = manifest.get("chapter_decision", {})
        required = ("chapter_goal", "obstacle", "choice", "consequence", "state_change", "chapter_state_before", "chapter_state_after", "progression_target", "irreversible_change", "suspense_handoff", "next_action_interface")
        for key in required:
            if not str(decision.get(key) or "").strip():
                errors.append(f"第{manifest.get('chapter_id')}章缺少决策字段：{key}")
        for item in manifest.get("selected_evidence", []):
            if item.get("evidence_level") in {"candidate", "blocked", "unconfirmed"} or item.get("direct_fact_allowed") is True:
                errors.append(f"第{manifest.get('chapter_id')}章存在越界来源：{item.get('source_id')}")
        scenes = manifest.get("scenes", [])
        if len(scenes) != 3:
            errors.append(f"第{manifest.get('chapter_id')}章必须有三场")
        for scene in scenes:
            if any(not str(scene.get(key) or "").strip() for key in ("goal", "obstacle", "new_information", "choice", "consequence")):
                errors.append(f"场景链不完整：{scene.get('scene_id')}")
        information_units = decision.get("information_units")
        if not isinstance(information_units, list) or not information_units or any(not str(item).strip() for item in information_units):
            errors.append(f"第{manifest.get('chapter_id')}章缺少结构化信息单元")
        elif index:
            prior_units = manifests[index - 1].get("chapter_decision", {}).get("information_units", [])
            repeated = sorted(set(map(str, information_units)) & set(map(str, prior_units)))
            if repeated:
                errors.append(f"第{manifest.get('chapter_id')}章重复上一章信息：{'、'.join(repeated)}")
        if index and str(decision.get("previous_action_interface") or "").strip() != prior_interface:
            errors.append(f"第{manifest.get('chapter_id')}章未精确承接上一章行动接口：{prior_interface}")
        if index and str(decision.get("chapter_state_before") or "").strip() != str(manifests[index - 1].get("chapter_decision", {}).get("chapter_state_after") or "").strip():
            errors.append(f"第{manifest.get('chapter_id')}章状态未承接上一章 after 状态")
        prior_interface = str(decision.get("next_action_interface") or "")
    return {"schema_version": "golden-three-chapter-validation-1.1", "status": "planning_gate_passed" if not errors else "blocked", "prose_authorization": "draft_only_not_formal_fact", "errors": errors, "chapter_count": len(manifests), "cross_chapter_gate": {"status": "passed" if not errors else "blocked", "checked": ["chapter_state_before", "chapter_state_after", "progression_target", "irreversible_change", "suspense_handoff", "information_units", "previous_action_interface"]}, "next_step": "以每批6条资料建立章节决策包；不得直接续跑旧的24条自动正文批次。"}


def build_micro_batch_queue(plan: dict[str, Any], levels: dict[str, str], batch_size: int = 6) -> list[dict[str, Any]]:
    """Re-batch source work as decision-only packets without assigning prose."""
    if batch_size < 1:
        raise ValueError("batch_size 必须为正整数")
    kind_levels = {
        "动态网络": levels.get("动态网络.txt", "blocked"),
        "静态网络": levels.get("静态网络.txt", "blocked"),
        "锚点网络": levels.get("锚点网络.txt", "blocked"),
        "资料库": levels.get("资料库.txt", "blocked"),
        "类型系统": levels.get("类型系统.txt", "blocked"),
        "类型系统来源块": levels.get("类型系统.txt", "blocked"),
        "类型连接": levels.get("类型连接.txt", "blocked"),
    }
    records = [row for row in plan.get("records", []) if isinstance(row, dict) and row.get("consumption_id")]
    packets = []
    for offset in range(0, len(records), batch_size):
        rows = records[offset:offset + batch_size]
        entries = [{"consumption_id": row["consumption_id"], "binding_id": row.get("binding_id"), "source_id": row.get("source_id"), "source_kind": row.get("source_kind"), "source_ref": row.get("source_ref"), "evidence_level": kind_levels.get(str(row.get("source_kind")), "blocked"), "required_decision": "选择、排除或保留为候选；说明其对三章中具体场景目标、阻碍、选择或后果的影响。"} for row in rows]
        packets.append({"micro_batch_id": f"DECISION-{offset // batch_size + 1:05d}", "status": "queued_for_chapter_decision_only", "chapter_scope": ["1", "2", "3"], "prose_write_allowed": False, "max_records": batch_size, "records": entries, "acceptance_criteria": ["逐条给出选中或排除决定", "candidate/blocked 来源只能被排除或请求核验", "每个选中项必须指向一个具体场景决策字段", "不得生成正文段落或声称已实现"]})
    return packets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    report = build_artifacts(args.project_root)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "planning_gate_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())