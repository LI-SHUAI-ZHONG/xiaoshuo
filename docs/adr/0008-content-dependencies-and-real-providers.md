# ADR 0008：正文、依赖上下文与真实模型

- 状态：Accepted（由 26–33 落实）
- 日期：2026-09-24
- 扩展 ADR 0002、0003、0005

projects 拥有 Artifact、WorkingCopy、不可变 Revision 与分支指针；assets 拥有实际字节。
正文编辑器 JSON 与文本投影必须先写入不可变资产并校验 hash，再提交数据库引用。
旧 `studio-input://sha256` 记录保留并标记 `legacy_content_unavailable`；哈希不能还原正文。
保存采用 If-Match、client_change_id 和服务端版本；恢复创建新 Revision，历史保持不变。

Workflow 是唯一持久调度器。每个定义版本有显式 depends_on、输入输出 schema、强制前置、
预算、审批、重试和补偿；线性旧定义可映射为依赖边，旧 Run 继续使用已冻结版本。
Memory.ContextBuilder 是唯一上下文组装者：前置引用必须授权、读取内容并实际加入请求。
ReadReceipt 记录版本、hash、span、字节与 token；它证明输入传递，不证明模型理解。

models 统一实现云端和本地协议、Prompt 版本、路由、预算预留/结算、重试/未知结果对账。
API 与 Worker 从同一组合策略获得 Provider。新增真实功能不得默默回退 Fake；缺配置明确阻塞。
旧 Fake/Null 只保留在隔离测试或作者主动启用的演示模式，不能构成真实运行成功的证据。
模型只生成候选；缺数据或未检查不得默认高分或通过。用户资料可以空，通用运行包必须交付。

接受章节由 Workflow 应用协调器经公开端口、同一数据库事务提交批准、正文引用、领域事实
与 Outbox。模型调用和对象上传发生在事务锁外。Memory/图/搜索为异步投影；下一章如强依赖，
必须等待所需 watermark。草稿、模拟和推断保持候选，不直接覆盖 Canon。

旧事件信封继续保留。新事件 payload 加 `payload_schema_version` 与 `aggregate_version`，
二者独立于旧 envelope 的 `version`；消费者用事件 ID 去重，未知 schema 停止消费并报错。
新事件只携带 ID、版本、引用和 hash，正文与密钥不得进入事件。
