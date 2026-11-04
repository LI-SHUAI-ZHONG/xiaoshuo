# 新框架 v0

独立的小说写作命令行骨架，施工规则见 AGENTS.md，设计与验收见 Codex总指令与里程碑.md。
M0–M4 已验收：本地项目存储、模型适配器、六节点流程、可注册上下文与持久 A/B 盲测。M5 的项目级模型任务与预算见 [M5 验收记录](docs/M5-验收记录.md)；M6 的真实源段、卡片版本和确认历史见 [M6 验收记录](docs/M6-验收记录.md)。

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
预期帮助显示 story、cards、plan 和现有命令，pytest 全部通过。裸运行 `python -m nw` 也显示帮助。

## 目录与配置

- `src/nw/`：Python 包和 CLI；`llm/` 提供三种适配器；`flow/` 实现六节点与恢复；`context/` 提供上下文包；`experiments/ab.py` 实现盲测。
- `src/nw/models.py`：B2 数据类；`schema.py`、`migrations.py`：逐级迁移到 v7；`store.py`：SQLite 与接受正文导出。
- `tests/`：导入、存储与独立 CLI 进程测试；`fixtures/`：包含最小示例与六条手工规则。
- `workspace/`：运行数据目录，已忽略上传，每个项目使用 `<project>/nw.db`，已接受正文导出到 `<project>/正文/ch01_s01.md`。
- `config.example.toml`：模型和路径配置示例；复制为 config.toml 后填写真实模型。密钥只读环境变量，配置文件不允许 api_key 字段。
- `pyproject.toml`：运行时无第三方依赖；pytest 用于测试，setuptools 用于安装。

## M5 调用基础

现有 CLI 命令保持原用法。项目级调用供后续工作流通过 Python 接口调用：`nw.tasks.create_budget` 注册限制，`freeze_manifest` 保存实际参数与上下文包，`run_task` 派发，`read_task` 查看结果。接入方可用 `nw.call_budget.prepare_call` 获取套用输出上限后的参数，再以 `model_settings` 冻结配置。

旧库第一次打开会逐级升级，并在项目目录旁于每步升级前生成一份经完整性检查的 SQLite 备份。未知调用会保留预算；确认重试后要用新调用 ID、递增 attempt 并设置 retry_of。旧场景流程仍通过原来的 `flow resume --retry-failed` 显式重试。


## M6 来源与卡片

`fixtures/story_seed/manifest.json` 登记首批资料的相对路径、行号及 SHA-256，`cards.json` 保存候选转译和关系。用 `nw.sources.import_seed_cards(store, manifest_path, root=repo_root)` 导入；只导入方法及来源记录时用 `import_rule_cards`。后者也接收明确标记 `origin="author"` 的原创规则候选。

`read_source_version` 和 `read_span` 可回查定位和原文；`nw.cards.read_card`、`decision_history`、`read_decision` 和 `read_links` 可检查指定版本和历史。卡片默认是待审候选，`decide_card` 记录显式决定。编辑卡片时以当前版本作 `expected_version`，将新内容以 `proposal` 提交；原决定归旧版本。导入种子不会创建传统场景、草稿或已接受正文。

## M7 接入并审阅已有稿件

`story adopt --baseline PATH` 由作者显式切换项目。文件包含 `expected_accepted`（场景 ID 到已接受草稿 ID 的映射）、`baseline` 和 `baseline_sha256`。用 `show accepted` 查看现有映射。基线字段为 `as_of_story_order`、`disclosure_order`（三段整数）、`coverage`（`entities` 和 `predicates` 两个列表）、`facts` 和 `card_refs`。若采用某张基础卡，须填写 `card_id`、`version` 和批准的 `decision_id`。基线摘要用 `nw.task_models.content_sha256(baseline)` 计算。旧流程需要先完成，或通过 `story decide` 记录 `abandon`，目标写明 `scene_id` 或未结束的 `run_id`。

接入后，用 `story show --branch main --revision 0 --time 0 --holder WORLD` 查世界事实。查人物时将 holder 换成稳定人物 ID。查读者时用 `--holder READER --disclosure 1,1,0`，章和场沿用既有编号，末位为从零开始的披露段落。用 `cards import --file PATH` 导入候选卡，`cards show --id ID --version N` 查看引用及决定历史。

接受稿件时依次执行：

