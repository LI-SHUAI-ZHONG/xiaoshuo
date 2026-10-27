# 步骤 27：真实模型Prompt与Agent执行

本卡是待授权执行的施工/验收要求，不是完成记录。当前状态以[进度](../进度.json)和实际交接证据为准；任务范围与接手规则见[13](../13_接管说明与施工断点.md)。

## 先读与前置

[00总览](../00_开始这里.md)、[02裁决](../02_冲突裁决与范围.md)、[04架构](../04_目标架构与运行契约.md)、[05数据/API](../05_数据模型API事件规范.md)、[06创作流程](../06_完整小说创作工作流.md)、[07界面/内容](../07_界面高级能力与内容分配.md)、[09迁移](../09_迁移交付与恢复.md)、[11协议](../11_关键协议与默认运行包.md)；再读本卡对应R/T和直接前置的实际`docs/handoffs/NN.md`。相关源码按当前版本核对，CodeGraph存在时优先使用；前端遵守其AGENTS.md与本地Next文档。

直接依赖：`25`、`26`。默认仍按24→45编号顺序执行；这是依赖清单，不是并行或跳号授权。

25凭据/预算设置，26内容读写；现有ModelRequest metadata-only和FakeAgentExecutor。

## 文件落点

后端相对根为`services/core/src/accos/`；resources相对`services/core/`。以下为现有或应新增目标，实施前先查同职能文件并复用。

modules/models/{application,prompts,registry,budgets}.py；adapters/models；modules/agents；composition factories；services/core/resources/prompts；API/client/Studio配置。

## 依序实施

1. 新增内容型ModelInvocation v2并兼容旧测试协议；解析受权ContentRef，真实输入/output存储，不把正文塞日志。

2. 实现OpenAI Responses、独立Chat Completions兼容、Ollama chat/embed及OpenAI embedding适配器，能力/参数/模型名配置化；按官方协议实现schema/工具/流/拒绝/未完成/错误。

3. 实现Prompt registry/renderer/版本发布、变量/输出校验，先交director和公共任务协议；后续各步补自己专业模板。wheel/Docker必须包含resources。

4. 实现真实AgentExecutor：任务/上下文→Prompt→模型/受权工具→有界工具循环→结构化产物。Planner任务与普通角色结果区分，不固定返回framework_smoke。

5. PG原子预算预留/结算/unknown和多worker配额；重试/fallback计费、超时对账、cache按scope/版本/隐私；不能以未知价为0费用。

6. API/Worker共用factory，正常模式未配置即CONFIG_REQUIRED，Fake只显式测试/演示；写Settings、Prompt/调用历史/模型策略界面。

## 契约与防冲突边界

invoke/stream/embed公共端口；ProviderProfile能力版本；ModelCallSettled；工具结果call关联；预算reservation持久状态。

施工不发模型试调用。前后端显示已实现与未配置/未测试分开，不能拿Fake顶替真实输出。

## 本步必须覆盖

| 需求 | 完成行为 | 最后统一验收 |
|---|---|---|
| R017 真实云模型网关 | Responses文本/结构/工具/错误与用量真实映射 | T017 |
| R018 兼容协议和本地模型 | 独立Chat Completions和Ollama chat/embed，不假定能力相同 | T018 |
| R019 通用Prompt正文与运行Agent | 模板有正文/变量/schema、版本冻结、真实Agent执行并保存结果 | T019 |
| R020 流式生成和中断语义 | chunk暂存、完整输出落盘再完成、refusal/incomplete/取消分态 | T020 |
| R021 共享预算与多模型路由 | PG原子预留/结算/unknown，Redis共享限流，fallback遵守隐私 | T021 |
| R022 模型能力/价格/参数配置 | 按任务能力路由、tokenizer/维度/价格版本、缓存scope与Prompt版本 | T022 |
| R023 模型调用评价与历史 | 历史列表、输入输出ref、延时/费用/错误、可比较模型profile | T023 |

## 施工完成条件（不是测试通过）

领域行为、schema/迁移、权限、持久化/异步接线、API/生成客户端、页面操作和恢复全部有实码；软件运行Prompt/工作流/rubric按本步需要交付。新增依赖由同一步维护唯一锁文件；新增迁移读取真实head追加，不改旧迁移。无业务内容时空库合法，但不能以此省略实现。

编写上述T的必要测试/夹具和执行入口，登记[统一待测试表](../08_统一待测试表.md)，**不运行**。只允许确认无测试/服务/外网副作用的静态核对/代码生成，旧check/quick/lint/api:check不得直接调用。

全部实码完成可标IMPLEMENTED_UNTESTED；缺核心实现为IN_PROGRESS/BLOCKED并说明具体动作。缺外部配置单列，不用Fake顶替。一次只由当前步骤修改共享迁移/组合根/路由/锁文件，禁止复制第二份事实模型。

## 交接与下一步

每Provider支持矩阵、密钥引用、v1/v2兼容、正常/Fake装配路径、实际通用Prompt列表。

更新`docs/handoffs/27.md`及[进度.json](../进度.json)：实际文件、R项、迁移head/是否执行、API/事件/配置、静态核对（与运行测试分开）、T项、外部缺项/风险、恢复路径、下一动作。正文/密钥不得进入日志或公开交接。

下一步：[28 依赖工作流调度与总控](28_依赖工作流调度与总控.md)。满足本步施工完成条件后直接继续；无需按天等待或为正常可逆实施重复确认。
