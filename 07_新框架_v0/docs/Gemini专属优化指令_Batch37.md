# Gemini 专属优化指令（发挥 Gemini 独特优势的针对性任务）

> **文档定位**：由 Gemini 4 Carbon 编写，供 Gemini 2.5 Pro 接手执行。
> **仓库**：`https://github.com/LI-SHUAI-ZHONG/xiaoshuo`，分支 `master`，最新 commit `3e9d85e`
> **工作目录**：`D:\搭建\07_新框架_v0`
> **当前基线**：1128 passed in 735.78s（0 失败），Batch 36 交付

---

## ⚠️ 你必须知道的绝对红线

1. ❌ **禁止修改 `02_原版资料/`** — 只读历史基准
2. ❌ **禁止引入第三方运行时依赖** — 纯 Python 3.14 stdlib
3. ❌ **禁止改动 `phase_routes.py` 的 REQUIRES 拓扑** — 用 `step_guard.py` 补充
4. ❌ **禁止无意改动 21 个核心裁定文件** — 触发 312MB `adjudication.db` 重算
5. ❌ **禁止在文件中保存 API Key 明文**
6. ✅ 每次改动后运行全量 `pytest` 并更新 `00_资料说明.md`
7. ✅ 前端必须保持零依赖：纯 HTML + CSS + vanilla JS

---

## 🎯 你的任务范围（只做你擅长的）

你的优势是：**超长上下文记忆、角色一致性守卫、多角色群戏管理、主动剧情推进、因果链追踪、伏笔回收**。

以下 4 个优化方向全部围绕这些优势，**不要触碰文学文笔优化**（WRITE_PROMPT / REVIEW_PROMPT / REVISE_PROMPT 的文学增强留给 Claude Opus 5.5）。

---

## 任务一：强化角色一致性检查机制（P0 最高优先）

### 1.1 现状

`step_guard.py` 的 `build_continuity_ledger()` 目前只守护 4 类约束：
- `type_guard`：类型选择与适配边界
- `world_guard`：世界规则与限制
- `plot_guard`：剧情承诺与读者情绪
- `entity_guard`：实体可见性与行动能力

**缺失**：没有专门的**角色嗓音/性格/口癖/知情范围**的跨步一致性守卫。

### 1.2 你要做的

在 `step_guard.py` 的 `build_continuity_ledger()` 中，**新增第 5 个守卫**：`character_voice_guard`

```python
# 5. 角色嗓音、性格基线和知情范围守卫
# 在 event_design / action_design / expression_design / writing 步骤中生效
# 防止同一角色在不同场景中性格漂移、口癖丢失、知情范围越界
if stage in ('event_design', 'action_design', 'expression_design', 'writing', 'anchor_design') and 'character_design' in products:
    cd = products['character_design'].get('products', {})
    voice_profiles = []
    for m in cd.get('members', ())[:6]:
        if isinstance(m, dict) and isinstance(m.get('body'), dict):
            body = m['body']
            profile = {
                'entity': m.get('key', ''),
                'voice_traits': _clip(body.get('voice_traits') or body.get('speech_pattern', ''), 80),
                'core_personality': _clip(body.get('core_personality') or body.get('personality', ''), 80),
                'knowledge_boundary': _clip(body.get('knowledge_boundary') or body.get('visibility', ''), 60),
            }
            # 只保留有实质内容的
            if any(v for k, v in profile.items() if k != 'entity'):
                voice_profiles.append(profile)
    if voice_profiles:
        ledger['character_voice_guard'] = {
            'profiles': voice_profiles,
            'rule': '同一角色的嗓音特征、核心性格和知情范围在所有场景中必须一致；'
                    '性格变化必须有明确的情节驱动事件；'
                    '角色不得获知其知情范围之外的信息。'
        }
```

**注意**：
- 字段名 `voice_traits` / `core_personality` / `knowledge_boundary` 请先阅读 `character_design.py` 和相关步骤文件确认实际使用的字段名，上面只是参考
- 你需要用 CodeGraph 或 grep 确认 `character_design` 产物的实际 schema
- 命令：`cd D:\搭建\07_新框架_v0; codegraph explore "character_design products members body"`

### 1.3 配套测试

在 `tests/` 下新建或扩展测试文件，至少覆盖：
- 同一角色跨场景嗓音一致性检查
- 知情范围越界检测（角色获知了不该知道的信息）
- 性格变化必须有事件驱动

---

## 任务二：伏笔追踪与回收提醒系统（P0）

