@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=src
echo ========================================================
echo   小说细粒度创作工作流客户端 (Novel Workflow Studio v0)
echo   当前默认：离线沙盘与全流程工作台（无需外部 API 即可运行）
echo ========================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m nw studio --host 127.0.0.1 --port 8765 --open-browser
) else (
    python -m nw studio --host 127.0.0.1 --port 8765 --open-browser
)
pause
