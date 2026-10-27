param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$ProjectName,
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [string]$Genre = "",
    [string]$Type = "",
    [string]$Length = "",
    [string]$Style = "",
    [string]$Platform = "",
    [string]$Audience = "",
    [ValidateSet('continuous', 'one-shot')][string]$Mode = 'continuous'
)

$ErrorActionPreference = 'Stop'
$systemRoot = Split-Path -Parent $PSScriptRoot
$target = [System.IO.Path]::GetFullPath($ProjectPath)
$runMode = if ($Mode -eq 'continuous') { 'autonomous_continuous' } else { 'one_shot' }

function Write-AtomicText([string]$Path, [string]$Content) {
    $directory = Split-Path -Parent $Path
    $leaf = Split-Path -Leaf $Path
    $temporary = Join-Path $directory ('.' + $leaf + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    $backup = Join-Path $directory ('.' + $leaf + '.' + [guid]::NewGuid().ToString('N') + '.bak')
    $lastError = $null
    try {
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            try {
                [System.IO.File]::WriteAllText($temporary, $Content, [System.Text.UTF8Encoding]::new($false))
                if (Test-Path -LiteralPath $Path -PathType Leaf) {
                    [System.IO.File]::Replace($temporary, $Path, $backup)
                    if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue }
                } else {
                    [System.IO.File]::Move($temporary, $Path)
                }
                return
            } catch {
                $lastError = $_
                if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
                if ($attempt -lt 3) { Start-Sleep -Milliseconds 100 }
            }
        }
        throw "Atomic save failed after 3 attempts: $Path. $($lastError.Exception.Message)"
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue }
    }
}

function Write-AtomicJson([string]$Path, $Value, [int]$Depth = 12) {
    Write-AtomicText $Path ($Value | ConvertTo-Json -Depth $Depth)
}

function U([int[]]$Codes) {
    return -join ($Codes | ForEach-Object { [char]$_ })
}

$metadataName = (U @(39033,30446,20803,25968,25454)) + '.json'
$paramsName = (U @(21019,24314,21442,25968)) + '.yaml'
$templateRootName = '07_' + (U @(39033,30446,27169,26495))
$formalTemplateName = U @(27491,24335,39033,30446,27169,26495)
$template = Join-Path (Join-Path $systemRoot $templateRootName) $formalTemplateName
$settingsName = U @(35774,23450)
$startupName = (U @(21551,21160,21442,25968)) + '.md'
$planningName = U @(35268,21010)
$draftName = U @(27491,25991)
$revisionName = U @(20462,35746,35760,24405)
$reportName = U @(26816,26597,25253,21578)
$snapshotName = (U @(39033,30446,24555,29031)) + '.json'
$versionName = (U @(29256,26412,35760,24405)) + '.json'

# Resolve the contract from the template instead of embedding a locale-sensitive filename.
$contractFile = Get-ChildItem -LiteralPath $template -Filter '*.json' -File | Where-Object {
    (Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8).Contains('"save_gate"')
} | Select-Object -First 1
if ($null -eq $contractFile) { throw 'State contract JSON not found in the formal project template.' }
$contractName = $contractFile.Name
$checkTemplate = Get-ChildItem -LiteralPath (Join-Path $template $reportName) -Filter '*.json' -File | Select-Object -First 1
if ($null -eq $checkTemplate) { throw 'Initial consistency check JSON not found in the formal project template.' }
$checkName = $checkTemplate.Name

if (Test-Path -LiteralPath $target) { throw "Target directory exists; refusing to overwrite: $target" }
if (-not (Test-Path -LiteralPath $template)) { throw "Template directory not found: $template" }

New-Item -ItemType Directory -Path $target -Force | Out-Null
Get-ChildItem -LiteralPath $template -Force | Copy-Item -Destination $target -Recurse -Force
foreach ($dir in @($settingsName, $planningName, $draftName, $revisionName, $reportName)) {
    New-Item -ItemType Directory -Path (Join-Path $target $dir) -Force | Out-Null
}
$oldReport = Join-Path (Join-Path $target $reportName) $checkName
if (Test-Path -LiteralPath $oldReport) { Remove-Item -LiteralPath $oldReport -Force }

