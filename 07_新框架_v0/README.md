# 新框架 v0

独立的小说写作命令行骨架，施工规则见 AGENTS.md，设计与验收见 Codex总指令与里程碑.md。
M0–M4 已实现：本地项目存储、模型适配器、六节点流程、可注册上下文与持久 A/B 盲测。

## 安装、运行与测试（Windows PowerShell）

需要 Python 3.11 或以上。进入本目录后执行以下命令；使用独立虚拟环境，无需激活脚本或更改执行策略。
首次安装需要网络下载 setuptools 与 pytest。

```powershell
cd 'D:\搭建\07_新框架_v0'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m nw --help
.\.venv\Scripts\python.exe -m pytest
```

仓库位置不同时只修改第一行路径。虚拟环境激活后，对应命令就是 `python -m nw --help` 和 `python -m pytest`。
预期：帮助显示 M4 context and A/B，pytest 全部通过。裸运行 `python -m nw` 也显示帮助。

## 目录与配置

- `src/nw/`：Python 包和 CLI；`llm/` 提供三种适配器；`flow/` 实现六节点与恢复；`context/` 提供上下文包；`experiments/ab.py` 实现盲测。
- `src/nw/models.py`：B2 数据类；`schema.py`：建表脚本与版本 1→2→3→4 迁移；`store.py`：SQLite 与接受正文导出。
- `tests/`：导入、存储与独立 CLI 进程测试；`fixtures/`：包含最小示例与六条手工规则。
- `workspace/`：运行数据目录，已忽略上传，每个项目使用 `<project>/nw.db`，已接受正文导出到 `<project>/正文/ch01_s01.md`。
- `config.example.toml`：模型和路径配置示例；复制为 config.toml 后填写真实模型。密钥只读环境变量，配置文件不允许 api_key 字段。
- `pyproject.toml`：运行时无第三方依赖；pytest 用于测试，setuptools 用于安装。

M4 验收后停止；里程碑之外的功能需作者另行决定。


## M1 使用示例（PowerShell）

在本目录运行。`--project` 是单个目录名；`--workspace` 可省略，默认固定为本框架目录下的 workspace，不随当前工作目录改变。全局选项放在子命令之前。

```powershell
.\.venv\Scripts\python.exe -m nw --project demo init --name '示例项目'
.\.venv\Scripts\python.exe -m nw --project demo brief --text '作者的一句话需求' --constraints '受限第三人称'
.\.venv\Scripts\python.exe -m nw --project demo bible add --kind style --name '叙述方式' --body '受限第三人称'
.\.venv\Scripts\python.exe -m nw --project demo bible list
.\.venv\Scripts\python.exe -m nw --project demo outline chapter --index 1 --title '第一章'
```

命令输出 JSON，其中章的 `id` 用于下一步。场景卡由作者提供 UTF-8 JSON 对象，可写目的、视角人物、信息权限、预期状态变化、文风要求；M1 保存原文，不推断或生成内容。

```powershell
# card.json 是你准备好的场景卡；替换下列 ID 和文件路径。
.\.venv\Scripts\python.exe -m nw --project demo outline scene --chapter CHAPTER_ID --index 1 --card 'C:\path\card.json'
.\.venv\Scripts\python.exe -m nw --project demo show project
.\.venv\Scripts\python.exe -m nw --project demo show brief
.\.venv\Scripts\python.exe -m nw --project demo show chapter
.\.venv\Scripts\python.exe -m nw --project demo show scene SCENE_ID
```

`show draft DRAFT_ID` 和 `show run RUN_ID` 查看已存记录；不传 ID 则列出记录。需求和同名同类设定重复添加会新增版本，列表保留历史。章节/场景序号从 1 开始，同一父级下不可重复。重复 init 会报错，不覆盖项目。关闭终端后使用同一项目名即可读取。

## M1 存储边界与验收

