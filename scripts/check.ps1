[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repositoryRoot
try {
    & corepack pnpm run check
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $exitCode

