@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=src
echo ========================================================
echo   叙事 · 小说生产客户端 v3
echo   首页 / 制作台 / 成品仓库 / 类型图鉴 / 知识库 / 预存库
echo   写作和自动拆解需要配置可用模型；书库与人工审核可离线使用。
echo ========================================================
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8767/' -TimeoutSec 2; if ($r.Headers['Server'] -like 'NovelWorkflowStudio/3.0*') { Start-Process 'http://127.0.0.1:8767/'; exit 0 }; exit 1 } catch { exit 1 }"
if not errorlevel 1 exit /b 0
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m nw --config "%~dp0studio.config.toml" studio --host 127.0.0.1 --port 8767 --open-browser
) else (
    python -m nw --config "%~dp0studio.config.toml" studio --host 127.0.0.1 --port 8767 --open-browser
)
pause
