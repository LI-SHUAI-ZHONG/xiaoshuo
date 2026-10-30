# Codex 总指令与里程碑（v0 小说写作骨架）

先读 `AGENTS.md`，再读本文件。**一次只做一个里程碑，做完停下汇报。**

## A. 可直接粘贴给 Codex 的开场指令

```text
请在仓库 xiaoshuo 的 07_新框架_v0/ 目录内，按 AGENTS.md 与《Codex总指令与里程碑.md》施工。
规则：
1. 先读根目录 00_资料说明.md、07_新框架_v0/AGENTS.md、本指令文件；不要重读全部资料，不要读 01_搭建框架_ACCOS/后续执行/ 的施工卡。
2. 只做 M0。做完运行测试并按 AGENTS.md 第 7 节格式汇报，然后停下，等我回复“继续”再做 M1。
3. 不删除、不移动任何已有文件；改动前后都要更新 00_资料说明.md。
4. 不确定就写成问题，不要自己扩范围。
```

之后每个里程碑把“只做 M0”换成对应编号。

## B. 总体设计（全部里程碑共用，务必按此，不要自行重新设计）

### B1. 目录结构（目标形态，随里程碑逐步长出来）

```
07_新框架_v0/
  AGENTS.md  README.md  pyproject.toml  .gitignore
  config.example.toml          # 模型与路径配置示例（不含密钥）
  src/nw/
    models.py                  # 数据类
    store.py                   # SQLite + 文本文件读写
    llm/  base.py fake.py ollama.py openai_compat.py
    flow/ nodes.py engine.py   # M3
    context/ base.py minimal.py rules_pack.py registry.py   # M4
    experiments/ ab.py         # M4
    cli.py                     # 命令入口：python -m nw ...
  tests/
  fixtures/                    # 示例项目《潮痕入骨》等
  workspace/                   # 运行数据（不上传）
```

### B2. 数据模型（`models.py`，用 dataclass）

- `Project(id, name, created_at)`
- `Brief(project_id, text, constraints, version)`：作者需求
- `BibleEntry(project_id, kind[world|character|style|taboo], name, body, version)`：设定条目，body 为文本
- `Chapter(id, project_id, index, title)`、`Scene(id, chapter_id, index, card_json)`：场景卡（目的、视角人物、信息权限、预期状态变化、文风要求）
- `Draft(id, scene_id, version, text, status[partial|complete|truncated|error], run_id, created_at)`：**不可变**
- `Accepted(scene_id, draft_id, accepted_at)`：指针
- `Run(id, scene_id, kind[write|review|revise], provider, model, params_json, input_snapshot_json, context_package_json, output_text, finish_reason, usage_json, started_at, ended_at)`
- `StateNote(scene_id, kind[character_state|foreshadow|fact], text)`：接受场景后记录的简易状态（v0 只做文本记录，不做图谱）

### B3. 存储

- SQLite 一个库文件：`workspace/<project>/nw.db`；迁移用简单的版本号 + 建表脚本，不引入 ORM。
- 同时把每个接受的场景正文导出为 `workspace/<project>/正文/ch01_s01.md`（便于人读）。
- 所有写操作在事务里；重启后一切可读。

### B4. 模型适配器（`llm/base.py`）

```python
@dataclass
class GenResult:
    text: str
    finish_reason: Literal["complete", "truncated", "error", "refused"]
    usage: dict
    request_id: str | None
    raw: dict | None

class LLMProvider(Protocol):
    name: str
    def generate(self, messages: list[dict], **params) -> GenResult: ...
```

- `fake`：仅测试用，输出以 `[FAKE]` 开头，行为可编程（可模拟 truncated / error）。
- `ollama`：HTTP 调本地 Ollama。`openai_compat`：任意兼容 `/v1/chat/completions` 的服务（base_url、model 来自配置，密钥来自环境变量）。
- `finish_reason != "complete"` 的结果可以存为草稿，但**不能被接受**。

### B5. 6 个核心节点（M3 实现；每个节点输入/输出都落库）

| 节点 | 内容 | 人工关卡 |
|---|---|---|
| N1 需求 | 记录作者需求 Brief | 确认 |
| N2 设定 | 世界/人物/文风/禁忌条目（作者可手写，也可让模型出候选再确认） | 确认 |
| N3 章纲与场景卡 | 章节列表、场景卡 | 确认 |
| N4 上下文包 | 由“上下文提供器”（M4 可替换）生成，保存为 `ContextPackage` | 无 |
| N5 写作与审改 | 写→审→（最多 2 轮）修订；每次都是一条 Run | 作者选择接受/退回 |
| N6 接受入库 | 写 `Accepted` 指针、导出 md、记录 StateNote | 无 |

节点状态持久化：中途中断后 `resume` 能从最后完成的节点继续。

### B6. 上下文包与提供器（M4）

