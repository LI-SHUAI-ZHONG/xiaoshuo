# 施工公共协议 1.0.0

执行 24 冻结本登记。表格中的后续协议是实现约束，不能当作已实现功能；只有生成的公共值
当前有代码。25–44 按 owner 与步骤扩展，接口/迁移/客户端/页面由同一步串行集成。

## 唯一来源和版本

| 协议 | 所有者 / 实施 | 冻结字段与约束 |
|---|---|---|
| ScopeRef、ContentRef、EntityRevisionRef、Provenance | kernel 公共值，assets/projects/事实模块使用 /24 | 显式 scope anchor；资产版本、真实字节 hash/长度；实体 owner/不可变 revision/branch；来源和候选权威分开 |
| CapabilityStatus v2 | kernel 公共值，identity/组合根提供清单 /24–25 | implementation/configuration/health/verification/data 独立；实现需版本，验证需证据/时间；开关不证明实现 |
| CursorPageRequest | kernel /24 | cursor 为不透明且绑定 actor/scope/filter 的服务端令牌，limit 1–100；授权在查询之前 |
| RuntimePackageManifest | kernel 公共值，models/tools 等使用 /24、27、38 | owner/type/version、逐文件路径/hash/长度、entrypoints、精确依赖版本/hash、最小契约版本、schema/permissions；入口必须在清单内 |
| WorkBrief | creative.novel /31 | 原始思想引用、作者目标、推断候选、读者/长度/主题/禁限、模式、预算、缺项分字段 |
| CreativePayload | creative 子域 /31–32 | entity_type/schema_version/revision/branch、按类型判别的 payload、来源；禁止无校验 JSON 桶 |
| StageRequirement | workflows /28 | artifact_type、scope/branch、accepted_required、min_schema、mandatory、freshness |
| StepInputManifest | workflows /28 | definition/prompt/model/policy 精确版本、resolved refs/hash、grant/consent版本、预算预留；冻结后不可变 |
| ContextPackage | memory /30 | manifest_ref、sections/span、priority、mandatory、tokens、omitted/reasons、授权版本；统一 ContextBuilder |
| ReadReceipt | workflows /28、30 | run/step/source revision/hash、实际加入模型输入的 section/span/bytes/tokens/input digest |
| ModelInvocation v2 | models /27 | typed messages/content refs、结构化输出schema、受限工具、预算、operation_key；legacy metadata 协议继续读取 |
| AgentTask/Result | agents /27–28 | task_kind、input/context、allowed tools、limits；artifact refs/findings/next proposal；不含可授予权限的模型字段 |
| GenerationRequest | creative.novel /33 | 操作类型、scene、基线revision、稳定选区、锁段、候选数、POV/style；partial/complete分开 |
| CheckReport | quality /33 | revision/hash、checker/rubric版本、维度、evidence span、not_checked/findings；未检查不能算通过 |
| AcceptanceBatch | workflows /33 | 正文ref、受审事实候选、expected versions、approval/manual review、检查快照；同一UoW的owner端口提交 |
| ChangePackage | evolution /37–38 | target类型/旧新版本、样本与评估、permissions diff、迁移、回退、hash；配置与核心代码发布器分离 |

公共值由 `services/core/src/accos/kernel/shared_contracts.py` 生成 JSON Schema 与 TS。
不得手改 generated 文件；正式 API 在接线时导入同一 Pydantic 类型，客户端类型由 OpenAPI生成。
跨模块 Python 依赖仍只经过 `modules/<owner>/public.py`，由其重导出必要 port；不导入别人的 ORM。
未来领域 schema 放所属 owner，生成时显式登记纯 schema 类，不能加载应用或数据库来生成公共值。

版本规则：发布的 Prompt/Workflow/模型策略/包不可原地改变；字段兼容增加升 minor，修复描述升patch；
删字段、换语义、缩小合法范围或改变必填规则升 major，保留旧 decoder 与迁移。运行输入继续锁定
原版本。新增 enum 需同步消费者，不能默认未知值是成功；去除 legacy 类型前必须有最终迁移证据。

## 公开端口定版

下列端口名称固定职责。所属步骤复用既有公开应用门面，只有开始接线时才增加实际 Protocol。

| 端口 | owner | 服务端受信输入 → 结果 |
|---|---|---|
| ContentRepository.get / put_snapshot | assets | SecurityContext + scope + ContentRef / 有限 bytes 与类型 → 受权bytes / ContentRef |
| DependencyResolver.resolve | workflows | scope + definition version + requirements → 冻结refs或明确缺项 |
| ContextBuilder.build / explain | memory | 服务端manifest + query + budget → ContextPackage / 选入排除理由 |
| Provider.invoke / stream / embed | models | ModelInvocation v2 / 维度锁定embedding请求 → typed结果、usage、partial/unknown/refusal |
| BudgetLedger.reserve / settle / reconcile | models | scope + operation_key + policy版本 → 原子预留/结算/未知记录 |
| WorkflowExecutor.execute / compensate | workflows | 冻结StepInput + lease token → 产物refs/补偿记录 |
| CreativeReadPort.snapshot_at | creative | scope + EntityRevisionRef → 指定版本typed payload |
| AcceptanceWriter.prepare / apply | 各事实owner，workflows协调 | 已审候选+expected版本+同一UoW → 新版本与Outbox，不自行commit |
| ProjectionReader.watermark | memory/各投影owner | scope + producer版本 → 当前已处理版本/lag |
| PackagePublisher.promote / rollback | evolution协调、目标owner应用 | 固定包hash+政策/批准+expected active版本 → CAS新版本/回退记录 |

