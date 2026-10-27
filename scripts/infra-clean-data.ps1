[CmdletBinding()]
param([switch]$ConfirmDataLoss)

$ErrorActionPreference = 'Stop'
if (-not $ConfirmDataLoss) {
    [Console]::Error.WriteLine('DESTRUCTIVE: this removes all ACCOS PostgreSQL, Redis, and MinIO local volumes. Re-run with -ConfirmDataLoss.')
    exit 2
}

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$environmentFile = Join-Path $repositoryRoot '.env'
$composeFile = Join-Path $repositoryRoot 'infra\compose.yaml'
if (-not (Test-Path -LiteralPath $environmentFile -PathType Leaf)) {
    [Console]::Error.WriteLine('Missing .env; refusing to guess which Compose project owns the volumes.')
    exit 2
}

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $dockerCommand) {
    $perUserDocker = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'
    if (Test-Path -LiteralPath $perUserDocker -PathType Leaf) {
        $dockerCommand = $perUserDocker
    }
    else {
        [Console]::Error.WriteLine('Docker CLI is unavailable.')
        exit 3
    }
}

Write-Warning 'Removing ACCOS local infrastructure containers and named data volumes.'
& $dockerCommand compose --env-file $environmentFile --file $composeFile down --volumes --remove-orphans
exit $LASTEXITCODE
