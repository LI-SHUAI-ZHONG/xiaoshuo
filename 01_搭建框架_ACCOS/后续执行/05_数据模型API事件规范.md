# 数据模型、API、事件与迁移规范

## 1. 共用信封

新增业务实体统一包含 `id(UUID), workspace_id, project_id(适用时), schema_version, version, created_at, updated_at, created_by, archived_at`。Universe/Creator/Workspace资源使用自己明确的anchor，不能用null project_id绕过鉴权。时间为UTC，小说内时间使用独立StoryTime，不能把虚构历法强塞UTC。

`ContentRef = {asset_id, asset_version_id, sha256, media_type, byte_length}`；`EntityRevisionRef = {owner, entity_type, id, revision_id, version, branch_id}`；`Provenance = {source_refs[], run_id?, step_id?, prompt_version?, model_profile_version?, extraction_version?, authority, confidence?, license_ref?}`。

完整正文不进入事件、日志、幂等记录和指标标签；它是受权内容资源。Snippet仅按查看者权限提供。资产hash由服务端按实际字节计算，不能信任浏览器提交hash。

## 2. 数据表族与所有权

表名是目标命名约束；实施前对照 `证据/既有表所有者.csv`。能扩展既有表时扩展，禁止仅为命名一致创建重复事实表。每个新增表都需显式唯一约束、scope索引、FK或可验证跨域引用、归档和导出归属。

