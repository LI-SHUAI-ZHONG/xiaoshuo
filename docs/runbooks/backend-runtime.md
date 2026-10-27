# 后端运行时手册

## 范围

FastAPI API 与工作流 Worker 读取同一个 `.env`、调用同一个 composition root，并按 Kernel → Persistence → Workflow Consumer Persistence → Identity → Projects → Assets → Workflows → Health 顺序启动、逆序关闭。主 Persistence 持有应用/Relay 的异步 SQLAlchemy 连接池；Celery consumer 使用独立 NullPool，避免跨线程事件循环复用连接。应用启动不会自动迁移。本阶段 HTTP 仍只有受保护的身份上下文 API；项目、资产和工作流资源路由按计划留到执行 16，真实 AI 调用仍关闭。

## 前置条件

1. 激活 `.python-version` 指定的 Python 3.12.14 和 uv 0.12.7。
2. 从 `.env.example` 创建未提交的 `.env`，使用非生产本地凭据。
3. 启动执行 03 的基础设施并确认三个服务 healthy：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra.ps1 up
```

```sh
sh scripts/infra.sh up
```

## 启动与停止

从仓库根启动 API：

```powershell
uv run --frozen python -m accos.entrypoints.api
```

```sh
uv run --frozen python -m accos.entrypoints.api
```

默认只监听 `127.0.0.1:8000`。另一个终端启动 Worker：

```powershell
uv run --frozen python -m accos.entrypoints.worker
```

```sh
uv run --frozen python -m accos.entrypoints.worker
```

API 与 Worker 都可用 `Ctrl+C` 停止，并按注册顺序的逆序释放模块。VS Code 的 `ACCOS: API`、`ACCOS: Worker` 调试配置和同名任务调用相同模块入口。

## 健康契约

### `GET /live`

只表示 API 进程能够响应，不访问外部依赖。成功固定返回 HTTP 200：

```json
{
  "status": "alive",
  "version": "0.0.0",
  "timestamp": "2026-09-03T00:00:00Z"
}
```

### `GET /ready`

检查 PostgreSQL、Redis、对象存储和可选 AI Provider：

- 所有关键依赖健康：HTTP 200，`status=ready`；
- 任一关键依赖不可用或超时：HTTP 503，`status=not_ready`；
- Fake 模式没有 AI Provider：该非关键项为 `not_configured/fake_mode`，不会阻塞启动或 readiness；
- 探测错误只返回 `timeout` 或 `check_failed` 等稳定描述，不返回连接串或驱动异常文本。

本地检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/live
Invoke-RestMethod http://127.0.0.1:8000/ready
```

## 关联 ID 与错误

API 接受规范 UUIDv4 格式的 `X-Correlation-ID`/`X-Request-ID`、`X-Trace-ID` 和可选 `X-Task-ID`。无效或缺失的请求/Trace ID 会被替换；Task ID 无效时会被丢弃。响应、请求完成日志和错误信封使用相同的请求与 Trace ID。

预期运行时错误、请求校验错误和未知错误分别使用稳定错误码。未知错误只返回通用消息，不返回异常文本或堆栈。所有响应默认带 `no-store`、`nosniff`、禁止 frame、严格 referrer 与 permissions 等安全头。

所有 `/api/v1/` 路径默认受保护，要求 `Authorization: Bearer ...` 与 `X-Workspace-ID`。当前上下文端点为 `GET /api/v1/identity/context`。开发身份、生产 OIDC 边界、审计和排障见 [`identity-security.md`](identity-security.md)。

## 配置与日志

配置分为：

- `RequiredSettings`：数据库、Redis、S3 endpoint/bucket 和对象存储凭据；
- `OptionalSettings`：环境、日志级别、S3 region、API 主机/端口、健康超时和可选 Provider 名；
- 数据库池参数：`ACCOS_DB_POOL_SIZE`、`ACCOS_DB_MAX_OVERFLOW`、`ACCOS_DB_POOL_TIMEOUT_SECONDS`、`ACCOS_DB_POOL_RECYCLE_SECONDS`；
- `FeatureFlags`：真实 Provider 调用开关，默认关闭。
- `SecuritySettings`：显式开发身份开关、token 与 actor/workspace；开发身份默认关闭且生产禁止。

生产环境会拒绝短凭据或 `replace-with-*` 占位值。测试必须传入显式 fixture 配置，不存在隐式测试秘密。

日志为单行 JSON。数据库 URL、Redis URL、password、secret、token、authorization、access key 与 URL user-info 会递归脱敏。请求日志不记录查询字符串、请求体或请求头；排障时也不得打印完整 `RuntimeSettings`，只能记录 `safe_summary()`。

## 故障排查

- 启动立即返回 `configuration_error`：检查 `.env` 是否存在以及错误中列出的变量名；错误不会回显变量值。
- `/live` 为 200、`/ready` 为 503：查看 `checks` 中的依赖名和稳定 detail，再运行执行 03 自检；不要把带凭据的 Compose 展开配置粘贴到日志。
- 端口 8000 被占用：在 `.env` 设置未占用的 `ACCOS_API_PORT`，保持 `ACCOS_API_HOST=127.0.0.1`。
- Worker 启动后没有任务：确认日志为 `registered_tasks=1` 且列出 `accos.workflows.consume`；再检查未发布 Outbox、Redis 连接、Task `available_at`/lease 和 Run 是否 paused/waiting_approval。恢复步骤见 [`workflows.md`](workflows.md)。
- 当前 API 未开放 Swagger/ReDoc 页面；机器可读 OpenAPI 仍位于 `/openapi.json`。
- 数据库结构未迁移时 `/ready` 的 `SELECT 1` 仍可能成功；部署流程必须在启动应用前显式执行 Alembic。迁移方法见 [`database-migrations.md`](database-migrations.md)。
