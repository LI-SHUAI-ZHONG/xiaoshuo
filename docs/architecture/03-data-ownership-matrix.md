# 数据所有权矩阵

## 原则

- “同一 PostgreSQL”不等于“共享数据”。一个持久记录只能有一个模块拥有者。
- 只有拥有者可以定义 schema、迁移、写入和删除规则。
- 其他模块通过公开 application/port、版本化事件或拥有者维护的投影访问。
- 除平台级公共配置外，业务记录显式包含 `workspace_id`；项目级记录同时包含 `project_id`。
- 仓储必须在服务端强制工作区过滤；调用者传入对象 ID 不能绕过范围。

## 模块矩阵

| 模块 | 拥有的数据 | 对外公开边界 | 禁止直接访问 |
|---|---|---|---|
| `identity` | 主体映射、工作区、成员关系、角色绑定、授权策略引用、身份审计元数据 | 当前主体/工作区上下文、权限判定、成员管理用例、成员变更事件 | 其他模块不得写成员或角色表；不得把前端可见性当授权 |
| `projects` | 项目、项目设置与生命周期、Artifact 容器和不可变修订元数据 | 项目/Artifact 命令与查询、项目存在性与范围校验、版本化生命周期事件 | 不拥有资产二进制、具体创作域对象或工作流状态 |
| `assets` | 对象元数据、对象键、校验值、媒体类型、版本、上传状态、保留状态 | 上传/下载授权、对象元数据查询、资产版本事件 | 不读取 S3 key 作为权限；其他模块不得直接改对象元数据 |
| `workflows` | 工作流定义引用、运行、步骤、重试、取消、检查点、幂等记录、任务事件 | 启动/取消/恢复用例、状态查询、进度事件 | 不拥有 Agent 配置、模型调用账本或领域产物 |
| `models` | Provider 配置引用、能力目录、路由策略、配额、模型调用账本 | 模型网关端口、能力查询、用量/预算结果、调用审计事件 | 不保存真实密钥；其他模块不得直接调用供应商 SDK |
| `tools` | 工具目录、能力声明、权限授予、执行记录、工具调用账本 | 工具网关端口、授权检查、执行结果与审计事件 | 不隐式继承工作区全部权限；不拥有 Provider 业务数据 |
| `agents` | Agent 定义、版本、能力绑定、运行分配、预算引用、人工关卡引用 | 注册/调度契约、Agent 运行结果、生命周期事件 | 不直接写工作流步骤、模型账本、工具账本或创作对象 |
| `knowledge` | 来源元数据、采集记录、分段、嵌入引用、索引状态、引用关系 | 采集/检索端口、可追溯检索结果、索引事件 | 不把外部资料当创作者内容；其他模块不得直接查询向量表 |
| `memory` | 分层记忆项、来源引用、作用域、有效期、冲突候选、上下文包引用 | 记忆写入/检索、上下文构建、冲突提案事件 | 不自行覆盖冲突记忆；其他模块不得读取私有记忆表 |
| `creative` | 创作域对象及版本；未来的 `novel`、`world`、`character`、`creator` 子域记录 | 创作命令/查询、版本与领域事件 | 不拥有资产二进制、知识来源、记忆项或质量报告；子域不得跨私有表耦合 |
| `consistency` | Canon 规则引用、一致性检查运行、确定性问题、修复提案 | 检查用例、问题报告、提案事件 | 不直接修改 `creative` 数据；修复必须由拥有者应用并受审批 |
| `quality` | 评估定义引用、评估运行、维度结果、质量问题、来源证据 | 评估端口、报告查询、质量事件 | 不直接修改创作内容；不得把模型分数当无证据事实 |
| `feedback` | 反馈提交、来源、分类、指标观察、聚合引用 | 反馈采集/查询、指标事件 | 不修改创作者偏好、创作对象或实验配置 |
| `evolution` | 改进提案、证据引用、审批、实验引用、应用状态、回滚引用 | 提案生命周期、人工批准/拒绝、状态事件 | 不自行改代码、权限、策略或部署；不绕过目标模块公开命令 |

## 平台技术表

平台技术表不归任何业务模块共享写入。其唯一拥有者与写路径如下：

