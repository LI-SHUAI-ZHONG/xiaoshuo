# 执行 17：API 资源路由与实时事件

## 任务目标

在执行 16 的公共契约上分批公开 Workflow、Agent、Knowledge、Memory、Creative、Consistency/Quality、Feedback 资源，并建立可恢复、按权限过滤的 SSE 任务事件流。

## 前置条件

- 执行 16 的第一批端点、OpenAPI 快照与生成客户端通过。
- Workflow/Agent/Knowledge/Memory 等应用用例已有持久化与权限测试。

## 本阶段实施

1. 第二批路由按模块逐组落地并逐组验证：
   - workflows、runs、steps、tasks、approvals；
   - agents/runs、models/status、tools/status；
   - knowledge/documents、ingestion-runs、search；
   - memories、conflicts、context-packages；
   - creative/worlds、characters、works、drafts；
   - consistency/findings、resolutions、quality/evaluations；
   - feedback、diagnostics、improvement-proposals。
2. 只公开当前已有用例；远期或 Null 能力不注册路由，或在明确 Feature Flag 下返回 `FEATURE_DISABLED/NOT_CONFIGURED`，不得返回伪造成功。
3. 所有长任务统一返回 202、Run/Task Location 和幂等结果；取消、重试、审批、并发版本和终态使用统一语义。
4. 创建 SSE `/api/v1/events` 或资源级流：事件 ID/递增序列、类型、schema 版本、关联 ID、run ID、时间；支持 `Last-Event-ID`、心跳、断线重连、过期游标和 Workspace/Project 权限过滤。
5. 浏览器连接只用于展示；真实状态从 PostgreSQL查询，断线不取消 Workflow。SSE Relay 只消费已发布的版本化运行事件。
6. 每组路由复用执行 16 的公共矩阵，并补充：异步 202、取消/重试、空检索、not-configured、冲突/审批和终态测试；无需为同一公共断言机械复制八份测试。
7. 重新生成 OpenAPI 快照与 `packages/api-client`，检查破坏性变更；前端不手改生成结果。
8. 进行关联链验证：API -> Workflow -> Agent -> Model/Tool -> Finding/Memory -> SSE，所有引用可追踪。
9. 写入 `docs/handoffs/17.md`，按资源组列出状态、端点、权限和测试证据。

## 本阶段不做

- 不实现多人实时协同编辑 WebSocket，不把 SSE 当消息队列或事实源。
- 不暴露内部 Worker、Celery、数据库、模型密钥或原始错误堆栈。
- 不创建万能 `/api/master/run`，不绕过模块应用用例。

## 验证

- 每一资源组在加入下一组前独立通过公共矩阵与本组特例。
- 同一异步幂等请求只产生一个 Run；版本冲突、取消、审批和终态契约稳定。
- SSE 断线重连从最后事件继续，不重复改变 UI 终态；无权限事件不可见，过期游标有明确恢复策略。
- 禁用远期 Feature Flag 后 OpenAPI、客户端和核心路由保持稳定。
- 生成客户端 strict 编译，OpenAPI breaking diff 通过。

## 完成标准

- 全部已启用骨架能力可通过类型化 API 与 SSE 使用，未实现能力状态真实。
- `docs/handoffs/17.md` 标记 `PASS`，附第二批端点、事件 schema 和权限矩阵。

