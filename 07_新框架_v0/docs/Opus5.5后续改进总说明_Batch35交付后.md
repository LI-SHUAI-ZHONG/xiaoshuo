# Opus 5.5 后续改进总说明（Batch 35 交付后）

> **文档定位**：由 Gemini 4 Carbon 在完成 Batch 35 后编写，供 Opus 5.5 在获得额度后按图索骥推进剩余文学精修、原始资料缺口补全与前端体验打磨。
> **基线**：Batch 37 commit，全量回归 1146 passed，F2 台账 open=117，前端 v2 重建与角色/伏笔/群戏/因果四大守卫均已落地。

---

## 一、Carbon 已完成的工作清单

### 底层架构与工程（100% 完成）
- 14步因果状态机、哈希冻结与断点恢复
- 六大资料库 22,941 条入步解析与路由对齐
- 跨步防遗忘账本（`continuity_ledger`）
- 多资料联合创作角色仲裁（`joint_material_plan`）
- 前后状态防冲突硬守卫（`validate_cross_step_consistency`）
- **Batch 37 角色/伏笔/群戏/因果质量守卫增强（发挥长上下文与一致性强项）：**
  - `character_voice_guard`：跨场锁定角色嗓音(`voice`)、核心性格基线(`behavior`/`boundaries`)、可转变条件(`change_conditions`)与知情范围(`holders`/`unknowns`)，拦截无驱动事件的声线漂移、情绪突变与性格跳变
  - `foreshadow_reminder`：伏笔三态（`planted` 已埋设 / `hinted` 已暗示 / `paid_off` 已回收）全链路追踪，自动识别本场到期回收项（`due_this_scene`）与超出窗口/阈值的滞后预警（`overdue_warnings`），写作步硬拦截漏收或矛盾覆盖
  - `build_multi_character_coordination` / `multi_char_guard`：2+ 活跃角色群戏自动编组，隔离各角色声线人设、静态关系条件、知情不对称矩阵（`information_asymmetry`）与非行动实体禁令（`non_acting_entities`），防对白张冠李戴与场外幽灵插话
  - `plot_design` / `event_design` / `scene_design` 候选方案硬守卫：拦截因果链未闭合、因果环路、重复事件循环、`promise_plan` 倒果为因/同事件自埋自收、同刻异地分身、跨场状态断裂及无时间提示词的无故时间线跳跃
- 分步骤双模型路由（`[stage_models]`）
- TEMP 磁盘重定向（`conftest.py`）

### F2 台账处理（91.6% 完成）
- 总条目：2,532
- 已结项（resolved）：2,320
- 已废弃（discarded）：93
- 已恢复（recovered）：2
- **仍待处理（open）：117**（全部为 `needs_author_input`）

### 前端客户端（全部功能已落地）
- 6 大基础工作台（Batch 33）
- 异步错误处理、JSON 友好提示、缓存失效、路径遍历加固（Batch 34）
- Zen Reader & Diff View（Batch 35）
- SVG 交互式人物关系图（Batch 35）
- Job Stepper Drawer（Batch 35）
- 单草稿 GET 端点 + 任务列表 GET 端点（Batch 35）
- **前端 v2 完整重建（Batch 36）：**
  - 完整 CSS 设计系统（830 行，含亮/暗主题切换、CSS 变量体系）
  - 响应式布局（3 档断点：768/960/1280px，移动端抽屉式侧边栏）
  - 全局搜索覆盖层（Ctrl+K 快速检索资料/卡片/场景）
  - 通知中心滑出面板（操作日志记录）
  - Modal 对话框系统（替代 alert/confirm）
  - 项目统计仪表盘（章/场/卡片/草稿/Brief 版本 5 项统计卡片）
  - 面包屑导航
  - 加载状态管理（骨架屏 + 旋转器 + 叠加层）
  - Tooltips 组件
  - 键盘快捷键（Ctrl+1-6 切换标签，Ctrl+K 搜索，Ctrl+S 保存，ESC 关闭）
  - 侧边栏折叠/展开
  - 33 项 Batch 36 专项测试 + 完整向后兼容

### API 接入准备（路径已验证）
- `config.toml` 双模型配置预设已就绪
- `/api/projects/<name>/jobs` 创建/取消/列表接口已实现
- 环境变量安全检测已内置

---

## 二、Opus 5.5 专属改进项

### 🔴 P0: 文学正文提示词精修（Opus 5.5 绝对强项）

