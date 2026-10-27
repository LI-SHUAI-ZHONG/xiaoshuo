# 执行 18：Studio 前端底座与设计系统

## 任务目标

创建 Next.js Creator Studio 应用壳、共享 UI 包、路由上下文、鉴权、数据请求和统一加载/错误/空状态，为原资料中的工作台页面提供稳定底座。

## 前置条件

- 执行 17 的生成客户端、资源 API 与 SSE 契约通过，API/Fake 模式可启动。
- pnpm workspace、VS Code 和前端质量门禁可用。

## 本阶段实施

1. 在 `apps/studio` 初始化 Next.js App Router + TypeScript strict + Tailwind；使用项目锁定版本，不重新生成或覆盖根级配置。
2. 在 `packages/ui` 建立设计 Token：颜色、间距、字体、层级、焦点、状态色；创建 Button、Input、Select、Dialog、Tabs、Table、Badge、Toast、Skeleton、EmptyState、ErrorState 等基础组件。
3. 建立根布局、全局导航、项目切换区、命令区、用户/工作区菜单和响应式侧栏；先显示真实空状态。
4. 建立 Route Group 与权限边界：公开状态页、已登录区、Workspace/Project 上下文；路由参数使用 `[projectId]`，不照抄 `/project/:id`。
5. 集成生成的 `packages/api-client`、TanStack Query 和统一 query key 工厂；服务端数据只进 Query Cache，Zustand 仅保存侧栏、面板、草稿 UI 等本地状态。
6. 实现 Auth/Workspace/Project Provider、Feature Flag Provider、API 错误映射、全局 Error Boundary、Not Found、Loading、Empty、No Permission、Offline/Degraded 状态。
7. 建立 SSE client 抽象和状态归并器；实际页面订阅留到执行 18。
8. 建立基础可访问性、键盘导航、焦点管理、颜色对比和响应式测试；不得只靠颜色表达状态。
9. 配置组件测试、路由烟雾测试和构建检查；写入 `docs/handoffs/18.md`。

## 本阶段不做

- 不硬编码项目名、进度数字、Agent 在线状态或任何演示内容。
- 不实现富文本编辑、拖拽工作流、图谱可视化或多人协作。
- 不直接使用 `fetch` 绕过生成客户端，也不把 API 密钥放进浏览器。

## 验证

- lint、TypeScript、组件测试和生产构建全部通过。
- 未登录、无 Workspace、无 Project、无权限、API 失败、API degraded 和空数据状态可独立呈现。
- 键盘可到达导航和核心交互；焦点不会困在关闭后的 Dialog。
- 前端没有手写重复后端 DTO，项目内无绝对 API URL。
- 禁用所有远期 Feature Flag 时应用仍可启动和导航。

## 完成标准

- Studio 壳在 Fake/空数据环境下真实可用，页面状态来自 API 而非假统计。
- `docs/handoffs/18.md` 标记 `PASS`，附路由图、状态管理边界和组件目录。
