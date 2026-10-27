# 项目与资产运行手册

## 当前能力

执行 07 提供可由 Python 应用层调用的项目、Artifact 和资产服务。REST 资源端点尚未发布，必须等执行 16；不要绕过应用服务直接写表或拼接 S3 key。

数据库应处于：

```text
0008_memory_context (head；Project/Asset 结构来自 0003)
```

检查命令：

```powershell
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
uv run --frozen python scripts/verify_stage07_storage.py
```

最后一条命令只写入一个无业务含义的技术对象，校验 put/get/stat 和 SHA-256 后，在 `finally` 中删除该探针对象；它不是资产永久清理器。

## 上传排障

| 状态 | 含义 | 处理 |
|---|---|---|
| `pending` | UploadSession 已入库，对象尚未确认 | 检查对象存储可用性；不要手工创建 Asset |
| `object_stored` | 对象成功，最终元数据事务尚未完成 | 调用受授权的 `resume_upload` |
| `compensation_required` | 对象成功但最终数据库事务失败 | 修复数据库后调用 `resume_upload`；系统会复核 key、MIME、大小与哈希 |
| `failed` | 对象写失败或补偿对象不满足会话 | 保留诊断记录；不得把它伪装成 completed |
| `completed` | Asset、AssetVersion 与 Outbox 已原子提交 | 可按 scoped 服务下载或继续追加版本 |

AssetVersion 的 `missing_object` 表示数据库记录存在但对象无法读取或完整性失败。先恢复同一系统生成 key 的原对象，再通过正常下载进行哈希验证；验证成功会恢复为 `available`。

## 删除与保留

本阶段只有 `active → pending_deletion` 标记。标记时按 ProjectSettings 写入 `deletion_marked_at` 与 `retention_until`，并追加 `assets.asset-deletion-marked`。没有定时清理器、永久删除应用端口或级联删除；执行 08 以后也必须通过受控任务和审批设计后才能新增物理清理。

## 回退

1. 停止 API/Worker，确认没有执行中的项目或上传写入。
2. 备份 07 表和对象前缀；若已有非测试对象，不得只回退数据库。
3. 执行 `uv run --frozen alembic -c services/core/alembic.ini downgrade 0002_identity_security`。
4. 恢复执行 07 代码与文档变更，重新运行执行 06 全部门禁。

回退迁移删除 07 的六张表，不删除 S3 对象。对象处理必须遵守保留和人工确认流程。