这些端口不替代权限、范围或领域不变量；仅看方法签名无法断言功能已完成。

## API、事件与错误

继续 `/api/v1`，旧端点保持可读。新写请求绑定 actor/scope/operation/digest 的 Idempotency-Key，
版本写入强制 If-Match：缺失428、冲突409。集合采用稳定 keyset，任务202+Location与状态/SSE入口。
错误使用现有 ErrorEnvelope，公开安全 message/details/correlation_id/trace_id，不记录正文/密钥。

保留现有小写 ErrorCode。后续保留码（接通所属业务时加入枚举/OpenAPI，不在24虚报已可返回）：

| 代码 | HTTP | 意义 |
|---|---|---|
| configuration_required | 409 | 需要明确配置后才能执行；details列缺项与本地设置入口 |
| mandatory_input_missing | 409 | 缺强制前置，不能生成假成功 |
| dependency_stale | 409 | 锁定输入已过时，需linked Run或重审 |
| content_unavailable | 409 | legacy正文不可恢复或引用内容暂不可用，原记录保留 |
| budget_exhausted | 409 | 原子预算不足，区别于429调用频率限制 |
| projection_not_ready | 409 | 依赖水位尚未追上 |
| insufficient_data | 422 | 任务缺证据/样本，不能声称已学习或已评估 |
| package_invalid | 422 | 包路径/完整性/schema/权限不合格 |
| capability_unavailable | 503 | 已实现的依赖暂不可用，区别于缺配置 |

`awaiting_external_result` 是持久任务子状态，不伪装成失败后盲重试；返回任务查询引用。
新增运行等待状态见后续执行04；在28同步数据库约束、状态机、Worker、SSE与客户端。

新事件在旧 EventEnvelope.payload 内放 `payload_schema_version=1`、`aggregate_version` 和
本行列出的引用。避免新增未持久字段被旧 Outbox 默默丢弃；旧 envelope.version 语义保持不变。

| 事件名称 | 唯一发布owner / 开始实施 | 最小事件引用 |
|---|---|---|
| ArtifactContentSaved.v1 | projects /26 | artifact_id、revision_id、content_ref |
| RevisionAccepted.v1 | projects，经workflows事务协调 /33 | revision_id、acceptance_batch_id |
| CreativeFactRevisionCommitted.v1 | 各creative子域 /31–33 | entity_ref、acceptance_batch_id（若属批次） |
| ContextInvalidated.v1 | memory /30 | context_id、changed_revision_ref、reason_code |
| KnowledgeComponentPublished.v1 | knowledge /29 | component_ref、source_refs |
| MemoryProjectionReady.v1 | memory /30 | projection_id、producer_ref、watermark |
| ModelCallSettled.v1 | models /27 | call_id、reservation_id、usage_ref |
| ExperimentEvaluated.v1 | evolution /37 | experiment_id、evaluation_ref、dataset_version |
| PackagePromoted.v1 | evolution /37 | package_ref、deployment_id、previous_version |
| PluginInstalled.v1 | tools /38 | installation_id、package_ref、grant_version |
| PublicationCreated.v1 | publishing /39 | publication_id、snapshot_ref、manifest_ref |
| MediaJobCompleted.v1 | media /40 | job_id、input_refs、output_refs、usage_ref |
| LicenseGranted.v1 | ecosystem /42 | license_id、package_ref、order_id（如有） |

消费者有持久 Inbox；投影与消费checkpoint同事务，按event ID去重、aggregate_version检测乱序。
语义改变创建新版本事件，旧版本继续消费，不能重写历史payload。

## 表、迁移和运行包

物理表登记：[ownership.json](ownership.json)。旧迁移逐文件 hash、head和新迁移分配登记：
[migrations.json](migrations.json)。当前 head 来自源码，不证明数据库已升级。
每步开始重读head；0013只是24观察到的下一可用前缀，后续不得照抄预占号。

`resources/prompts|workflows|rubrics|schemas` 是发布软件，27起填实并打包到wheel/Docker；
内容包仅提供格式，用户小说/知识/风格可以为空。每个包的entrypoints与schema必须在hash清单内。
软件 Prompt 包包含任务、输入、引用、缺项、输出schema、工具白名单与停止条件。
依赖锁定精确版本/hash；安装器检查环与权限；原稿和运行正文不会打入软件默认包。

新增端口/API/表/配置必须写本步交接并登记R/T。不能把本文件中“未来必须提供”的项目计入实现数量。
