$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$indexPath = Join-Path $root 'docs\library_index.jsonl'
$evidenceDir = Join-Path $root 'docs\evidence'
$logPath = Join-Path $evidenceDir 'library_module_assignment_log.jsonl'
$summaryPath = Join-Path $evidenceDir 'library_module_assignment_summary.json'

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
$records = @(Get-Content -LiteralPath $indexPath -Encoding UTF8 | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })

function Get-ModuleAssignment([string]$entryId) {
    $prefixText = ($entryId -split '[._]')[0]
    [int]$prefix = 0
    if (-not [int]::TryParse($prefixText, [ref]$prefix)) { return @{ Module = '00'; Reason = 'unparseable_entry_id' } }

    if ($prefix -ge 1 -and $prefix -le 19) { return @{ Module = '06'; Reason = 'character_core_01_19' } }
    if ($prefix -ge 20 -and $prefix -le 40) { return @{ Module = '04'; Reason = 'world_setting_20_40' } }
    if ($prefix -ge 41 -and $prefix -le 45) { return @{ Module = '06'; Reason = 'plot_core_41_45' } }
    if ($prefix -ge 46 -and $prefix -le 48) { return @{ Module = '07'; Reason = 'execution_46_48' } }
    if ($prefix -ge 49 -and $prefix -le 60) { return @{ Module = '09'; Reason = 'writer_49_60' } }
    if ($prefix -ge 61 -and $prefix -le 62) { return @{ Module = '07'; Reason = 'execution_61_62' } }
    if ($prefix -eq 63) { return @{ Module = '00'; Reason = 'unassigned_theme_63' } }
    if ($prefix -ge 64 -and $prefix -le 66) { return @{ Module = '10'; Reason = 'editor_reader_64_66' } }
    if ($prefix -ge 67 -and $prefix -le 76) { return @{ Module = '06'; Reason = 'character_core_67_76' } }
    if ($prefix -ge 77 -and $prefix -le 79) { return @{ Module = '07'; Reason = 'execution_77_79' } }
    if ($prefix -ge 80 -and $prefix -le 82) { return @{ Module = '06'; Reason = 'character_core_80_82' } }
    if ($prefix -ge 83 -and $prefix -le 86) { return @{ Module = '07'; Reason = 'execution_83_86' } }
    if ($prefix -eq 87) { return @{ Module = '08'; Reason = 'planner_87' } }
    if ($prefix -eq 88) { return @{ Module = '09'; Reason = 'writer_88' } }
    if ($prefix -eq 89) { return @{ Module = '10'; Reason = 'editor_89' } }
    if ($prefix -eq 90) { return @{ Module = '11'; Reason = 'transfer_90' } }
    if ($prefix -ge 91 -and $prefix -le 108) { return @{ Module = '10'; Reason = 'editor_checks_91_108' } }
    if ($prefix -ge 109 -and $prefix -le 111) { return @{ Module = '00'; Reason = 'unassigned_narrator_atmosphere_symbol_109_111' } }
    if ($prefix -ge 112 -and $prefix -le 113) { return @{ Module = '05'; Reason = 'opening_112_113' } }
    if ($prefix -eq 114) { return @{ Module = '02'; Reason = 'decision_type_114' } }
    if ($prefix -eq 115) { return @{ Module = '07'; Reason = 'execution_space_115' } }
    if ($prefix -eq 116 -or $prefix -eq 117) { return @{ Module = '10'; Reason = 'editor_information_116_117' } }
    if ($prefix -eq 118) { return @{ Module = '06'; Reason = 'character_core_cost_118' } }
    if ($prefix -eq 119) { return @{ Module = '05'; Reason = 'opening_identity_119' } }
    if ($prefix -eq 120) { return @{ Module = '07'; Reason = 'execution_pov_120' } }
    if ($prefix -eq 121) { return @{ Module = '06'; Reason = 'character_core_supporting_121' } }
    if ($prefix -eq 122) { return @{ Module = '07'; Reason = 'execution_progress_122' } }
    if ($prefix -eq 123 -or $prefix -eq 124) { return @{ Module = '02'; Reason = 'decision_market_and_kind_123_124' } }
    if ($prefix -eq 125) { return @{ Module = '07'; Reason = 'execution_resource_library_125' } }
    if ($prefix -ge 126 -and $prefix -le 128) { return @{ Module = '11'; Reason = 'transfer_126_128' } }
    if ($prefix -eq 129 -or $prefix -eq 130) { return @{ Module = '02'; Reason = 'decision_terms_and_mystery_129_130' } }
    if ($prefix -eq 131 -or $prefix -eq 132 -or $prefix -eq 133) { return @{ Module = '01'; Reason = 'startup_131_133' } }
    if ($prefix -eq 134) { return @{ Module = '10'; Reason = 'editor_version_134' } }
    if ($prefix -eq 135 -or $prefix -eq 136) { return @{ Module = '10'; Reason = 'editor_feedback_and_block_135_136' } }
    if ($prefix -eq 137 -or $prefix -eq 138) { return @{ Module = '00'; Reason = 'unassigned_schedule_and_naming_137_138' } }
    if ($prefix -eq 139) { return @{ Module = '11'; Reason = 'transfer_adaptation_139' } }
    if ($prefix -ge 140 -and $prefix -le 154) { return @{ Module = '06'; Reason = 'character_core_unknown_and_supporting_140_154' } }
    if ($prefix -eq 155) { if ($entryId -match '^155\.2_') { return @{ Module = '05'; Reason = 'opening_empathy_155_2' } } return @{ Module = '07'; Reason = 'execution_emotion_155' } }
    if ($prefix -eq 156) { return @{ Module = '09'; Reason = 'writer_aesthetics_156' } }
    if ($prefix -eq 157) { return @{ Module = '07'; Reason = 'execution_density_157' } }
    if ($prefix -eq 158) { if ($entryId -match '^158\.1_') { return @{ Module = '05'; Reason = 'opening_cognition_158_1' } } return @{ Module = '09'; Reason = 'writer_cognition_158' } }
    if ($prefix -eq 159) { if ($entryId -match '^159\.1_') { return @{ Module = '08'; Reason = 'planner_action_plan_159_1' } } return @{ Module = '09'; Reason = 'writer_action_review_159' } }
    if ($prefix -ge 160 -and $prefix -le 162) { if ($entryId -match '^162\.2_') { return @{ Module = '10'; Reason = 'editor_aesthetic_check_162_2' } } return @{ Module = '09'; Reason = 'writer_aesthetics_160_162' } }
    return @{ Module = '00'; Reason = 'unassigned_uncovered' }
}

