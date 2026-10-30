# Agent Runtime 运行与故障处理手册

## 当前能力

默认 composition 注册七个无内容 Agent，使用 `FakeAgentExecutor`、`fake-model` 与 `fixture.reference@1.0.0`。Master 可把技术目标引用选择为 `framework_smoke@1`；Workflow 的首个技术步骤调用 Quality Agent。全链路不读取真实密钥、不访问模型网络、不运行 Shell、不读取任意文件。

数据库事实表：

- `accos.agent_context_snapshots`：不可变 descriptor/policy/prompt-metadata/tool/permission/input-digest 快照；
- `accos.agent_runs`：Workspace/Project 范围内的状态、Workflow/结果引用和一次用量结算；
- `accos.agent_run_events`：递增、append-only 生命周期事件；
- 关联的 `accos.outbox_events`、`model_usage_records`、`tool_call_records`、`audit_events` 与 Workflow 表。

## 启动与检查

先迁移到 `0008_memory_context (head；Agent Runtime 主结构来自 0006)`：

```powershell
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

再按通常方式启动 API/Worker。Agent REST 路由仍留到执行 16/17；当前通过 Python 应用契约与 Worker 链路调用，不要直接插入或修改 Agent 表。

```powershell
uv run --frozen python -m accos.entrypoints.api
uv run --frozen python -m accos.entrypoints.worker
```

## 诊断

| 结果/现象 | 含义 | 安全处理 |
|---|---|---|
| `UNKNOWN_AGENT` | ID 未注册 | 检查版本化代码配置；不要动态下载或执行 Agent |
| `SCHEMA_MISMATCH` | 输入、Director 输出或 Agent 结果不符合 Descriptor | 保留 Run/Event，修复调用方或 Fake/Provider 适配器后用新幂等键重试 |
| `TOOL_DENIED` | 工具不在 Descriptor、版本未固定或缺权限 | 检查 Descriptor 与可信 Task Grant；不要扩大 Workspace 权限 |
| `BUDGET_EXHAUSTED` | Agent 调用扩张上限、缺模型权限或结算超过调用/token 上限 | 收窄任务，检查 Agent/Model/Workspace 三层预算；重试不得重置账本 |
| `*_LIMIT_EXCEEDED` / `LOOP_DETECTED` | 步骤、递归、并行、时长或规划路径越界 | 拆分目标或修复计划；禁止无界递归与隐式继续 |
| `waiting_approval` | 受保护 Plan 已进入 Workflow 人工审批 | 由不同的人类 approver 明确批准/拒绝；服务身份不能自动批准 |
| 重投仍返回首次结果 | 幂等保护正常 | 对照 Agent Run、Context Snapshot、Model/Tool ledger；不应出现第二次用量 |
| 同键不同请求返回冲突 | 幂等摘要不同 | 使用新键表达新任务，不能覆盖首次结果 |

诊断时先按 `workspace_id + agent_run_id` 读取 Agent Run/Event，再沿 `context_snapshot_id`、`workflow_run_id`、Task ID 与 `correlation_id` 关联。不得把 Redis 队列状态当事实，不得更新 append-only 快照/事件或手工把失败 Run 改成成功。

## 重放检查

同一 Agent 任务的可追踪版本必须完全一致：

1. `agent_id + agent_version`；
2. `model_policy_id + model_policy_version`；
3. `prompt_metadata_id + version + checksum`；
4. 排序后的 `tool_id@version`；
5. 权限快照；
6. 规范化输入 SHA-256。

若任一项需要改变，应提交新任务和新幂等键，而不是修改旧快照。Worker at-least-once 重投先命中 Agent 幂等结果，因此不会产生两个 proposal/draft 引用或重复模型/工具结算。

## 验证

```powershell
uv run --frozen pytest services/core/tests/test_agents.py
uv run --frozen pytest services/core/tests/test_persistence.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

数据库测试使用随机创建并清理的测试库；Fake Provider 不发起网络请求。验证应覆盖 Director 选择、Workflow 运行、人工拒绝、越权 Tool、schema、预算、递归/循环、重投幂等和 append-only 保护。

## 回退

1. 停止 API/Worker，确认没有进行中的 Agent/Workflow 调用；备份三张 Agent 表及关联 Workflow、Outbox、Model/Tool/Audit 记录。
2. 执行 `uv run --frozen alembic -c services/core/alembic.ini downgrade 0005_model_tool_gateways`。该操作删除三张 Agent 表，保留执行 09 的模型/工具账本与 Workflow 权限快照。
3. 恢复 composition、Agent 模块/适配器、Workflow Agent executor、测试与文档变更；当前未提交工作树不能依赖 commit 自动回滚。
4. 重新运行执行 09 完整门禁、`alembic check` 与 `framework_smoke`，确认 revision 为 `0005_model_tool_gateways`。
