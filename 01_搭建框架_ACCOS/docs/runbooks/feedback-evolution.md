# 反馈、指标与受控进化运行手册

## 正常检查

先确认迁移和 ORM 一致：

```powershell
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

期望 revision 为 `0011_feedback_evolution (head)`，`alembic check` 输出 `No new upgrade operations detected.`。

运行第 15 步定向和全量门禁：

```powershell
uv run --frozen pytest services/core/tests/test_feedback_evolution.py services/core/tests/test_feedback_evolution_persistence.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

受限 Windows 会话若默认临时目录不可写，可追加工作区内的 `--basetemp` 并禁用 cache provider；不要修改仓库的测试门槛。

## 行为同意与撤回

行为采集默认关闭。排查 `behavior-consented` 事件被拒绝时依次确认：

1. actor kind 是 USER，并拥有当前项目的 `project:write`；
2. 项目存在、属于同一 Workspace 且未归档；
3. 存在同 actor、Workspace、Project 的 ACTIVE 同意；
4. 事件携带的 consent policy version 与 ACTIVE 记录完全一致；
5. schema version、signal code 和可选 source reference 都是稳定代码或不透明 URI。

撤回后必须同时看到：

- 同意状态为 `withdrawn`，`withdrawn_at` 非空；
- 原行为事件状态为 `anonymized`，actor、signal、数值、来源、consent 和 Creator link 均为空；
- 关联 MetricPoint/ExperimentSample 为 `included=false` 且具有 `tombstoned_at`；
- MetricPoint tombstone action 为 `recompute`；实验样本和 Creator signal tombstone 为 `exclude`；
- Outbox 的撤回事件只含 schema、actor、policy version 与 `recompute_required`，不含行为正文。

不要通过恢复数据库字段、重放旧事件或绕过 ACTIVE consent 查询来“撤销撤回”。需要重新采集时，由用户重新明确授予同意。

## 指标与 System Doctor

写入 MetricPoint 前先安装或注册对应定义。若返回注册表错误：

- 核对 name/unit/version/retention/sensitivity；
- 维度不得超过四个，且每个维度必须有 1–32 个有限预注册值；
- 禁止把用户、Workspace、Project、对象、请求、Prompt、正文或密钥放入 label；
- point 必须提供定义要求的全部维度且不能增加额外维度；
- value 不能是 NaN 或 Infinity。

System Doctor 没有 Finding 时，确认 point 仍为 `included=true`、metric name 命中规则、有限维度命中条件且值达到阈值。不要通过修改阈值或把未运行状态伪装为健康来通过诊断。

## 技术实验

实验只允许 `technical-smoke` sample scope，至少两个唯一 variant，primary metric 必须已注册，起止时间必须正序，停止条件不能为空。正常状态是：

```text
planned -> running -> completed
                   -> stopped
```

结果只保存稳定 result code。行为反馈派生的样本在用户撤回后立即排除；读取实验结果时必须过滤 `included=false`，并根据 metric tombstone 重算聚合。

## Evolution 提案

安全流程固定为：

```text
observed -> proposed -> simulated -> evaluated -> awaiting_approval
                                                      |-> approved
                                                      `-> rejected
```

排查状态失败时重新读取 Proposal `version`，不要重放旧版本。批准必须由不同于请求者的授权 USER 执行。`approved` 只表示人工接受建议，不表示已修改配置或已部署。

若 Proposal 命中以下 rule code，它必须保持 `rejected`：

```text
immutable-no-ownership-change
immutable-no-safety-disable
immutable-no-permission-escalation
immutable-no-approval-bypass
immutable-no-auto-commit
immutable-no-auto-deploy
immutable-no-unmigrated-schema
```

本模块没有部署入口。真实变更必须在未来独立、授权、可回滚的外部发布流程中完成；不得向 Evolution Service 注入文件、Shell、Git、迁移或部署适配器。

## 回退

先停止 API/Worker，并备份第 15 步十一张表、相关 Audit 与 Outbox。确认无需保留反馈、同意、实验和 Proposal 状态后执行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0010_consistency_quality
```

该操作只删除第 15 步十一张表并把 schema metadata 恢复为 `0010_consistency_quality`，保留第 14 步 Canon/Consistency/Quality 状态。随后恢复第 15 步源码与文档，运行第 14 步门禁及 `alembic check`。生产环境优先使用前向修复迁移。
