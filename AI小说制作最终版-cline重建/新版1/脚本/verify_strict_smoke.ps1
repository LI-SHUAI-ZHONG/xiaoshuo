$python = 'C:\Users\li\AppData\Local\Programs\Python\Python312\python.exe'
$wrapper = Join-Path $PSScriptRoot 'verify_strict_smoke.py'
& $python $wrapper
exit $LASTEXITCODE