| 表 | 唯一拥有者 | 允许写路径 | 扩展规则 |
|---|---|---|---|
| `public.alembic_version` | Alembic 迁移运行时 | 仅 `alembic upgrade/downgrade` | 禁止应用代码修改 |
| `accos.schema_metadata` | persistence 平台适配器 | 仅版本化迁移 | 记录组件与迁移修订，不承载业务配置 |
| `accos.idempotency_records` | persistence 平台适配器 | 应用层 UoW 内的 `IdempotencyStore` | 模块必须使用显式 workspace/scope/key；不得自行建立无约束重试表 |
| `accos.outbox_events` | persistence 平台适配器 | 业务 UoW 内只追加事件；仅 Outbox Relay 更新租约、重试与发布状态 | 普通 Worker 不得扫描业务表或直接把事件标为已发布 |

新业务表必须由一个命名模块拥有，并同时增加迁移、该模块私有 ORM 映射、仓储过滤测试和本矩阵条目。不得把 ORM Model 放入模块公开契约；跨模块读取仍通过拥有者的 application/port 或版本化事件。

## Identity 模块已落地表

| 表 | 唯一写路径 | 隔离与不可变规则 |
|---|---|---|
| `accos.identity_users` | identity 身份映射适配器 | issuer + subject 唯一；全局主体映射例外，不承载用户画像 |
| `accos.identity_workspaces` | identity 工作区管理用例 | 创作者控制的顶级边界；不允许其他模块改 owner |
| `accos.identity_memberships` | identity 成员管理用例 | 每次查询必须同时带 workspace/user；角色仅服务端解析 |
| `accos.identity_service_identities` | identity ServiceIdentity 管理用例 | workspace scoped；权限与 SERVICE 硬上限取交集 |
| `accos.identity_control_requests` | identity 创作者控制用例 | 只保存所有权/导出/归档/删除请求状态；不执行物理删除 |
| `accos.identity_human_approvals` | identity 人工批准用例 | 每个请求一次决定；应用无更新/删除端口，数据库 trigger 阻止修改 |
| `accos.audit_events` | identity 统一授权审计器 | workspace scoped append-only；数据库 trigger 阻止更新/删除，payload 严格 allowlist |

## Projects 与 Assets 模块已落地表

| 表 | 唯一写路径 | 隔离与生命周期规则 |
|---|---|---|
| `accos.projects` | projects 应用服务与 scoped repository | Workspace 必填；整数乐观锁；归档后禁止写入 |
| `accos.project_artifacts` | projects Artifact 用例 | Workspace + Project 双 scope；仅作为版本容器 |
| `accos.project_artifact_revisions` | projects Revision 用例 | 每个 Artifact 的 revision_number 唯一，只追加 |
| `accos.assets` | assets 应用服务与 scoped repository | Workspace + Project 双 scope；删除只有标记与保留期 |
| `accos.asset_versions` | assets 上传/补偿用例 | 对象键唯一；Project 内 SHA-256 去重；缺失对象状态可诊断 |
| `accos.asset_upload_sessions` | assets 上传/补偿用例 | 对象写入前建立；记录 partial failure；不承担永久清理 |

## Workflows 模块已落地表

| 表 | 唯一写路径 | 隔离与生命周期规则 |
|---|---|---|
| `accos.workflow_definitions` | workflows 定义仓储 | `name + definition_version` 唯一；数据库 trigger 禁止更新/删除 |
| `accos.workflow_step_definitions` | workflows 定义仓储 | 定义内 key/position 唯一且连续；数据库 trigger 禁止更新/删除 |
| `accos.workflow_runs` | workflows 应用服务与 Worker 仓储 | Workspace + Project 双 scope；显式状态机与整数版本；Redis 不拥有状态 |
| `accos.workflow_step_runs` | workflows Worker 仓储 | Run 内 position 唯一；保存 attempt、deadline、输入/输出/错误引用 |
| `accos.workflow_task_runs` | workflows Worker 仓储 | Workspace 内幂等键唯一；租约 token/expiry 保护 at-least-once 结算；失败可进入 `dead_letter` |
| `accos.workflow_approval_requests` | workflows 审批用例 | Workspace + Project 双 scope；显式过期；不能自动批准 |
| `accos.workflow_approval_decisions` | workflows 审批用例 | 每个请求只允许一次决定；数据库 trigger 禁止更新/删除 |
| `accos.workflow_run_events` | workflows 状态迁移仓储 | 每个 Run 的 sequence 严格递增且唯一；数据库 trigger 禁止更新/删除 |

## Models 与 Tools 模块已落地表

| 表 | 唯一写路径 | 隔离与不可变规则 |
|---|---|---|
| `accos.model_usage_records` | models 模型网关与 `UsageLedger` | Workspace + Workflow + Task scope；每个 Provider 尝试、预算拒绝和熔断跳过只追加；不存凭据、输入内容或供应商 payload |
| `accos.tool_call_records` | tools 工具网关与 `ToolCallLedger` | Workspace + Workflow + Task scope；授权、schema、scope、超时与执行结果只追加；不存工具输入/输出 payload、网络响应或文件内容 |

`workflow_runs.permission_snapshot` 与 `workflow_runs.policy_version` 仍由 workflows 拥有，只保存提交时的服务端可信授权快照，供 Worker 重建调用上下文。它们不是 models/tools 的共享写字段。Provider 注册、路由策略、工具描述符和测试插件 manifest 当前是版本化代码配置；真实凭据只存在于 `SecretProvider` 边界之后。

## Agents 模块已落地表

| 表 | 唯一写路径 | 隔离与不可变规则 |
|---|---|---|
| `accos.agent_context_snapshots` | agents Supervisor 与 repository | Workspace + Project scope；固定 Agent/模型策略/Prompt 元数据/Tool/权限/输入摘要版本；数据库 trigger 禁止更新/删除，不保存 Prompt 或输入正文 |
| `accos.agent_runs` | agents Supervisor、Master 与 repository | Workspace + Project scope；Workspace 内幂等键唯一；只保存 Workflow/结果引用、稳定状态与一次用量结算，不拥有 Workflow 状态或领域产物 |
| `accos.agent_run_events` | agents repository | 每个 Agent Run 的 sequence 递增且唯一；与事务 Outbox 同事务追加；数据库 trigger 禁止更新/删除 |

Agent Descriptor 当前是版本化代码配置，不是可由 Agent 自行创建或修改的数据库对象。`agent_runs.workflow_run_id` 只保存跨模块引用；Workflow 的步骤、审批、重试、取消与终态仍完全由 workflows 模块写入。

## Knowledge 模块已落地表

| 表 | 唯一写路径 | 隔离、来源与重建规则 |
|---|---|---|
| `accos.knowledge_sources` | knowledge ingestion repository | 每个 AssetVersion 一条不可变来源元数据；保存对象定位符和 SHA-256，不拥有对象字节 |
| `accos.knowledge_documents` | knowledge ingestion repository | Workspace + Project + Asset 的逻辑版本容器 |
| `accos.knowledge_document_versions` | knowledge ingestion repository | 保存规范化事实、状态、验证状态和 active 标记；旧版本保留但不进入默认检索 |
| `accos.knowledge_ingestion_runs` | knowledge service/repository | Workspace 级幂等键、失败阶段、稳定错误、attempt 与恢复检查点；不拥有 Workflow 调度状态 |
| `accos.knowledge_chunks` | knowledge projection replacement | 确定性 version-scoped 分块；重试/重建按版本整体替换 |
| `accos.knowledge_embedding_refs` | knowledge projection replacement | Fake/未来 Embedder 身份、维度、向量 payload 与内容哈希；可从 Chunk 重建 |
| `accos.knowledge_citations` | knowledge projection replacement | 每个 Chunk 固定到 Source/DocumentVersion/AssetVersion locator；随 Chunk 投影替换 |
| `accos.knowledge_vector_index` | `VectorIndex` adapter | Workspace + Project + DocumentVersion scope；原生 pgvector 或测试 shim，永不作为来源事实 |
| `accos.knowledge_edges` | `GraphProjection` adapter | PostgreSQL 内最小 source/contains/cites/derived_from 关系；按版本替换，不引入独立图数据库 |

Assets 仍唯一拥有原始对象和版本元数据。Knowledge 通过 Assets 公共契约读取并校验字节；Agents、Memory、API 与其他模块必须通过 Knowledge 公共 Retriever/Service 获取带来源结果，不得直接查询上述表或对象存储。