- `Draft` 为冻结数据类；数据库触发器拒绝更新/删除旧草稿、跳号插入，接口在事务中分配连续版本。草稿必须关联同场景的 Run。
- `Store.accept(draft_id)` 更新接受指针并导出 UTF-8 Markdown；草稿状态和对应 Run 的 finish_reason 均须为 complete。旧草稿继续保留。
- 所有数据库写操作使用事务；迁移以 `PRAGMA user_version` 记录版本，未知版本拒绝打开。
- SQLite 是权威记录，Markdown 是可恢复导出。先提交接受指针，再在单独事务锁内导出当前已接受版本，避免提交失败却留下未接受正文。提交前失败会回滚指针；提交后导出失败会明确报错“Acceptance recorded in SQLite; export failed”，已接受记录仍保留。SQLite 与文件系统不是一个原子事务：异常终止或磁盘故障可能让导出暂时缺失/陈旧，修复磁盘问题后重新打开项目，会按已接受指针恢复导出；以数据库为准。
- M1 提供 B2 数据类及存储；M2 新增 write、runs、accept 命令。StateNote 自动提取仍未实现。
- 自动测试在 pytest 临时目录中存储明确标注 `[FAKE]` 的测试文本，覆盖 3 个版本、不可变、重开数据库、接受限制、导出一致、提交失败不发布正文、导出失败恢复和 CLI 跨进程读取。不产生正式项目正文。


## M2 配置与手动模型冒烟（由作者执行）