| 表族/扩展 | 必须字段与关键规则 | 所有者 / 步骤 |
|---|---|---|
| 本地credentials/sessions、membership、workspace_settings | 密码摘要/会话hash、expires/revoked、policy_version；凭据不回显；一次性Owner初始化标记 | identity /25 |
| approval_policies/approval_decisions | human_owner或dual_control、resource_kind、requester、approved_by、input_version；旧请求固定旧策略 | policy唯一属identity；请求/决定留其现有identity/workflows/evolution各资源owner，不建共享可写决定表 /25、28 |
| artifact_working_copies、扩展artifact_revisions | editor_schema_version、document_json/text_blob_ref、base_revision、client_change_id、etag、content_status；旧sha引用保持legacy | projects /26 |
| artifact_branches、revision_edges、revision_patches | branch head、parent/base、operation、stable_block_id；恢复生成新Revision，禁止抹除历史 | projects /26 |
| provider_profiles/model_profiles | endpoint引用、secret_ref、capabilities、tokenizer/dimension、价格版本、timeout；模型名可配置 | models /27 |
| prompt_versions/prompt_bindings | template正文引用、变量schema、output_schema、checksum、status、allowed_tasks；发布后不可修改 | models /27 |
| budget_reservations/model_call_attempts | workspace/run/call幂等键、reserved/settled/unknown、输入/输出/费用、provider_request_id；并发原子上限 | models /27 |
| workflow_definitions/steps扩展、workflow_edges/input_manifests | definition_version、executor_key、depends_on、required_refs、policy/budget；旧position映射线性edges | workflows /28 |
| read_receipts、dependency_edges | consumer_run/step、producer_revision、hash、role、loaded_bytes/token_count；以输入版本建立失效传播 | workflows /28、30 |
| schedules、dispatch_leases、compensation_records | due_at、timezone、misfire、lease_until、operation_key、结果unknown；审批到期和死信由同一调度器处理 | workflows /28 |
| source_versions/extraction_results | asset版本、parser版本、页/段/字符offset、encoding、OCR/解析质量、source rights | knowledge /29 |
| knowledge_nodes/translated_components/component_usages | raw→extracted→model→component→application链、purpose/input/output/constraints/applicability/genre links；事实与创作转译分开 | knowledge /29 |
| embedding_generations/index_jobs | model、dimension、chunker、metric、namespace、ready/checksum/active；切模型重嵌入不覆盖旧索引 | knowledge /29 |
| memory_records/context_packages扩展 | authoritative_revision、story_time范围、branch、provenance、mandatory标记、tokenizer_version、omissions、consent_versions | memory /30 |
| summary_versions/memory_extractions | 源Revision集合、分层摘要、保真检查、superseded_by；遗忘只降权/归档 | memory /30 |
| creative_payload_revisions | 既有CreativeRecord键 + typed payload + schema_version + content_ref；禁止通用无校验JSON桶 | creative /31–32 |
| genre_profiles/blend_plans、work_briefs | 六维基因、权重/兼容风险、目标读者、字数范围、类型演化范围；author override | novel /31 |
| work_structures/story_threads/scenes/foreshadows | series/volume/arc/chapter/scene parent、排序、POV、时间、目的、依赖、伏笔期限/回收引用 | novel /31 |
| world_components/rules/events | environment/civilization/politics/economy/technology/culture；断言强度、科技前置、资源约束、位置与距离单位 | world /32 |
| character_states/knowledge/relationships/growth | stable身份与状态分离，角色知道信息的时间/来源、动态关系维度、动机→选择→变化证据 | character /32 |
| scenario_runs/scenario_branches | baseline_revision、seed、assumptions、horizon、candidate_events、weights_label、max_steps；绝不直写Canon | creative /32 |
| generation_requests/draft_candidates/revision_batches | scene/上下文/Prompt/model绑定、finish_reason、partial标记、variants、patch、接受/拒绝理由 | 请求/候选归novel；正文Revision唯一归projects，批次协调归workflows /33 |
| check_runs/findings/rubric_versions扩展 | evidence span/Revision、checker/prompt版本、severity/confidence、not_checked区分、硬规则和主观分数分开 | consistency/quality /33 |
| acceptance_batches/projection_checkpoints | 被批准的Revision集合、expected_versions、approval_ref、committed事件序号；失败整批不发布 | workflows/各事实模块 /33 |
| research_plans/claims/evidence/reports | 问题、来源快照、retrieved_at、引用位置、支持/反证、verified/unknown/conflict、budget | knowledge /35 |
| production_plans/calendar_items/risk_signals | 多项目资源上限、依赖/截止、章节计划、暂停、风险依据；不是销量预测事实 | plan/calendar唯一归workflows；risk_signals唯一归feedback /35 |
| creator_models/style_features/learning_samples | creator anchor、consent、revision_pair/explicit signal、训练/留出划分、confidence、sample_count、可撤回 | creator /36 |
| experiments/variants/evaluations/release_packages | 固定dataset/version、基线、candidate、metric、min_samples、停止/晋升策略、回滚ref | evolution/quality /37 |
| plugin_versions/installations/sandbox_jobs | package_hash、manifest、capability grants、resource_limits、image_digest、review状态 | tools /38 |
| universes/universe_memberships/asset_bindings | explicit grant、project→universe、canonical/variant、copy/reference/derive三种复用、许可 | ip /39 |
| publication_snapshots/export_import_jobs | AcceptedRevision冻结清单、目标格式、导出hash、ID映射、import staging/commit/compensation | publishing /39 |
| media_jobs/storyboards/visual_profiles | input/输出资产版本、model/profile、seed(支持时)、provider_job_id、部分失败、cost、cancel状态 | media /40 |
| collab_documents/updates/snapshots/comments/tasks | document/branch、schema_version、update_seq、server_ack、stable block/range锚点；在线态非事实 | collaboration /41 |
| listings/package_versions/licenses/contributions/orders/ledger_entries | 安装权限、许可证版本、贡献比例、生效时间、不可变双分录、currency、refund/reversal、回调去重 | ecosystem /42 |
| backup_manifests/maintenance_runs | schema/app/package版本、PG一致性点、对象版本清单、加密key_ref、restore target、验证状态 | backup_manifests归assets；maintenance_runs复用workflows任务与记录，不另造调度 /43 |

不要同时把同一字段写入Novel、Canon和Memory作为可独立编辑事实。事实模块保存主记录，Canon保存约束/引用，Memory保存带provenance的可重建记忆视图。

每个物理表只能有一个写入owner；上表跨模块组合行表示不同表/端口协作，不表示多人共享写表。类型/API DTO可共用schema，ORM与事务提交权不能混用。

## 3. API 契约规则

