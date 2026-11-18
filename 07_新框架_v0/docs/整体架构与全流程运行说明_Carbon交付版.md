# 小说细粒度工作流整体架构与全流程运行说明（Carbon 交付版）

> **适用版本**：`07_新框架_v0`（含 M0–M10 全量底座 + Batch 32 全资料入步路由闭环 + Batch 33 跨步防遗忘/多资料协同守卫/分步骤双模型路由 + 本地前端客户端 `nw.studio`）
> **运行策略**：`artifact-stage-binding-v4` + `stage-material-input-v1`（当前默认离线沙盘就绪，外部 API 按需接入）

---

## 一、整体四层架构总览

整套小说创作工作流由下至上分为**严格解耦、全链路 SHA-256 可追溯**的四层：

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 第四层：本地可视化创作客户端 (src/nw/studio/ · 零第三方依赖 Web Studio)     │
│  01.项目设定总览 │ 02.14步联合资料沙盘 │ 03.章场与POV工作台 │ 04.卡片与知情矩阵 │
│  05.六大资料与F2台账浏览器 │ 06.离线沙盘与 Carbon+Opus5.5 分步骤模型路由中心    │
├────────────────────────────────────────────────────────────────────────────┤
│ 第三层：受管连续创作与写审改提受协调器 (novel_flow / novel_scene / scoped)  │
│  POV受限上下文组包 -> 起草(write) -> 独立审稿(review) -> 修订(revise)       │
│  -> 状态提取(state_extract) -> 独立事实复核(fact_review) -> 硬规则check_delta│
│  -> 整章范围审稿(scope_review) -> 原子批次提交(accept_batch) -> 章总结复盘   │
├────────────────────────────────────────────────────────────────────────────┤
│ 第二层：7/14步细粒度分阶段设计与联合资料调度引擎 (phase_flow / step_guard)  │
│  128.4逐步前置取材 + 原义合同核验 + continuity_ledger跨步防遗忘账本         │
│  + joint_material_plan多资料角色分工 + validate_cross_step_consistency硬防崩 │
├────────────────────────────────────────────────────────────────────────────┤
│ 第一层：不可变存储与六大资料裁定底座 (store / story_state / SourceDesk)     │
│  SQLite v10 事务库 + 不可变卡片与多主体知情重放 + 22,941条已裁定资料目录库   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、创作期 14 步流水线精确运行逻辑与防错机制

系统区分两种规划粒度：
- **全书总纲（`scope = 'book'`，7步 + 1步总装）**：执行第 `01`–`06` 步 + 第 `14` 步 `bind_scope`。
- **卷 / 章 / 场 / 重规划细化（`scope = 'volume' | 'chapter' | 'scene' | 'replan'`，14步 + 1步总装）**：完整执行第 `01`–`14` 步 + 总装冻结。

### 2.1 14 步逐环职责、输入、产物与防崩塌守卫表

| 步序 | 步骤 ID | 核心职责 | 直连前置 (`REQUIRES`) | 防遗忘与一致性硬守卫 (`step_guard.py` + `phase_contract.py`) |
|---:|---|---|---|---|
| 01 | `type_selection` | 判定主/副类型、激活题材概念、确立题材禁区与读者核心承诺 | 无（读取 `Brief`） | 原名/别名/父子层级核对；确立向全流程广播的 `boundaries` |
| 02 | `type_adaptation` | 处理多类型组合分工、表达适配参数及 `TDR_TEMPLATE_002` 概念触发 | `01` | 核验治理输入与动态引用资格（`TDV_020`），拦截空泛套话 |
| 03 | `world_design` | 设计世界规则卡、运行限制、能力代价与明确待决项 (`unknowns`) | `01, 02` | 区分 `public` / `holders` / `author_only` 可见域，防止设定全知外泄 |
| 04 | `character_design` | 设计人物动机(`want`/`need`)、初始状态、可行动性(`can_act`)与能力依据 | `01, 02, 03` | 非角色实体标记 `can_act=false`，严禁后续步骤派发主动行为 |
| 05 | `static_relations` | 建立人物/势力/世界间的静态关系边、限制条件与指向后续步骤的方法约束 | `01..04` | 生成带明确目标步骤的 `requirements`，下游未承接则无法通过校验 |
| 06 | `plot_design` | 设计主次剧情卡、事件因果骨架、伏笔计划(`promise_plan`)与读者情绪曲线(`reader_plan`)；续章自动读取上章 `chapter_handoff` 与 `chapter_summary` | `01..05` | 伏笔必须绑定真实 `plant_event`，读者体验不得用角色情绪顶替 |
| 07 | `event_design` | 结合 `TDR_TEMPLATE_004` 将剧情节点拆解为带前置条件与完成判据的事件候选 | `03..06` | **自动补偿 `type_guard` + `entity_guard`**，防止中段事件偏离题材禁区 |
| 08 | `action_design` | 结合 `TDR_TEMPLATE_005` 设计具体行动博弈：动作步骤、阻碍、应对与代价 | `03..07` | 校验行动发起者必须 `can_act=true` 且具备第4步登记的能力依据 |
| 09 | `scene_design` | 选定实际落场事件与行动，确定章场坐标、单场 POV、冲突、允许披露范围与变化前状态(`before_state`) | `03..08` | **自动补偿 `type_guard` + `entity_guard`**；**硬拦截同场同实体多事件 `before_state` 自相矛盾**；单视角自动屏蔽多视角噪声资料 |
| 10 | `state_transition` | 结合 `TDR_TEMPLATE_003` 将场内变化落实为具体行动、代价(`cost`)、失败分支与变化后状态(`after_state`) | `04, 05, 06, 08, 09` | **自动补偿 `type_guard` + `world_guard` + `entity_guard`**（弥补未直连 `world_design` 的空白）；**硬拦截 `after_state` 冲突与 `TODO`/`待定`/`<填写>` 占位幻觉** |
| 11 | `state_propagation` | 结合 `TDR_TEMPLATE_001` 与 `TDF_001` 设计根变化确认后的跨主体传播预案 | `03..06, 08..10` | 根变化未确认或外部行动未选中时仅作条件预案，严禁自动生效成既定事实 |
| 12 | `anchor_design` | 将选中动作步骤(`action_ref`+`step_index`)与状态变化转化为本场 POV 可感知的具体器物、动作与身体节拍 | `04, 05, 08..11` | **自动补偿 `type_guard` + `world_guard` + `plot_guard` + `entity_guard`**（确保锚点同时服务于第6步伏笔与读者情绪目标） |
| 13 | `expression_design` | 结合视角、人物嗓音、感官规则与叙述距离，制定本场具体表达指导与审稿检验点 | `01..06, 08..12` | 把抽象风格转化为可核查的句法、视距与感官禁区 |
| 14 | `bind_scope` | 汇总全链路实际使用(`_uses`)的资料、剔除未选分支、绑定场景级与整章范围级审稿检查合同 | 读取前序全部产物 | 核验所有上游 `requirements` 与语义条款均已落实或依规说明 `_excluded`；通过 `compact_session` 剥离传输态审计冗余，防超长上下文溢出 |

---

## 三、多资料联合创作与残缺资料防卡环机制

针对作者重点关心的「**多份资料在同一创作步骤联合使用如何避免打架、卡环，以及部分原始资料仍有缺陷时如何安全运行**」，系统建立了四重保障：

1. **五级冲突裁决铁律（`PRIORITY_HIERARCHY`）**
   - 任何步骤出现规则张力时，严格执行：
     `已接受正文事实 (accepted_state) > 作者需求与硬约束 (brief) > 前置步骤已冻结产物 (upstream_products) > 合格方法原义 (design_ready) > 候选参考模板 (reference_template)`。
2. **同一步骤内多资料角色自动编组（`build_joint_material_plan`）**
   - 当某一步召回 2 份及以上资料时，`step_guard.py` 自动按资料职责拆分为三组协同角色：
     - **驱动推进类（`drivers`）**：如剧情、人物动机、开篇、动态迁移，负责决定本步核心目标与推进方向；
     - **边界约束类（`boundaries`）**：如世界规则、静态关系、知情限制、时间线/视角流程，负责划定不可逾越的物理与认知红线；
     - **锚点与表达类（`anchors_and_expression`）**：负责将上述目标与限制落地为可见动作、感官与对白质感。
3. **不适用条款与残缺原件的合法出口（绝不死锁卡环）**
   - `blocked` 资料默认拦截在自动召回之外；`reference` 模板必须结合本项目实体实例化，绝不强制套用无关设定；
   - 若某份已召回资料中的个别子条款因项目设定差异不适用，允许写入 `_excluded` 并注明本项目具体差异原因；
   - 若某份资料存在 `F2_统一问题台账.jsonl` 已登记的原文局部缺义，允许按 `source_unresolved` 如实标记，既不迫使模型编造假事实，也不会卡死整条流水线。
4. **治理输入全链路透传（`JobRequest.governance_inputs`）**
   - 修复了持久化 `novel` 任务在真实六大资料库下无法向 `book` / `chapter` 阶段分别传入作者治理确认参数的卡点，支持按 `{'book': {...}, 'detail': {...}}` 或按阶段名精确投递。

---

## 四、正文写作期「防遗忘、防幻觉、防泄密、防断气」七环闭环

