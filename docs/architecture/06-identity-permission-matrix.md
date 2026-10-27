# 身份、权限与创作者控制矩阵

## 固定角色

权限由服务端 `identity-rbac-v1` 策略解析为不可变快照。客户端可以根据快照调整展示，但不能据此自行授权。未知角色、未知权限和缺失上下文全部拒绝。

| 权限（资源:动作） | OWNER | EDITOR | VIEWER | SERVICE 上限 |
|---|:---:|:---:|:---:|:---:|
| `workspace:read` | 是 | 是 | 是 | 可显式授予 |
| `workspace:write` | 是 | 是 | 否 | 否 |
| `membership:manage` | 是 | 否 | 否 | 否 |
| `ownership:transfer` | 是 | 否 | 否 | 否 |
| `data:export` | 是 | 是 | 否 | 否 |
| `data:archive` | 是 | 是 | 否 | 否 |
| `data:request-delete` | 是 | 是 | 否 | 否 |
| `approval:decide` | 是 | 否 | 否 | 否 |
| `audit:read` | 是 | 是 | 是 | 否 |
| `project:read` | 是 | 是 | 是 | 可显式授予 |
| `project:write` | 是 | 是 | 否 | 否 |
| `feature-flag:manage` | 是 | 否 | 否 | 否 |
| `evolution:apply` | 是 | 否 | 否 | 否 |
| `agent:run` | 是 | 是 | 否 | 可显式授予 |
| `tool:run` | 是 | 是 | 否 | 可显式授予 |

`SERVICE` 的数据库授权列表与上表上限取交集，因此配置错误也不能赋予成员管理、所有权、审批、功能开关或 Evolution 应用权限。项目权限以后只能缩小工作区权限，不能扩大它。

## 判定顺序

1. 身份提供方验证凭据；未验证主体不进入授权。
2. 服务端按 `workspace_id` 查询成员或 ServiceIdentity；不接受客户端提供的角色。
3. 先比较资源真实工作区/项目作用域，再检查权限快照。
4. 授权允许或拒绝都写入 append-only 审计；审计不可写时操作失败关闭。
5. 功能开关、Agent、Tool 和 Evolution 只能调用同一个 `AuthorizationService`，其自身状态不能变成授权依据。

## 创作者控制协议

所有权转移、导出、归档和删除先形成 `ControlRequest`。请求只保存资源范围、稳定的变更码和风险码，不保存正文或密钥。高影响请求由另一名有 `approval:decide` 的人类主体产生一次性 `HumanApproval`；ServiceIdentity 不能批准，请求人不能自行批准。本阶段不执行物理删除，也不提供绕过请求状态的数据库写路径。
