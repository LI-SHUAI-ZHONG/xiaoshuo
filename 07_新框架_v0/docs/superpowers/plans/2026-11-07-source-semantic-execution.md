# 原义逐项执行与配套规则接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Independent source audit/compiler tasks use superpowers:dispatching-parallel-agents.

**Goal:** 按已批准小说工作流，把有效资料的原义义务、项目实例、真实产物及下游检验连通，执行7份配套文档的原定规则。本轮不调用真实模型。

**Architecture:** 原件保持只读。来源资格与项目方法用途分开；逐原义条件、操作、限制、判据形成独立合同，阶段实例引用冻结输入与实际产物路径；逐义务进入后续设计、写审和接受检查。7份治理原文单独编译为有版本、作用域的确定性检查或明确的语义/裁定门，不从名称或自评分发明规则。

**Tech Stack:** 现有Windows Python标准库、SQLite及pytest，无新增依赖或服务。

**Spec:** `08_工作流设计/小说工作流设计_v1.md`第4–9节；`05_小说资料全量融入计划_v1.md`第1、3–5节；7份冻结治理文档及资料原件。已复现缺口见任务work/round19-semantic-audit.{json,md}、round19-governance-audit.{json,md}。

## Global Constraints

- 作者要求先完成工程接入，不运行真实模型；假模型仅在明确隔离测试Store，不写正式正文。
- 不改、不删、不移动01–06及ACCOS；不改已接受正文，不补造原文、枚举或定量阈值，不继承旧项目授权。
- 阶段顺序沿用需求→类型/连接→世界/人物→关系→剧情/事件/动作→场景→变化/传播→锚点→表达→冻结→写审接受。前置缺失只影响相应任务。
- 导航边不是书内实体关系；候选不是已完成事件；正式状态依赖同稿正文证据与接受事务。
- 自然语言语义不能由字符串非空、关键词或模型自评分自动通过；独立检查必须逐条有依据。
- 旧工作树含既有未提交改动，继续本次已授权目录施工，不重置、不混合提交、无推送。
- 工作记录放当前任务work，交付放outputs；收尾更新根00说明、原文范围对账、工程回归与限制。

## Review Focus

1. metadata/reference中有实质方法字段的adapter不能因旧profile被丢到governance。
2. 使用读者波形、伏笔子项、动作法和锚点时，任意字符串/无关动作不能替代实际对应设计。
3. 后置动态规则只有采用过真实上游静态关系才能使用；待建剧情端点须后置绑定，不凭空提前创建。
4. 运用层被拒字段不得重新发送；对齐指导要有当前项目转译及独立layer_check。
5. 缺输入/枚举/算法或原义冲突不得空集通过；通过的结构检查不冒充语义判断。

### Task 1: 原文逐义务合同（工程完成，原义未决项保留）

**Files:** 新增materials/source_semantics.py及必要semantic_fields.py；tests/test_material_source_semantics.py。

**Interfaces:** `compile_semantics(source, context=None)->dict`输出原义条款、条件/例外、参数/限制、来源/层定位、依赖、阶段和哈希；`infer_stages(original,profile,key='',context=None)->list[str]`只覆盖已识别原始对象形状，其他由既有发现路由处理。

- [x] 按真实原文写adapter、动作三条、伏笔窗口、三网及拒绝层字段的失败测试，实跑红。
- [x] 实现逐字段/逐句定位与义务编译；metadata不生成创作义务，未解释文本保留未验证，不以资格替代原义。
- [x] 实跑新合同测试，核对原字段/条款覆盖和版本敏感性。

### Task 2: 七份配套原文的实际消费者

**Files:** 新增materials/governance_contracts.py、governance_checks.py及必要小模块；tests/test_material_governance_execution.py。

**Interfaces:** `compile_governance(documents)->dict`，`evaluate_governance(contract,inputs)->dict`。documents包含name/value/source_ref/document_ref；inputs明确scope、subjects、registries、project_config、execution_trace及独立审查/作者决定。逐规则输出来源、实际输入、status、findings、影响范围。

