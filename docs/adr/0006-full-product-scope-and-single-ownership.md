# ADR 0006：完整产品范围与唯一模块所有权

- 状态：Accepted（架构决策；不表示功能已实现）
- 日期：2026-09-24
- 对应：R001、R002；后续执行 24–45

继续当前模块化单体、独立 Worker、PostgreSQL/pgvector、Redis、S3 和 Next Studio。
原 01–23 是既有骨架，阶段 23 的容器验收仍有历史缺项。24–44 补齐全部产品功能，45 集中验收。
本决策取代旧文档中“高级功能永远只预留”“运行 Prompt 不属于交付”的范围限制。

每个物理表只有一个写入模块。新表必须追加到 `docs/contracts/ownership.json`，指定声明文件、
唯一 owner、迁移与步骤；不建第二套正文、作者身份、调度、上下文或预算事实模型。
跨模块仅导入 `public`；其中可重导出协议，不放 ORM。适配器只写自己模块的表。
同一接受批次通过同一 UoW 装配的 owner 写端口提交，不串联多个自行 commit 的仓储冒充事务。

通用横切值放 kernel；创作理论、WorkBrief、检查报告等保留在其业务模块。
`kernel/shared_contracts.py` 是本阶段公共值的唯一源，JSON Schema 和 TypeScript 由其生成。
后续域契约在本阶段登记 owner、最低字段和不变量，随其实施步骤形成真实代码，不提前堆空实现。

五层映射见 `docs/architecture/17-full-product-contracts.md`。部署单元数量不决定业务完整度。
只有实时协作传输和安全沙箱因协议或隔离要求新增进程；不按愿景名词拆几十个微服务。

保留原聊天、`执行/`、01–23 交接与 0001–0005 ADR 原文作为历史。
施工前源代码基线在 `.construction/baselines/stage24-source-only-20260924/`，有归档、逐文件 hash
和恢复入口；不包含 `.env`、基础设施运行数据、依赖或缓存。它不能代替 PostgreSQL/S3 业务备份。

所有新功能完成状态由实际接线和证据决定：源码存在只可记 `IMPLEMENTED_UNTESTED`。
本次施工禁止运行测试不改变最终覆盖率、安全、迁移和真实适配器验收门槛。
