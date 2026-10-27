[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'infra.ps1') check
exit $LASTEXITCODE
