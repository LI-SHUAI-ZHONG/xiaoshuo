# Opus 5.5 接手改进与双模型能力分工说明

> **文档定位**：本说明由 **Gemini 4 Carbon** 在完成底层架构加固、全量资料入步闭环（Batch 32）、跨步防遗忘与多资料联合创作守卫（Batch 33）以及本地前端写作客户端（`nw.studio`）落地后编写，专供 **作者** 与后续接手的 **Claude Opus 5.5** 直接按图索骥推进文学精修、原始资料缺口补全、前端体验打磨与最终 API 创作实测。

---

## 一、Carbon 与 Opus 5.5 能力分工全景对照表

按照「**Carbon 强项 + 两者能力相近项全部由 Carbon 先行落地闭环；Opus 5.5 绝对强项单独留口并附精细改造指南**」的原则，当前工程切分如下：

| 领域模块 | 能力归属判断 | 当前完成状态（Carbon 交付基线） | 涉及核心文件 | Opus 5.5 后续动作建议 |
|---|---|---|---|---|
| **1. 14步因果状态机、哈希冻结与断点恢复** | Carbon 强项（长程硬约束推理、状态机严密性） | **100% 已完成** | [phase_flow.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/phase_flow.py)、[novel_flow.py](file:///D:/搭建/07_新框架_v0/src/nw/novel_flow.py)、[tasks.py](file:///D:/搭建/07_新框架_v0/src/nw/tasks.py) | **无需重改底层协议**；直接复用现有事务与重放机制 |
| **2. 六大资料库 22,941 条入步解析与路由对齐** | Carbon 强项（超大规模符号对账、零漏项解析） | **100% 已完成**（6,150 个 `design_ready` 唯一键投递漏项 0、错配 0；1,850 锚点写审 100% 覆盖） | [stage_input.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/stage_input.py)、[phase_routes.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/phase_routes.py) | 保持标题与键解析协议不变；补全资料后按第四节流程增量刷新索引 |
| **3. 跨步防遗忘账本、先后冲突拦截与联合资料仲裁** | Carbon 强项 + 两者相近项 | **100% 已落地**（新增 `continuity_ledger`、`joint_material_plan`、`validate_cross_step_consistency`、`compact_session` 瘦身） | [step_guard.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/step_guard.py)、[work_contract.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/work_contract.py)、[phase_contract.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/phase_contract.py) | **可微调提示措辞**：Opus 5.5 可优化 `joint_material_plan['rule']` 的文学融合引导语 |
| **4. 分步骤多模型路由（`[stage_models]`）与治理参数透传** | Carbon 强项（配置与协议工程） | **100% 已落地**（支持 14 个设计步 + 7 个运行步独立指定 Carbon / Opus 5.5） | [config.py](file:///D:/搭建/07_新框架_v0/src/nw/config.py)、[novel_calls.py](file:///D:/搭建/07_新框架_v0/src/nw/novel_calls.py)、[novel_scene.py](file:///D:/搭建/07_新框架_v0/src/nw/novel_scene.py)、[story_extract.py](file:///D:/搭建/07_新框架_v0/src/nw/story_extract.py) | 实测接入 API 时微调各步骤最佳 `temperature` 与 `max_tokens` |
| **5. 零依赖本地前端客户端（后端服务 + 6大工作台 UI）** | 后端架构 Carbon 强项；前端视觉交互 Opus 5.5 略优（WebDev `1814` vs `1768`） | **完整功能版已落地**（离线零 API 可跑通项目/14步干跑/POV包/草稿Delta验收/资料库/F2台账/双模型配置） | [api.py](file:///D:/搭建/07_新框架_v0/src/nw/studio/api.py)、[server.py](file:///D:/搭建/07_新框架_v0/src/nw/studio/server.py)、[index.html](file:///D:/搭建/07_新框架_v0/src/nw/studio/static/index.html)、[styles.css](file:///D:/搭建/07_新框架_v0/src/nw/studio/static/styles.css)、[app.js](file:///D:/搭建/07_新框架_v0/src/nw/studio/static/app.js) | **推荐精修视觉与沉浸写作交互**（见第四节详细清单） |
| **6. 文学正文提示词、潜台词张力、叙述距离与情感颗粒度** | **Opus 5.5 绝对强项**（EQ-Bench Creative Writing 顶尖，中文语感与留白显著占优） | 已具备严密防泄密与防幻觉契约，但基座提示词偏工程克制 | [story.py](file:///D:/搭建/07_新框架_v0/src/nw/context/story.py)、[novel_scene.py](file:///D:/搭建/07_新框架_v0/src/nw/novel_scene.py)、[writing.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/steps/writing.py)、[expression_design.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/steps/expression_design.py) | **Opus 5.5 第一优先级重任**（见第二节） |
| **7. 原始资料缺失板块创作补全与文学示例重写** | **Opus 5.5 绝对强项 + 作者共创**（严禁工程阶段无授权编造原件） | 已全部精确定位在 `F2_统一问题台账.jsonl`（1,684 条开放缺口），运行期已做防卡环隔离 | [F2_统一问题台账.jsonl](file:///D:/搭建/08_工作流设计/F2_统一问题台账.jsonl) | **Opus 5.5 第二优先级重任**（见第三节） |

---

## 二、Opus 5.5 第一优先级任务：文学表达、人物弧光与反套路提示词精修

当前框架已经解决了「**不泄密、不遗忘、不自相矛盾、不漏发资料**」，但最终生成的小说正文是否真正好看、耐读、有呼吸感，取决于送给写手与表达设计步骤的文学指令质量。这是 Opus 5.5 最核心的发力点。

### 2.1 需要 Opus 5.5 精修的核心位置

1. **正文起草主指令 `WRITE_PROMPT`**
   - 位置：[story.py](file:///D:/搭建/07_新框架_v0/src/nw/context/story.py#L21-L22)
   - 现状：`WRITE_PROMPT` 仅 79 字，侧重信息边界（仅用 POV 可知信息、belief 可能有误、只输出正文），缺少对**中文叙事节奏、感官锚点自然融入、潜台词留白、避免 AI 腔总结句（如“他心中五味杂陈”“命运的齿轮开始转动”）**的审美约束。
   - **重要兼容性提醒**：检查 `tests/` 中是否有对默认 `WRITE_PROMPT` 精确字符串做快照比对的用例；若存在，可保持模块级默认常量兼容，或在新增的文学增强配置开关/步骤说明头段中扩展，并同步更新相关预期哈希测试。

2. **修订与独立审稿主指令 `REVIEW_PROMPT` / `REVISE_PROMPT`**
   - 位置：[novel_scene.py](file:///D:/搭建/07_新框架_v0/src/nw/novel_scene.py#L24-L31)
   - 改进方向：
     - `REVIEW_PROMPT` 目前能精准抓出事实越界和资料漏检，但对「**多份资料生硬堆砌（机械打卡感）**」「**人物对话像说明书**」「**段尾强行升华点题**」缺乏审美否决标准。建议在不破坏返回 JSON 结构 `{"recommendation":"pass或revise","notes":"...","core_changes":[]}` 的前提下，加入「资料无痕化融入检查」与「人物口吻一致性检查」。
     - `REVISE_PROMPT` 应强调：**局部手术优于推倒重写**，保留原稿已成立的具象细节与文气，仅针对 `notes` 指出的缺陷修补，防止越改越干瘪。

3. **四个人物与文学步骤的引导头段与【本步用法】润色**
   - 人物设计：[character_design.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/steps/character_design.py) —— 强化人物「表层欲望 `want` vs 深层匮乏 `need`」「言行反差」「独立于主角利益之外的配角自驱力」。
   - 行动博弈：[action_design.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/steps/action_design.py) —— 强化「试错—受阻—换招—付出真实代价」的动态交互颗粒度。
   - 具象锚点：[anchor_design.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/steps/anchor_design.py) —— 引导模型把抽象情绪转化为**与当前场景器物、气候、伤势、职业习惯绑定**的唯一动作节拍，杜绝通用套话（如动辄“攥紧拳头”“瞳孔微缩”）。
   - 表达设计 & 正文写法：[expression_design.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/steps/expression_design.py)、[writing.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/steps/writing.py) —— 优化叙述距离推拉（远景冷峻铺陈 vs 近景感官切入）与句法长短错落指引。

### 2.2 【极其重要】针对 Opus 5.5 自身倾向的「防冲突柔化护栏」

根据多平台评测（EQ-Bench Creative Writing v3 等），Opus 5.5 在长篇创作中有一个典型弱点：**Safety-Maxxing / 冲突柔化与道德自省偏置**——遇到残酷利益博弈、师徒背叛、制度压迫、灰色抉择或不可调和的立场冲突时，容易让角色过早共情和解、把锋利的潜台词写成温和沟通，或在结尾加一段自我宽慰。

**Opus 5.5 在优化上述提示词及《潮痕入骨》文风卡（`style` / `taboo`）时，请务必显式写入以下四条硬护栏**：
1. **禁止提前消解冲突**：在本场场景卡 `planned_result` 未要求和解前，严禁让对立角色互相体谅、主动退让或用温和长句化解尴尬；悬而未决的紧绷感必须保留到场末。
2. **禁止替角色做道德总结或抒情升华**：严禁在段落末尾写旁白式的心理鸡汤、哲理感叹或价值评判；一切心理震动只能落在具体动作停顿、视线回避、失手错漏或答非所问的台词上。
3. **代价不可打折**：上游 `state_transition` 冻结的 `cost`（伤势、失物、暴露、结怨、资源损耗）必须在正文中实打实发生，不得用“幸好及时收手”“只是虚惊一场”弱化。
4. **资料联合无痕化**：同一场使用 3–6 份资料时，资料是幕后脚手架，正文中严禁露出方法论术语，所有锚点与感官必须服务于同一个核心戏剧动作，宁可少用修饰词也绝不堆砌形容词。

---

## 三、Opus 5.5 第二优先级任务：原始资料缺口补全与 F2 台账消缺指南

目前 `02_原版资料/原始资料/` 为**只读历史基准**，其中存在作者已知的原件缺口，全部登记在 [F2_统一问题台账.jsonl](file:///D:/搭建/08_工作流设计/F2_统一问题台账.jsonl)（共 2,532 条，已结项 763 条，开放 1,684 条；可在前端客户端「**05 · 六大资料库与F2问题台账**」页直接检索筛选）。

### 3.1 最关键的四类待补原始资料缺口（按对小说质量影响排序）

1. **整块缺失的核心板块（最高优，需与作者确认口径后撰补）**
   - **《资料库》板块 78–80（时间规则 / 双轴时间同步）**：多处上下游条目引用了该板块，但原件整块缺失。需补齐：故事内时间流逝计量、叙事省略/跳时标记规则、多线/单线时间锚定与冷却窗口规则。
   - **《资料库》72.3–72.6（四种决策类型细则）**：目前仅有总括引用，缺四类决策各自的触发情境、权衡维度、常见误判与行动落点。
   - **《资料库》136.x（约 8 条卡文诊断与破局子项）、8.2（亢奋情绪）、134.1、155.3**：原件缺失或编号断层。

2. **《类型系统》中「玄幻 / 制度悬疑」表达适配缺口（直接关系试验作《潮痕入骨》）**
   - 现状：《类型表达适配总表》118 条中仅 23 条 `design_ready`（集中在仙侠/都市/末日/科幻/悬疑），**玄幻大类与「玄幻+制度悬疑」融合方向缺少成规模的推荐表达、禁用套话、修炼/制度代价具象化规则**；62 条混合类型中有 60 条因兼容字段与冲突说明为空处于 `blocked`。
   - 建议：由 Opus 5.5 结合《潮痕入骨》试写需求，为玄幻及核心混合类型补齐「环境质感、能力代价外显、阶层/宗门制度压迫感、反套路叙事」的具体适配条目。

3. **冒号截断与通用填充示例（约 363 条通用模板句 + 多处“包括以下维度：”截断）**
   - 如 `2.3_角色动作` 等条目定义停在冒号处丢失列表；《资料库》397 条示例中有 363 条为无信息量的套话。Opus 5.5 极擅长将这些空洞示例改写为**高密度、分正反例（Bad Case vs Good Case）的文学示范片段**。

4. **量化口径与跨表冲突待核项**
   - `TDF_001` 复合候选计数口径、愤怒/喜悦等相邻情绪分档判据、古代言情跨表层级冲突、部分静态/动态网络简写端点。

### 3.2 补全资料后的标准工程接入流程（严禁直接涂改 `02_原版资料/`）

为保证全仓库 SHA-256 证据链不断裂：
1. **保持 `02_原版资料/` 只读不动**；将作者确认的新增/修补资料写入独立的补充源文件（例如放入受控补充目录并登记到 `workspace/materials/资料来源补充_F2.json` 补充清单）。
2. 若在 `src/nw/materials/steps/*.py` 中同步写入【本步用法】，**必须严格遵守 `stage_input.py` 的标题格式**：
   - 《资料库》条目必须使用完整复合标题：`### 板块XX 板块名#子项名`
   - 紧接 `【本步用法】` 段落写出当前步骤的具体操作、前置核对与检验标准。
3. 依次执行命令重建目录、裁定与原义索引（均无需外部 API）：
   ```powershell
   cd D:\搭建\07_新框架_v0
   $env:PYTHONPATH = "src"
   .\.venv\Scripts\python.exe -m nw materials adjudicate
   .\.venv\Scripts\python.exe -m nw materials audit-semantics --write-index
   ```

---

## 四、能力相近区说明（已由 Carbon 完成底座，Opus 5.5 可按需深化）

以下两部分属于 Carbon 与 Opus 5.5 能力接近的领域，Carbon 已按高标准完成工程闭环并通过测试，留给 Opus 5.5 清晰的扩展切口：

### 4.1 本地前端客户端（`src/nw/studio/`）的视觉与交互深化点
Carbon 已采用 **零第三方依赖架构**（Python 标准库 `ThreadingHTTPServer` + 原生模块化 HTML5/CSS3/ES6）将整套写作系统装入客户端：
- 后端服务层：[src/nw/studio/api.py](file:///D:/搭建/07_新框架_v0/src/nw/studio/api.py)（提供项目、卡片、状态矩阵、14步干跑模拟、POV 工作包检视、离线样章草稿/StateDelta/批次验收、22,941 条资料检索、F2 台账筛选、双模型路由配置全套接口）
- HTTP 路由层：[src/nw/studio/server.py](file:///D:/搭建/07_新框架_v0/src/nw/studio/server.py)
- 前端静态层：[index.html](file:///D:/搭建/07_新框架_v0/src/nw/studio/static/index.html)、[styles.css](file:///D:/搭建/07_新框架_v0/src/nw/studio/static/styles.css)、[app.js](file:///D:/搭建/07_新框架_v0/src/nw/studio/static/app.js)

**Opus 5.5 可发挥前端审美优势继续增强的方向**：
1. **沉浸式双栏/三栏「禅意写作审校视图（Zen Reader & Diff View）」**：在 `tab-scenes` 中增加多版本草稿逐段 Diff 高亮，以及点击 `StateDelta` 的 `evidence[start:end]` 时在草稿正文中自动滚动并荧光高亮对应原句。
2. **SVG 交互式人物关系与事件因果拓扑图**：利用 `/api/projects/<name>/cards` 返回的 `links` 与 `state-matrix` 数据，在前端绘制可拖拽的人物关系网与伏笔埋设—回收时间轴。
3. **接入真实 API 后的实时任务流抽屉（Job Stepper Drawer）**：当前后端已提供 `/api/projects/<name>/jobs` 创建与取消接口；接入 API 后可在前端补充 `novel resume` 与人工门禁确认按钮（`plan:confirm`、`core-state`、`batch:confirm`）的一键弹窗审批交互。

### 4.2 跨步防遗忘与多资料协同守卫（`src/nw/materials/step_guard.py`）
Carbon 在 [step_guard.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/step_guard.py) 中实现了三大核心机制：
1. `build_continuity_ledger(stage, products, deps, context)`：针对未直连某上游步骤的中后段步骤（例如 `state_transition` 未直连 `world_design`；`anchor_design` 未直连 `plot_design` 与 `world_design`），在不改动 `REQUIRES` 冻结输入哈希的前提下，通过 `payload['continuity_ledger']` 自动注入精简的 `type_guard`、`world_guard`、`plot_guard`（含伏笔窗口与读者情绪转向）和 `entity_guard`（非公开实体与不可行动实体提醒）。
2. `build_joint_material_plan(stage, sources)`：当单步联合召回 `>=2` 份资料时，自动按 `profile` 归入 `drivers`（驱动推进）、`boundaries`（边界限制）、`anchors_and_expression`（锚点表达）与 `needs_instantiation_or_clause_guard`（候选模板或局部缺义条款提醒），并强制声明五级裁决优先级：`accepted_state > brief > upstream_products > design_ready > reference_template`。
3. `validate_cross_step_consistency(stage, value, products, context)`：在 `scene_design` 拦截同场同实体多事件 `before_state` 自相矛盾；在 `state_transition` 拦截 `after_state` 冲突及 `TODO`/`TBD`/`待定`/`<填写>` 等占位符幻觉。

**Opus 5.5 可继续微调之处**：若在实测写作中发现某类特定题材下多份表达资料仍有风格打架，可在 `build_joint_material_plan` 中细化 `expression` 与 `type_expression` 之间的主次融合提示语。

---

## 五、最终阶段：API 接入与真实创作调试作战流程

当资料补全与前端精修就绪、准备正式接入 API 进入创作测试时，按以下四步即可零摩擦启动：

1. **在操作系统环境变量中配置网关密钥（切勿写入任何代码或 TOML 文件）**：
   ```powershell
   $env:NOVEL_GATEWAY_API_KEY = "你的真实网关密钥"
   ```
2. **启动写作客户端并启用双模型分工预设**：
   双击 [启动写作客户端.bat](file:///D:/搭建/07_新框架_v0/启动写作客户端.bat)（或运行 `python -m nw studio --open-browser`），进入「**06 · API接入与双模型分工配置**」，点击「**Gemini 4 Carbon + Claude Opus 5.5 黄金双模型分工模式**」，填入真实网关 `base_url`，点击「**校验并写入 config.toml**」。
3. **先跑「14步沙盘干跑」再跑真实 `plan propose`**：
   在「**02 · 14步创作与联合资料沙盘**」中用《潮痕入骨》首章 Brief 逐一检视第 1–14 步召回的资料组合与 `continuity_ledger`，确认无噪声资料混入后，发起正式书级（7步）与首章（14步）规划。
4. **逐场检验「写—审—改—提—核—受」闭环**：
   重点观察首章前 3 场：
   - 同视角场际衔接（前场末尾 1,200 字）是否自然；
   - `StateDelta` 提取出的事实是否 100% 带精确原文区间且无人物误信混入 `WORLD`；
   - 第一章全部验收后记录百字 `chapter-summary`，验证第二章 `plot_design` 是否准确承接章末状态。

---

## 六、严禁破坏的五条工程红线（必读）

1. **禁止无意改动 `adjudication.py:_code_hash` 监控的 21 个核心裁定文件**（见 [adjudication.py](file:///D:/搭建/07_新框架_v0/src/nw/materials/adjudication.py#L35-L38)），否则 `workspace/materials/adjudication.db`（312MB）会判定为 `stale` 并要求耗费数分钟全量重算。
2. **禁止直接修改 `phase_routes.py` 中的 `REQUIRES` 拓扑字典**，否则已有保存链的 `verify_chain` 输入哈希对账会失效；任何跨步补充记忆统一走 `step_guard.py:build_continuity_ledger`。
3. **禁止向 `pyproject.toml` 引入第三方运行时依赖**，保持纯 Python 3.14 标准库零依赖可移植架构。
4. **禁止在任何文件、数据库或前端缓存中保存 API Key 明文**。
5. **每次增删改文件后必须同步更新根目录 [00_资料说明.md](file:///D:/搭建/00_资料说明.md) 并运行全量 `pytest`**。
