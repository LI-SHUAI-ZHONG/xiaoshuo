# 执行 05：数据层、迁移、仓储与 Outbox

## 任务目标

建立 PostgreSQL 唯一事实源、数据库迁移、事务工作单元、模块仓储边界和事务 Outbox，为后续所有模块提供可恢复、可审计的数据底座。

## 前置条件

- 执行 04 通过。
- PostgreSQL/pgvector 健康；测试环境可创建独立数据库。

## 本阶段实施

1. 在 `adapters/persistence` 建立 SQLAlchemy 异步引擎、Session 工厂、连接池配置和健康检查；领域层只依赖仓储/UoW 协议。
2. 配置 Alembic，禁止应用启动时自动 `create_all`。首个迁移负责扩展、核心 schema 与版本元数据。
3. 固化通用字段与约束：主键、`workspace_id`、`project_id`、创建/更新时间、乐观锁版本、软归档状态；时间统一 UTC。
4. 建立基础技术表：
   - `outbox_events`：事件 ID、聚合 ID、类型、版本、payload、发生时间、发布状态、重试信息；
   - `idempotency_records`：作用域、键、请求摘要、结果引用、过期时间；
   - `schema_metadata` 或等价迁移审计信息。
5. 定义 `UnitOfWork`、仓储协议、分页规范和事务边界；一个用例只在应用层控制事务。
6. 实现事务 Outbox 写入，以及独立 `OutboxRelay` 的租约、游标、认领、发布确认和失败重试协议；本阶段用内存测试 Publisher 验证 at-least-once 投递，不接 Redis/Celery 业务消费。Relay 负责从数据库发布，不能由普通 Worker 直接扫业务表。
7. 为将来图关系建立 `GraphStore` 端口；默认关系表/递归查询适配器延后，禁止现在引入独立图数据库。
8. 建立数据库测试夹具与并行测试隔离；迁移测试必须从空库执行。
9. 写入数据所有权规则和 `docs/handoffs/05.md`。

## 数据不变量

- PostgreSQL 中的事务数据是权威事实；向量、图投影、缓存和搜索索引都可重建。
- Redis 不保存唯一副本的业务状态。
- 模块只能通过自己的仓储写自己的表；跨模块协作使用应用服务或事件。
- 任何重试路径必须使用幂等键或唯一约束防止重复副作用。

## 本阶段不做

- 不一次性创建所有远期业务表。
- 不填充种子项目、知识、记忆或 Agent 数据。
- 不允许跨模块公开 SQLAlchemy Model 作为 API 契约。

## 验证

- 在全新测试库执行 `upgrade head` 成功；重复检查没有漂移。
- 在临时库完成 `upgrade -> downgrade -> upgrade`，关键数据迁移步骤有说明。
- UoW 提交、回滚、并发冲突、幂等记录和 Outbox 同事务测试通过。
- 模拟进程在提交后、发布前中断，Outbox 仍可被后续发布器认领且只产生一次可见副作用。
- 数据库不可用时 `/ready` 为 not ready，错误与日志不泄露连接凭据。

## 完成标准

- 空库可一键迁移；任何 schema 变化都有迁移文件和测试。
- `docs/handoffs/05.md` 标记 `PASS`，列出当前表、所有者和下一阶段扩展规则。