- `/api/v1` 保持现有路径，新增明确资源；不用万能 `/master/run`。同一写操作必须走公开application用例。
- 写请求使用 `Idempotency-Key`；幂等键绑定actor/scope/operation/request digest，重复不同payload返回409。
- 更新/提交使用 `If-Match`；缺少返回428，冲突409并返回最新版本引用；响应错误统一code/message/details/correlation_id。
- 长任务202返回 `{operation_id, run_id, status_url, events_url, capabilities}`，设置Location；小型保存操作200/201。
- 集合必须有授权scope、稳定keyset cursor、limit上限、过滤；不能仅提供按ID查询供用户手工粘贴。
- API DTO→领域DTO→ORM严格分开。生成客户端是唯一TS后端类型来源；新增接口、query/mutation、页面同阶段接线。

## 4. 必须提供的资源操作族

表中省略统一前缀；`P=/projects/{project_id}`，`W=/workspaces/{workspace_id}`。详情、集合、合法编辑、归档、历史按资源实际行为实现，不盲目生成通用CRUD。

| 资源与操作 | 主要端点 | 步骤 |
|---|---|---|
| 初始化/登录/退出/会话、成员/工作区管理 | `/auth/{bootstrap,login,logout,session}`、`/workspaces`、`W/memberships` | 25 |
| 设置、能力、Provider与密钥写入 | `W/settings`、`W/capabilities`、`W/model-profiles`、`W/credentials`（只写） | 25、27 |
| 工作副本读写、正文读取、修订/恢复/分支/差异 | `P/artifacts/{id}/{working-copy,content,revisions,branches,diffs}` | 26 |
| Prompt版本、模型策略、调用历史/预算 | `W/prompt-templates`、`W/model-policies`、`P/model-calls`、`W/budgets` | 27 |
| 定义/验证/发布DAG、运行历史、输入/读取凭证/依赖 | `P/workflow-definitions`、`P/workflow-runs`、`/workflow-runs/{id}/{inputs,receipts,dependencies}` | 28 |
| 暂停/继续/取消/重试/死信重驱/审批 | 沿用现有run路径；重试创建linked Run且返回新ID，不偷偷重置终态 | 28 |
| 文档上传/解析/版本、搜索、转译、组件编辑/发布/使用 | `P/knowledge/{documents,search,translations,components}` | 29 |
| 记忆集合/版本/冲突/摘要/遗忘、context解释与依赖检查 | `P/memories`、`P/context-packages`、`P/context-preflights` | 30 |
| 创意/类型/混合/大纲/章节/场景/伏笔/故事线 | `P/creative/{briefs,genres,blend-plans,structures,chapters,scenes,foreshadows,threads}` | 31 |
| 世界/角色全编辑、关系、状态历史、时间线、模拟 | `P/creative/{worlds,characters,relationships,timelines,scenarios}` | 32 |
| 生成/变体/局部改写、检查/修复/批量接受/影响分析 | `P/writing/{requests,candidates,revisions,acceptance-batches}`、`P/consistency/impacts` | 33 |
| 合法全局搜索/命令/图投影 | `W/search`、`P/graphs/{kind}`；命令只映射已授权API | 34 |
| 研究/来源验证/报告、多项目计划/日历/队列 | `P/research/{plans,runs,reports}`、`W/production-plans`、`W/schedules` | 35 |
| 作者模型/学习信号/同意/历史、反馈和诊断集合 | `W/creators/{id}/{models,signals,consents}`、`P/{feedback,diagnostics,metric-points}` | 36 |
| 实验/改进/评估/晋升/回滚 | `P/experiments`、`W/evolution/{proposals,packages,deployments}` | 37 |
| 插件包/审查/安装/启停/沙箱、工具生成/模块蓝图 | `W/plugins`、`W/sandbox-jobs`、`W/extension-blueprints` | 38 |
| Universe/关联/共享、定稿/导出/导入/改编 | `W/universes`、`P/publications`、`P/{exports,imports,adaptations}` | 39 |
| 多模态请求/任务/视觉档案/分镜/媒体版本 | `P/media/{jobs,visual-profiles,storyboards}` | 40 |
| 团队/任务/评论/共享文档/短期协作ticket | `P/collaboration/{tasks,comments,documents,tickets}` | 41 |
| 私有目录/包/授权/贡献/订单/退款/账本/信誉 | `W/ecosystem/{listings,licenses,contributions,orders,ledger,reputation}` | 42 |
| 备份/恢复计划/维护/健康和日志关联查询 | `W/operations/{backups,restore-plans,maintenance}` | 43 |

