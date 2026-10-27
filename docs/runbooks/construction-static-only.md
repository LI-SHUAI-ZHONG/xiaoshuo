# 24–44 的施工入口与第45步运行验收

构建阶段不运行项目测试、服务、数据库迁移、模型连接、烟雾、恢复演练或费用调用。
静态核对只说明源代码可解析/类型可检查，不说明功能已运行。

| 允许入口 | 实际行为 |
|---|---|
| `node scripts/static-toolchain.mjs syntax` | Python AST、JSON/TOML解析；Node `--check`，不import业务模块 |
| `node scripts/static-toolchain.mjs format` | 已安装Ruff/Prettier；固定纯JSON格式配置；不运行lint或测试 |
| `node scripts/static-toolchain.mjs types` | 已安装mypy/tsc，固定无插件mypy配置；不执行API、Next构建或typegen |
| `node scripts/static-toolchain.mjs contracts` | 只加载纯公共值schema，生成本地JSON/TS；无远程引用，无应用装配 |
| `node scripts/static-toolchain.mjs api` | 25新增schema_only分支：注册路由/schema，container置空，不创建连接、不执行lifespan；从本地OpenAPI生成客户端，禁止远程ref |
| 上述入口加 `--plan` | 仅显示固定的子命令清单，不执行子进程 |
| `node scripts/toolchain.mjs static <模式>` | 转到同一静态入口，绕过旧Corepack/uv准备和所有旧门禁 |

package.json 中有对应 `static:*` 别名；施工优先直接运行node，避免包管理器初始化。
本地编译器缺失时明确失败，不自动安装/下载。子进程不继承API凭据、Python路径或Node启动hook。
这里只承诺已审阅固定调用链无网络/服务操作，不把环境变量当操作系统网络沙箱。

| 延后到45的旧入口 | 已读代码中的原因 |
|---|---|
| `check`、`check:quick`、`lint`、`scripts/check.ps1/.sh` | toolchain.runLinters包含`check-openapi --self-test`；check还跑pytest/Vitest/Playwright |
| `api:check` | 显式self-test与客户端重复生成检查 |
| 旧`typecheck` | 调api-client check；经uv/Corepack准备，不是新静态白名单 |
| 旧`format:check`、`verify:toolchain` | verifyBaseToolchain/verifyPython经Corepack/uv，可能准备依赖 |
| `build`、Next build/dev/typegen | 可能加载配置或构建期取数，未纳入本阶段静态入口 |
| `security:local`、security_checks.py | 读取.env并可能调用Docker Compose config；留统一验收 |
| 旧`api:export`包管理器入口 | 施工只允许经static入口运行已审阅的schema_only导出；不调用旧包管理器聚合命令 |
| install、infra-self-check、verify_stage07_storage、full_stack_smoke、recovery drill | 安装、服务、连接或运行演练 |

旧门禁保留，且最终lint新增表所有权检查；最终test新增T003的命令录制用例。
静态入口独立于旧门禁，不能把旧门禁名字换成“静态”继续调用。

源码基线恢复命令只在45隔离新目录运行：

```powershell
.\.venv\Scripts\python.exe -I scripts/source_baseline.py restore --archive .construction/baselines/stage24-source-only-20260924/source.zip --target .construction/recovered/stage24-acceptance
```

目标必须不存在，不覆盖用户工作树。恢复后比对逐文件hash和原资料hash，再由明确维护操作决定
回退哪些代码；不要将恢复工具指向现有项目目录。基线不包含业务库/S3，不能用于还原小说数据。
