# 执行 19：Studio 项目与创作工作区

## 任务目标

先落地 Dashboard、Project Studio、Writing、Knowledge、Memory 五类项目/创作页面；所有页面连接真实骨架 API，优先呈现空状态。运行监控、Agent、反馈和系统页面留到执行 20。

## 前置条件

- 执行 18 前端底座通过。
- 执行 17 的基础资源与 Knowledge/Memory API 客户端可用。

## 本阶段实施

1. 创建本阶段路由：
   - `/` 或 `/dashboard`：系统/当前工作区概览；
   - `/projects`、`/projects/[projectId]`：空项目与 Project Studio；
   - `/projects/[projectId]/write/[artifactId]`：Writing Space；
   - `/projects/[projectId]/knowledge`；
   - `/projects/[projectId]/memory`。
2. Dashboard 本阶段只展示 API 返回的 Workspace、项目和资产概览；无数据时明确引导创建空项目，不放 Run/系统假指标。
3. Project Studio 提供容器导航：Project Info、World、Characters、Timeline、Artifacts、Assets。未填内容的模块显示功能状态和空操作入口。
4. Writing Space 搭建可替换的 Editor Port 与简单受控技术输入框、Revision 面板、Context/Memory/Knowledge 来源面板、Agent Task 面板；不引入正式富文本编辑器。
5. Knowledge 页面展示资产、摄取状态、来源和检索空/错误状态；Memory 页面展示 scope/type/filter/来源，不显示虚构记忆。
6. 为本阶段路由覆盖直接访问、刷新、空数据、无权限、404、后端失败与窄屏；写入 `docs/handoffs/19.md`。

## 本阶段不做

- 不写章节、人物、世界、知识、记忆、反馈或创作样例。
- 不实现高级编辑器、实时协同、图片/声音/视频生成或可视化图谱。
- 不用前端假数据掩盖 `NOT_CONFIGURED/FEATURE_DISABLED`。

## 验证

- 新用户可在 UI 创建一个空项目，刷新后仍存在且作用域正确。
- 最小技术文件上传、摄取状态、带来源检索和 Memory 技术记录可从页面查看。
- VIEWER 无写按钮且直接调用写 API 仍被拒绝；跨项目 URL 不泄露数据。
- 所有页面在无内容时提供真实空状态，无硬编码成功/在线/统计数字。
- 前端 lint、类型、单测、构建与关键页面 Playwright 测试通过。

## 完成标准

- Dashboard、Project Studio、Writing、Knowledge、Memory 五类页面真实可导航，项目上下文在刷新后保持正确。
- `docs/handoffs/19.md` 标记 `PASS`，附页面—API—权限映射表。
