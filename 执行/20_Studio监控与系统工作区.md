# 执行 20：Studio 监控与系统工作区

## 任务目标

在执行 19 的项目工作区上补齐 Workflow Monitor、Agent Center、Consistency/Quality、Feedback、System/Settings 页面，并用 SSE 展示技术烟雾任务的真实状态。

## 前置条件

- 执行 19 的项目与创作页面通过。
- 执行 17 的 Workflow/Agent/Consistency/Feedback API 与 SSE 契约可用。

## 本阶段实施

1. 创建 `/projects/[projectId]/workflows`、Run 详情、`/projects/[projectId]/agents`、`/projects/[projectId]/quality`、`/feedback`、`/system`、`/settings` 路由。
2. Workflow Monitor 使用状态查询 + SSE，展示步骤、尝试、等待审批、重试、失败原因、预算、取消/重试和终态；断线时从最后事件恢复，再以服务器状态校准。
3. Agent Center 展示 Descriptor/Run/工具权限/模型策略/预算和 `NOT_CONFIGURED` 状态；不得将注册描述符误显示为在线 Agent。
4. Consistency/Quality 页面展示 Finding、证据引用、检查状态与 Resolution Proposal；只有授权 actor 可批准，不能提供“自动修改全部”。
5. Feedback 页面展示脱敏指标、Diagnostic Finding、Experiment/Improvement Proposal 与行为同意状态；撤回入口连接真实应用用例。
6. System 页面展示 live/ready/degraded、数据库/Redis/S3/Fake Provider/Worker/Outbox 状态和关联诊断；Settings 只显示当前可配置项与 Feature Flag 状态。
7. Dashboard 现在可以加入真实 Run/Agent/依赖健康摘要，所有数字来自 API，并链接到对应详情。
8. 所有修改操作处理 202、409、403、429、终态竞争和确认 Dialog；浏览器状态不是事实源。
9. 覆盖直接访问、刷新、空数据、无权限、后端失败、SSE 断线/过期游标、窄屏和键盘操作；写入 `docs/handoffs/20.md`。

## 本阶段不做

- 不生成章节、人物、世界、反馈样例或系统假指标。
- 不实现高级工作流拖拽、实时协同、自动修复或自动部署。
- 不在浏览器保存模型密钥、后台任务状态或权限真相。

## 验证

- 可从页面提交 `framework_smoke`，观察 Director/Workflow/Fake Agent/Fake Model 全过程，刷新与断线重连终态一致。
- 取消、重试、待审批、审批拒绝、预算耗尽和 Provider 降级均显示真实服务端状态。
- VIEWER 无写操作且直接调用仍被拒绝；无权限 SSE 事件不可见。
- Finding/Improvement Proposal 未获批准不能产生事实修改或部署状态。
- Dashboard/System 不含硬编码在线、成功或统计数字。
- 前端 lint、类型、单测、构建与监控页面 Playwright 测试通过。

## 完成标准

- 原资料七类核心工作区及系统/反馈页面全部具有真实空状态、权限态、错误态和任务状态。
- `docs/handoffs/20.md` 标记 `PASS`，附页面—API—SSE—权限映射表。

