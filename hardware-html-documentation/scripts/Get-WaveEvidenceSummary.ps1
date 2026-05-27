param(
  [Parameter(Mandatory=$true)][string]$CasesDir,
  [string]$LogName = "check_trace.log",
  [string[]]$RequirePositive = @(),
  [switch]$Csv
)

$ErrorActionPreference = "Stop"

$root = [System.IO.Path]::GetFullPath($CasesDir)
$rows = @()

foreach ($dir in Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name) {
  $log = Join-Path $dir.FullName $LogName
  if (-not (Test-Path -LiteralPath $log)) {
    continue
  }
  $summary = Select-String -Path $log -Pattern 'TRACE_SUMMARY' | Select-Object -Last 1
  if (-not $summary) {
    continue
  }
  $obj = [ordered]@{ case_dir = $dir.Name }
  foreach ($m in [regex]::Matches($summary.Line, '(\w+)=([0-9]+)')) {
    $obj[$m.Groups[1].Value] = [int]$m.Groups[2].Value
  }
  $rows += [pscustomobject]$obj
}

if ($Csv) {
  $rows | ConvertTo-Csv -NoTypeInformation
} else {
  $rows | Format-Table -AutoSize
}

$failures = @()
foreach ($row in $rows) {
  foreach ($metric in $RequirePositive) {
    if (-not ($row.PSObject.Properties.Name -contains $metric) -or [int]$row.$metric -le 0) {
      $failures += "$($row.case_dir):$metric=0"
    }
  }
}

if ($failures.Count -gt 0) {
  Write-Host "MISSING_EXPECTED_EVIDENCE $($failures -join ', ')"
  exit 1
}
Write-Host "WAVE_EVIDENCE_SUMMARY cases=$($rows.Count)"