当 14 步设计经作者批准落地为版本化卡片与章场后，每场正文执行以下闭环（代码见 [story.py](file:///D:/搭建/07_新框架_v0/src/nw/context/story.py)、[novel_scene.py](file:///D:/搭建/07_新框架_v0/src/nw/novel_scene.py)、[story_extract.py](file:///D:/搭建/07_新框架_v0/src/nw/story_extract.py)、[scoped.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/scoped.py)）：

1. **受限 POV 写作工作包冻结（`build_story_context`）**
   - 仅向写手投喂该场 `pov` 角色有权获知的卡片（`public` 或 `holders` 含该 POV）与截至当前 `story_order` 的已知事实/主观误信（`belief`）；`author_only` 真相卡与他人的私密信息在物理层面不进入写手消息。
   - **同视角紧邻前场衔接**：若上一场同属当前 POV，自动在预算内附带上一场末尾 `1,200` 字正文（`previous:<scene_id>`）及过往事实的 `<=240` 字原文证据摘录（`prior-evidence`），彻底消除场与场之间文气断裂与细节遗忘；若上一场为异 POV，则严格不附带前场私密心理正文。
2. **正文起草（`write`）与独立审稿（`review`）**
   - 写手只写正文；独立审稿人同时核对剧情一致性与每项绑定资料的逐字段原文证据（`[start, end)` Unicode 半开区间 + 精确 `quote`），空泛评语或缺少原文引用的“通过”会被程序直接打回。
3. **受控修订（`revise`）与核心设定门禁（`core_gate`）**
   - 若审稿发现触及生死、核心目标、世界规则、视角或终局承诺的变更（`core_changes`），立即暂停并交由作者门禁裁决，模型无权擅自篡改主干设定。
4. **状态增量提取（`state_extract`）与独立事实复核（`fact_review`）**
   - 从定稿正文中提取结构化状态变更 `operations`，并强制区分客观事实（`WORLD` + `fact`）、读者披露（`READER`）、人物信念/误信（`belief`/`suspicion`）、人物口头说辞（`utterance`）与未发生计划（`plan`）——**彻底杜绝把人物随口说的话或内心猜测当成客观既成事实的幻觉**。
5. **程序级硬规则核验（`check_delta` + `check_material_acceptance`）**
   - 校验每条状态变更的 `expected_old` 是否与当前分支状态严格一致、证据区间是否真实落在正文中；存在任何 `hard` 级冲突立即阻断。
6. **整章/跨章范围独立审稿（`scope_review`）**
   - 对涉及整章对话比例、多场节奏交替、跨章语体连续性、前三句/章末钩子等范围型资料，在集齐完整章节草稿后执行跨场联合核验。
7. **原子批次验收与续章交接（`accept_batch` + `chapter_summary` / `chapter_review`）**
   - 在单个 SQLite 事务内推进分支 `revision`、更新场景槽位并导出 `正文/chXX_sXX.md`；随后生成章末状态与百字章总结，自动注入下一章 `plot_design`。

---

## 五、本地前端客户端（`nw.studio`）使用与模块映射

### 5.1 启动方式（零第三方依赖，无需外部 API Key）

- **方式一（双击启动）**：直接运行 [启动写作客户端.bat](file:///D:/搭建/07_新框架_v0/启动写作客户端.bat)
- **方式二（命令行启动）**：
  ```powershell
  cd D:\搭建\07_新框架_v0
  $env:PYTHONPATH = "src"
  .\.venv\Scripts\python.exe -m nw studio --host 127.0.0.1 --port 8765 --open-browser
  ```

### 5.2 客户端六大工作台功能一览

1. **01 · 项目与设定总览**：新建/切换项目、版本化保存 `Brief` 与硬约束、管理 `Bible` 备忘、一键初始化 `Story Adoption` 状态机基线（`main@r0`）并查看分支。
2. **02 · 14步创作与联合资料沙盘**：零 Token 离线实测任意构想在 7 步/14 步中的 `128.4` 资料召回结果、多资料角色协同表（`joint_material_plan`）、跨步防遗忘账本（`continuity_ledger`）以及注入后的完整 `System Prompt`。
3. **03 · 章场工作台与 POV 上下文**：创建章场结构、实时预览 `build_story_context` 生成的 POV 受限工作包与字符预算占用条、离线录入样章草稿、生成并校验 `StateDelta`、一键执行 `accept_batch` 导出 Markdown 正文并记录章总结。
4. **04 · 卡片库与多视角知情矩阵**：使用标准模板创建并审批 `character` / `world` / `scene` / `plot` / `promise` / `style` / `taboo` 卡片，并在同一张表格中横向对比 `WORLD`、`READER` 与各角色在任意故事时间点的知情差异。
5. **05 · 六大资料库与 F2 问题台账**：全文检索 22,941 条已裁定资料（查看原义、SHA-256 与进入各步骤的【本步用法】），并按关键词或处置状态排查 `F2_统一问题台账.jsonl` 中的全部待补缺口。
6. **06 · API 接入与双模型分工配置**：提供「离线沙盘」「Carbon + Opus 5.5 黄金双模型分工」「Opus 5.5 单模型」「本地 Ollama」四套预设，自动检测本机环境变量是否就绪、拦截明文密钥误填，并校验生成 `config.toml`。
