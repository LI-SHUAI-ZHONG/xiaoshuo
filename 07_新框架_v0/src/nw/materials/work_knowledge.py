"""Read the selected type system's work knowledge procedures and references."""
from pathlib import Path

from nw.materials.catalog import list_catalog, show_fragment
from nw.materials.work_catalog import original_text
from nw.materials.work_knowledge_checks import review_work_input


TYPE_SOURCE_ID = "6cd30d00d42a5b3410bed51599a705463517ef6316fbfc6c4319c45fc0a3cba5"
TYPE_PATH = "02_原版资料/原始资料/类型系统.txt"
TYPE_HASH = "aa0ac0359d8fb51d35a95f76cc29a652bab7dbfdbdf283a3fcf7acedefb4e582"

ANALYSIS = "作品知识库\\作品拆解\\"
REVIEW = "作品知识库\\人工复核\\"
SOURCE = "作品知识库\\来源记录\\"

STAGES = {
    "intake": (
        (382, ANALYSIS + "本地资料导入说明.md", "核对输入的来源、授权、内容范围及实际登记字段。"),
        (383, ANALYSIS + "本地资料完整度检查.py", "旧脚本仅供查证字段和分级思路。实际等级按已核验输入与原分级规则确定。"),
        (384, ANALYSIS + "拆解资料完整度规则.json", "从已确认的等级读取可分析项、禁止项和资料不足标记。"),
        (387, ANALYSIS + "合法拆解输入说明.md", "用实际来源和授权记录核对可处理范围及可保存的输出。"),
    ),
    "breakdown": (
        (60, "热门作品拆解模板.json", "只在来源可靠、相应信息已核验时填写相应字段。示例行说明结构。"),
        (80, "作品拆解批处理规则.json", "按原批次限制组织已通过来源核验的作品，分别记录失败、冲突和结果。"),
        (388, ANALYSIS + "两路径拆解对照表.json", "按项目实际所选路径确定观察重点，保留共用维度和各自输出限制。"),
        (389, ANALYSIS + "商业深度拆解字段.json", "按实际资料选择可分析的维度，分别填写事实、观察、分析和应用。"),
        (390, ANALYSIS + "作品拆解模板.json", "用模板对照拆解字段和待核项，按已核资料留下最小可回查依据。"),
        (391, ANALYSIS + "作品拆解验证规则.json", "核对提交的拆解记录、统计口径、比例、模式以及正文风险。"),
        (392, ANALYSIS + "作品拆解字段说明.json", "按各模块原口径理解统计、比例和证据字段。"),
        (393, ANALYSIS + "作品拆解总表.json", "读取原登记结构与原表计数。实际拆解结果按项目提交和复核记录核对。"),
    ),
    "abstraction": (
        (385, ANALYSIS + "抽象模式模板.json", "把已有证据提炼为可迁移的用途、条件、失败路径及连续性限制。"),
        (386, ANALYSIS + "抽象模式验证规则.json", "按原字段、来源、非保证边界、相似度及原创性要求检查抽象结果。"),
    ),
    "review": (
        (373, REVIEW + "作品拆解复核流程.md", "逐项核对来源、可迁移性、独特文本和现行规则冲突，读取实际人工结论。"),
        (374, REVIEW + "作品拆解复核模板.json", "按复核人、时间、逐项判据及允许的范围记录人工判断。"),
    ),
    "archive": (
        (349, SOURCE + "离线来源记录.json", "历史离线来源档案。以原标记的待核状态保留来源沿革。"),
        (356, SOURCE + "外部采集能力配置.json", "旧环境采集能力记录。用于核对历史状态。"),
    ),
}

STEP_SOURCE_KEYS = frozenset(key for step in STAGES.values() for _, key, _ in step)
ISOLATED_DIRECTORIES = ("作品知识库\\测试夹具\\", "作品知识库\\候选作品\\", "作品资料库\\候选清单\\")