真实外部提供商的connection check也是测试，应登记于45；在构建时只实现按钮和后端，不发起调用。发布/支付webhook签名检查、去重和受限payload需在代码中实现，不用未验证回调改变已付费状态。

## 5. 关键事件与提交协议

`EventEnvelope` 保留旧格式并新增payload schema版本；新增 `ArtifactContentSaved.v1`、`RevisionAccepted.v1`、`CreativeFactRevisionCommitted.v1`、`ContextInvalidated.v1`、`KnowledgeComponentPublished.v1`、`MemoryProjectionReady.v1`、`ModelCallSettled.v1`、`ExperimentEvaluated.v1`、`PackagePromoted.v1`、`PluginInstalled.v1`、`PublicationCreated.v1`、`MediaJobCompleted.v1`、`LicenseGranted.v1`。

每个消费者持久保存inbox与最后aggregate_version；投影与消费进度同事务。事件携带ID/版本/hash/引用，不能把长正文或secret塞进去。

接受章节协议：

1. 冻结草稿与所有检查对应的Revision/hash，显示差异、发现与影响。
2. 验证操作者、approval_policy、expected版本、未过期检查、待提取事实、必需上下文。
3. 先确保正文资产存在且hash一致；创建AcceptanceBatch。
4. 同一PG UoW通过公开写端口提交Novel/World/Character各自新Revision、当前指针、批准记录和Outbox；任一步失败全事务回滚。若必须异步跨事务，改用有明确prepare/commit和恢复记录的协调流程，不能静默部分成功。
5. 提交后异步抽取/投影Memory/图/搜索；有幂等键和checkpoint。下一章强依赖相关事实投影时等待watermark，不能读旧状态继续生成。
6. 自动提取的未证实事实进入候选，不覆盖作者Canon。补偿不是删除已发布事实，而是建立可追踪的撤销/替代Revision。

现有projects/creative仓储多处自行`self._sessions.begin()`，不能直接串调这些旧方法然后声称同一事务。33需由应用协调器通过新`AcceptanceTransaction`端口获取同一UoW装配的各owner写端口，仓储在该调用内只flush不commit，由最外层统一提交。事务相关锁按固定实体顺序获得，检查expected_versions并在冲突时整体回滚；不得在事务锁内等待模型或对象上传。单模块旧用例可保留自己创建UoW的包装器，核心业务校验必须复用。

## 6. 迁移规则

原始基线从0013起使用追加迁移和单一顺序号；接管时0013源码已存在、登记尚未同步，见[13](13_接管说明与施工断点.md)。每步开始读取真实源码head再分配，不能因本文件表序号或过期登记而硬编码迁移号；源码head不代表数据库已应用。遵循 expand→backfill→切换读写→后续contract，构建只准备脚本；真正迁移/回退演练放45隔离库。

对旧8维索引新建generation并保留旧查询；对旧CreativeRecord追加payload和status；对旧 `studio-input://sha256` 标记 `legacy_content_unavailable`，不能从hash伪造原文；旧Workflow的position转换为edges并保持定义版本；Creator/Universe anchor创建显式映射表，不跨项目自动合并人名/世界名。

向量“可存储”不等于“可建立所选索引”。29须记录pgvector扩展版本、存储精度/索引类型及其维度上限：常见vector HNSW/IVFFlat上限为2000维，halfvec为4000维。优先选模型实际支持的合适输出维度；较高维度可保留原向量并用halfvec候选索引+原精度重排，或明确精确检索降级。不得任意截断/补零来适配，须有召回评估；超过安装版本能力明确拒绝/待配置。[pgvector索引说明](https://github.com/pgvector/pgvector#hnsw)。
