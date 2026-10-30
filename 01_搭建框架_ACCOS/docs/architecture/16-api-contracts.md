# API 基础契约与版本策略

## 范围

执行 16 固化受鉴权的 `/api/v1` REST 边界，只公开 Identity、Workspace、Membership、Project、Artifact、Revision、Asset 和系统健康。Workflow、Agent、Knowledge、Memory、Creative、Consistency、Quality、Feedback、Evolution 与 SSE 仍属于执行 17，不注册占位路由。

API 路由只能调用组合根提供的应用服务。DTO 和映射位于 `entrypoints/api/v1`，不导入或序列化 SQLAlchemy Model；写请求继续由应用服务执行授权、事务、审计和 Outbox。

## 服务端信任边界

每个 `/api/v1` 请求按以下顺序建立可信上下文：

1. HTTP 中间件验证 Bearer credential，并将 `X-Workspace-ID` 交给身份适配器解析。
2. 身份应用服务用服务端 User、Membership 或 ServiceIdentity 数据生成不可变 `SecurityContext`。
3. 路由依赖再次确认声明的 Workspace header 与已验证上下文一致，并按路由模板限流。
4. Workspace path、Project 和子资源的真实归属由统一依赖或应用服务校验；请求体不能提供 actor、membership 或 permission。
5. 应用服务执行 RBAC、UoW、审计和 Outbox。错误在最外层转换为安全错误信封。

客户端提供的 actor、权限或 scope 字段属于额外字段，DTO 以 `extra=forbid` 拒绝。跨 Workspace/Project 的受限资源不会被直接读取。

## 公共传输契约

| 契约 | v1 规则 |
|---|---|
| 身份 | `Authorization: Bearer …` 与 `X-Workspace-ID`；缺失或无效身份返回 401 |
| 关联 ID | 接受有效的 `X-Request-ID`、`X-Correlation-ID`、`X-Trace-ID`、`X-Task-ID`；服务端规范化或生成，并回写响应头 |
| 错误 | 非 2xx 使用 `{ "error": { "code", "message", "correlation_id", "trace_id", "details" } }`；未知异常固定为无内部细节的 500 |
| 内容类型 | 有请求体的 POST/PUT/PATCH 只接受 `application/json`，否则 415 |
| 分页 | `limit` 为 1–100；`cursor` 是不透明的 URL-safe token；响应给出 `total`、`limit`、`next_cursor` |
| 过滤与排序 | 每个集合使用有界枚举；未知值返回 422；SQL 查询包含稳定的 ID 次排序键 |
| 时间与 ID | UUID 使用规范字符串；业务时间来自 UTC aware clock，并以 RFC 3339 `date-time` 输出 |
| 幂等 | 创建 Project 要求 `Idempotency-Key`；相同 scope/key/payload 重放原结果，不同 payload 返回 409。Asset 内容哈希去重沿用资产应用用例 |
| 乐观并发 | 版本化变更要求强 ETag 形式的 `If-Match: "N"`；缺失返回 428，旧版本返回带 `current_version` 的 409 |
| 异步引用 | OpenAPI 固化 `AsyncOperationReference` 的 202 schema；实际异步任务路由留到执行 17 |
| 限流 | 按可信 actor、Workspace 与路由模板计数；429 可带 `Retry-After` |
| 缓存与浏览器安全 | API 响应为 `no-store`，并统一写入 CSP、Permissions Policy、Referrer Policy、nosniff 与 frame deny |

## 第一批端点

| 资源 | 操作 |
|---|---|
| Identity | `GET /identity/me`；弃用兼容入口 `GET /identity/context` |
| Workspace | `GET /workspaces`、`GET /workspaces/{workspace_id}` |
| Membership | `GET /workspaces/{workspace_id}/memberships` |
| Project | 创建/列表、读取、更新 settings、归档 |
| Artifact | 创建/列表/读取；Revision 创建/列表 |
| Asset | 创建/列表/读取、创建新版本、下载内容、标记删除 |
| System | `GET /system/health`；既有 `/live`、`/ready` 语义保持不变 |

以上路径均以 `/api/v1` 为前缀，表中省略前缀。删除 Asset 是保留期内的逻辑标记，不做物理删除。

## 版本与弃用策略

- URL major version 是兼容边界。新增可选字段、响应和端点可在 v1 内发布；删除/重命名端点、收紧输入、删除响应字段或枚举值必须创建新的 major path。
- `packages/api-client/openapi.snapshot.json` 是当前 major 的兼容基线。常规检查比较操作、响应、必填响应字段和枚举值；只有经过明确评审的兼容变更才更新快照。
- 弃用操作在 OpenAPI 中标记 `deprecated: true`，运行时发送 `Deprecation: true` 与指向替代操作的 `Link: …; rel="successor-version"`。没有迁移证据时不从同一 major 删除。
- 当前兼容示例 `/identity/context` 的替代入口是 `/identity/me`。它仍受相同认证、Workspace scope 和服务端授权保护。
- 服务端可并行承载两个 major 以便迁移；客户端不得通过忽略 schema 或手写重复 DTO 绕过生成契约。

## OpenAPI 与 TypeScript 所有权

`scripts/export_openapi.py` 从应用工厂生成规范化 OpenAPI；`openapi.json` 是生成输入，`openapi.snapshot.json` 是兼容基线。`scripts/api-client.mjs` 使用锁定的 `openapi-typescript` 生成 `src/generated/schema.ts`，手写的 `client.ts` 仅封装 base URL、Bearer token、Workspace header 和可注入 fetch。

OpenAPI JSON 与 `src/generated` 由各自生成器控制，不接受 Prettier/ESLint 自动改写；它们仍受导出一致性、生成两次一致性、breaking-change 自测和 TypeScript strict 编译约束。
