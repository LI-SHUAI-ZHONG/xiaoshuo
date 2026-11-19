# 当前资料运行基线

`v3-20261119/` 是客户端 v3 交付时的当前有效资料快照，包含三份普通 Git 压缩分片和校验清单；不使用 Git LFS。

在 `07_新框架_v0` 目录执行：

```powershell
python tools/materials_baseline.py verify
python tools/materials_baseline.py restore --workspace workspace
```

恢复不会覆盖已有不同内容的文件。输入原件仍使用仓库根目录 `02_原版资料/` 的当前六文件完整版本；不会启用其他旧资料版本。

文件清单、恢复核验和完整使用说明见 `../../docs/客户端v3交付包/README.md`。