### 2.1 现状

`plot_guard` 在 `continuity_ledger` 中保留了 `promise_plan`（最多 4 条）。但这只是**静态传递**，没有：
- 伏笔的"已埋设/已暗示/已回收"三态跟踪
- 写作步骤中的自动提醒"本场有 N 个待回收伏笔"
- 超过 N 场未回收的伏笔预警

### 2.2 你要做的

#### 方案 A：增强 `continuity_ledger` 的 `plot_guard`

在 `build_continuity_ledger()` 中，当 `stage == 'writing'` 时，额外计算：

```python
# 伏笔回收提醒（writing 步骤特供）
if stage == 'writing' and 'plot_design' in products:
    pd = products['plot_design'].get('products', {})
    current_scene = context.get('current_scene', '')
    planted = []
    due_for_payoff = []
    for p in pd.get('promise_plan', ()):
        if not isinstance(p, dict):
            continue
        status = p.get('status', 'planted')
        payoff_scene = p.get('payoff_scene') or p.get('payoff_event', '')
        if status in ('planted', 'hinted') and payoff_scene == current_scene:
            due_for_payoff.append({
                'promise': _clip(p.get('promise', ''), 80),
                'plant_scene': p.get('plant_scene') or p.get('plant_event', ''),
            })
        elif status == 'planted':
            planted.append(_clip(p.get('promise', ''), 60))
    
    if due_for_payoff or planted:
        ledger['foreshadow_reminder'] = {
            'due_this_scene': due_for_payoff,
            'still_open': planted[:6],
            'rule': '本场标记为 payoff 的伏笔必须在正文中回收或明确推迟；'
                    '已埋伏笔不得矛盾覆盖；新埋伏笔必须记录 plant_scene。'
        }
```

#### 方案 B：在 `validate_cross_step_consistency()` 中增加检查

```python
elif stage == 'writing':
    # 检查正文是否与已有伏笔矛盾
    # （具体实现取决于 writing 步骤的 value schema）
```

**请先阅读 `writing.py` 确认 writing 步骤产物的实际 schema 再决定怎么实现**。

---

## 任务三：多角色群戏协调增强（P1）

### 3.1 现状

`build_joint_material_plan()` 按资料的 profile 分为三类角色：drivers / boundaries / anchors。但这是**资料级别**的分工，不是**角色级别**的。

### 3.2 你要做的

在 `step_guard.py` 中新增函数：

```python
def build_multi_character_coordination(stage: str, products: dict, context: dict) -> dict | None:
    """
    当一个场景涉及 2+ 个活跃角色时，生成角色间的协调约束。
    防止：
    1. 对白张冠李戴（A 的台词写给了 B）
    2. 知情范围交叉污染（A 不该知道的事 B 在对话中泄露）
    3. 行动能力越界（无法行动的角色突然采取行动）
    4. 情感反应不符（性格温和的角色突然暴怒，无事件驱动）
    """
```

具体约束内容：
- 从 `character_design` 产物中提取每个角色的知情范围
- 从 `event_design` / `scene_design` 产物中提取本场参与角色
- 交叉检查：角色 A 的对白中不得出现角色 B 的私有信息
- 输出格式参考 `build_joint_material_plan` 的结构

### 3.3 集成

这个函数应该在 `expression_design` 和 `writing` 步骤中被调用，或者直接嵌入 `build_continuity_ledger()` 作为 `multi_char_guard` 条目。

---

## 任务四：剧情候选方案质量守卫（P1）

### 4.1 现状

`plot_design` 和 `scene_design` 步骤会生成候选方案，但没有系统的质量检查。

### 4.2 你要做的

在 `validate_cross_step_consistency()` 中增加 `plot_design` 的检查：

```python
elif stage == 'plot_design':
    # 1. 检查新提出的剧情事件是否与已有的 promise_plan 矛盾
    # 2. 检查因果链是否闭合（有原因没结果，或有结果没原因）
    # 3. 检查人物行动是否在其能力范围内
    # 4. 检查新事件是否重复了已有事件（防止剧情循环）
```

以及 `scene_design` 的增强：

```python
elif stage == 'scene_design':
    # 在现有的 before_state 冲突检查基础上，增加：
    # 1. 场景中出现的角色是否都在本场的参与者列表中
    # 2. 角色的位置/状态是否与前场衔接
    # 3. 时间线是否连续（不允许无理由的时间跳跃）
```

---

## 执行流程

