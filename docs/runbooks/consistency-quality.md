# Canon、一致性与质量评估运行手册

## 正常检查

先确认数据库迁移到 `0010_consistency_quality (head)` 且 ORM 无漂移：

```powershell
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
```

运行第 14 步定向与全量验证：

```powershell
uv run --frozen pytest services/core/tests/test_consistency_quality.py services/core/tests/test_consistency_persistence.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

测试会创建随机 PostgreSQL 数据库并在结束时删除；开发库不写入 fixture Canon、Finding、Rubric 或评估结果。

## 状态判读

Consistency 只有 `PASSED` 可以通过门禁：

| 状态 | 判读 | 处理 |
|---|---|---|
| `NOT_RUN` | 尚未执行 | 调度检查，不得继续 Accepted Revision |
| `NOT_CONFIGURED` | 检查器不存在或 Null | 配置实现，或由人决定是否另开受控流程；不得改成 passed |
| `RUN_FAILED` | 检查器异常 | 用稳定 `validator_execution_failed` 定位检查器；内部异常不写入结果 |
| `FINDINGS` | 检查完成且发现问题 | 从 Finding 读取证据引用、检查器 key/version 与 Workflow |
| `PASSED` | 所请求检查器真实完成且无 Finding | 可以进入 Quality Gate |

Quality 的 `NOT_RUN`、`NOT_CONFIGURED`、`RUN_FAILED`、`FAILED` 同样都阻断；只有 `PASSED` 继续。当前默认评估器只检查上游结构一致性，不代表真实创作质量。

## Finding 与 Resolution 排障

1. 用 `check_run_id` 和 `workflow_run_id` 定位检查运行。
2. 核对 Finding 的 `validator_key`、`validator_version`、`finding_type`、severity 与 `evidence_references`。
3. Resolution 必须引用同 Workspace/Project 下真实存在的 Finding；target 必须是 `creative-record://<novel|world|character>/<uuid>`。
4. 使用具备 `APPROVAL_DECIDE` 的 actor 显式批准，记录当时的 Proposal `version`。
5. 应用时传入批准后的 Proposal 版本。服务会重新读取 Creative 当前 Revision；若返回 `current_version`，重新检查影响范围并创建新 Proposal，不要覆盖。
6. 应用成功后核对 Resolution 为 `APPLIED`、`applied_by` 与 result reference/version，关联 Finding 为 `RESOLVED`，再允许 Memory Update。

Workflow Approval 与 Resolution Approval 是两道独立的持久门。Workflow Step 通过但 Resolution 仍是 `PROPOSED` 时，Accepted Revision 会失败关闭；调用层必须由同一次显式人工决定驱动两者，不能依据 UI 可见性或缺省值自动批准。

## 并发与失败

- Proposal `version` 不匹配表示另一个 actor 已决定或 claim；重新读取，不要重试旧版本。
- target `expected_version` 不匹配会返回安全的 `current_version`；这表示证据已过期，必须重新检查。
- claim 后状态为 `APPLYING`。只有 Creative 公共 Revision 用例成功返回并保存结果后才进入 `APPLIED`；未知异常不会伪装成完成。
- Quality evaluator 异常统一保存为 `RUN_FAILED` 和 `quality-result://run-failed`，不持久化供应商或内部异常文本。

## 投影重建

`ProjectionRebuilder` 只接受 `AuthoritativeEvidenceReader` 返回的 pointer-only `EvidenceProjection`，然后按 Workspace/Project 整体替换本地投影。重建来源必须是 Creative 的公开查询或版本化事件，不得查询或更新 Creative 私有 ORM 表。

重建后至少核对：

- reference、owner、entity ID、revision ID、revision version 完整；
- 所有记录属于调用上下文的 Workspace/Project；
- 同一权威输入重复重建结果一致；
- 删除投影后仍可从权威来源恢复。

## Workflow 输入引用

`canon_quality_gate@1` 使用以下技术引用传递门禁对象：

```text
canon-gate://<consistency-check-id>/<quality-run-id>/<resolution-id>/<approved-proposal-version>
consistency-resolution://<resolution-id>/applied/<accepted-revision-version>
```

格式、UUID 或版本无效时返回稳定的 `invalid-gate-reference` / `invalid-resolution-reference`；Memory Update 还会重新读取 Resolution，只有 `APPLIED` 才继续。

## 回退

先停止 API/Worker，并备份九张第 14 步表、Audit 与 Outbox。确认不需保留第 14 步数据后执行：

```powershell
uv run --frozen alembic -c services/core/alembic.ini downgrade 0009_creative_domains
```

该操作只删除 Consistency/Quality 九张表，保留第 13 步 Creative 数据。随后恢复第 14 步源码与文档，并运行第 13 步门禁和 `alembic check`。生产环境优先使用前向修复迁移。