自动测试只使用 fake 与本机模拟 HTTP 服务，未验证任何真实模型。协议参考：[Ollama Chat](https://docs.ollama.com/api/chat)、[Chat Completions](https://developers.openai.com/api/reference/resources/chat)。

1. 按前文创建项目、需求、设定和场景卡，记下 SCENE_ID。
2. 将 config.example.toml 复制为本目录的 config.toml（若已有配置则直接编辑）。填写已安装的 Ollama 模型名；确认本机 Ollama 正在运行。
3. 执行一条真实生成冒烟命令：

```powershell
.\.venv\Scripts\python.exe -m nw --config .\config.toml --project demo write --scene SCENE_ID --provider ollama
```

使用兼容 API 时，将 `[model]` 配为：

```toml
[model]
provider = "openai_compat"
base_url = "https://你的服务/v1"
model = "你的模型名"
api_key_env = "NW_API_KEY"
timeout = 120
```

密钥须预先设置在当前进程的 `NW_API_KEY` 环境变量中，不写入 TOML 或仓库文件。将冒烟命令的 provider 改为 openai_compat；它必须与配置匹配。配置缺失、占位模型名或缺少密钥变量时退出码为 2，并显示 CONFIG_REQUIRED；不发送请求、不产生虚假成功记录。

```powershell
.\.venv\Scripts\python.exe -m nw --project demo runs
.\.venv\Scripts\python.exe -m nw --project demo show run RUN_ID
.\.venv\Scripts\python.exe -m nw --project demo show draft DRAFT_ID
.\.venv\Scripts\python.exe -m nw --project demo accept --draft DRAFT_ID
```

自定义配置路径或 workspace 时，查看、接受命令也应使用相同全局选项。路径优先级：--workspace > 配置 paths.workspace > 框架 workspace；配置中的相对路径以配置文件目录为基准。

- 每次通过配置检查的生成，先持久化 Run 输入快照（实际 messages、模型、参数、提供器、地址、超时）和本次需求/设定/场景数据，再调用模型。M4 起由 --context 指定提供器，默认 minimal。
- 返回后在同一事务内保存 Run 全文输出、finish_reason、usage、原始响应与 request_id，以及可用草稿。show run / runs 可查看完整记录。鉴权头不存储；响应中意外回显的当前 API 密钥会替换为 [REDACTED]。
- complete → complete 草稿；truncated → truncated 草稿且不得接受；error/refused → 保存 Run（含服务返回文本/原始响应），不创建正文草稿。只有 complete 的 write 退出码为 0，其余为 1。没有兜底正文、自动重试或截断补全。
- 非流式 HTTP；Ollama 地址填服务根，兼容 API 地址填 /v1。未知终止原因和不合法/空的成功响应保守记为 error。超时/网络错误按实际失败记录，不把错误详情当正文。
- 进程在调用中被强制终止时，已经写入的 Run 保留 error 初始状态且 ended_at 为空，表示调用未完成；无法恢复未收到的模型输出，也不自动重跑。
- schema v2 仅新增 run_outputs 表保存原始输出元数据，自动迁移旧 v1 数据库，不重建或删除旧记录。
- fake 仅通过测试 API 使用：Store(test_mode=True) 且目录不得位于正式 workspace 或任何 projects 目录中；输出均带 [FAKE]。CLI 不提供 fake 选项。测试中的模拟 HTTP 文本同样标记为 [FAKE]，只存临时目录。


## M3 六节点流程与恢复（Windows PowerShell）

先用 init/brief/bible/outline 录入作者需求、设定与章纲/场景卡。流程以一个已有 SCENE_ID 为单位；不重新生成或重复插入这些记录。为接受后的 StateNote 准备 UTF-8 notes.json，内容是作者确认的文本记录，例如：

```json
[{"kind":"character_state","text":"填写作者确认的角色状态"}]
```

kind 支持 character_state、foreshadow、fact。至少提供一条非空记录；它们在 N6 接受后才落入 state_notes，不由脚本推断或编造小说事实。下面命令会使用配置中的真实模型，由作者手动执行：

```powershell
.\.venv\Scripts\python.exe -m nw --config .\config.toml --project demo flow run --scene SCENE_ID --notes .\notes.json
.\.venv\Scripts\python.exe -m nw --config .\config.toml --project demo flow resume --scene SCENE_ID
.\.venv\Scripts\python.exe -m nw --config .\config.toml --project demo review --draft DRAFT_ID
```

- N1 需求、N2 设定、N3 章纲/场景卡分别显示快照，输入 confirm 继续；其他输入或输入流结束会保存 BLOCKED 并停止。尚未确认的节点在 resume 时读取最新作者输入，便于暂停后纠正；已经确认的 DONE 节点保持原快照，不会悄悄替换为后来新增的需求/设定版本。
- N4 用 --context 指定的提供器处理已确认的 N1–N3 快照并落库；恢复时复用已保存的 N4，不重新选规则或读取新版需求。
- N5 先写作，再审稿；展示草稿全文和审稿意见。输入 accept 接受当前版本，revise 按审稿意见修订，pause 停止。每次修订后再审，最多修订两轮；第三次退回后转人工决定，resume 仍显示该版本，不继续修订。所有被退回草稿和审稿 Run 均保留。
- N6 更新 Accepted、导出 Markdown、写入作者 StateNote。笔记和 N6 DONE 检查点在同一事务提交，恢复时不会重复写笔记。导出失败沿用 M1 的“数据库权威、重开修复”机制。
- flow run/resume 可追加 --yes，表示明确跳过逐项询问并接受首个完整且完成审稿的版本。该参数便于自动测试，也可由作者主动选择；默认是交互确认，模型失败时 --yes 不绕过状态限制。
- flow 完成输出含六个节点的状态和输入/输出的 JSON，退出码 0；等待确认、达到修订上限、调用失败/结果未知时返回 BLOCKED、具体原因与退出码 1；缺模型配置为 CONFIG_REQUIRED、退出码 2。
- schema v3 新增 flow_meta/flow_nodes，迁移保留旧数据。每个场景只建一个流程，重复 run 会提示使用 resume；恢复要求原提供器、模型、参数、端点及超时设置相同，密钥仍只从环境读取。
- 恢复跳过 DONE 节点，并复用已落库的 write/review/revise Run；审稿只产 Run，不产正文 Draft。进程若在模型调用中被强制终止，结果未知的 Run 保留且流程阻塞，不自动重发或冒充完成。可用 runs/show run/show draft 检查。确认要重新请求模型时，显式执行 `flow resume --scene SCENE_ID --retry-failed`；它为失败/未知调用新增 Run，旧记录不变，已完成调用不重复。重试仍失败则再次停止；两轮修订上限保持不变。未知调用可能已在服务端执行，显式重试可能产生第二次请求。
- 可先通过单独 review 命令审查已存草稿；每次审稿都有独立 Run 和完整快照。普通 write 命令的行为保持不变。

自动验收使用隔离 fake 和本机 HTTP 模拟服务：全流程接受导出、N3 中断后重开恢复、两轮上限、退回版本保留、StateNote 不重复、N5 默认不重试未知调用且支持显式重试、N6 导出失败恢复、未确认需求修正、本地恢复交错不重复写笔记、CLI 跨进程运行。没有连接真实模型，也不写正式项目正文。


## M4 上下文与 A/B 盲测（Windows PowerShell）

`write` 和 `flow run/resume` 可加 `--context minimal|rules_pack`，默认 minimal。

- minimal：最新 Brief、各设定的最新版本、场景卡及上一场已接受正文的末尾 1200 字符。按章序号/场景序号确定上一场；上一场未接受时不引入草稿。世界、文风、禁忌为通用项；人物名必须出现在场景卡中才选入。需要的人物可写入 `characters` 数组。
- rules_pack：完整保留 minimal，再按场景卡 `tags` 数组与 `fixtures/rules/*.json` 中规则标签的交集筛选。无匹配不加规则。每项保存 source/text/reason；token_estimate 是字符数粗估，并非模型 tokenizer 的精确值。规则六条摘自 2026-10-29 盲测记录中“版本二”规则说明，没有读取大资料库。
- `context.registry.register(provider)` 按唯一名字注册；实现 `name` 和 `build(project, scene)` 即可，其中 project 是资料快照字典，scene 是场景记录字典。CLI 接受注册名，未知名称在调用模型前拒绝。
- flow 恢复要求 context 名与首次一致；M3 旧流程按 minimal 兼容，已完成的旧 N4 快照原样保留。schema v4 只新增 ab_experiments，保留原表和数据。

创建独立《潮痕入骨》作者草案示例（项目名不得已存在）；仅录入资料，不调用模型、不生成正文：

```powershell
$example = .\.venv\Scripts\python.exe .\fixtures\create_example.py --project chaohen | ConvertFrom-Json
$sceneId = $example.scene_id
```

`fixtures/chaohen_minimal.json` 复制指定圣经中的世界现状、灵息规则、代价、沈砚与陆昭设定，以及首章简报第一场的目的与草案声明。场景卡的信息权限和六条规则的匹配标签是本夹具的显式组织字段，不是新剧情事实；原文件未改动。示例保持 authorial_draft，不确认正式剧情事实。

配好真实模型后，由作者手动执行（`ab start` 会发出两次真实模型请求）：

```powershell
.\.venv\Scripts\python.exe -m nw --project chaohen ab start --scene $sceneId --a minimal --b rules_pack --seed 42
.\.venv\Scripts\python.exe -m nw --project chaohen ab show
.\.venv\Scripts\python.exe -m nw --project chaohen ab choose 1
.\.venv\Scripts\python.exe -m nw --project chaohen ab reveal
```

- start/show 只展示“一/二”、实验 ID、状态与封存码。show 方便重新打开后继续盲读；choose/show/reveal 不要求模型密钥。默认使用项目内最新实验，可用 `--experiment EXPERIMENT_ID` 指定旧实验。
- 相同 seed 复现相同展示顺序；不控制模型输出。两版使用同一模型、参数及调用提示词，每版独立保存完整 Run 输入、上下文、输出与草稿。
- 映射是 `{"1":{"provider":...,"run_id":...},"2":...}`；封存码为 UTF-8、sort_keys=True、ensure_ascii=False、紧凑分隔符的 JSON 的 SHA256 前8位。封存码包含本次 Run ID，所以不同实验即使 seed 相同也有不同码。choose/reveal/show 均重新校验；映射被修改会报错。它用于核对映射，不是加密或防管理员篡改机制。
- 先 choose 后 reveal，选择只允许记录一次，揭晓后不可修改。揭晓给出提供器与 Run ID；作者可随后通过 runs/show draft 找到草稿并显式 accept。盲测选择本身不接受、不导出正文。
- 任一版失败/截断/拒绝时实验为 BLOCKED，start 退出码1，两条 Run 都保留，禁止 choose/reveal。强制终止时实验留 IN_PROGRESS，已落库调用保留；不会自动重发，可显式 start 新实验。
- 原始 runs/show run 是审计入口，会显示完整上下文。为保持盲测，请在选择前只看 ab start/show；这里不做权限隔离。真实模型也可能在正文中透露提示词内容，需作者审慎判断。
- 无真实模型配置时 start 返回 CONFIG_REQUIRED（退出码2）。自动测试仅使用临时目录中的 fake 或本机模拟 HTTP；未执行真实模型联调。
