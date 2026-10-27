$python = 'C:\Users\li\AppData\Local\Programs\Python\Python312\python.exe'
$wrapper = Join-Path $PSScriptRoot 'run_strict_smoke.py'
$process = Start-Process -FilePath $python -ArgumentList $wrapper -PassThru -WindowStyle Hidden
$process.Id | Set-Content -Encoding ascii (Join-Path $PSScriptRoot 'strict-smoke.pid')
Write-Output $process.Id