1. `story extract --draft ID --manifest SCOPE.json --budget BUDGET.json` 提取并独立审查。范围文件包含 `id`、`branch_id`、`base_revision`、`story_order`，可选 `candidate_delta_refs`（按序列出的 `[delta_id, sha256]`）。预算至少包含 `max_calls`、`context_char_limit`、`output_limit`，提取及审查各占一次。作者手工整理变更时可改用 `story delta --file PATH`，文件含 `id`、`draft_id`、同形 `scope` 和 `operations` 列表。
2. `story check --delta ID` 查看证据和问题。每项操作须含 `op`、`entity_id`、`predicate`、`holder`、`claim`、`story_order`、`disclosure_order`、`expected_old`、`new_value` 和 `evidence`。证据条目含 `draft_id`、`text_sha256`、`start`、`end`，采用 Unicode 半开区间。无旧值用 JSON `null`。
3. `story decide --file PATH` 登记决定。JSON 对象含 `action: "accept"`、`reason` 及 `targets`。目标必须含确切的 `branch_id`、`scene_id`、`draft_id`、`delta_id`、`manifest_id`。将目标加上返回的 `decision_id`，作为批次 JSON 数组的一项。
4. `accept --batch BATCH.json --expected-head N --commit-id ID` 提交。候选分支加 `--branch NAME`。若改动早场，用 `story fork` 建分支并通过 `story impacts --branch NAME` 查看需重审的场景。提升前用 `story decide` 保存 `promote` 决定，其目标为 `candidate` 和 `expected_main` 两个 `{branch_id,revision}` 对象。

命令示例和验证结果另见 [M7 验收记录](docs/M7-验收记录.md)。

## M8 从 Brief 到候选设计和场景工作包

用 `brief --text TEXT --constraints TEXT` 保存作者需求。示例需求在 `fixtures/story_seed/brief.json`，`show brief` 可查看版本。要使用托管写作，先按 M7 的步骤执行 `story adopt`。新项目可用空接受映射、空事实与空卡片，从故事时间 0 开始接入。

可用 `cards import --file fixtures/story_seed/manifest.json` 导入种子。按需用 `cards decide --id CARD --version N --decision trial --reason REASON` 允许方法卡参与选配。批准和试用的方法才会被召回。把下面的 JSON 保存为 UTF-8 的 `budget.json`，数值按本次模型调用的需要填写。

```json
{"max_calls": 2, "context_char_limit": 45000, "output_limit": 2000}
```

在 07 目录用以下顺序操作。大写占位符取自上一条命令的 JSON 输出，模型配置沿用 `config.toml`。

```powershell
$nwPython = '.\.venv\Scripts\python.exe'
& $nwPython -m nw --project demo plan propose --scope book --brief-version 1 --budget budget.json
& $nwPython -m nw --project demo plan show --id BOOK_PLAN
& $nwPython -m nw --project demo cards decide --id ROOT_CARD --version 1 --decision approved --reason '选择此方向'
& $nwPython -m nw --project demo plan apply --id BOOK_PLAN --decision APPROVAL
& $nwPython -m nw --project demo plan propose --scope chapter --parent BOOK_PLAN --brief-version 1 --budget budget.json
# 对章级方案重复 show、cards decide、plan apply，取得 chapters 下的 scene_id。
& $nwPython -m nw --project demo story context --scene SCENE_ID --context-char-limit 45000
& $nwPython -m nw --project demo write --scene SCENE_ID --budget budget.json
& $nwPython -m nw --project demo review --draft DRAFT_ID --budget budget.json
```

- `plan show` 展示完整候选、成员版本、开放问题和落地映射。详案也可用 `volume` 或 `scene`，均须指定已应用的父方案。应用时核对批准决定、章场号、Brief 与分支版本。重复应用同一决定会返回既有 ID。未决的关键世界规则随子方案保留，相关场景会停在 `OPEN_DESIGN_QUESTIONS`。调用失败可以先用 `plan show --id ID` 查看记录，再用 `plan retry --id ID` 按原输入和剩余预算显式重试。
- `replan` 需要托管候选分支和已应用的父方案。应用后，未接受的受影响章场在该分支标记为过期。涉及已接受场景的替换返回 `REPLAN_ACCEPTED_DESCENDANTS` 并列出场景 ID。已有正文仍可按 M7 的分支证据流程修订和重审。
- `story context` 可以在调用前核对命中的方法、弃用理由、必需卡片、来源定位和稿件依赖。系统最多召回 20 个方法候选，并选用 0–5 个。前文按可见事实和段落定位承接。读者信息只显示与本场 POV 已知事实重合的已披露内容。模型实际收到的 `package` 与版本、预算、选配记录分开冻结，硬约束超出预算会停止。
- 已落地的场景默认按其绑定及当前分支装配。旧托管场景可传 `--story-input PATH` 给 `write` 或 `story context`，文件形如 `{"branch_id":"main","revision":2,"story_order":1,"scene_ref":{"card_id":"scene-card","version":1}}`。该场景卡与必需人物卡须已绑定到该分支版本。审稿复用写作工作包，使用独立调用预算。作者按 M7 的步骤提取证据、审查和接受正文。

见 [M8 验收记录](docs/M8-验收记录.md)。

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