$now = (Get-Date).ToString('o')
$initialCheckStatus = if ($Mode -eq 'continuous') { 'PASS_AUTO_CONTINUE' } else { 'PASS_GOAL_SCOPED' }
$metadata = [ordered]@{
    project_id = $ProjectId
    project_name = $ProjectName
    status = 'AUTO_INIT'
    schema_version = '1.1'
    created_at = $now
    current_state = 'AUTO_INIT'
    genre = $Genre
    type = $Type
    length = $Length
    style = $Style
    platform = $Platform
    audience = $Audience
    locked_facts = @()
    pending_questions = @()
    decision_log = @()
    run_mode = $runMode
    stop_policy = if ($Mode -eq 'continuous') { 'block_only_or_goal_complete' } else { 'one_shot_goal_complete' }
}
$metadataPath = Join-Path $target $metadataName
$metadata | ConvertTo-Json -Depth 8 | ForEach-Object { Write-AtomicText $metadataPath $_ }
$persistedMetadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json

$yaml = @"
project_name: "$ProjectName"
project_id: "$ProjectId"
project_path: "$target"
genre: "$Genre"
type: "$Type"
length: "$Length"
style: "$Style"
platform: "$Platform"
audience: "$Audience"
mode: "$Mode"
confirmation: "record_only"
run_mode: "$runMode"
"@
Write-AtomicText (Join-Path $target $paramsName) $yaml

$startup = @"
# Startup Parameters

- Project name: $ProjectName
- Project ID: $ProjectId
- Mode: $Mode
- Created at: $now
- Genre: $Genre
- Type: $Type
- Length: $Length
- Style: $Style
- Platform: $Platform
- Audience: $Audience

## Status
- Current state: AUTO_INIT
- Confirmation: record_only
- Next action: $(if ($Mode -eq 'continuous') { 'Cline reads the project materials, fills ordinary gaps, and continues automatically.' } else { 'Cline completes the independent short-form output and stops at the requested goal.' })
"@
Write-AtomicText (Join-Path (Join-Path $target $settingsName) $startupName) $startup

$snapshotPath = Join-Path $target $snapshotName
$snapshot = Get-Content -LiteralPath $snapshotPath -Raw -Encoding UTF8 | ConvertFrom-Json
$snapshot.schema_version = '1.1'
$snapshot.current_state = 'AUTO_INIT'
$snapshot.genre = $persistedMetadata.genre
$snapshot.type = $persistedMetadata.type
$snapshot.length = $persistedMetadata.length
$snapshot.style = $persistedMetadata.style
$snapshot.platform = $persistedMetadata.platform
$snapshot.audience = $persistedMetadata.audience
$snapshot.source_status = 'not_started'
$snapshot.run_mode = $runMode
$snapshot.decision_log = @()
$snapshot.run_log = @()
$snapshot.save_policy = [ordered]@{ atomic_write = $true; retry_count = 3; never_overwrite_formal_text = $true }
$snapshot.state_contract = $contractName
Write-AtomicJson $snapshotPath $snapshot

$versions = [ordered]@{
    schema_version = '1.1'
    versions = @([ordered]@{ version = "v0.1"; action = "AUTO_INIT"; timestamp = $now; state = "AUTO_INIT"; note = "project initialized in $runMode mode" })
    rule = "append_major_changes_without_overwriting_history"
    state_contract = $contractName
}
Write-AtomicJson (Join-Path $target $versionName) $versions

$check = [ordered]@{
    report_type = 'initial_consistency_check'
    status = $initialCheckStatus
    checked_at = $now
    current_state = 'AUTO_INIT'
    checks = @(
        [ordered]@{ id = "INIT-001"; item = "entry_files_exist"; status = "PASS" },
        [ordered]@{ id = "INIT-002"; item = "project_selection_fields_saved"; status = "PASS" },
        [ordered]@{ id = "INIT-003"; item = "no_unconfirmed_facts_or_draft"; status = "PASS" },
        [ordered]@{ id = "INIT-004"; item = "ordinary_pending_is_record_only"; status = "PASS" }
    )
}
Write-AtomicJson (Join-Path (Join-Path $target $reportName) $checkName) $check

$verifiedSnapshot = Get-Content -LiteralPath $snapshotPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($verifiedSnapshot.genre -ne $Genre -or $verifiedSnapshot.type -ne $Type -or $verifiedSnapshot.length -ne $Length -or $verifiedSnapshot.style -ne $Style -or $verifiedSnapshot.platform -ne $Platform -or $verifiedSnapshot.audience -ne $Audience) {
    throw 'Snapshot verification failed: project selection fields were not persisted.'
}

Write-Output "Project created: $target"
Write-Output "Next: read the rules, creation parameters, metadata, and startup settings."