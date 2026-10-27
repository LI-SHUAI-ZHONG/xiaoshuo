# 执行 14：Canon、一致性与质量评估

## 任务目标

建立长篇系统的规则事实、时间线、状态快照、Finding、质量结果和修复提案框架；先实现确定性的结构检查，语义检查保留端口。任何检查器都不能自动篡改 Canon 或正文。

## 前置条件

- 执行 13 的唯一模块归属和 Proposal/Accepted 边界通过。
- Workflow 能插入检查与人工审批 Step。

## 本阶段实施

1. 创建 `consistency` 模块：
   - `CanonEntry` 与 Level 1–4、版本、有效时间、来源、状态；
   - `TimelineEvent`、人物/世界状态引用、规则约束、依赖边；
   - `Finding`：类型、严重度、证据引用、检查器版本、状态；
   - `ResolutionProposal`：方案、影响范围、所需批准、应用结果。
2. 明确事实归属：World/Character/Novel 的当前状态与 Revision 始终由各自模块权威保存；Consistency 只拥有跨域 Canon 约束、Finding、Resolution 和只读证据投影。`TimelineEvent` 是对权威事件/Revision 的规范化断言与引用，不是第二份可独立修改的世界或人物状态。批准修复后，必须调用事实模块的应用用例生成新 Revision，再由事件重建 Consistency 投影。
3. 创建 Validator Registry 与端口：character、timeline、world rule、plot dependency、theme alignment。语义检查默认 Null，不得把未检查标为通过。
4. 实现最小确定性检查器：必填/引用完整性、时间顺序、同一实体互斥状态、版本冲突、Level 1 Canon 修改保护、未解析依赖。
5. 创建 `quality` 模块：`EvaluationRun`、`RubricVersion`、`ScoreDimension`、`QualityResult`。Rubric 只有 schema 和版本元数据，不填创作评分内容。
6. 固定工作流顺序：Draft -> Consistency Check -> Quality Check -> Approval -> Accepted Revision -> Memory Update。检查失败可阻断或转人工，不能伪装成功。
7. `ResolutionProposal` 只能由有权限的 actor 应用；应用前重新校验版本，保存审计、影响分析与新 Revision。
8. Consistency 通过只读公开接口或事件投影读取 World/Character/Novel，禁止跨模块直接写表。
9. 添加显式冲突、非法 Canon 变更、过期 Proposal、并发应用、投影重建和未配置检查器测试；写入 `docs/handoffs/14.md`。

## 本阶段不做

- 不写真实创作规则、评分权重、主题判断或修复文本。
- 不自动改章节、世界、人物、时间线或 Canon。
- 不扫描百万字内容做性能宣称；只建立可扩展批处理/分页边界。

## 验证

- 技术测试夹具能触发时间倒置、无效引用、互斥状态和受保护 Canon 修改 Finding。
- 未运行、未配置、运行失败和真正通过是四种不同状态。
- 未批准的 Resolution 不能产生 Accepted Revision 或 Memory Update。
- 过期/并发 Proposal 应用被拒绝，并返回当前版本。
- 从 Finding 可追溯证据、检查器、Workflow、actor、决议和最终 Revision。
- 模块依赖测试证明 Consistency 无跨模块写权限。

## 完成标准

- 空内容条件下，结构性一致性与质量状态链真实可运行并进入 Workflow。
- `docs/handoffs/14.md` 标记 `PASS`，附工作流门禁图和检查状态语义。
