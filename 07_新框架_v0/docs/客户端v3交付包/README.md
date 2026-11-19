# 客户端 v3：仓库内完整交付包

正式位置是本目录、`../../src/nw/studio/`、`../../tests/test_studio_v3_*.py` 及下述资料基线。Codex 聊天附件目录只保留副本；客户端运行不依赖 `C:/Users/li/Documents/Codex/`。

## 内容与位置

| 内容 | 仓库内位置 |
| --- | --- |
| 作者输入规格原文 | 本目录 `作者输入规格原文.txt`，保留原始字节；与 `../客户端v3框架设计规格.md` 正文一致，仅换行不同 |
| 客户端前后端与图标 | `../../src/nw/studio/` |
| 参考用法阶段输入 | `../../src/nw/materials/author_references.py` |
| 工作流衔接 | `../../src/nw/novel_flow.py`、`../../src/nw/novel_store.py` |
| 开发与使用配置示例 | `../../config.example.toml`；实际密钥读取环境变量 |
| 自动化回归 | `../../tests/test_studio_v3_*.py` 及已明确迁移的旧客户端测试 |
| 交付说明、快速上手、截图、测试日志 | 本目录对应 Markdown、PNG、TXT、JSON |
| 浏览器验收脚本与隔离服务器 | 本目录 `验收脚本/`；输出默认写入 `build/`，不写正式小说库 |
| 九个原版资料文件 | 仓库根目录 `02_原版资料/`，已由 Git 跟踪，未修改原件 |
| 当前六文件解析清单 | `../../fixtures/material_semantics/current_version_manifest.json` |
| 当前运行资料完整基线 | `../../fixtures/materials_runtime_baseline/v3-20261119/` |
| 校验、恢复与新建快照工具 | `../../tools/materials_baseline.py` |

## 当前资料运行基线

归档包含 `catalog.db`、`adjudication.db`、`active_source_set.json`、F1/F2 台账、网络身份对账、来源登记、作者待确认清单等 16 个文件。SQLite 使用只读连接及在线备份冻结一致快照，没有改写正在使用的资料数据库。

三个压缩分片合计 196,375,966 字节；每个分片不超过 64 MiB。`manifest.json` 保存各分片、解压文件、当前六份原件的大小和 SHA-256，以及 21 个核心裁定文件的联合指纹。

实际恢复核对见 `资料恢复核验.json`：六个当前来源、22,941 条运行资料，6,365 条 design_ready、9,315 条 blocked、7,261 条 reference，与当前工作区的 ID/状态/类型签名一致；裁定状态为 `current`。该结果证明运行资料可还原，不代表所有资料原义或文学效果已验收。

重复的历史语义索引、1 GB 级全量审计明细和中断的 `.tmp` 文件是可再生缓存，没有混入正式基线；它们逐项列在清单的 `excluded_caches`。实际小说项目库、API 个人配置及密钥也不在这份资料基线中。

## 从 Git 检出后恢复并启动

在 `07_新框架_v0` 目录执行，使用 Python 3.14：

```powershell
python tools/materials_baseline.py verify
python tools/materials_baseline.py restore --workspace workspace
if (-not (Test-Path -LiteralPath config.toml)) {
    Copy-Item -LiteralPath config.example.toml -Destination config.toml
}
$env:PYTHONPATH='src'
python -m nw studio --host 127.0.0.1 --port 8767 --open-browser
```

上述命令仅在本地没有 `config.toml` 时复制示例配置。随后在设置中填写通用 API 地址、模型名称和密钥环境变量名。运行客户端不需要 Node、Playwright 或前端构建。

恢复工具不会覆盖内容不同的已有文件；已有创作工作区请选择一个空目录先恢复。原件版本或受保护代码指纹不同会明确拒绝恢复，不能靠旧裁定库掩盖差异。所有路径相对工具所在仓库解析，不依赖原机器的 C 盘聊天目录。

仓库现在固定九份原件的字节保存规则，并固定 21 个核心文件和阶段路由的 LF 换行。旧 Git 索引曾自动规范化五份原件的换行，本次将 D 盘现存原件的准确字节存入 Git；没有编辑原件内容，逐份去除换行差异后与原 HEAD 完全一致。这样重新检出不会因 Git 换行转换而使原件哈希或裁定指纹失效。

## 验收与历史记录

- v3 整仓基线：`1189 passed in 897.33s (0:14:57)`，日志为 `完整回归日志.txt`。
- 随后的通用 API 设置改动：相关专项 `22 passed in 5.59s`，浏览器保存/重载记录见 `通用API设置验收.json`。
- 仓库交付包复验：同一专项实际 `22 passed in 3.40s`；直接从本目录运行可移植浏览器脚本，配置空值拦截、预览、保存和刷新全部通过，未发起模型调用。六份 Node 脚本语法和保护文件复核通过。
- 受保护文件校验：`protected-baseline.json`、`protected-check.json` 与 `验收脚本/check_protected.py`。
- 浏览器测试的正文均来自有显式标记的隔离 FAKE 测试模型。正式工作区没有接受任何测试正文；真实模型创作验收仍未完成。

可选的浏览器脚本需要当前环境提供 `@playwright/test`。可通过 `PLAYWRIGHT_MODULE` 指定已有包的位置、通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 指定已有 Chromium/Chrome、通过 `STUDIO_CHECK_OUTPUT` 指定截图输出目录。

从项目目录启动 `验收脚本/serve_studio_v3.py`（18765）和 `serve_studio_fixture.py`（18766），它们默认使用项目 `build/client-v3-browser/` 下的隔离数据。随后可运行对应的 shell、wizard、library、production、controls、generic_api_settings 检查脚本。书籍写入型检查只对这些隔离服务器使用；重复验收请为服务器指定新的隔离目录。

恢复资料后可用标准库脚本 `python docs/客户端v3交付包/验收脚本/check_repository_restore.py`，检查九份原件、21 个核心文件、完整阶段路由、资料裁定状态和客户端真实 HTTP 响应。它不调用模型、不写小说正文。

## Git 保存范围

本次源码、规格、交付文档、验收记录、图标、可移植验收脚本和有效资料基线应一同提交到 Git。`workspace/` 中的个人小说状态、实际 API 配置和 `build/` 临时缓存继续保留原忽略规则；资料基线已在 `fixtures/` 单独归档，不依赖被忽略的运行库才能恢复。

`原版资料完整`、`交付文件已提交`、`所有功能已完成`、`真实创作已验收`是不同结论。尚未实现的语义自动升级和设计单步重做等边界，仍以 `../客户端v3初版验收.md` 为准。
