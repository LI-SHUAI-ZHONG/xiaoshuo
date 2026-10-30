# Creative 模块运行手册

## 正常检查

在仓库根运行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

预期 revision 为 `0009_creative_domains (head)`，并返回 `No new upgrade operations detected.`。执行 13 的事实表只有 `creative_containers` 与 `creative_records`；领域事件通过既有事务 Outbox 发布。

## Proposal 不生效诊断

1. 确认记录 `status=proposal` 且 `current=false`；这是未批准时的预期状态。
2. 确认审批者拥有目标 workspace/project 的 `project:write`。
3. 确认项目仍为 active；归档项目禁止写入。
4. 用容器最新 `version` 作为 `expected_container_version`；版本落后应返回并发冲突，不能覆盖。
5. 批准新版本后，验证旧 current 为 `superseded/current=false`，新版本为 `current/current=true`。

不得直接更新 current、跳过审批或删除旧版本。

## 因果事件重放

World/Character 影响提案必须同时携带 `source_event_id` 与 `causation_id`。同一 workspace/project/owner/causation ID 重放时，仓储返回已有 proposal 和 `created=false`，不会追加第二个 Outbox 副作用。若数据库报告 causation 唯一冲突，按重放处理并读取已有 proposal；不要生成新的 causation ID 来绕过防循环规则。

## `NOT_CONFIGURED`

所有生成、模拟、情绪、风格、作者学习和世界组件端口默认返回 `NOT_CONFIGURED`。这表示可选能力未接适配器，不是项目或工作流故障。不得在本阶段配置真实模型、Prompt 或付费调用。Creator 的信号摄取端口同样默认不保存；执行 15 才允许从 Feedback 公开事件接线。

## 隔离问题

Creative Repository 的每次查询都必须提供 workspace、project 和 owner。记录到容器的复合外键还会校验这三个范围。出现 scope violation 时检查调用方的 `SecurityContext.project_id` 与公开 `creative://<owner>/<uuid>` 引用，不得扩大 SQL 条件或直接读取私有表。

## 回退

停止 API/Worker，备份 `creative_containers`、`creative_records`、关联 Audit 与 Outbox 后运行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0008_memory_context
```

回退会删除全部 Creative 容器和 proposal/current 元数据，不影响第 12 步 Memory/Context Package、Knowledge、Agent、Workflow、模型或工具账本。回退后运行 `alembic check` 和第 12 步统一门禁。当前仓库没有提交基线，不能依赖 Git commit 自动回滚。

