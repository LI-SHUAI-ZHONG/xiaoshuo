# M4 Implementation Plan

> 执行：superpowers:executing-plans；当前会话实施，最后独立审查。

Goal: 实现既定 B6 与 M4，不改设计、不扩范围。
Architecture: ContextProvider 构建可审计 items；现有调用与 Run 存储复用；SQLite v4 增加实验与两条运行关联。
Tech Stack: Python 标准库、pytest，无新增依赖。
Spec: ../../07_新框架_v0/Codex总指令与里程碑.md B6、C/M4。

约束：只新增/修改 07 与根索引；不删除移动，不自动接受盲测草稿，不做真实联调。保留未提交既有成果，原地施工、不提交。

Review Focus: 失败/截断不得进入选择；揭晓前不得泄漏映射；篡改映射须报错；恢复流程不得重建已冻结上下文；旧库迁移保留数据。

## Task 1: 上下文与夹具
- [x] 先写 tests/test_context.py，验证注册、最新版本、相关人物、上一场已接受正文、规则标签/原因。
- [x] 运行测试确认失败；实现 context/base.py minimal.py rules_pack.py registry.py；build(project, scene) 中 project 是项目资料快照字典。
- [x] 接入 generation.write_scene(context_name='minimal') 与 FlowEngine(context_name='minimal')；N4 使用已确认输入，恢复保留 N4。
- [x] 复制指定 JSON 关键字段与六条规则到 fixtures；文档给出 PowerShell 建例流程。
## Task 2: 持久 A/B
- [x] 先写 tests/test_ab.py 与 test_ab_cli.py；运行确认失败。
- [x] schema/store 升级 v4；experiments/ab.py 提供 start/choose/reveal；封存规范 JSON 的 sha256 前8位。保存 run IDs，失败保留实验，不自动重试。
- [x] CLI --context 与 ab start/choose/reveal；默认操作最新实验，可 --experiment 指定。seed 只影响排列。
- [x] 测试覆盖同 seed、映射篡改、双 Run 输入、选择与揭晓重开持久化、失败状态与真实 CLI 跨进程。
## Task 3: 验证与汇报
- [x] 独立代码审查、必要回归修复；完整 pytest 与帮助命令、diff 检查。
- [x] 更新 README 与根索引文件数/大小/目录/状态/验收；按 AGENTS 第7节汇报后停止。

执行记录：测试先失败（缺失模块/CLI/示例脚本），实现后完整62项通过；独立审查无重要问题，其相关测试34项通过。遵循用户范围原地保留未提交文件，不创建worktree、不提交、不清理文件。
