# 工作流与 Worker 运行手册

## 当前能力与默认值

执行 08 提供 Python 应用层的 Workflow 提交、查询、暂停、恢复、取消、审批决定/过期和递增事件查询，以及 `accos.workflows.consume` Celery consumer。REST/SSE 路由尚未发布，必须等执行 16/17；不要直接更新 workflow 表或把 Redis/Celery result 当作状态。

| 项目 | 默认值 |
|---|---|
| 通用 RetryPolicy | 最多 3 次；1 秒起步；2 倍指数退避；60 秒封顶 |
| `framework_smoke` RetryPolicy | 最多 3 次；1 秒起步；2 倍退避；8 秒封顶 |
| `framework_smoke` 每次尝试 timeout | 10 秒 |
| Worker 任务租约 | 30 秒 |
| Outbox batch / lease / publish retry | 100 / 30 秒 / 5 秒 |
| Worker Relay 轮询间隔 | 250 ms |
| 审批过期 | 每个 StepDefinition 必须显式配置；没有隐式全局值 |

## 启动

确认 `.env` 使用本地凭据、PostgreSQL 与 Redis 可用，然后先迁移：

```powershell
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

期望 revision 为 `0008_memory_context (head；Workflow 主结构来自 0004)`。另一个终端启动 Worker：

```powershell
uv run --frozen python -m accos.entrypoints.worker
```

启动日志应包含 `registered_tasks=1`，Celery task 列表应包含 `accos.workflows.consume`，并显示已连接到经过脱敏的 Redis 地址。Worker 同时运行唯一 Outbox Relay；不要另写扫描业务表的调度器。普通终端用 `Ctrl+C` 请求有序停止。

## 观察与诊断

以应用查询或只读 SQL 查看事实，重点关联 Run ID、Task ID 和 Outbox event ID。不得手工改状态、租约或 attempt。

| 现象 | 事实检查 | 安全处理 |
|---|---|---|
| Run 长时间 `pending` | 对应 `task-dispatched` Outbox 是否未发布；Redis 是否可用 | 恢复 Redis 并保持 Worker/Relay 运行；Relay 会按 available_at 重试 |
| Task 长时间 `running` | `lease_expires_at`、Worker 日志和数据库连通性 | 恢复 Worker；租约到期后的重复投递会由新 Worker 重新认领 |
| Run `paused` | `pause_requested_at`、当前 Task/Approval | 由具备权限的应用调用 `resume`；普通任务会产生新 dispatch，审批步骤回到等待审批 |
| Run `cancelling` | 当前 Task 是否仍持租约 | 等待执行器返回/超时；Worker 会先补偿再结算 `cancelled` |
| Run `waiting_approval` | pending request、`expires_at`、requester | 由不同的人类 approver 明确批准/拒绝；不得自动批准 |
| Task `dead_letter` / Run `failed` | error reference、attempt、运行事件、补偿结果 | 修复根因后通过应用提交新的 Run/幂等键；本阶段没有直接 redrive 或手工改终态的端口 |
| `workflow-error://compensation-failed` | 原 Task、hook 名与拥有模块的诊断记录 | 人工处理补偿；不要把 Run 改成成功或重复执行未知副作用 |

审批过期目前是“已知 Run 的显式应用操作”，没有全表扫描器。后续调度必须仍通过 Workflow/Outbox，不能绕过 scope 扫描其他模块私有表。

## 中断与恢复顺序

1. 不删除 Redis 消息、不清空 Outbox、不修改 Task lease；先保留 PostgreSQL 事实和日志。
2. 恢复 PostgreSQL，再恢复 Redis；确认 Alembic revision 仍为 `0008_memory_context`。
3. 启动一个 Worker。Relay 会重新认领未发布或发布确认前中断且租约已过期的 Outbox。
4. Celery 重投后，未到期的 Task lease会拒绝重复执行；到期 lease可由新 Worker 认领并递增 attempt。
5. 通过 scoped Run 查询和递增运行事件确认进入 `succeeded`、`failed` 或 `cancelled`。不要以队列为空作为完成证据。

若中断发生在外部副作用之后、Task 成功结算之前，at-least-once 会再次调用 StepExecutor。真实适配器必须用传入的 task idempotency key 在其拥有的数据源保存/返回首次结果；不能只依赖进程内缓存。

## 队列不可用

业务事务仍提交 Run/Task 与 Outbox。Publisher 失败时 Relay 保存稳定失败信息并把 Outbox `available_at` 延后 5 秒；Redis 恢复后继续发布。事件可能在“已发布但确认前崩溃”的窗口被再次发送，consumer 必须依赖 PostgreSQL Task 状态和租约处理重复投递。

## 验证

```powershell
uv run --frozen pytest services/core/tests/test_workflows.py services/core/tests/test_worker.py
uv run --frozen pytest services/core/tests/test_persistence.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

数据库测试会创建随机空库、迁移到 head，并验证 Fake 与真实 Redis/Celery 的同一 `framework_smoke` 契约；不会向开发库写业务夹具。

## 回退

1. 停止 API 和 Worker，确认没有活动 Run/Task lease；备份 workflow 八张表、相关 Outbox 和审计记录。
2. 仅在确认不再需要 08 状态后执行 `uv run --frozen alembic -c services/core/alembic.ini downgrade 0003_projects_assets`。
3. 该迁移会删除所有 workflow 定义、运行、步骤、任务、审批和运行事件，但保留执行 07 的项目/资产表；Redis 中的旧消息必须在受控维护窗口按对应环境清理，不能让旧 consumer 再处理。
4. 恢复 08 源码与文档变更，并重新运行执行 07 全部门禁。
