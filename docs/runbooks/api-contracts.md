# API 契约与客户端运行手册

## 前置版本

在仓库根启用 `.node-version`、`.python-version` 和根 `package.json` 锁定的 Node 22.23.2、Python 3.12.14、uv 0.12.7、pnpm 11.25.0。不要使用系统中更高版本替代验收结果。

## 生成与检查

```powershell
pnpm api:export
pnpm api:generate
pnpm api:check
pnpm --filter @accos/api-client typecheck
```

`api:export` 重写 `packages/api-client/openapi.json`；`api:generate` 重写 `packages/api-client/src/generated/schema.ts`。`api:check` 不写文件，会验证：

- 当前应用工厂与 `openapi.json` 完全一致；
- schema lint 和当前快照兼容；
- 临时删除一个操作时 breaking-change 检查确实失败；
- TypeScript 生成两次字节一致，且仓库内生成物没有过期。

生成文件禁止手改。若 `api:check` 失败，先修改 Python DTO/路由或生成脚本，再重新导出、生成并评审差异。只有确认变更与 v1 兼容时，才用审核后的 `openapi.json` 更新 `openapi.snapshot.json`。

## 前端使用

```ts
import { createAccosClient } from "@accos/api-client";

const api = createAccosClient({
  baseUrl: "http://127.0.0.1:8000",
  token,
  workspaceId,
});

const result = await api.GET("/api/v1/identity/me");
```

调用方从生成的 `paths`、`operations` 和 `components` 获取类型，不再维护平行 DTO。token 只通过运行时参数提供，不写入生成物、源码或日志。

## 常见失败

- 401：Bearer credential 缺失、失效，或 `X-Workspace-ID` 不能建立身份。
- 403：角色缺少权限，或 Workspace/Project scope 与资源归属不一致。
- 409：幂等键被不同 payload 复用，或 `If-Match` 已过期；版本冲突读取 `error.details.current_version` 后重新获取资源。
- 415/422：请求不是 JSON，或 body/query/header 不符合 schema。
- 428：版本化写请求缺少 `If-Match`。
- 429：遵守 `Retry-After`，不要绕过客户端限流重试。

排障时使用响应中的 correlation/request/trace headers 和错误信封 ID 对照结构化日志；响应不会返回内部堆栈或密钥。

## 回滚

本阶段没有数据库迁移。回滚 API 时恢复 `entrypoints/api/v1`、应用工厂接线、查询/分页端口、OpenAPI 工具、客户端包、快照、测试和本文档，然后复跑执行 15 的完整门禁。不要只恢复生成文件而保留不匹配的 Python schema。