REVIEW_RULES = {
    27: "类型动态传播限制.json",
    80: "作品拆解批处理规则.json",
    342: SOURCE + "来源导入模板.json",
    351: SOURCE + "平台指标兼容矩阵.json",
    374: REVIEW + "作品拆解复核模板.json",
    384: ANALYSIS + "拆解资料完整度规则.json",
    386: ANALYSIS + "抽象模式验证规则.json",
    391: ANALYSIS + "作品拆解验证规则.json",
}
RULES_BY_KIND = {
    "intake": (384,),
    "source_template": (342,),
    "metric_comparison": (351,),
    "analysis": (80, 386, 391),
    "abstract_pattern": (386,),
    "dynamic_pattern": (27, 386),
    "type_case": (386,),
    "style_case": (386,),
    "static_pattern": (386,),
    "combination": (386,),
    "review": (374,),
}
KINDS_BY_STAGE = {
    "intake": {
        "intake", "source_template", "source", "source_conflict", "metric_comparison", "work",
    },
    "breakdown": {"analysis"},
    "abstraction": {"abstract_pattern", "type_case", "style_case", "static_pattern",
                    "dynamic_pattern", "combination", "index"},
    "review": {"review"},
}


def work_knowledge_only(key: object) -> bool:
    return isinstance(key, str) and (key in STEP_SOURCE_KEYS or key.startswith(ISOLATED_DIRECTORIES))


def _read(workspace: Path, number: int, key: str) -> dict:
    matches = [
        row for row in list_catalog(workspace, TYPE_SOURCE_ID, key)["fragments"]
        if row["kind"] == "source_block"
    ]
    if len(matches) != 1:
        raise ValueError(f"WORK_KNOWLEDGE: missing or ambiguous selected source {number}: {key}")
    result = show_fragment(workspace, matches[0]["fragment_id"])
    header, _, body = result.pop("text").split("\n", 2)
    if header.rstrip("\r") != "SOURCE: " + key:
        raise ValueError(f"WORK_KNOWLEDGE: source header differs: {number}")
    _, value = original_text(body.strip())
    if key.endswith(".json") and not isinstance(value, dict):
        raise ValueError(f"WORK_KNOWLEDGE: invalid source JSON: {number}")
    return {**result, "source_block": number, "source_path": TYPE_PATH,
            "file_sha256": TYPE_HASH, "original": value}


def check_work_inputs(workspace: Path, stage: str, inputs: object, *, test_mode: bool = False) -> dict:
    if not isinstance(inputs, dict) or not isinstance(inputs.get("kind"), str):
        raise ValueError("WORK_KNOWLEDGE: inputs require kind and records")
    kind, records = inputs["kind"], inputs.get("records")
    if kind not in KINDS_BY_STAGE.get(stage, ()):
        raise ValueError("WORK_KNOWLEDGE: input kind does not belong to this step")
    if not isinstance(records, list) or not records or not all(isinstance(record, dict) for record in records):
        raise ValueError("WORK_KNOWLEDGE: records must be a nonempty list of objects")
    rules = {number: _read(workspace, number, REVIEW_RULES[number])["original"]
             for number in RULES_BY_KIND.get(kind, ())}
    return review_work_input(kind, records, rules, test_mode=test_mode)


def work_knowledge(workspace: Path, stage: str, inputs: object = None) -> dict:
    if stage not in STAGES:
        raise ValueError("WORK_KNOWLEDGE: unknown step")
    if stage == "archive" and inputs is not None:
        raise ValueError("WORK_KNOWLEDGE: archive only displays source records")
    report = {
        "stage": stage,
        "use": "provenance_only" if stage == "archive" else "work_knowledge",
        "materials": [{**_read(workspace, number, key), "usage": usage}
                      for number, key, usage in STAGES[stage]],
    }
    if inputs is not None:
        report["input_review"] = check_work_inputs(workspace, stage, inputs)
    return report
