"""动作设计中信息缺口导致的代价原文。"""

MATERIAL = """【行动依赖角色确实掌握的信息】
在实际事件和能力范围内，按角色已经掌握或缺失的信息说明本次选择、障碍、应对和代价。

### 116.9_遗漏信息的代价
【原文位置】板块116 角色未知信息 第124803行
**定义**：信息的缺席本身产生后果。**代价类型**：
- 错误决策：因为没有某条信息，角色做了错误的选择
- 错失时机：因为信息来得太晚，错过了行动窗口
- 关系损伤：因为信息不对称，信任被破坏
- 代价累积：因为不知道某条信息，代价持续累积
**写作规则**：遗漏信息不是中性的“等以后再说”。
【本步用法】
当缺少或迟收信息确实影响选择时，指出失去的实际机会、关系或资源，把所产生的后果留给后续状态和情节承接。

#### G3B_CT_050 故事调查适配
【类型系统原文位置】故事调查类型适配.json 第2163行
【原文字段】第2166–2170行
  "stable_id": "G3B_CT_050",
  "object_kind": "investigation_type_adapter",
  "source_refs": [],
  "evidence_type": "template",
  "confidence": "template",
【原文字段】第2174–2192行
  "adapter_scope": "investigation",
  "adapter_template": {
    "adapter_id": "<ADAPTER_ID>",
    "type_or_style": "<type_or_style>",
    "adjustments": {
      "hook_retrieval_priority": [],
      "info_reveal_speed": "standard",
      "investigation_density": "standard",
      "misleading_density": "standard",
      "relationship_resource_focus": "balanced",
      "anomaly_presentation": "standard",
      "narrative_perspective": "standard",
      "pacing": "standard",
      "reader_information_gap": "standard",
      "candidate_ranking": {}
    },
    "constraint": "只调整排序和表达方式，不自动决定钩子真相、调查成功、角色选择、伏笔建立或回收、关系变化、死亡、爱情、背叛、升级或复仇。"
  },
  "design_constraint": "类型和风格只能调整检索优先级、揭示速度、调查密度、误导密度、焦点、呈现方式、视角、节奏、信息差和候选排序。不得自动决定真相或剧情选择。",
【本步用法】
已有调查事件、可行动人物及线索时，用所采用的调查密度、焦点及已知信息安排具体行动、阻碍与可见结果。调查成败依已选行动与证据。"""
