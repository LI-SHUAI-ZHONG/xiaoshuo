# 新方案分析与原始资料深度检查

生成时间：`2026-08-13T04:59:38.723060+00:00`

## 一、方案逻辑

数据流为：`原始资料/*.txt` 只读进入解析器或派生生成器；解析器按稳定标题、字段、ID 和来源位置切分条目，生成全局索引；规则文件声明消费条件、证据要求、状态和阻断级别；执行任务先加载索引与规则，按依赖顺序选择条目，再把选择结果写入项目消费记录；执行管道读取已验证的消费记录，将数据依次传递给类型、连接、静态网络、动态网络、锚点和正文执行模块，最终把设计、正文位置和验证结果回写项目。

文字数据流：

`原始资料 → 解析器/生成器 → 全局索引 → 规则文件校验 → 项目消费记录 → 执行管道 → 设计/章节/正文 → 结果验证`

依赖顺序是：类型系统先于类型连接；静态网络先于动态网络；动态网络先于锚点网络；所有有效证据最终进入执行正文清单。索引命中、读取或提及都不等于消费，必须经过消费记录和可定位证据。

## 二、组件职责

- **全局索引**：为每条原始资料建立机器可读摘要，提供稳定 ID、名称、类别、字段、来源位置和状态，支持按 ID、名称、类型、关键词和关系查询。
- **规则文件**：定义何时允许选择、需要哪些字段、怎样绑定设计或正文、证据达到什么等级，以及缺失时 warning 还是 block。
- **消费记录**：记录项目、任务、索引项、状态、决策影响、设计路径、章节路径、正文位置、时间和来源哈希，形成可复核证据链。
- **执行管道**：加载并校验这些输入，按依赖顺序调用模块，向下游传递结构化结果，并在正文前后执行阻断和落点检查。

## 三、字段与格式要求

### 索引

- 资料库 JSONL：`entry_id`、`name`、`type`、`key_attributes`、`dependencies`、`source_ref`、`source_sha256`、`line_start`、`line_end`、`status`；可选 `examples`、`conditions`、`placeholder_flags`。
- 类型 JSON：`type_id/name`、`core_elements`、`reader_expectations`、`style_constraints`、`length_rhythm`、`source_ref`、`source_status`。
- 类型连接：`connection_id`、`combination_id`、`types`、`conflicts`、`recommended_mechanisms`、`resolutions`、`source_ref`、`status`。
- 动态链：`chain_id`、`source`、`target`、`type`、`condition`、`effect`、`state_layer`、`validation_status`、`source_ref`。
- 静态连接：`edge_id`、`source`、`target`、`type`、`bound_target_types`、`mainline_level`、`source_ref`。
- 锚点：`anchor_id`、`category`、`name/definition`、`format_valid`、`source_ref`。

### 规则

每条规则至少需要 `rule_id`、`name`、`condition`、`action`、`required_fields`、`evidence_requirements`、`blocking_level`、`failure_status`。规则还应声明输入索引、输出记录和验证方式。

### 消费记录

每条记录至少需要 `record_id`、`project_id`、`task_id`、`item_id`、`status`、`used_in_design`、`used_in_chapter`、`decision_statement`、`source_ref`、`confidence`、`consumed_at`、`source_sha256`。不同网络还需分别记录 chain、edge 或 anchor 的绑定对象和正文位置。

## 四、运行方式

1. 管道读取索引，校验 JSON/JSONL、唯一 ID、来源文件、哈希和状态。
2. 管道读取规则，按任务和当前项目状态选择适用条目；`candidate`、`template`、`pending`、`needs_review` 和 `unconfirmed` 不得约束正文。
3. 类型模块输出类型约束，连接模块消费类型约束并输出组合裁决；静态模块输出稳定关系，动态模块基于静态关系输出状态变化，锚点模块把动态结果落到场景。
4. 每个模块输出结构化数据和 `source_trace`，管道在进入下一阶段前写入对应消费记录。
5. 正文生成前，缺少类型连接记录、主线静态连接、章节动态链、场景锚点或执行清单时按规则触发阻断；正文生成后，缺少正文位置或锚点落点时至少触发 warning，关键链路缺失则 block。

## 五、深检摘要

| 资料 | 总量 | 可提取 | 占位数 | 目标组件缺口 | 状态 |
|---|---:|---:|---:|---|---|
| 资料库.txt | 542 | 542 | 5126 | dependencies, examples | partial |
| 类型系统.txt | 15 | 15 | 2620 | core_elements, reader_params, style_constraints | partial |
| 类型连接.txt | 2100 | 2100 | 5991 | conflict_details, recommended_mechanism_explanation, source_connection_id | partial |
| 动态网络.txt | 1824 | 1824 | 22 | 无 | partial |
| 静态网络.txt | 1341 | 1341 | 19 | 无 | partial |
| 锚点网络.txt | 1790 | 1790 | 42 | anchor_definition, scene_binding, text_location | partial |

可提取率只表示字段或结构可以被扫描器识别，不代表已经通过规则验证或被项目消费。
