$evidence = 'D:\AI小说制作最终版-cline重建\新版1\文档\证据\全量资料升级运行'
$pid = 25788
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$pid" -ErrorAction SilentlyContinue
$details = Get-Process -Id $pid -ErrorAction SilentlyContinue
[pscustomobject]@{
    recorded_at = [DateTime]::UtcNow.ToString('o')
    run_id = '20260817T000000Z-strict-smoke-03'
    reason = 'no progress after baseline-lock phase; no run artifact or active Ollama model'
    process_exists = $null -ne $process
    command_line = if ($process) { $process.CommandLine } else { $null }
    cpu_seconds = if ($details) { $details.CPU } else { $null }
    action = 'Stop-Process -Force'
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $evidence '20260817T000000Z-strict-smoke-03.execution-anomaly.json')
if ($details) { Stop-Process -Id $pid -Force }