- [x] 对4份验证合同53条、5个限额与标志、33模板字段/字段format建立原文清单。
- [x] 原定整数范围、枚举、引用、依赖、状态权限、限制及轨迹检查分别写正反例并实跑红。
- [x] 实现仅有明确原义依据的确定性检查；相似/原创阈值未定义不发明，转为有来源的独立判断要求。
- [x] 无输入、缺枚举、原义变更/冲突返回明确waiting/failed；不将损坏字段扩大成整库阻断。
- [x] 实跑专门规则测试，逐条登记执行证据；治理规则不能成为正文自动生成权限。

### Task 3: 当前阶段实例与领域合同

**Files:** 新增materials/semantic_application.py、semantic_products.py；修改phase_contract.py、phase_schema.py、phase_routes.py；tests/test_material_semantic_application.py及来源反例回归。

**Interfaces:** 产物新增`_criteria`，每项引用source_id/contract_sha256，每条义务记录适用性、原文义务ID、真实input/output JSON路径、操作、表现及判据。结构路径不能指向自身标签或空值。领域产物分别落实读者信息/情绪/触发、伏笔埋设/回收窗口、动作前因及顺序、锚点的所选动作/对象/时机、采用静态关系的后置端点。

- [x] 将原文已复现的4个错误方案变为红测试；覆盖metadata方法真实路线、错输入hash、空/伪落点及弃选动作。
- [x] 实现逐义务完整性及领域结构/依赖检查，不把NL判断变成关键词匹配通过。
- [x] 允许未到触发时机的明确条件预案；不适用/等待必须有当前任务依据，不因template一律弃用。
- [x] 正反例回归通过后进入主入口。

### Task 4: 正常入口、下游检查和全量源义账本

**Files:** 修改phase_flow.py、phase_projection.py、work_application.py、work_session.py及必要planning/accept入口；新增semantic_audit.py和CLI；更新隔离fixture。

- [x] 正常新设计采用带原义义务的版本化合同，按当前步骤冻结，不恢复全库统一研读。
- [x] 每条实际采用义务进入相应下游检查和源/层回链；不能只用一条整段原文检查代替所有条件。
- [x] 治理数据/项目约束接到对应创建、选择、审查、接受和续写消费者；未知作用域保持待裁定，不擅自改义。
- [x] 新合同与原文/层/输入hash同时复验，旧记录保留可读，不伪装升级为新语义证明。
- [x] 对当前冻结范围逐原始owner及其字段/条款生成实核账本：义务、结构/导航、缺义/争议分别对账。原文及单元hash验证，不重复读取大BLOB。
- [x] 各有效路线运行隔离的正反例；逐项出处与规则消费者可回放，不将生成的标签计为语义通过。

### Task 5: 收尾核验与如实交付

- [x] 运行本轮专测和完整`.venv/Scripts/python.exe -m pytest`，临时目录放新的`.venv/_qa_*`。
- [ ] 最终接入的额外独立代码复审：专项原文审计已完成；额度中断后由主进程自查和96项相关回归，未冒充新增独立复审。
- [x] 更新07文档与根00；outputs保存源义/治理逐条清单、消费者覆盖、工程结果和未解来源问题。
- [x] 真实模型/文学效果保持暂缓，不借工程通过宣布文学或全部源问题已解决；无提交、无推送。

## 2026-11-07工程结果

已完成上述工程接入及全量原义定位对账：23,012 owner、552,014条款位置、定位/字段错误0。全量758 passed in 242.32s (0:04:02)；随后96 passed in 16.95s，与全量重叠不相加。无真实模型调用，未修造缺失原文/枚举/评分定义，逐项自然语言语义和真实文学效果未宣称全量通过，M10保持IN_PROGRESS。当前状态、入口和未决项见docs/资料原义与治理执行.md及任务outputs/19文件。
