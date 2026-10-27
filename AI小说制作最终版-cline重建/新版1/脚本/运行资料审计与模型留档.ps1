param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$LogDirectory = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ([string]::IsNullOrWhiteSpace($LogDirectory)) {
    $LogDirectory = Join-Path $root "文档\证据\执行日志\资料审计"
}
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

function Invoke-AndRecord {
    param(
        [string]$Name,
        [string]$Slug,
        [string]$FilePath,
        [string[]]$ArgumentList
    )
    $started = [DateTime]::UtcNow
    $stdoutFile = Join-Path $LogDirectory "$Slug.stdout.txt"
    $stderrFile = Join-Path $LogDirectory "$Slug.stderr.txt"
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $FilePath
    $info.WorkingDirectory = $root
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.Arguments = (($ArgumentList | ForEach-Object {
        '"' + ($_.Replace('"', '\"')) + '"'
    }) -join ' ')
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        $exitCode = $process.ExitCode
    } catch {
        $stdout = ""
        $stderr = $_.Exception.ToString()
        $exitCode = 127
    } finally {
        $process.Dispose()
    }
    Set-Content -LiteralPath $stdoutFile -Value $stdout -Encoding UTF8
    Set-Content -LiteralPath $stderrFile -Value $stderr -Encoding UTF8
    $finished = [DateTime]::UtcNow
    $record = [ordered]@{
        schema_version = "command-execution-record-1.0"
        name = $Name
        command = (@($FilePath) + $ArgumentList) -join " "
        started_at = $started.ToString("o")
        finished_at = $finished.ToString("o")
        exit_code = $exitCode
        stdout_file = (Resolve-Path -LiteralPath $stdoutFile).Path
        stderr_file = (Resolve-Path -LiteralPath $stderrFile).Path
        stdout = $stdout
        stderr = $stderr
    }
    $record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $LogDirectory "$Slug.json") -Encoding UTF8
    return $record
}

$python = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python -ErrorAction Stop).Source }
$scriptDir = $PSScriptRoot
$strictTest = (Get-ChildItem -LiteralPath $scriptDir -Filter "test_*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "StrictSourceUpgradeTests" -Quiet }).FullName
$batchTest = (Get-ChildItem -LiteralPath $scriptDir -Filter "test_*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "FullSourceBatchUpgradeAuthorizationTests" -Quiet }).FullName
$continuousTest = (Get-ChildItem -LiteralPath $scriptDir -Filter "test_*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "ContinuousSourceUpgradeLedgerTests" -Quiet }).FullName
$records = @()
$policyScript = Join-Path $scriptDir "项目创作生产政策.py"
$records += Invoke-AndRecord "project_creative_production_policy" "project_creative_production_policy" $python @($policyScript, "--project-root", $root)
$records += Invoke-AndRecord "test_strict_source_upgrade" "test_strict_source_upgrade" $python @($strictTest)
$records += Invoke-AndRecord "test_full_source_batch_upgrade" "test_full_source_batch_upgrade" $python @($batchTest)
$records += Invoke-AndRecord "test_continuous_source_upgrade" "test_continuous_source_upgrade" $python @($continuousTest)

$modelScript = (Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "def generate_json" -Quiet }).FullName
$probe = @'
import json
import importlib.util
import sys
from pathlib import Path
root = Path(sys.argv[1])
model_path = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("project_text_generation_model", model_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    response, metadata = module.generate_json(
        root,
        "Return only a JSON object.",
        "Return a JSON object with status set to ok. Do not generate prose.",
    )
    print(json.dumps({"status": "passed", "response": response, "metadata": metadata}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False))
    raise
'@
$probeFile = Join-Path $LogDirectory "model_minimal_json_probe.py"
Set-Content -LiteralPath $probeFile -Value $probe -Encoding UTF8
$records += Invoke-AndRecord "model_minimal_json_probe" "model_minimal_json_probe" $python @($probeFile, $root, $modelScript)

$authorizationAudit = (Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "per_binding_explicit_use_authorization_audit" -Quiet }).FullName
$bindingSync = (Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "Translate every registered source item into an explicit creation contract" -Quiet }).FullName
$records += Invoke-AndRecord "full_source_use_authorization_audit" "full_source_use_authorization_audit" $python @($authorizationAudit, "--project-root", $root, "--audit")
# Rebuild the material binding projection after its authority ledger is audited.
$records += Invoke-AndRecord "binding_authorization_projection_sync" "binding_authorization_projection_sync" $python @($bindingSync, "--project-root", $root)

$consumptionGate = (Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "full-source-prose-consumption-validation-1.0" -Quiet }).FullName
$isolationGate = (Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "full-source-strict-isolation-audit-1.0" -Quiet }).FullName
$capabilityGate = (Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "source-production-capability-1.0" -Quiet }).FullName
$releaseGate = (Get-ChildItem -LiteralPath $scriptDir -Filter "*.py" | Where-Object { Select-String -LiteralPath $_.FullName -Pattern "full-source-formal-release-gate-1.0" -Quiet }).FullName
$records += Invoke-AndRecord "prose_consumption_validation" "prose_consumption_validation" $python @($consumptionGate, "--project-root", $root)
$records += Invoke-AndRecord "strict_isolation_audit" "strict_isolation_audit" $python @($isolationGate, "--project-root", $root)
$records += Invoke-AndRecord "production_capability_gate" "production_capability_gate" $python @($capabilityGate, "--project-root", $root)
$records += Invoke-AndRecord "formal_release_gate" "formal_release_gate" $python @($releaseGate, "--project-root", $root)

$summary = [ordered]@{
    schema_version = "source-audit-run-summary-1.0"
    project_root = $root
    generated_at = [DateTime]::UtcNow.ToString("o")
    log_directory = (Resolve-Path -LiteralPath $LogDirectory).Path
    commands = @($records | ForEach-Object {
        [ordered]@{ name = $_.name; exit_code = $_.exit_code; started_at = $_.started_at; finished_at = $_.finished_at }
    })
    all_commands_passed = (@($records | Where-Object { $_.exit_code -ne 0 }).Count -eq 0)
}
$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $LogDirectory "执行摘要.json") -Encoding UTF8
$summary | ConvertTo-Json -Depth 10
if (-not $summary.all_commands_passed) { exit 2 }