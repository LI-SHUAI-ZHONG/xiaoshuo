param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$ReferenceRoot = ''
)

$ErrorActionPreference = 'Stop'
$errors = @()
$warnings = @()

function Add-Error([string]$Message) { $script:errors += $Message }
function Require-Path([string]$RelativePath) {
    $path = Join-Path ([System.IO.Path]::GetFullPath($Root)) $RelativePath
    if (-not (Test-Path -LiteralPath $path)) {
        Add-Error "Missing path: $RelativePath"
    }
}

function Require-File([string]$Path, [string]$Message) {
    if (-not [System.IO.File]::Exists([System.IO.Path]::GetFullPath($Path))) {
        Add-Error $Message
    }
}

Require-Path '.clinerules'
Require-Path 'README.md'
Require-Path 'docs'
Require-Path '00_资料索引/索引调用映射契约.json'
Require-Path '工具/运行资料闭环.py'

$contentBaseline = Join-Path $Root '阶段状态\资料内容审计基线.json'
$contentEvidence = Join-Path $Root '阶段状态\规范化资料证据包.json'
$normalizedLayerPath = Join-Path $Root '阶段状态\规范化资料层.json'
$normalizedSchemaPath = Join-Path $Root '阶段状态\规范化资料层.schema.json'
Write-Output ('CHECK_NORMALIZED_LAYER=' + [System.IO.Path]::GetFullPath($normalizedLayerPath) + '; EXISTS=' + [System.IO.File]::Exists([System.IO.Path]::GetFullPath($normalizedLayerPath)))
Write-Output ('CHECK_NORMALIZED_SCHEMA=' + [System.IO.Path]::GetFullPath($normalizedSchemaPath) + '; EXISTS=' + [System.IO.File]::Exists([System.IO.Path]::GetFullPath($normalizedSchemaPath)))
Require-File $normalizedLayerPath 'Normalized content layer is missing'
Require-File $normalizedSchemaPath 'Normalized content layer schema is missing'
if ([System.IO.File]::Exists($normalizedLayerPath) -and [System.IO.File]::Exists($normalizedSchemaPath)) {
    try {
        $layer = Get-Content -LiteralPath $normalizedLayerPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $schema = Get-Content -LiteralPath $normalizedSchemaPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($layer.schema_version -ne 'normalized-content-layer-1.0') { Add-Error 'Normalized content layer schema_version is invalid' }
        if ($layer.status -eq 'partial_blocked') { $warnings += 'Normalized content layer is partial_blocked; formal generation remains blocked.' }
        if ($null -eq $layer.records -or $null -eq $layer.indexes -or $null -eq $layer.gates) { Add-Error 'Normalized content layer missing records, indexes or gates' }
        foreach ($record in @($layer.records)) {
            if ($record.source_refs.Count -eq 0) { Add-Error ('Normalized record has no source_refs: ' + $record.id) }
            if ($record.runtime_usable -eq $true -and $record.evidence_level -notin @('confirmed_raw','cross_confirmed')) { Add-Error ('Unverified record marked runtime_usable: ' + $record.id) }
        }
    } catch { Add-Error ('Invalid normalized content layer: ' + $_.Exception.Message) }
}
if (-not [System.IO.File]::Exists($contentBaseline)) {
    Add-Error 'Content audit baseline is missing'
} else {
    try {
        $baseline = Get-Content -LiteralPath $contentBaseline -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($baseline.missing_workspace_sources.Count -gt 0) {
            Add-Error ('Content audit reports missing raw sources: ' + ($baseline.missing_workspace_sources -join ', '))
        }
        $unreadable = @($baseline.source_files | Where-Object { -not $_.readable })
        if ($unreadable.Count -gt 0) { Add-Error 'Content audit reports unreadable raw sources' }
    } catch {
        Add-Error ('Invalid content audit baseline: ' + $_.Exception.Message)
    }
}
Write-Output ('CHECK_CONTENT_BASELINE=' + [System.IO.Path]::GetFullPath($contentBaseline) + '; EXISTS=' + [System.IO.File]::Exists([System.IO.Path]::GetFullPath($contentBaseline)))
Write-Output ('CHECK_CONTENT_EVIDENCE=' + [System.IO.Path]::GetFullPath($contentEvidence) + '; EXISTS=' + [System.IO.File]::Exists([System.IO.Path]::GetFullPath($contentEvidence)))
if (-not [System.IO.File]::Exists($contentEvidence)) {
    Add-Error 'Normalized content evidence package is missing'
} else {
    try {
        $evidence = Get-Content -LiteralPath $contentEvidence -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($evidence.status -eq 'partial_blocked') {
            $warnings += 'Content evidence package is partial_blocked; formal generation must remain blocked.'
        }
        if ($null -eq $evidence.evidence_policy -or $null -eq $evidence.records) {
            Add-Error 'Normalized content evidence package missing policy or records'
        }
        $blockers = @($evidence.records | Where-Object { $_.use -eq 'blocker' -or $_.runtime_usable -eq $false })
        if ($blockers.Count -gt 0) { $warnings += ('Content evidence contains blocked records: ' + $blockers.Count) }
    } catch {
        Add-Error ('Invalid normalized content evidence package: ' + $_.Exception.Message)
    }
}
$closureTool = Get-ChildItem -LiteralPath $Root -Recurse -Filter '*.ps1' -File | Where-Object { (Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8).Contains('influence_contract') } | Select-Object -First 1
if ($null -eq $closureTool) { Add-Error 'Closure runner is missing' }

