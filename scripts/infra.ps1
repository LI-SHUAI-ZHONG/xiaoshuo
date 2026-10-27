[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'status', 'check')]
    [string]$Command = 'status'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $repositoryRoot 'infra\compose.yaml'
$environmentFile = Join-Path $repositoryRoot '.env'

if (-not (Test-Path -LiteralPath $environmentFile -PathType Leaf)) {
    [Console]::Error.WriteLine('Missing .env. Copy .env.example to .env and replace every local credential placeholder.')
    exit 2
}

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $dockerCommand) {
    $perUserDocker = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'
    if (Test-Path -LiteralPath $perUserDocker -PathType Leaf) {
        $dockerCommand = $perUserDocker
    }
    else {
        [Console]::Error.WriteLine('Docker CLI is unavailable. Install and start Docker Desktop or Docker Engine with Compose.')
        exit 3
    }
}

$composeArguments = @('compose', '--env-file', $environmentFile, '--file', $composeFile)

function Invoke-Compose {
    param([Parameter(Mandatory)][string[]]$DockerArguments)

    & $dockerCommand @composeArguments @DockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose command failed with exit code $LASTEXITCODE."
    }
}

function Invoke-InfrastructureCheck {
    Invoke-Compose -DockerArguments @('--profile', 'tools', 'run', '--rm', '--no-deps', 'postgres-check')
    Invoke-Compose -DockerArguments @('--profile', 'tools', 'run', '--rm', '--no-deps', 'redis-check')
    Invoke-Compose -DockerArguments @('--profile', 'tools', 'run', '--rm', '--no-deps', 'minio-check')
    Write-Output 'Infrastructure self-check passed: PostgreSQL/pgvector, Redis, and S3 read/write are healthy.'
}

Push-Location $repositoryRoot
try {
    Invoke-Compose -DockerArguments @('config', '--quiet')

    switch ($Command) {
        'up' {
            Invoke-Compose -DockerArguments @('up', '--detach', '--wait', '--wait-timeout', '180', 'postgres', 'redis', 'minio')
            Invoke-Compose -DockerArguments @('--profile', 'tools', 'run', '--rm', '--no-deps', 'minio-init')
            Invoke-InfrastructureCheck
        }
        'down' {
            Invoke-Compose -DockerArguments @('down', '--remove-orphans')
            Write-Output 'Infrastructure stopped. Named volumes were preserved.'
        }
        'status' {
            Invoke-Compose -DockerArguments @('ps')
        }
        'check' {
            Invoke-InfrastructureCheck
        }
    }
}
finally {
    Pop-Location
}
