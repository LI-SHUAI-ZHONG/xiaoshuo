# 本地基础设施运行手册

## 范围与前置条件

本地栈由 `infra/compose.yaml` 定义，只包含 PostgreSQL 17 + pgvector、Redis 7 和 MinIO。它不包含 API、Worker、真实 AI 服务或业务种子数据。

运行前需要：

- Docker Engine 与 Docker Compose v2；Windows 推荐 Docker Desktop 的 Linux 容器模式。
- 仓库根存在 `.env`。从 `.env.example` 复制后，必须替换全部 `replace-with-*` 占位值。
- 默认端口 `5432`、`6379`、`9000`、`9001` 未被其他进程占用。

所有发布端口只绑定 `127.0.0.1`，不会默认暴露到局域网。不要把示例凭据用于共享环境或生产环境。

## 配置分层

运行时配置采用以下优先级，后者覆盖前者：

1. `accos.kernel.settings` 中的非敏感代码默认值；
2. 仓库根 `.env`；
3. API 或 Worker 的进程环境变量。

数据库、Redis 与对象存储连接信息没有代码内秘密默认值，缺失时会仅按变量名快速失败。`RuntimeSettings.safe_summary()` 会隐藏数据库 URL、Redis URL、S3 access key 和 secret key，日志只能使用这个脱敏摘要。

Compose 包装脚本同样要求 `.env`，并以 `docker compose config --quiet` 校验。`ACCOS_DATABASE_URL`、`ACCOS_REDIS_URL` 中的主机端口和凭据必须与同文件中的 Compose 分项保持一致；修改端口或密码时同步修改 URL。

## 启动、检查与停止

Windows PowerShell：

```powershell
Copy-Item .env.example .env
# 编辑 .env，替换全部 replace-with-* 值
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra.ps1 up
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra-self-check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra.ps1 down
```

POSIX shell：

```sh
cp .env.example .env
# 编辑 .env，替换全部 replace-with-* 值
sh scripts/infra.sh up
sh scripts/infra.sh status
sh scripts/infra-self-check.sh
sh scripts/infra.sh down
```

`up` 会按顺序完成配置校验、等待三个长驻服务健康、幂等创建开发 bucket，并执行全部自检。`down` 不带 `--volumes`，因此数据库、Redis AOF 与对象数据会保留。VS Code 的 `ACCOS: Infra up/status/self-check/down` 任务调用相同入口。

## 自检内容

自检通过 Compose 的 `tools` profile 运行一次性容器，不要求宿主机安装 `psql`、`redis-cli` 或 `mc`：

- PostgreSQL：连接目标数据库，确保 `vector` 扩展存在并校验向量类型；
- Redis：使用容器内环境凭据执行 `PING`；
- MinIO：确认 bucket，写入固定测试对象、读取比对，并通过退出 trap 清理对象。

脚本不会把密码或 key 拼入输出。查看服务日志时仍应避免使用 `docker compose config` 的非 quiet 输出，因为配置展开结果属于敏感信息。

## 默认端口、网络与卷

| 能力          |         宿主端口 | 容器端口 | 默认持久卷            |
| ------------- | ---------------: | -------: | --------------------- |
| PostgreSQL    | `127.0.0.1:5432` |   `5432` | `accos-postgres-data` |
| Redis         | `127.0.0.1:6379` |   `6379` | `accos-redis-data`    |
| MinIO S3 API  | `127.0.0.1:9000` |   `9000` | `accos-minio-data`    |
| MinIO Console | `127.0.0.1:9001` |   `9001` | 同上                  |

服务间通信使用显式网络 `accos-infrastructure`。若修改 `ACCOS_COMPOSE_PROJECT_NAME`，网络和卷名称也会使用新的前缀。

Docker Desktop 的卷位于其 Linux VM/WSL 数据盘中，不要直接编辑。用以下只读命令定位和查看：

```powershell
docker volume ls --filter name=accos-
docker volume inspect accos-postgres-data
```

## 端口冲突

先用 `scripts/infra.ps1 status` 或 `scripts/infra.sh status` 排除已有 ACCOS 容器。若默认端口被其他程序占用，在 `.env` 中修改对应宿主端口：

- `ACCOS_POSTGRES_PORT`
- `ACCOS_REDIS_PORT`
- `ACCOS_MINIO_API_PORT`
- `ACCOS_MINIO_CONSOLE_PORT`

随后同步修改 `ACCOS_DATABASE_URL`、`ACCOS_REDIS_URL` 或 `ACCOS_S3_ENDPOINT`。容器端口不变。

## 清空本地数据

普通 `down` 永不删除卷。只有明确要丢弃全部本地基础设施数据时，才运行独立的破坏性脚本；脚本还要求第二个确认参数：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\infra-clean-data.ps1 -ConfirmDataLoss
```

```sh
sh scripts/infra-clean-data.sh --confirm-data-loss
```

此操作删除 PostgreSQL、Redis 和 MinIO 的本地命名卷，不可由仓库恢复。执行前先按备份运行手册（执行 22 交付）生成可验证备份；当前阶段尚未提供生产级备份工具。

## 无损升级与回滚

1. 保持现有栈运行并记录 `docker compose ... images` 与卷名。
2. 为持久数据创建并验证备份。PostgreSQL 大版本升级必须走逻辑备份/恢复或官方升级流程，不能让新主版本直接复用旧数据目录。
3. 只把 `infra/compose.yaml` 中的一个镜像改到明确版本或 digest，禁止 `latest`。
4. 运行 `docker compose --env-file .env --file infra/compose.yaml config --quiet`，再拉取镜像并执行 `infra up` 与自检。
5. 验证失败时恢复原镜像引用并重新执行 `infra up`。数据格式已迁移时，按该版本的恢复流程还原备份，不要直接删除卷。

## 故障排查

- `Missing .env`：复制 `.env.example`，替换凭据占位并重试。
- `Docker CLI is unavailable`：安装 Docker Desktop/Engine 和 Compose v2，启动引擎后用 `docker info` 验证。
- `Cannot connect to the Docker daemon`：Docker Desktop 尚未启动、Linux 容器后端未就绪或当前用户无权限。
- 容器 `unhealthy`：运行 `docker compose --env-file .env --file infra/compose.yaml ps`，再按单个服务查看 `docker compose ... logs --tail 100 <service>`。日志输出不得粘贴到公开渠道。
- PostgreSQL 报扩展缺失：运行自检；它会幂等创建 `vector`。初始化 SQL 只在空 PostgreSQL 卷首次创建时自动执行。
- MinIO bucket 缺失：重新执行 `infra up`；`minio-init` 使用 `--ignore-existing`，可安全重复。
- 修改 `.env` 密码后无法连接旧卷：容器初始化凭据已存入持久卷。恢复原凭据，或在确认数据可丢弃后使用独立清理脚本重建。

镜像引用与版本变更同时受 `docs/runbooks/dependency-upgrades.md` 的锁定规则约束。
