# 数据库迁移、事务与 Outbox 运行手册

## 边界

PostgreSQL 是事务数据的唯一事实源。Redis 只用于队列、缓存与短期协调，不能保存唯一业务副本。应用启动不调用 `create_all`；所有结构变更必须先写 Alembic 修订并在独立空库验证。

当前 head 为 `0010_consistency_quality`，迁移创建：

- `vector` 扩展与 `accos` schema；
- `accos.schema_metadata` 迁移审计元数据；
- `accos.idempotency_records` 幂等请求记录；
- `accos.outbox_events` 事务事件、顺序游标、租约与重试状态；
- `accos.identity_users`、`identity_workspaces`、`identity_memberships` 与 `identity_service_identities`；
- `accos.identity_control_requests` 与 append-only `identity_human_approvals`；
- workspace scoped、数据库级 append-only 的 `accos.audit_events`；
- Project、Artifact/Revision、Asset/Version 与 UploadSession 六张执行 07 表；
- Workflow Definition/Step Definition、Run/Step/Task、Approval Request/Decision 与 Run Event 八张执行 08 表；
- append-only `model_usage_records` 与 `tool_call_records`，以及 Workflow 的可信权限/策略快照；
- Agent Run、append-only Context Snapshot 与 append-only Run Event 三张执行 10 表；
- Knowledge Source/Document/DocumentVersion/IngestionRun 四张事实与状态表，以及 Chunk/EmbeddingRef/Citation/VectorIndex/Edge 五张可重建投影表；
- Memory Record/Link、Grant、Conflict、Context Package 与 Event 六张表，以及 Agent Context Snapshot 的 package 关联；
- Creative Container/Record 两张唯一所有权与版本状态表；
- Consistency Canon/Timeline/Check/Finding/Resolution/EvidenceProjection 六张表；
- Quality RubricVersion/EvaluationRun/Result 三张 schema-only 评估表；
- Alembic 自有的 `public.alembic_version`。

没有创建 Feedback、Evolution 或其他后续模块表；Creative 不保存正文，Consistency 只保存跨域约束、证据指针和人工 Resolution，Quality 不保存真实评分内容或权重。Knowledge/Memory 只保存可追溯事实与技术元数据，Agent 快照不保存 Prompt/原始输入正文，模型与工具只拥有调用账本，不保存密钥或工具 payload。

## 正向迁移与漂移检查

确认 `.env` 指向目标 PostgreSQL 后，从仓库根执行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

```sh
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

`check` 报告新操作时，说明 ORM metadata 与迁移历史不一致。不得用 `create_all` 修补；应审查差异并生成、精简和测试新的修订。

## 回退

只回退执行 14、保留执行 13 Creative 的受控命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0009_creative_domains
```

继续回退执行 13、保留执行 12 Memory/Context 的受控命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0008_memory_context
```

继续回退执行 12、保留执行 11 Knowledge 的受控命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0007_knowledge_pipeline
```

只回退执行 11、保留执行 10 Agent Runtime 的受控命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0006_agent_runtime
```

继续回退执行 10、保留执行 09 模型/工具边界的受控命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0005_model_tool_gateways
```

继续回退执行 09、保留执行 08 Workflow 的受控命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0004_workflow_engine
```

继续回退执行 08、保留执行 07 Project/Asset 的命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0003_projects_assets
```

继续回退执行 07、保留执行 06 Identity/Security 的命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0002_identity_security
```

继续回退执行 06、保留执行 05 技术表的命令是：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0001_persistence
```

只有需要继续回退执行 05 且确认数据库为空时才执行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade base
```

回退至 `0009_creative_domains` 会删除 Consistency/Quality 九张表；回退至 `0008_memory_context` 会继续删除 Creative 两张表；回退至 `0007_knowledge_pipeline` 会继续删除 Memory 六张表和 Agent Context Package 关联；回退至 `0006_agent_runtime` 会继续删除 Knowledge 事实与投影表；回退至 `0005_model_tool_gateways` 会继续删除 Agent Run/Snapshot/Event；回退至 `0004_workflow_engine` 会继续删除模型/工具调用账本及 Workflow 权限快照；回退至 `0003_projects_assets` 会继续删除 workflow 八张表；回退至 `0002_identity_security` 还会删除项目/资产六张表；回退至 `0001_persistence` 还会删除身份、工作区、成员、ServiceIdentity、控制请求、批准和审计记录。每一步都必须先确认无需保留并已有恢复点。回退至 `base` 还会删除三个 `accos` 技术表、schema 和 `vector` 扩展，只能用于空测试库。生产回退优先使用前向修复迁移。

## 事务规则

- 一个应用用例只打开一个 `UnitOfWork`，并在应用层显式 `commit()`；离开上下文但未提交时自动回滚。
- 模块仓储只接收当前 UoW 的 Session，不自行提交，不返回 SQLAlchemy Model。
- 工作区级仓储查询必须显式带 `workspace_id`；项目级查询还要验证同一工作区的 `project_id`。
- 可并发更新的记录使用正整数 `version` 乐观锁；冲突映射为稳定的 `concurrency_conflict`，调用方不得静默覆盖。
- 重试副作用前先在同一事务中保留 `(workspace_id, scope, key)`；同键不同请求摘要返回 `idempotency_conflict`。

## Outbox Relay

业务写入与 `outbox_events` 追加必须在同一 UoW 提交。提交后只有独立 `OutboxRelay` 可以认领事件：

1. 按 `sequence` 顺序使用 `FOR UPDATE SKIP LOCKED` 认领可用事件；
2. 写入租约 token、过期时间和尝试次数并提交认领事务；
3. 在事务外调用 Publisher；
4. 使用相同租约 token 确认发布，或记录稳定失败码和下次可用时间；
5. 进程在发布前或确认前退出时，过期租约可被下一实例重新认领。

投递语义是 at-least-once。Publisher/消费者必须以事件 UUID 做幂等去重；`sequence` 是排查与批次高水位游标，不是唯一业务标识。普通 Worker 不得扫描业务表代替 Relay。

## 测试隔离

数据库集成测试从 `.env` 取得服务器连接信息，为每个用例创建随机命名的独立数据库，执行 `upgrade head`，结束后先终止残留连接再删除数据库。测试不复用开发数据库、不写种子业务数据，因此可由并行测试进程安全执行。

Windows 下 psycopg 异步连接必须使用 Selector 事件循环；迁移、API 和 Worker 入口已统一使用 `selector_loop_factory`。Worker 的 Relay 与 Celery consumer 运行在不同事件循环，consumer 因此使用独立 `NullPool`，禁止共享主异步连接池。连接异常由 readiness 边界转换为稳定状态，不输出连接串或驱动异常文本。
