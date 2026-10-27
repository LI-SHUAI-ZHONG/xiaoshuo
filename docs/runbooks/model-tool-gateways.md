# 模型与工具网关运行手册

## 默认离线运行

API 和 Worker 不需要任何模型密钥。composition root 默认装配 `FakeModelProvider`、`NullModelProvider`、`NullSecretProvider` 与 `FakeToolExecutor`；`ACCOS_REAL_PROVIDER_CALLS_ENABLED` 保持 `false`。不要把测试或真实凭据写入 `.env.example`、Workflow payload、模型/工具请求、错误引用、日志或数据库。

`framework_smoke` 的 `pass-token` 任务会先调用 Fake Model，再把其 opaque output reference 交给 Fake Tool。后续受控失败/重试和延迟步骤仍由执行 08 的确定性执行器处理。成功后可以用相同 Workspace/Workflow/Task/correlation ID 在以下事实中追踪：

- `accos.workflow_runs` 与 `workflow_task_runs`；
- `accos.model_usage_records`；
- `accos.tool_call_records`；
- `accos.audit_events`。

## 故障判读

| 稳定码/状态 | 含义 | 安全处理 |
|---|---|---|
| `NOT_CONFIGURED` | allowlist 路由没有该能力，或 Null Provider 被调用 | 配置经过审查的 Provider 适配器；不得伪造成功 |
| `BUDGET_EXHAUSTED` | 单次、Workspace、Task 或总尝试上限耗尽 | 降低调用规模或由有权人员调整显式策略；重试/切换不重置额度 |
| `RATE_LIMITED` | Provider 通过统一端口报告限流 | 遵守有限重试/退避；不得换用未允许 Provider |
| `TIMED_OUT` | Provider/Tool 超过 Descriptor/Policy timeout | 检查依赖健康；调用保持失败或按既有有限策略重试 |
| `CIRCUIT_OPEN` | 连续失败触发冷却 | 等待显式冷却后探测；不得绕过熔断 |
| `UNKNOWN_TOOL` | Registry 无该工具 | 修正版本化注册；不得动态下载或执行代码 |
| `PERMISSION_DENIED` / `SCOPE_VIOLATION` | RBAC、Task Grant 或资源范围不允许 | 修正可信 Grant 来源；失败不能扩大权限 |
| `SCHEMA_INVALID` / `INVALID_OUTPUT` | 输入或执行器输出不符合 Descriptor | 修复调用者/适配器契约；不要记录 payload 排障 |

排查时只使用 ID、状态、稳定码、时间和用量。Provider 原始错误或工具输入可能含敏感数据，禁止复制进日志或审计 metadata。

## 验证

```powershell
uv run --frozen pytest services/core/tests/test_model_tool_gateways.py
uv run --frozen pytest services/core/tests/test_persistence.py
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

期望 migration 为 `0008_memory_context (head；模型/工具结构来自 0005)`，开发库的两个调用账本在没有实际 Workflow 调用时应为空。测试使用随机数据库和固定 fixture，不会发起付费请求。

## 回退

1. 停止 API/Worker，确认没有模型或工具调用正在执行；备份两个调用账本以及需关联的 Workflow/Audit 记录。
2. 执行 `uv run --frozen alembic -c services/core/alembic.ini downgrade 0004_workflow_engine`。该操作删除两个账本及 Workflow 权限/策略快照，不删除执行 08 的 Workflow 主表。
3. 恢复执行 09 的 composition、模块、适配器和文档变更，重新运行执行 08 门禁。当前仓库没有提交时，不能依赖 Git 自动恢复。
