# ACCOS 身份、权限与审计威胁模型

## 范围与资产

本模型覆盖 API/Worker 到身份提供方端口、请求与任务上下文、工作区 RBAC、身份仓储、Project/Asset/Workflow scope、创作者控制请求和审计表。要保护的资产是创作者工作区边界、成员/角色绑定、项目与资产、工作流状态、凭据、审批证据及审计完整性。

信任边界如下：客户端输入不可信；OIDC/JWT 解码器只有在验证签名后才可信；角色和权限只来自 PostgreSQL；任务上下文只能从已验证并由服务端签名的任务信封恢复；Feature Flag、Agent、Tool、Evolution 和模型输出均不可信，不能授予权限。

## 主要威胁与控制

| 威胁 | 影响 | 当前控制 | 验证证据 |
|---|---|---|---|
| 伪造、过期、错误受众或错误签名 JWT | 冒充用户/服务 | decoder-neutral OIDC/JWT 端口；issuer、audience、expiry、subject 和 service ID 二次校验；稳定 401 | 四类反向契约测试 |
| 开发身份误入生产 | 固定凭据绕过企业身份 | 默认关闭；显式 token/actor/workspace；生产配置启用即启动失败 | 配置正反测试 |
| 客户端伪造角色或工作区 | 越权或跨租户读取 | 角色只从 scoped membership/service 表解析；每个查询必须带 workspace；先检查真实资源 scope | 双工作区仓储与授权测试 |
| VIEWER 写入、EDITOR 改所有权、SERVICE 提权 | 修改创作者控制状态 | 固定默认拒绝矩阵；Service grants 与硬上限取交集 | 角色反向测试 |
| 功能开关、Agent、Tool 或 Evolution 绕权 | 间接高权限操作 | 共用 `AuthorizationService`；开关只能在授权后评估 | 通用 capability 反向测试 |
| 拒绝路径产生部分写入/Outbox | 不一致或隐藏副作用 | 授权先于业务 UoW；拒绝只允许审计副作用 | 数据库副作用计数测试 |
| 修改/删除审计或批准 | 抹除证据 | 应用端口只提供 append；PostgreSQL trigger 对 UPDATE/DELETE 失败关闭 | 数据库级 mutation 反向测试 |
| 正文、密钥或 token 进入日志/审计 | 敏感数据泄漏 | 结构化日志递归脱敏；审计 payload 仅允许短 operation/state code | 脱敏与 allowlist 测试 |
| 恶意上传 | 恶意文件、资源耗尽 | MIME/扩展、大小、SHA-256、路径与对象隔离校验；扫描器未配置时记录 `not_configured`，拒绝/故障失败关闭 | Project/Asset 正反与对象补偿测试 |
| 伪造或重放队列事件 | 越权执行、重复副作用、耗尽尝试 | 队列事件不携带权限快照；consumer 只接受受控 schema/task UUID，再从 PostgreSQL 重建 scope、状态、available_at 与租约；Task 幂等键唯一 | 反序列化、重复投递、租约和跨 Workspace 测试 |
| 请求洪泛 | 可用性下降 | 限流端口已建立且当前默认拒绝；实际部署预算尚未配置 | 默认拒绝适配器测试 |
| 删除请求直接变成物理删除 | 不可恢复数据损失 | Asset 只有保留期删除标记；工作流没有物理删除执行器 | schema 与用例测试 |

## 剩余风险与后续责任

- 尚未接入真实 OIDC/JWKS SDK、密钥轮换、撤销和时钟偏差策略；部署必须显式注入通过安全评审的 JWT decoder，当前默认 Provider 拒绝所有凭据。
- 队列事件不承载身份或授权信息，Worker 只信任 PostgreSQL 中已提交的 Task/Run 事实。Redis 若被攻破仍可造成消息丢弃、重放和可用性攻击；生产网络隔离、凭据轮换及在存在非受信生产者时增加事件签名属于执行 22 的加固责任。
- 限流只有端口和默认拒绝适配器；执行 22 配置分布式预算、代理 IP 信任和指标。
- 上传校验与对象隔离已落地，但内容扫描适配器仍明确未配置；对外接收文件前必须配置经安全评审的扫描器和隔离流程，不能把 `not_configured` 当作 clean。
- 审计保留、导出和备份恢复策略在执行 22 完成；在此之前禁止直接维护或清理审计表。

## 安全变更规则

修改角色矩阵、审批分离、审计不可变性、OIDC 信任条件或开发身份生产禁令属于安全策略变更，必须更新策略版本、迁移/回滚说明、威胁模型和反向测试；不能只改变前端或 Feature Flag。