$moduleCounters = @{}
$updatedLines = [System.Collections.Generic.List[string]]::new()
$logs = [System.Collections.Generic.List[object]]::new()
foreach ($record in $records) {
    $assignment = Get-ModuleAssignment $record.entry_id
    if (-not $moduleCounters.ContainsKey($assignment.Module)) { $moduleCounters[$assignment.Module] = 0 }
    $moduleCounters[$assignment.Module]++
    $record | Add-Member -NotePropertyName assigned_to_module -NotePropertyValue $assignment.Module -Force
    $record | Add-Member -NotePropertyName load_order -NotePropertyValue $moduleCounters[$assignment.Module] -Force
    $updatedLines.Add(($record | ConvertTo-Json -Compress -Depth 20))
    $logs.Add([PSCustomObject]@{ entry_id = $record.entry_id; assigned_to_module = $assignment.Module; load_order = $moduleCounters[$assignment.Module]; basis = $assignment.Reason })
}

$updatedLines | Set-Content -LiteralPath $indexPath -Encoding UTF8
$logs | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 10 } | Set-Content -LiteralPath $logPath -Encoding UTF8
$summary = [ordered]@{ total_entries = $records.Count; module_counts = [ordered]@{}; unassigned_count = 0 }
foreach ($module in 1..11) { $key = '{0:D2}' -f $module; $summary.module_counts[$key] = if ($moduleCounters.ContainsKey($key)) { $moduleCounters[$key] } else { 0 } }
$summary.unassigned_count = if ($moduleCounters.ContainsKey('00')) { $moduleCounters['00'] } else { 0 }
$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryPath -Encoding UTF8