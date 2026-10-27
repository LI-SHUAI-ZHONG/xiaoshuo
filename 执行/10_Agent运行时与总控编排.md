# 执行 10：Agent 运行时与总控编排

## 任务目标

建立可注册、可授权、可预算、可追踪的无状态 Agent Runtime。总控只负责解释目标、选择工作流和分配任务，Workflow Engine 仍是唯一状态调度者。

## 前置条件

- 执行 09 的模型与工具契约测试通过。
- `framework_smoke` 工作流可调用 Fake Provider。

## 本阶段实施

1. 创建 `agents` 模块，定义：
   - `AgentDescriptor`：ID、版本、能力、输入/输出 schema、允许工具、模型策略、预算上限；
   - `AgentRun`：任务、上下文快照引用、状态、尝试、结果引用、用量和错误；
   - `AgentRegistry`、`AgentExecutor`、`AgentSupervisor` 端口。
2. 注册无内容描述符：Director、Research、World、Character、Writer、Editor、Quality。它们只有契约与能力名称，不含 Prompt 或创作规则。
3. Director/Master 只允许输出类型化的 `WorkflowSelection` 或 `WorkflowPlanProposal`；必须经过 schema 校验、权限/预算检查和必要的人工批准。
4. Agent 本身不拥有业务表，不直接访问 SQL、Redis、S3 或模型 SDK；所有数据访问通过受权 Tool Port 和应用用例。
5. 固化执行边界：最大步骤、最大递归深度、最大并行数、总时长、总调用和总预算；超限进入明确终态。
6. 建立 context snapshot 引用，固定 Agent、模型策略、Prompt 元数据、工具版本、权限和输入摘要，保证重放可追踪。
7. Agent 结果默认是 proposal/draft reference；涉及 Canon、所有权、权限、发布和删除的操作必须进入人工审批 Step。
8. 发布 Agent 状态事件并接入审计、指标和 Workflow；实现 Fake Agent Executor。
9. 添加未知 Agent、越权工具、预算耗尽、schema 不匹配、循环规划和人工拒绝测试。
10. 写入 `docs/handoffs/10.md`。

## 本阶段不做

- 不填充 Agent Prompt、人设、专业知识或创作策略。
- 不允许 Agent 获得通用 Shell、任意网络、任意文件或跨工作区权限。
- 不实现“Agent 文明”自治组织、自由繁殖 Agent 或自行部署。

## 验证

- Fake Director 能选择 `framework_smoke`，Workflow 执行并返回固定技术结果。
- 未注册 Agent、超预算、递归超限、越权 Tool 和错误输出 schema 均失败且可诊断。
- Worker 重试不会产生两个 Agent 业务结果或重复用量结算。
- Agent 任务重放能查到完全相同的 descriptor/policy/tool/context 版本。
- 架构测试证明 Agent 不直接依赖具体基础设施或其他模块仓储。

## 完成标准

- “提交技术目标—Director 选择工作流—Fake Agent/Fake Model 执行—状态持久化”的纵向空链路通过。
- `docs/handoffs/10.md` 标记 `PASS`，附 Agent 状态图和安全限额。

