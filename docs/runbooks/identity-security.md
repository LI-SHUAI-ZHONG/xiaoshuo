# 身份、授权与审计运行手册

## 安全默认值

`/live`、`/ready` 和 `/openapi.json` 是非业务运行端点；所有 `/api/v1/` 路径默认要求 Bearer 凭据和规范 UUIDv4 `X-Workspace-ID`。当前没有配置生产 OIDC decoder 时，Provider 会拒绝所有凭据。稳定失败码为 `authentication_required`、`permission_denied` 与 `scope_violation`。

服务端从成员关系或 ServiceIdentity 解析权限快照，不读取客户端角色。权限矩阵见 [`../architecture/06-identity-permission-matrix.md`](../architecture/06-identity-permission-matrix.md)，威胁分析见 [`../security/threat-model.md`](../security/threat-model.md)。

## 显式本地开发身份

仅在本地开发数据库已经迁移至 `0002_identity_security` 后，才可在未提交的 `.env` 中设置：

```dotenv
ACCOS_DEV_IDENTITY_ENABLED=true
ACCOS_DEV_IDENTITY_TOKEN=replace-with-a-local-token-at-least-16-characters
ACCOS_DEV_IDENTITY_ACTOR_ID=11111111-1111-4111-8111-111111111111
ACCOS_DEV_IDENTITY_WORKSPACE_ID=22222222-2222-4222-8222-222222222222
```

启动时只在显式启用后幂等建立该本地 User、Workspace 与 OWNER Membership。没有默认管理员密码，token 不得提交、打印或用于共享环境。`ACCOS_ENV=production` 与开发身份同时启用会在打开监听端口前返回 `configuration_error`。

调用当前上下文端点：

```powershell
$headers = @{
  Authorization = "Bearer $env:ACCOS_DEV_IDENTITY_TOKEN"
  "X-Workspace-ID" = $env:ACCOS_DEV_IDENTITY_WORKSPACE_ID
}
Invoke-RestMethod http://127.0.0.1:8000/api/v1/identity/context -Headers $headers
```

响应只包含 actor/workspace、主体类型、策略版本和权限名，不返回 token、issuer subject 或数据库记录。

## 审计操作

`accos.audit_events` 对普通应用和数据库会话都是 append-only；数据库 trigger 会拒绝 UPDATE/DELETE。审计查询必须包含 `workspace_id`，并按单调 `sequence` 排序。payload 只允许 `operation_code` 和 `state_code` 两类最多 100 字符的稳定码，正文、请求头、凭据和任意 metadata 会被丢弃。

不要为“修复”审计记录而禁用 trigger。若存在错误事件，追加纠正事件并保留关联 ID。任何保留期清理需等待执行 22 的审批、备份与审计导出方案。

## 生产 OIDC 接入边界

当前交付 `IdentityProvider` 与 decoder-neutral `OidcJwtIdentityProvider`，验证 issuer、audience、expiry、subject、actor kind 和 ServiceIdentity ID；不包含真实企业 IdP/JWKS 连接。后续接入必须：

1. 在 adapters 实现签名、算法白名单、JWKS 缓存/轮换和网络超时；
2. 通过组合根显式注入，不能回退到开发身份；
3. 保留有效、过期、错误 audience 和错误签名契约测试；
4. 不把 JWT、Authorization header、密钥或完整 claims 写入日志/审计。