```
1. 克隆仓库 / 拉取最新 master (commit 3e9d85e)
2. 阅读关键文件（按以下顺序）：
   a. 00_资料说明.md（总地图）
   b. docs/整体架构与全流程运行说明_Carbon交付版.md（架构全图）
   c. src/nw/materials/step_guard.py（你主要改这个文件）
   d. src/nw/materials/steps/character_design.py（确认角色产物 schema）
   e. src/nw/materials/steps/writing.py（确认写作产物 schema）
   f. src/nw/materials/steps/plot_design.py（确认剧情产物 schema）
   g. src/nw/materials/steps/scene_design.py（确认场景产物 schema）
   h. docs/Opus5.5后续改进总说明_Batch35交付后.md（全局上下文）
3. 用 CodeGraph 探索你不确定的部分：
   - codegraph explore "build_continuity_ledger"
   - codegraph explore "character_design products"
   - codegraph explore "validate_cross_step_consistency"
4. 实施任务一（character_voice_guard）→ 写测试 → 运行 pytest
5. 实施任务二（foreshadow_reminder）→ 写测试 → 运行 pytest  
6. 实施任务三（multi_character_coordination）→ 写测试 → 运行 pytest
7. 实施任务四（plot/scene 质量守卫增强）→ 写测试 → 运行 pytest
8. 全量回归：cd D:\搭建\07_新框架_v0; $env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q --tb=short
9. 更新 00_资料说明.md 和 docs/前置产物与资料调度纠正.md
10. Git commit + push（消息格式：Batch 37: xxx (NNNN passed)）
```

## 测试命令

```powershell
# 虚拟环境
cd D:\搭建\07_新框架_v0
$env:PYTHONPATH='src'

# 单文件快速测试
.\.venv\Scripts\python.exe -m pytest tests/test_batch37_xxx.py -q --tb=short

# 全量回归（约 12 分钟，基线 1128 passed）
.\.venv\Scripts\python.exe -m pytest -q --tb=short
```

## Git 操作

```powershell
cd D:\搭建
git add -A  # 注意：如果报错 '小说/' submodule，改用 git add 单独指定文件
git commit -m "Batch 37: 角色一致性守卫/伏笔追踪/群戏协调/剧情质量检查 (NNNN passed)"
git push origin master 2>&1
# 注意：PowerShell 下 git push 会报 exit code 1，这是误报
# 看到 "master -> master" 就说明推送成功
```

---

## 你不应该做的事（留给 Claude Opus 5.5）

| 编号 | 事项 | 原因 |
|:---|:---|:---|
| ❌ 1 | WRITE_PROMPT 文学增强 | 需要极致文学表达力 |
| ❌ 2 | REVIEW_PROMPT 审稿增强 | 需要细腻情感颗粒度 |
| ❌ 3 | REVISE_PROMPT 修改增强 | 需要心理潜台词把控 |
| ❌ 4 | 叙述距离与表达设计精修 | 文学领域 Claude 更强 |
| ❌ 5 | 117 条 needs_author_input | 需要作者本人确认 |
| ❌ 6 | 前端视觉打磨（动画、布局美化） | 非你优势 |

---

## 关键文件路径速查

| 文件 | 路径 | 用途 |
|:---|:---|:---|
| 跨步守卫 | `src/nw/materials/step_guard.py`（195 行） | **主改文件** |
| 角色设计步骤 | `src/nw/materials/steps/character_design.py` | 确认角色 schema |
| 写作步骤 | `src/nw/materials/steps/writing.py` | 确认写作 schema |
| 剧情设计步骤 | `src/nw/materials/steps/plot_design.py` | 确认剧情 schema |
| 场景设计步骤 | `src/nw/materials/steps/scene_design.py` | 确认场景 schema |
| 阶段路由 | `src/nw/materials/phase_routes.py` | REQUIRES 拓扑（只读！） |
| 总索引 | `00_资料说明.md` | 每次改完更新 |
| 问题台账 | `docs/前置产物与资料调度纠正.md` | 追加新批次记录 |
| 交付说明 | `docs/Opus5.5后续改进总说明_Batch35交付后.md` | 更新进度 |
| 配置示例 | `config.example.toml` | `[stage_models]` 双模型路由 |
| conftest | `conftest.py` | TEMP 重定向到 D 盘 |
| 步骤子文件 | `src/nw/materials/steps/`（445 个 .py） | 各步骤的具体实现 |

> **提示**：仓库有 `.codegraph/` 目录，可以用 `codegraph explore "xxx"` 快速定位代码。