```python
@dataclass
class ContextItem: source: str; text: str; reason: str
@dataclass
class ContextPackage: items: list[ContextItem]; token_estimate: int

class ContextProvider(Protocol):
    name: str
    def build(self, project, scene) -> ContextPackage: ...
```

- `minimal`：Brief + 相关设定条目 + 场景卡 + 上一场景摘要/正文片段。
- `rules_pack`：`minimal` 的全部内容 + 从**小型手工规则文件** `fixtures/rules/*.yaml|json` 里按标签选出的若干条写作规则。种子规则取自 `03_运行资料/写作实验/2026-10-29_第七息回亮_盲测.md` 中版本二使用的 6 条。**不要读取 02_原版资料 里的大文件。**
- 提供器通过名字注册，CLI 用 `--context minimal|rules_pack` 选择。

### B7. 命令行（`python -m nw ...`）

`init` 建项目｜`brief` 记录需求｜`bible add/list` 设定｜`outline` 章纲与场景卡｜`write --scene ID --provider NAME [--context NAME]` 生成草稿｜`review` 审稿｜`accept --draft ID` 接受｜`show scene|draft|run ID` 查看｜`runs` 列出运行｜`flow run/resume` 走完整流程（M3）｜`ab ...` 盲测（M4）。

## C. 里程碑与验收

### M0 目录与规则落地
- 建立 B1 的目录骨架（空包即可）、`pyproject.toml`、`README.md`（写清安装、运行、测试命令，Windows 可用）、`.gitignore`（含 `workspace/`）、`config.example.toml`。
- 放入 1 个冒烟测试（`import nw` 成功）。
- 更新根 `00_资料说明.md`：新增 07 行、目录结构、变更记录，并在第 6 节记录“决定：新建 v0，冻结 ACCOS（日期）”。
- **验收**：`python -m pytest` 通过；`python -m nw --help` 能运行；README 里的命令照做可复现。

### M1 数据与存储
- 实现 B2、B3 与命令 `init / brief / bible / outline / show`。
- 草稿不可变、版本递增、`Accepted` 指针、md 导出。
- **验收（测试必须覆盖）**：创建项目→章→场景→写入 3 个草稿版本；旧版本内容不可被覆盖；重新打开数据库后全部数据仍在；`Accepted` 只能指向 `complete` 草稿；导出的 md 与库中文本一致。

### M2 模型适配器与单次生成
- 实现 B4（fake / ollama / openai_compat）、配置读取、`write` 命令。
- 每次 `write` 产生 1 条 `Run`，保存完整输入快照与完整输出；生成结果存为 `Draft`。
- **验收**：用 fake 适配器：正常生成→草稿 `complete`；模拟截断→草稿 `truncated` 且 `accept` 被拒绝；模拟报错→记录 `error`，不产生正文；`runs`/`show run` 能看到当时发给模型的全部消息；未配置真实模型时返回 `CONFIG_REQUIRED`。真实 Ollama/API 的联调**不属于自动验收**，由用户手动做，Codex 只需提供 README 里的一条手动冒烟命令。

### M3 6 节点流程
- 实现 B5：`flow run/resume`，带人工确认关卡（交互式输入；测试里用 `--yes` 或注入应答）。
- N5：写→审→修订，最多 2 轮，之后转人工；审稿同样是一条 Run。
- **验收**：用 fake 适配器，从 Brief 跑到“场景被接受并导出 md”的端到端测试通过；在 N3 之后强制中断，`resume` 能继续且不重复已完成节点；被退回的草稿保留、不丢；`StateNote` 在接受后写入。

### M4 上下文提供器与 A/B 盲测
- 实现 B6 与 `ab` 命令组：
  - `ab start --scene ID --a minimal --b rules_pack`：各生成一版，随机（可用固定种子复现）决定展示顺序，对外只显示“一/二”，另存封存码（映射关系的 sha256 前 8 位）。
  - `ab choose 1|2` 记录作者选择；`ab reveal` 揭晓对应的提供器并校验封存码；结果写入库。
- 夹具：把《潮痕入骨》的最小设定（取自 `03_运行资料/配置/` 里的项目创作圣经与首章简报，**复制关键内容到 fixtures，不修改原文件**）做成示例项目。
- **验收**：提供器可按名注册；同一种子下展示顺序可复现；封存码校验通过且篡改会被发现；`rules_pack` 的上下文包里能看到“选入了哪些规则及原因”；A/B 的两条 Run 都保存完整输入快照。

## D. 里程碑之外（现在不做，只列在这里防止“顺手做”）

按场景检索六大资料、多章状态与伏笔图谱、审稿委员会、Web 界面、文风自动学习。每一项都要等 M0–M4 在真实模型上跑过之后，由用户单独决定。

## E. 完成后用户要做的手动验证（不由 Codex 执行）

1. 配好 Ollama 或 API，运行 README 里的冒烟命令，确认真实模型能生成并存档。
2. 用《潮痕入骨》第一场景做一次 `ab`，凭手感选一版，再 `reveal`。
3. 重启电脑后 `show scene` 仍能读到全文。
