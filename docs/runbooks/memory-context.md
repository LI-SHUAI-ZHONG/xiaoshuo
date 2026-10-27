# Memory 与 Context Package 运行手册

## 正常检查

在仓库根运行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

预期 revision 为 `0008_memory_context (head)`，且 drift 检查返回 `No new upgrade operations detected.`。

Memory 事实表是 `memory_records`、`memory_links`、`memory_grants`、`memory_conflicts`、`memory_context_packages` 和 `memory_events`。Redis 仅是 Working/Session record ID 投影，不应被当作事实源。

## 无召回诊断顺序

1. 确认请求的项目存在，调用者具有 `project:read`。
2. 查看 Context Package 的 `allowed_anchors`，不要先查 MemoryRecord。
3. 对 `working/session/project` 确认 anchor 等于请求的 `project_id`，不能接受空值。
4. 对 Universe/Creator 系列确认目标项目存在活动 grant；Creator 本人例外只限 actor 自己的 creator ID。
5. 查看 omission：`anchor_unavailable`、`not_yet_valid`、`no_longer_valid`、`ttl_expired`、`retention_archived`、`archived` 或 `budget_exceeded`。
6. 检查请求的 scope/type 过滤；两个维度互不替代。

不得通过扩大 SQL 条件、跳过 `MemoryAccessPolicy` 或把 `project_id` 设为空来“修复”召回。

## Redis 投影丢失与重建

Redis 缓存丢失是可恢复事件：

1. 暂停依赖 Working/Session 热投影的消费方；持久 Context Builder 可继续从 PostgreSQL 工作。
2. 对目标 workspace/project 调用 `MemoryProjectionRebuilder.rebuild`。
3. Rebuilder 使用 Working/Session 项目 anchors 从 PostgreSQL 读取并原子替换 Redis ID 列表。
4. 对比重建前后的 PostgreSQL `memory_records` 行数和 current 版本；两者必须不变。
5. 恢复消费方。不要从 Redis 反向回填 PostgreSQL。

## 冲突处置

`pending` 冲突中的 current 记录仍是唯一有效版本。作者或授权用例只能选择：

- `keep_current`：候选归档，current 不变；
- `accept_candidate`：同一事务中先把旧版本置为 `superseded/current=false`，再把候选置为 `active/current=true`。

不得直接更新 current 内容或删除旧版本。`memory.conflict-proposed` 与 `memory.conflict-decided` 事件用于审计。

## 预算异常

字符预算是严格长度上限；可选 token 预算使用确定性的 `ceil(chars/4)` 估算。候选不能完整装入剩余预算时整项省略，并记录 `budget_exceeded`，不会截断来源内容。验证 `used_chars <= budget_chars`，配置 token 上限时还须验证 `used_tokens <= budget_tokens`。

## 回退

回退前停止 API/Worker，并备份六张 Memory 表、关联 Agent 快照、审计和 Outbox。执行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0007_knowledge_pipeline
```

此操作删除 Memory 事实、grant、冲突、Context Package 与事件，并移除 Agent 快照上的 package 外键；Knowledge、Agent Run、Workflow、模型和工具账本保留。回退完成后运行 `alembic check` 和第 11 步门禁。当前仓库没有提交基线，不能依赖 Git commit 自动回滚。