## Memory 与 Creative 模块已落地表

| 表 | 唯一写路径 | 隔离、版本与所有权规则 |
|---|---|---|
| `accos.memory_records`、`memory_links`、`memory_grants`、`memory_conflicts`、`memory_context_packages`、`memory_events` | memory 应用服务、仓储与投影重建器 | 七层 Scope/Type、授权 anchor、来源、保留、冲突与 Context Package 由 Memory 唯一拥有；其他模块不得读写私表 |
| `accos.creative_containers` | creative 四 owner 的公共应用服务 | Novel/World/Character/Creator 共用物理表但 owner 不可混淆；Workspace/Project scope 与容器整数版本强制执行 |
| `accos.creative_records` | creative proposal/decision 与公共 Revision 用例 | 版本只追加；同 logical ID 最多一个 current；未批准 proposal 不成为权威事实；跨域模块只能调用 `creative.public` |

Creative 记录只保存结构/状态元数据和 typed references，不保存正文。Consistency 的修复应用必须进入 Creative 公共 Revision 用例，不能直接写这两张表。

## Consistency 与 Quality 模块已落地表

| 表 | 唯一写路径 | 隔离、版本与门禁规则 |
|---|---|---|
| `accos.consistency_canon_entries` | consistency Canon 应用服务 | Level 1–4、逻辑版本、有效时间、来源与显式状态；不复制 Creative 状态 |
| `accos.consistency_timeline_events` | consistency 时间线应用服务 | 只保存权威事件/Revision 的规范化断言和人物/世界状态引用 |
| `accos.consistency_check_runs` | consistency Validator Registry | 保存请求的检查器报告和聚合状态；未运行、未配置、运行失败、Finding 与真正通过不合并 |
| `accos.consistency_findings` | consistency 检查运行 | 保存类型、严重度、证据引用、检查器版本、Workflow、actor 与处置状态 |
| `accos.consistency_resolution_proposals` | consistency 人工决定与应用服务 | 永远需要批准；target 与 Proposal 双版本校验；只有 Creative 返回新 Revision 后标记 applied |
| `accos.consistency_evidence_projection` | consistency ProjectionRebuilder | pointer-only、按 Workspace/Project 整体替换；可从 Creative 公开接口或事件重建，不是事实源 |
| `accos.quality_rubric_versions` | quality schema 注册用例 | 只保存 rubric/dimension key 与 schema/version 元数据，不保存真实评分内容或权重 |
| `accos.quality_evaluation_runs` | quality 评估服务 | 输入与 Workflow 只保存引用；显式记录 not-run/config/failure/pass 状态 |
| `accos.quality_results` | quality evaluator 边界 | 每次运行最多一个结果；维度为 schema key 和机器状态，不拥有创作事实 |

Workflow 只拥有调度与 Approval Step。Consistency 仍需单独保存 Resolution 的显式授权决定；Workflow 通过不能绕过目标版本重校验或直接产生 Creative Revision。Quality 只能读取上游一致性结果，不能修改 Canon、Creative 或 Memory。

## 跨模块公共字段

公共字段由 kernel 定义语义，不代表 kernel 拥有业务数据：

| 字段 | 语义 |
|---|---|
| `id` | 不泄漏顺序的稳定资源标识 |
| `workspace_id` | 授权与隔离范围；不得从对象 ID 推断 |
| `project_id` | 可选项目范围；必须属于同一工作区 |
| `correlation_id` | 一次调用链的关联标识 |
| `created_at` / `updated_at` | UTC 时间；由持久化边界统一处理 |
| `version` | 乐观并发或契约版本，具体语义由拥有者定义 |
| `archived_at` | UTC 软归档时间；空值表示活跃，物理删除由拥有者的保留策略控制 |

## 共享需求处理顺序

当两个模块都需要一份数据时，按以下顺序处理：

1. 确定唯一拥有者和权威写路径。
2. 优先调用拥有者公开查询契约。
3. 若读取量或故障隔离需要本地副本，由拥有者事件建立只读投影，并记录来源版本。
4. 若仍需双向写入，重新审查模块边界；不得建立共享可写表。