$rootDirs = @(Get-ChildItem -LiteralPath $Root -Directory)
$indexDir = $rootDirs | Where-Object { $_.Name.StartsWith('00_') } | Select-Object -First 1
$templateDir = $rootDirs | Where-Object { $_.Name.StartsWith('07_') } | Select-Object -First 1
$rawDir = $rootDirs | Where-Object { $_.Name.StartsWith('08_') } | Select-Object -First 1
$paths = @()

if ($null -eq $indexDir) {
    Add-Error 'Missing directory prefix: 00_'
} else {
    $indexFiles = @(Get-ChildItem -LiteralPath $indexDir.FullName -Filter '*.yaml' -File)
    if ($indexFiles.Count -eq 0) {
        Add-Error 'No YAML index found'
    } else {
        $indexText = [System.IO.File]::ReadAllText($indexFiles[0].FullName, [System.Text.Encoding]::UTF8)
        $pathValues = @()
        foreach ($indexLine in ($indexText -split "`r?`n")) {
            if ($indexLine -match '^\s+path:\s*"([^"]+)"\s*$') {
                $pathValues += $Matches[1]
            }
        }
        $paths = $pathValues
        if ($pathValues.Count -lt 9) { Add-Error ('Index records unexpectedly low: ' + $pathValues.Count) }
        foreach ($indexedPath in $pathValues) {
            $workspacePath = Join-Path $Root ($indexedPath -replace '/', '\')
            if (-not (Test-Path -LiteralPath $workspacePath -PathType Leaf)) {
                Add-Error "Indexed path is missing: $indexedPath"
            }
        }
    }
}

if ($null -eq $rawDir) { Add-Error 'Workspace raw directory is missing' }

$closurePath = if ($null -ne $closureTool) { $closureTool.FullName } else { $null }
if ($closurePath -and (Test-Path -LiteralPath $closurePath -PathType Leaf)) {
    $closureText = [System.IO.File]::ReadAllText($closurePath, [System.Text.Encoding]::UTF8)
    foreach ($term in @('selected_modules', 'dependency_edges', 'synthesis_contract', 'influence_contract', 'Verify')) {
        if (-not $closureText.Contains($term)) { Add-Error "Closure tool missing contract term: $term" }
    }
}

$ruleDir = Join-Path $Root '.clinerules'
$ruleFiles = @(Get-ChildItem -LiteralPath $ruleDir -Filter '*.md' -File -ErrorAction SilentlyContinue)
if ($ruleFiles.Count -eq 0) {
    Add-Error 'No rule file found'
} else {
    $ruleText = [System.IO.File]::ReadAllText($ruleFiles[0].FullName, [System.Text.Encoding]::UTF8)
    foreach ($term in @('read_mode', 'source_trace', 'unknown_source', 'WAIT_USER', 'BLOCKED')) {
        if (-not $ruleText.Contains($term)) { Add-Error "Missing rule term: $term" }
    }
}

if ($null -eq $templateDir) {
    Add-Error 'Missing directory prefix: 07_'
} else {
    $formalDirs = @(Get-ChildItem -LiteralPath $templateDir.FullName -Directory)
    if ($formalDirs.Count -eq 0) {
        Add-Error 'Formal project template directory is missing'
    } else {
        $jsonFiles = @(Get-ChildItem -LiteralPath $formalDirs[0].FullName -Filter '*.json' -File)
        $contractFile = $null
        $snapshotFile = $null
        foreach ($jsonFile in $jsonFiles) {
            $jsonText = [System.IO.File]::ReadAllText($jsonFile.FullName, [System.Text.Encoding]::UTF8)
            if ($null -eq $contractFile -and $jsonText.Contains('save_gate')) { $contractFile = $jsonFile }
            if ($null -eq $snapshotFile -and $jsonText.Contains('character_states')) { $snapshotFile = $jsonFile }
        }
        if ($null -eq $contractFile) { Add-Error 'State contract JSON is missing' }
        if ($null -eq $snapshotFile) { Add-Error 'Project snapshot JSON is missing' }
        if ($null -ne $contractFile -and $null -ne $snapshotFile) {
            try {
                $contract = Get-Content -LiteralPath $contractFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
                $snapshot = Get-Content -LiteralPath $snapshotFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
                foreach ($field in @('character_states', 'world_state', 'plot_state', 'change_log')) {
                    if ($null -eq $snapshot.continuity.$field) { Add-Error "Snapshot missing continuity field: $field" }
                }
                foreach ($section in @('plot_turn', 'character_current_state', 'world_current_state', 'change_record', 'save_gate')) {
                    if ($null -eq $contract.$section) { Add-Error "Contract missing section: $section" }
                }
                if ([string]::IsNullOrWhiteSpace([string]$snapshot.state_contract)) { Add-Error 'Snapshot state_contract is missing' }
                if (-not [string]::IsNullOrWhiteSpace([string]$snapshot.state_contract)) {
                    $snapshotContractPath = Join-Path $formalDirs[0].FullName ([string]$snapshot.state_contract)
                    if (-not (Test-Path -LiteralPath $snapshotContractPath -PathType Leaf)) {
                        Add-Error ('Snapshot state_contract target is missing: ' + $snapshot.state_contract)
                    } else {
                        try { Get-Content -LiteralPath $snapshotContractPath -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null }
                        catch { Add-Error ('Snapshot state_contract target is invalid JSON: ' + $_.Exception.Message) }
                    }
                }
            } catch {
                Add-Error ('Invalid state contract or snapshot JSON: ' + $_.Exception.Message)
            }
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($ReferenceRoot)) {
    $resolvedRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $resolvedReference = [System.IO.Path]::GetFullPath($ReferenceRoot).TrimEnd('\') + '\'
    if (-not $resolvedReference.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        Add-Error 'ReferenceRoot must remain inside the workspace root.'
    } elseif (Test-Path -LiteralPath $ReferenceRoot) {
        $referenceFiles = @(Get-ChildItem -LiteralPath $ReferenceRoot -Recurse -Force -File)
        if ($referenceFiles.Count -eq 0) { $warnings += 'Reference directory is empty' }
    } else {
        $warnings += "Reference directory unavailable: $ReferenceRoot"
    }
}

Write-Output ('ROOT=' + $Root)
Write-Output ('INDEXED_PATHS=' + $paths.Count)
Write-Output ('ERRORS=' + $errors.Count)
foreach ($errorMessage in $errors) { Write-Output ('ERROR: ' + $errorMessage) }
Write-Output ('WARNINGS=' + $warnings.Count)
foreach ($warningMessage in $warnings) { Write-Output ('WARNING: ' + $warningMessage) }
if ($errors.Count -gt 0) { exit 1 }