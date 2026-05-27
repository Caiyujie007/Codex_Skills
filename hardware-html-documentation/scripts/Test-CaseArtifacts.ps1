[CmdletBinding(PositionalBinding=$false)]
param(
  [Parameter(Mandatory=$true, Position=0)][string]$CasesDir,
  [string[]]$Required = @("sim.log", "waves.wdb", "waves.wcfg"),
  [string]$CaseGlob = "*",
  [switch]$Json,
  [Parameter(ValueFromRemainingArguments=$true)]
  [string[]]$RemainingRequired = @()
)

$ErrorActionPreference = "Stop"

$root = [System.IO.Path]::GetFullPath($CasesDir)
$requiredItems = @($Required) + @($RemainingRequired)
$requiredList = @()
foreach ($item in $requiredItems) {
  foreach ($part in ($item -split ",")) {
    $trimmed = $part.Trim()
    if ($trimmed.Length -gt 0) {
      $requiredList += $trimmed
    }
  }
}
$rows = @()

foreach ($dir in Get-ChildItem -LiteralPath $root -Directory -Filter $CaseGlob | Sort-Object Name) {
  $missing = @()
  $empty = @()
  foreach ($name in $requiredList) {
    $p = Join-Path $dir.FullName $name
    if (-not (Test-Path -LiteralPath $p)) {
      $missing += $name
    } elseif ((Get-Item -LiteralPath $p).Length -eq 0) {
      $empty += $name
    }
  }

  $simPath = Join-Path $dir.FullName "sim.log"
  $sim = if (Test-Path -LiteralPath $simPath) { [System.IO.File]::ReadAllText($simPath) } else { "" }
  $checkLogs = @(Get-ChildItem -LiteralPath $dir.FullName -Filter "check*.log" -File -ErrorAction SilentlyContinue)
  $checkText = ""
  foreach ($check in $checkLogs) {
    $checkText += [System.IO.File]::ReadAllText($check.FullName) + "`n"
  }

  $passSeen = $sim -match '\*\*\* CASE C\d+ PASSED \*\*\*'
  $holdSeen = $checkText -match 'TRACE INVARIANTS HOLD|WAVEFORM INVARIANTS HOLD'
  $failSeen = ($sim -match '\[FAIL\]|WATCHDOG|\*\*\* CASE C\d+ FAILED \*\*\*') -or
              ($checkText -match '\[FAIL\]|WATCHDOG|\*\*\* CASE C\d+ FAILED \*\*\*')

  $rows += [pscustomobject]@{
    Case = $dir.Name
    Pass = [bool]$passSeen
    Hold = [bool]$holdSeen
    Fail = [bool]$failSeen
    Missing = ($missing -join ",")
    Empty = ($empty -join ",")
    Ok = ($missing.Count -eq 0 -and $empty.Count -eq 0 -and $passSeen -and
          (($checkLogs.Count -eq 0) -or $holdSeen) -and -not $failSeen)
  }
}

if ($Json) {
  $rows | ConvertTo-Json -Depth 4
} else {
  $rows | Format-Table -AutoSize
}

$failed = @($rows | Where-Object { -not $_.Ok })
Write-Host "CASE_ARTIFACTS cases=$($rows.Count) failed=$($failed.Count)"
if ($failed.Count -gt 0) {
  exit 1
}
