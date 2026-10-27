# 执行 16：API 基础契约与客户端生成

## 任务目标

建立类型明确、版本化、可鉴权的 `/api/v1` API 基础，先公开系统、身份、Workspace、Project 与 Asset 资源，并通过 OpenAPI 自动生成 TypeScript 客户端。复杂任务资源与 SSE 留到执行 17。

## 前置条件

- G3 的执行 09–15 均通过；执行 04 的错误与关联 ID 契约稳定。
- 领域应用层已有可调用用例，API 不得绕过它们直接访问仓储。

## 本阶段实施

1. 建立 `/api/v1` Router、统一依赖注入、请求上下文、内容类型与 OpenAPI 元数据；保留既有 `/live`、`/ready` 语义。
2. 固化通用请求/响应规则：错误信封、分页游标、过滤、排序、UTC、ID 序列化、幂等键、`If-Match`/版本冲突、202 异步引用、关联 ID 和弃用 Header。
3. 授权和 Workspace/Project scope 由统一依赖注入，路由不得信任客户端传入的 actor、workspace membership 或权限。
4. 第一批资源只包含：identity/me、workspaces、memberships、projects、artifacts、revisions、assets、system/health。只公开现有用例；未实现能力不注册假路由。
5. 统一 DTO 与领域/ORM 映射层；公开 schema 不导入 SQLAlchemy Model，写接口必须执行应用用例、UoW、审计和 Outbox。
6. 生成稳定 OpenAPI 文档和快照；使用锁定的 OpenAPI TypeScript 生成器写入 `packages/api-client`。生成文件禁止手改。
7. 增加 schema lint、breaking-change diff、后端契约测试、生成可重复性和客户端 strict 编译测试。
8. 建立公共 API 测试矩阵：正常、无权限、跨项目、无效输入、404、409、429、幂等和关联 ID；每类资源复用该矩阵并添加领域特例。
9. 写 API 版本/弃用策略和 `docs/handoffs/16.md`。

## 本阶段不做

- 不公开 Workflow、Agent、Knowledge、Memory、Creative、Consistency、Feedback 路由或 SSE；它们属于执行 17。
- 不增加 GraphQL、万能 Master endpoint 或浏览器直连 Worker/数据库。
- 不用 200 响应包装所有错误，不把 Python ORM 直接序列化给前端。

## 验证

- OpenAPI 从同一提交生成两次无差异；TS 客户端在 strict 模式下编译。
- 第一批资源通过公共矩阵；同一幂等请求不创建两个资源，版本冲突返回当前版本。
- VIEWER、跨 Workspace 和伪造 actor/scope 均被后端拒绝。
- API -> application -> UoW/审计/Outbox 的关联 ID 贯通；响应不泄露内部堆栈和密钥。
- breaking-change 工具能在临时破坏 schema 时失败，恢复后重新通过。

## 完成标准

- 前端可用生成客户端安全访问第一批基础资源，无手写重复 DTO。
- `docs/handoffs/16.md` 标记 `PASS`，附公共契约、第一批端点和兼容策略。

