# 架构导览

> 2026-09-24：完整产品施工采用 [17 完整产品架构定版](17-full-product-contracts.md) 与
> [ADR 0006](../adr/0006-full-product-scope-and-single-ownership.md) 至 0009。
> 下文“仅骨架、扩展只预留、不交付 Prompt”描述原 01–23 的范围，不再限制后续 24–44。
> 实际实现/验收状态见 `后续执行/进度.json`，并非本文表格中的承载位置。

本目录把愿景中的五层结构收敛到可逐步验证的工程边界。当前只有架构契约；表格中的“承载位置”表示计划归属，不表示功能已经实现。

## 五层蓝图映射

| 蓝图层 | 责任 | 仓库承载位置 | 第一版边界 |
|---|---|---|---|
| 1. Creator Interface Layer | 创作者交互、工作台、命令与策略界面 | `apps/studio/`、`packages/ui/`、`packages/api-client/` | Next.js Studio 只通过生成客户端访问 `/api/v1`；本地 UI 状态与服务端状态分离 |
| 2. Creative Intelligence Layer | 上下文、记忆、知识、质量与创作域推理 | `services/core/src/accos/modules/` 中的 `knowledge`、`memory`、`creative`、`consistency`、`quality`、`feedback`、`evolution` | 只建立公开契约、确定性规则与 Fake 链路；不填充真实创作内容或正式 Prompt |
| 3. Agent Civilization Layer | Agent 注册、编排、专业能力与工具协作 | `agents`、`workflows`、`tools`、`models` 模块 | Agent 受工作流、权限、预算和人工关卡约束；不是自治组织，也不能自改代码或部署 |
| 4. Creative Infrastructure Layer | 工作流、数据、资产、Provider、权限与稳定运行 | `services/core/src/accos/adapters/`、`identity`、`projects`、`assets`、`infra/` | PostgreSQL + pgvector、Redis、S3/MinIO；外部系统经端口接入 |
| 5. Core Kernel Layer | 调度、事件、资源、状态和横切契约 | `services/core/src/accos/kernel/`、`entrypoints/`、独立 Worker、事务 Outbox | 模块化单体内核与独立进程入口；没有负载证据前不拆微服务 |

Creator Economy、市场、版权交易和收益分成不在 `v0.1-skeleton` 范围。多模态、协作和生态能力在后续阶段仅以端口和默认关闭的功能开关预留。

## 阅读顺序

1. [`00-system-context.md`](00-system-context.md)：系统、用户与外部边界。
2. [`01-container-view.md`](01-container-view.md)：Studio、API、Worker 和存储的运行关系。
3. [`02-module-dependency-rules.md`](02-module-dependency-rules.md)：允许的源码依赖和协作方式。
4. [`03-data-ownership-matrix.md`](03-data-ownership-matrix.md)：每个预留模块的数据所有权。
5. [`04-feature-flag-strategy.md`](04-feature-flag-strategy.md)：远期能力如何安全预留和启用。
6. [`05-service-extraction-criteria.md`](05-service-extraction-criteria.md)：何时才允许拆分微服务。
7. [`06-identity-permission-matrix.md`](06-identity-permission-matrix.md)：固定角色、统一授权与创作者控制协议。
8. [`07-project-asset-core.md`](07-project-asset-core.md)：项目、Artifact、资产版本与对象补偿协议。
9. [`08-workflow-engine.md`](08-workflow-engine.md)：持久化工作流、队列投递、租约恢复与人工审批协议。
10. [`09-model-tool-gateways.md`](09-model-tool-gateways.md)：模型/工具路由、预算、最小权限、插件 manifest 与调用账本。
11. [`10-agent-runtime.md`](10-agent-runtime.md)：Agent 注册、Director 总控、上下文快照、安全限额与人工关卡。
12. [`11-knowledge-pipeline.md`](11-knowledge-pipeline.md)：可恢复知识采集、可重建投影、来源引用、隔离检索与离线研究接口。
13. [`12-memory-context.md`](12-memory-context.md)：七层统一记忆、授权 anchor、保留/冲突和有预算 Context Package。
14. [`13-creative-domains.md`](13-creative-domains.md)：Novel、World、Character、Creator 唯一归属、提案审批、事件防循环与 Null 扩展端口。
15. [`14-consistency-quality.md`](14-consistency-quality.md)：Canon/时间线引用、确定性 Finding、诚实检查状态、人工 Resolution 与质量门禁。
16. [`15-feedback-evolution.md`](15-feedback-evolution.md)：同意、脱敏指标、只读诊断、技术烟雾实验与人工批准的受控 Evolution。
17. [`16-api-contracts.md`](16-api-contracts.md)：`/api/v1` 信任边界、公共传输契约、OpenAPI 客户端与版本/弃用策略。

## 已接受决策

- [ADR 0001：模块化单体与独立 Worker](../adr/0001-modular-monolith-and-worker.md)
- [ADR 0002：数据与存储基线](../adr/0002-data-and-storage.md)
- [ADR 0003：REST、OpenAPI 与 SSE](../adr/0003-rest-openapi-and-sse.md)
- [ADR 0004：创作者所有权与人工批准](../adr/0004-creator-ownership-and-human-approval.md)
- [ADR 0005：Provider、工具与插件边界](../adr/0005-provider-and-plugin-boundaries.md)

## 架构不变量

- PostgreSQL 是持久业务状态的事实源；Redis 不是。
- 模块的数据只能由拥有者写入，其他模块通过公开契约请求或订阅事件。
- 外部 SDK 只出现在 adapters 和组合根中。
- 工作区权限、预算与人工批准均在服务端执行，且不能由功能开关绕过。
- 任何“完成”声明都必须对应可运行、可迁移、可测试的证据；端口或 Fake 只能称为骨架能力。