1. **`WRITE_PROMPT`** (`src/nw/context/story.py:21`)
   - 当前仅 79 字符，偏工程克制
   - 建议增加：中文叙事节奏控制、感官锚点要求、反 AI 套话约束、潜台词张力指引
   - ⚠️ 测试使用 `startswith` 检查，追加安全但不可修改开头文字

2. **`REVIEW_PROMPT` / `REVISE_PROMPT`** (`src/nw/novel_scene.py:24-31`)
   - 审稿提示可增加文学评判维度（节奏、留白、感官密度）
   - 修订提示可增加反同质化引导

3. **表达设计步骤** (`src/nw/materials/steps/expression_design.py`)
   - 叙述距离、情感颗粒度、潜台词层次的指引可大幅增强

4. **`joint_material_plan` 文学融合引导语**
   - `src/nw/materials/step_guard.py` 中 `build_joint_material_plan` 的 `rule` 字段
   - 可优化多份表达资料间的风格主次融合提示

### 🟡 P1: 117 条 `needs_author_input` F2 条目

分类概览（需作者裁定后 Opus 5.5 执行）：
- 原文截断（38 条）：冒号后列表丢失，需核对原件
- 跨表范围冲突（32 条）：同概念不同定义，需裁定
- 来源缺失/不完整（19 条）：引用路径有误
- 定义指令冲突（7 条）：如文风定义与身体信号指令矛盾
- 其他（21 条）

处理位置：`workspace/materials/F2_triage_needs_author_input.jsonl`
处理模板：见 `docs/F2台账剩余处理指南_Batch34分类后.md` 第三节

### 🟢 P2: 前端视觉精修

1. Zen Reader 的字体渲染和排版微调（增加繁体字支持、段间距调整）
2. SVG 关系图增加力导向布局算法（当前为圆形布局）
3. Job Stepper 增加实时 WebSocket 推送（当前为手动刷新）
4. 整体配色方案和动画细节打磨

### 🔵 P3: 实测写作调试

按 `docs/Opus5.5接手与能力分工说明.md` 第五节的 4 步流程：
1. 配置网关密钥 → 2. 启用双模型分工预设 → 3. 14步沙盘干跑 → 4. 逐场检验写审改闭环

---

## 三、工程红线（必读）

1. ❌ 禁止修改 `02_原版资料/` 只读基准
2. ❌ 禁止引入第三方运行时依赖（纯 Python 3.14 stdlib）
3. ❌ 禁止改动 `phase_routes.py` 的 `REQUIRES` 拓扑
4. ❌ 禁止无意改动 21 个核心裁定文件（触发 312MB 重算）
5. ❌ 禁止在文件中保存 API Key 明文
6. ✅ 每次改动后运行全量 `pytest` 并更新 `00_资料说明.md`
7. ✅ 测试 TEMP 已重定向到 D: 盘（conftest.py 自动处理）

---

## 四、关键文件索引

| 文件 | 用途 |
|---|---|
| `src/nw/context/story.py` | WRITE_PROMPT, StoryScope, build_story_context |
| `src/nw/novel_scene.py` | REVIEW_PROMPT, REVISE_PROMPT, 写审改闭环 |
| `src/nw/materials/step_guard.py` | continuity_ledger(含角色嗓音/伏笔三态/群戏协同), joint_material_plan, validate_cross_step_consistency（~635 行） |
| `src/nw/materials/steps/expression_design.py` | 叙述距离与表达设计步骤 |
| `src/nw/materials/steps/writing.py` | 正文写作步骤 |
| `src/nw/studio/api.py` | 后端服务层（~1,222 行） |
| `src/nw/studio/server.py` | HTTP 路由（253 行） |
| `src/nw/studio/static/app.js` | 前端控制器（~1,180 行，含全局搜索/主题切换/Modal/通知/快捷键） |
| `src/nw/studio/static/index.html` | 前端 HTML（~627 行，含侧边栏/面包屑/搜索覆盖/通知面板/Modal） |
| `src/nw/studio/static/styles.css` | 前端样式（~830 行，含完整设计系统/暗亮主题/响应式断点） |
| `docs/Opus5.5接手与能力分工说明.md` | 原始分工说明 |
| `docs/F2台账剩余处理指南_Batch34分类后.md` | F2 处理模板 |
| `workspace/materials/F2_triage_needs_author_input.jsonl` | 117 条待作者确认 |
| `conftest.py` | TEMP 重定向到 D: 盘 |
