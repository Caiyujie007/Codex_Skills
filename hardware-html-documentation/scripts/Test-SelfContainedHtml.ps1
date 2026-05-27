param(
  [Parameter(Mandatory=$true)][string]$Html,
  [switch]$AllowLocalRefs
)

$ErrorActionPreference = "Stop"

$path = [System.IO.Path]::GetFullPath($Html)
$text = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
$errors = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

if ($text.Contains([char]0xfffd)) {
  $errors.Add("Unicode replacement character U+FFFD found")
}
if ($text -notmatch '(?is)<html\b') {
  $errors.Add("Missing <html> tag")
}
if ($text -notmatch '(?is)<meta[^>]+charset=["'']?utf-?8') {
  $warnings.Add("Missing explicit UTF-8 meta charset")
}
if ($text -notmatch '(?is)<title>\s*\S.*?</title>') {
  $warnings.Add("Missing or empty <title>")
}

$ids = @()
foreach ($m in [regex]::Matches($text, '\bid\s*=\s*["'']([^"'']+)["'']', 'IgnoreCase')) {
  $ids += $m.Groups[1].Value
}
$dups = $ids | Group-Object | Where-Object { $_.Count -gt 1 } | Select-Object -ExpandProperty Name
foreach ($id in $dups) {
  $errors.Add("Duplicate id: $id")
}

$refs = @()
foreach ($m in [regex]::Matches($text, '\b(src|href)\s*=\s*["'']([^"'']+)["'']', 'IgnoreCase')) {
  $attr = $m.Groups[1].Value
  $value = $m.Groups[2].Value.Trim()
  if (-not $value -or $value.StartsWith("#") -or $value.StartsWith("data:")) {
    continue
  }
  $isRemote = $value -match '^(https?:)?//' -or $value -match '^(file|mailto|javascript):'
  if ($AllowLocalRefs -and -not $isRemote) {
    continue
  }
  $refs += "$attr=$value"
}
foreach ($ref in $refs) {
  $errors.Add("External reference: $ref")
}

foreach ($m in [regex]::Matches($text, '(?is)<script\b([^>]*)>(.*?)</script>')) {
  $attrs = $m.Groups[1].Value
  $body = $m.Groups[2].Value
  $isJson = ($attrs -match 'type\s*=\s*["'']application/(ld\+)?json["'']') -or ($attrs -match 'id\s*=\s*["''][^"'']*map["'']')
  if ($isJson -and $body.Trim().Length -gt 0) {
    try {
      $null = $body | ConvertFrom-Json -ErrorAction Stop
    } catch {
      $errors.Add("Invalid JSON script: $($_.Exception.Message)")
    }
  }
}

Write-Host "HTML: $path"
Write-Host "ids=$($ids.Count) external_refs=$($refs.Count)"
foreach ($w in $warnings) {
  Write-Host "WARNING: $w"
}
foreach ($e in $errors) {
  Write-Host "ERROR: $e"
}
if ($errors.Count -gt 0) {
  exit 1
}
Write-Host "HTML_VALIDATION_OK"
