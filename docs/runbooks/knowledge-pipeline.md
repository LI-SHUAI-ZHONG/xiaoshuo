# 知识管线与检索运行手册

## 当前能力

默认 composition 使用 Assets 公开仓储与对象存储读取当前资产版本，配置 `TextMarkdownExtractor`、确定性 Normalizer/Chunker、`FakeEmbedder`、`PgVectorIndex`、PostgreSQL GraphProjection 和 `NotConfiguredVerificationProvider`。它不联网、不使用真实模型密钥，也不支持 PDF/DOCX/外部数据库；这些来源必须保持显式未配置。

数据库迁移 head 为 `0008_memory_context`（Knowledge 主结构来自 0007）。Knowledge REST/OpenAPI 资源留到执行 16/17；当前通过 Python 应用服务和 `knowledge_ingestion@1` Workflow 调用。

## 启动与检查

```powershell
uv run --frozen alembic -c services/core/alembic.ini upgrade head
uv run --frozen alembic -c services/core/alembic.ini current
uv run --frozen alembic -c services/core/alembic.ini check
uv run --frozen python -m accos.entrypoints.api
uv run --frozen python -m accos.entrypoints.worker
```

正常新 Run 的检查点依次为 `uploaded -> extracting -> normalized -> chunked -> embedded -> indexed -> verifying -> ready`。不要直接更新状态列、active 标记或向量表；所有重试和重建必须调用 Knowledge Service。

## 故障诊断

| 错误/状态 | 含义 | 安全处理 |
|---|---|---|
| `SOURCE_NOT_CONFIGURED` | 外部数据库或远程来源适配器未配置 | 保持失败关闭；后续实现正式适配器与凭据边界后用新请求重试 |
| `SOURCE_UNAVAILABLE` | 资产、对象或当前版本暂不可读 | 核对 Asset 状态和对象存储；仅 `retryable=true` 时重试 |
| `SOURCE_INTEGRITY_FAILED` | 对象字节 SHA-256 与资产版本不符 | 停止重试，修复/恢复对象；不得用新哈希覆盖旧来源证据 |
| `EXTRACTOR_NOT_CONFIGURED` | PDF、DOCX 或其他格式没有解析器 | 安装/实现受审查的解析适配器；不得把二进制强制当文本 |
| `EXTRACTION_FAILED` / `NORMALIZATION_FAILED` / `CHUNKING_FAILED` | 当前确定性处理阶段失败 | 按 `failed_stage` 诊断技术输入；不要删除原始资产 |
| `EMBEDDING_FAILED` | Fake/未来 Embedder 失败或数量不匹配 | 从 `chunked` 重试；确定性 Chunk ID 不会重复 |
| `INDEX_UNAVAILABLE` | pgvector 写入或检索不可用 | 修复 PostgreSQL/扩展后从 `embedded` 重试或执行重建 |
| `VERIFICATION_NOT_CONFIGURED` | 策略要求验证但没有验证器 | 配置验证器或由调用方明确采用非强制策略；不能改写为 verified |
| `VERIFICATION_UNVERIFIED` / `VERIFICATION_REJECTED` | 验证未通过 | 保留失败与来源证据；必须由新验证结果推进 |
| 空 `hits` / `NO_RESULTS` | 没有符合 scope/filter 的 active ready 版本 | 正常结果；同时检查 Workspace、Project、version 与 verification filter |

诊断顺序：先按 `workspace_id + ingestion_run_id` 读取 Run，再沿 source/document/version 检查保存的状态与哈希；随后检查 chunk/embedding/citation 投影，最后检查 vector/edge 投影。不得仅凭向量表判断资产是否存在，也不得用跨 Workspace 查询确认 ID。

## 受控重试与重建

- `retry` 只接受 `failed` Run，按 `failed_stage` 恢复并增加 attempt；已保存的 normalized/chunk/embedding 检查点保留。
- `rebuild` 可对任意已有 Run 执行，回到 `uploaded`，清除该版本的可重建投影并重新读取资产；原始 AssetVersion、KnowledgeSource 与 DocumentVersion 身份保留。
- 相同资产版本重复 `submit` 返回首次 Run；Workspace 内相同幂等键但不同资产版本或验证策略返回冲突。
- 新资产版本使用新幂等键并生成新 version；完成后旧 version 自动 `active=false`，引用仍可审计但不参与普通检索。

## pgvector 与测试 shim

正式 pgvector 环境应看到 `accos.knowledge_vector_index.embedding` 为 `vector(8)`，以及 HNSW `vector_cosine_ops` 索引。部分 Windows 测试环境的 `vector 0.8.6` 是 text domain；迁移会建立同名普通索引，适配器自动执行确定性余弦回退。若正式环境意外走回退路径，应检查：

```sql
SELECT typname, typtype FROM pg_type WHERE typname = 'vector';
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'accos' AND tablename = 'knowledge_vector_index';
```

原生扩展的 `typtype` 应为 `b`。不要在应用运行时替换扩展类型或手工转换已有向量列，应通过受测迁移处理。

## 验证

```powershell
uv run --frozen pytest services/core/tests/test_knowledge.py
uv run --frozen pytest services/core/tests/test_persistence.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

数据库测试创建随机空库，验证迁移、Fake/pgvector 共享契约、跨 scope 零结果、版本过期、重建与 Worker 租约恢复，并在结束后清理测试库。只使用 `fixture-*` 技术字符串。

## 回退

1. 停止 API/Worker，确认没有正在处理的 Knowledge/Workflow 任务；备份九张 Knowledge 表、关联 Workflow/Outbox/Audit 记录与对象存储定位信息。
2. 执行 `uv run --frozen alembic -c services/core/alembic.ini downgrade 0006_agent_runtime`。该操作删除 Knowledge 来源、文档、Run 与全部投影表，但保留 Assets、Workflow、Model/Tool 和 Agent Runtime。
3. 恢复 knowledge 模块、适配器、composition、测试和文档变更；当前仓库无提交基线，不能依赖 commit 自动回滚。
4. 重新运行执行 10 门禁与 `framework_smoke`，确认 revision 为 `0006_agent_runtime`。
