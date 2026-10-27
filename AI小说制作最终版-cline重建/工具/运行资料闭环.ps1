param(
    [ValidateSet('Audit','Plan','Verify')][string]$Mode = 'Audit',
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$Request = '',
    [string]$ProjectPath = '',
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
$Root = [IO.Path]::GetFullPath($Root)
$runner = @([IO.Directory]::GetFiles($PSScriptRoot, '*.py') | Where-Object {
    (Select-String -LiteralPath $_ -Pattern 'Standard-library runtime for the material routing contract' -Quiet)
}) | Select-Object -First 1
if (-not $runner) { throw 'Python runtime is missing' }

$arguments = @($runner, '--root', $Root, '--mode', $Mode)
if ($Request) { $arguments += @('--request', $Request) }
if ($ProjectPath) { $arguments += @('--project-path', $ProjectPath) }
if ($OutputPath) { $arguments += @('--output-path', $OutputPath) }

& python @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }