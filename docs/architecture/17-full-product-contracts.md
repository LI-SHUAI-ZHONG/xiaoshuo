# 完整产品架构定版（执行 24）

本文件是新施工基线，旧 00–16 记录既有实现。细项以 `后续执行/04`、`05`、`11` 为共同规范。
当前进度见 `后续执行/进度.json`，不要按模块名字推断完成度。

| 愿景层 | 当前唯一承载位置 | 后续实作边界 |
|---|---|---|
| Creator Interface | apps/studio、packages/ui、api-client | 可操作的中文工作台、编辑器、关系/时间线、配置与解释 |
| Creative Intelligence | knowledge、memory、creative、consistency、quality、feedback、evolution | 资料转译、六维类型、写作理论、世界人物、审稿、作者学习、进化 |
| Agent Civilization | agents、workflows、models、tools | 一个 Agent runtime、一个持久 DAG 调度器、统一模型/工具网关 |
| Creative Infrastructure | adapters、identity、projects、assets、infra | PG 事实、不可变内容资产、身份、存储、真实协议适配 |
| Core Kernel | kernel、composition、API/Worker entrypoints | 最小横切契约、UoW、事件、权限上下文、生命周期 |

新增 ip/publishing/media/collaboration/ecosystem 各自拥有业务事实，调用已有公开端口。
extensions 只做兼容描述与桥接，不重复储存这些事实。创作子域的物理存储暂由 creative owner
管理，明确实体 discriminator；正文 Revision 永远归 projects。

`docs/contracts/ownership.json` 登记现有 68 表及唯一声明文件；未来每次新增或迁移都更新此表。
`runtime_monitor` 的既有跨表聚合是有记录的只读例外，只读工作状态/计数/用量，43 改造时复核。
新增写路径不能沿用这个例外。门禁限制跨 owner 适配器导入、重复表、错 owner 声明与越界 SQL。
这些静态约束不能证明任意动态代码安全；权限、并发、事务和动态行为仍留最终运行测试。

`docs/contracts/migrations.json` 从源码读取真实链，当前为 0001→…→0012，无新增业务迁移。
它记录的是源码 head，未查询或操作运行数据库。下一步从当时真实 head 追加，当前可分配前缀0013。
旧 12 文件有固定 SHA-256，不可改写；新增记录同时填 owner、步骤、expand/backfill 和恢复说明。

数据写入顺序：授权/幂等与版本校验→无锁外部准备→owner UoW 提交→Outbox→可恢复投影。
Blob 不参与 PG 事务；先保存对象后引用，数据库失败产生的孤儿按保留策略延迟回收。
新工作流、Prompt、模型、策略、内容和授权版本形成输入快照，禁止在途把 latest 换进去。

公共值的唯一源为 `kernel/shared_contracts.py`。`static:contracts` 只编译该源，输出
`packages/api-client/shared-contracts.json` 和 `src/generated/shared-contracts.ts`，不装配服务。
这份无路径组件文件不是新增 HTTP API；接口在所属步骤接通时再纳入正式 OpenAPI 与客户端。
领域专属协议在 `docs/contracts/README.md` 冻结所有者和最小字段，不堆入 kernel。
