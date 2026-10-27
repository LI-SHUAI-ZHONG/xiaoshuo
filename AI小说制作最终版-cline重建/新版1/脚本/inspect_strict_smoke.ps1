$process = Get-CimInstance Win32_Process -Filter 'ProcessId=25788' -ErrorAction SilentlyContinue
$details = Get-Process -Id 25788 -ErrorAction SilentlyContinue
[pscustomobject]@{
    checked_at = [DateTime]::UtcNow.ToString('o')
    exists = $null -ne $process
    command_line = if ($process) { $process.CommandLine } else { $null }
    cpu_seconds = if ($details) { $details.CPU } else { $null }
    start_time = if ($details) { $details.StartTime.ToUniversalTime().ToString('o') } else { $null }
} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot 'strict-smoke-process.json')