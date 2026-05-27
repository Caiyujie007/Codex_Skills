param(
  [Parameter(Mandatory=$true)][string[]]$Files,
  [double]$MaxMarker = 14.0,
  [double]$MinFont = 9.0
)

$ErrorActionPreference = "Stop"

function Get-Attrs([string]$Fragment) {
  $map = @{}
  foreach ($m in [regex]::Matches($Fragment, '([\w:-]+)\s*=\s*["'']([^"'']*)["'']')) {
    $map[$m.Groups[1].Value] = $m.Groups[2].Value
  }
  return $map
}

function Get-Number([string]$Value) {
  if ($Value -match '-?\d+(\.\d+)?') {
    return [double]$matches[0]
  }
  return 0.0
}

$warnings = @()

foreach ($file in $Files) {
  $path = [System.IO.Path]::GetFullPath($file)
  $text = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
  if ([System.IO.Path]::GetExtension($path).ToLowerInvariant() -eq ".svg") {
    $svgs = @($text)
  } else {
    $svgs = @([regex]::Matches($text, '(?is)<svg\b.*?</svg>') | ForEach-Object { $_.Value })
  }

  if ($svgs.Count -eq 0) {
    $warnings += "${path}: no SVG found"
    continue
  }

  for ($i = 0; $i -lt $svgs.Count; $i++) {
    $svg = $svgs[$i]
    $openTag = ([regex]::Match($svg, '(?is)<svg\b[^>]*>')).Value
    $attrs = Get-Attrs $openTag
    if (-not $attrs.ContainsKey("viewBox")) {
      $warnings += "${path}: svg[$i] missing viewBox"
    }
    if (-not $attrs.ContainsKey("viewBox") -and -not $attrs.ContainsKey("width")) {
      $warnings += "${path}: svg[$i] has neither viewBox nor width"
    }
    if ($svg -notmatch '(?is)<title\b' -and $openTag -notmatch 'aria-label\s*=') {
      $warnings += "${path}: svg[$i] has no title or aria-label"
    }

    $markerIndex = 0
    foreach ($m in [regex]::Matches($svg, '(?is)<marker\b([^>]*)>')) {
      $ma = Get-Attrs $m.Groups[1].Value
      $mw = Get-Number $ma["markerWidth"]
      $mh = Get-Number $ma["markerHeight"]
      if ($mw -gt $MaxMarker -or $mh -gt $MaxMarker) {
        $warnings += "${path}: svg[$i] marker[$markerIndex] large markerWidth/Height=$mw/$mh"
      }
      $markerIndex++
    }

    $textIndex = 0
    foreach ($m in [regex]::Matches($svg, '(?is)<text\b([^>]*)>')) {
      $ta = Get-Attrs $m.Groups[1].Value
      $fs = Get-Number $ta["font-size"]
      if ($fs -gt 0 -and $fs -lt $MinFont) {
        $warnings += "${path}: svg[$i] text[$textIndex] small font-size=$fs"
      }
      $textIndex++
    }

    if ($svg -match '(?is)<path\b[^>]*\bd\s*=\s*["'']\s*["'']') {
      $warnings += "${path}: svg[$i] contains empty path"
    }
  }
}

foreach ($warning in $warnings) {
  Write-Host "WARNING: $warning"
}
Write-Host "SVG_CHECK warnings=$($warnings.Count)"
if ($warnings.Count -gt 0) {
  exit 1
}
