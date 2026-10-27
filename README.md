# ACCOS

ACCOS（Artificial Creative Civilization Operating System）当前处于 `v0.1-skeleton` 的框架建设阶段。本仓库采用模块化单体、独立后台 Worker 和端口/适配器架构，先建立可验证的工程边界，再按阶段引入运行时与业务骨架。

> 执行 23 交付基线已建立：三类非 root OCI 镜像、完整 Compose 应用 profile、Fake Provider 纵向烟雾、分层 CI、MinIO 恢复演练与发布清单均已纳入门禁。真实模型、正式内容和远期扩展仍默认关闭。

## 从这里开始

1. 阅读 [`docs/architecture/README.md`](docs/architecture/README.md)，了解五层蓝图如何映射到仓库。
2. 阅读 [`docs/architecture/02-module-dependency-rules.md`](docs/architecture/02-module-dependency-rules.md) 与 [`docs/architecture/03-data-ownership-matrix.md`](docs/architecture/03-data-ownership-matrix.md)，再新增模块或依赖。
3. 阅读 [`docs/adr/`](docs/adr/) 中已接受的架构决策。
4. 查看 [`docs/handoffs/23.md`](docs/handoffs/23.md) 获取最终验收状态和后续输入。
5. 全新检出按 [`docs/runbooks/first-run.md`](docs/runbooks/first-run.md) 启动并验证。

## 仓库结构

| 路径                   | 职责                                       |
| ---------------------- | ------------------------------------------ |
| `apps/studio/`         | Next.js 创作者工作台                       |
| `services/core/`       | FastAPI 模块化单体、后台 Worker 与后端模块 |
| `packages/api-client/` | 由 OpenAPI 生成的 TypeScript 客户端        |
| `packages/ui/`         | 共享 UI 组件和设计令牌                     |
| `infra/`               | 本地基础设施、容器和运维配置               |
| `tests/contract/`      | 跨边界接口与 OpenAPI 契约测试              |
| `tests/e2e/`           | Fake Provider 驱动的端到端测试             |
| `docs/`                | ADR、架构、交接和运行手册                  |
| `scripts/`             | 可重复的开发与验证脚本                     |
| `执行/`                | 编号执行包；只读保留，不得删除             |

## 固定技术基线

- 前端：Next.js App Router、React、TypeScript、Tailwind CSS、TanStack Query。
- 后端：Python、FastAPI、Pydantic、SQLAlchemy、Alembic。
- 异步任务：Celery 适配器与 Redis；工作流状态持久化在 PostgreSQL。
- 数据：PostgreSQL + pgvector、Redis、S3 兼容对象存储；本地对象存储使用 MinIO。
- 接口：版本化 REST/OpenAPI 与 SSE；WebSocket 协同编辑延后。
- AI 与外部工具：端口优先，默认 Fake/Null Provider；真实调用默认关闭。
- 本地交付：Docker Compose；生产交付 OCI 镜像和单节点部署说明。

开发工具链固定为 Python 3.12.14、uv 0.12.7、Node.js 22.23.2 与 pnpm 11.25.0；Python 和 pnpm 依赖分别由根级 `uv.lock` 与 `pnpm-lock.yaml` 唯一锁定。改变上述基线前必须新增 ADR，并写明兼容与迁移成本。

## 不可破坏的边界

- 依赖遵循 `entrypoints -> application -> domain <- ports <- adapters`；组合根是唯一允许同时装配应用与适配器的入口。
- 领域模块不得导入数据库、Redis、S3、模型 SDK 或前端实现。
- 模块间只能通过公开 application/port 契约或已发布事件协作，不得读取其他模块私有表。
- 工作区、项目与创作者数据必须隔离；授权不能由功能开关替代。
- 改进和“进化”只能产生可审计提案，应用前必须人工批准。
- 不提交密钥、真实创作内容或本地运行数据。

## 开发命令

先按 `.python-version` 与 `.node-version` 激活精确运行时，并安装 uv 0.12.7。pnpm 由 Corepack 按根级 `packageManager` 自动选择。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

```sh
sh scripts/install.sh
sh scripts/check.sh
```

`check` 依次执行格式检查、Python/TypeScript lint、导入和依赖循环检查、严格类型检查及两端单元测试。pre-commit 只执行快速门禁，完整检查留给 CI。依赖升级流程见 [`docs/runbooks/dependency-upgrades.md`](docs/runbooks/dependency-upgrades.md)。

## 本地基础设施

从 `.env.example` 复制 `.env` 并替换全部本地凭据占位后，可通过统一包装脚本启动、检查和无损停止基础设施：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra.ps1 up
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra.ps1 down
```

POSIX 环境使用 `sh scripts/infra.sh <up|status|down|check>`。普通停止保留全部命名卷；完整操作、端口、故障排查与显式清空数据流程见 [`docs/runbooks/local-infrastructure.md`](docs/runbooks/local-infrastructure.md)。

## 后端运行时

基础设施 healthy 且仓库根 `.env` 已配置时，可分别启动 API 与工作流 Worker：

```powershell
uv run --frozen python -m accos.entrypoints.api
uv run --frozen python -m accos.entrypoints.worker
```

API 默认仅监听 `127.0.0.1:8000`，提供公开 `/live`、`/ready`、`/openapi.json` 和默认拒绝的 `/api/v1/identity/context`。项目、资产、工作流、模型、工具、Agent、Creative、Consistency 与 Quality 应用契约已就绪，但资源路由按计划留到执行 16。Worker 同时运行唯一 Outbox Relay 和 `accos.workflows.consume` Celery consumer；默认 Agent/模型/工具链与语义检查完全离线。完整健康状态、身份配置、安全头和运行契约见 [`docs/runbooks/backend-runtime.md`](docs/runbooks/backend-runtime.md)、[`docs/runbooks/identity-security.md`](docs/runbooks/identity-security.md)、[`docs/runbooks/project-assets.md`](docs/runbooks/project-assets.md)、[`docs/runbooks/workflows.md`](docs/runbooks/workflows.md)、[`docs/runbooks/model-tool-gateways.md`](docs/runbooks/model-tool-gateways.md)、[`docs/runbooks/agent-runtime.md`](docs/runbooks/agent-runtime.md)、[`docs/runbooks/creative-domains.md`](docs/runbooks/creative-domains.md) 与 [`docs/runbooks/consistency-quality.md`](docs/runbooks/consistency-quality.md)。

## 数据库迁移

应用启动不会创建或修改表。首次启动或取得新迁移后，从仓库根显式执行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini check
```

迁移、回退、技术表、并行测试隔离与 Outbox 运维规则见 [`docs/runbooks/database-migrations.md`](docs/runbooks/database-migrations.md)。
