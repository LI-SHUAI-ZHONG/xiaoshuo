# ADR 0001：模块化单体与独立 Worker

- 状态：Accepted
- 日期：2026-09-02

## 背景

ACCOS 的愿景包含工作台、领域能力、Agent、工作流、存储和外部 Provider。当前仓库尚无可运行代码，也没有真实负载、团队边界或独立扩缩容证据。此时拆分微服务会提前引入网络失败、分布式事务、版本协调和运维成本。

## 决策

第一版采用一个后端模块化单体和一个独立后台 Worker：

- API 与 Worker 共享 `services/core/` 中的领域、应用和端口契约，但拥有不同入口和进程生命周期。
- 预留 `identity`、`projects`、`assets`、`workflows`、`models`、`tools`、`agents`、`knowledge`、`memory`、`creative`、`consistency`、`quality`、`feedback`、`evolution` 模块边界。
- `creative` 未来包含 `novel`、`world`、`character`、`creator` 子域；本阶段不创建无意义空实现。
- 模块内部遵循 `entrypoints -> application -> domain <- ports <- adapters`。组合根可以装配 application 与 adapters，但不得承载业务规则。
- 模块间只调用公开 application/port 契约或订阅已发布事件，禁止读取其他模块私有表。
- 跨进程事件使用事务 Outbox；Relay 将已提交事件送入队列，Worker 以幂等方式处理。
- 只有满足 [`../architecture/05-service-extraction-criteria.md`](../architecture/05-service-extraction-criteria.md) 的可测门槛并通过新 ADR，才允许拆分服务。

## 替代方案

### 一开始拆微服务

拒绝。当前不存在独立扩缩容、故障隔离或组织所有权证据，收益无法覆盖分布式复杂度。

### 单进程、无独立 Worker

拒绝。长任务会与请求生命周期耦合，无法建立可重试、可取消和可恢复的工作流边界。

### 以函数或无服务器任务为主

暂不采用。它会在尚未选定云平台时绑定运行模型，并使本地一致性验证更困难。

## 后果

### 正向

- 事务和本地开发路径较简单，同时保留未来拆分所需的契约。
- API 与后台任务可以独立运行和扩缩容。
- 模块所有权、依赖和测试范围可在单仓库中自动检查。

### 代价与风险

- 模块隔离主要依赖代码和测试约束，执行 02 必须加入导入边界检查。
- 单体数据库可能诱发跨模块联表，必须通过数据所有权矩阵和仓储边界禁止。
- Worker 与 API 共享发布版本；出现真实部署冲突后才评估拆分。
