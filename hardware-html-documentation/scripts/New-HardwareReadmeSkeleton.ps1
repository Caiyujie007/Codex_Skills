param(
  [string]$Output = "README.html",
  [string]$Title = "Hardware Demo README",
  [string]$Subject = "Self-contained hardware documentation skeleton.",
  [switch]$Force
)

$ErrorActionPreference = "Stop"

function HtmlEncode([string]$Text) {
  return [System.Net.WebUtility]::HtmlEncode($Text)
}

$outPath = [System.IO.Path]::GetFullPath($Output)
if ((Test-Path -LiteralPath $outPath) -and -not $Force) {
  throw "Refusing to overwrite existing file: $outPath. Use -Force."
}

$template = @'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #122033;
      --muted: #56657a;
      --line: #cfd8e3;
      --panel: #f6f9fc;
      --accent: #1f6fbf;
    }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--ink);
      background: #ffffff;
      line-height: 1.55;
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 24px 64px;
    }
    h1, h2, h3 { line-height: 1.25; }
    h1 { margin: 0 0 8px; font-size: 30px; }
    h2 { margin-top: 34px; padding-top: 16px; border-top: 1px solid var(--line); }
    .subtitle { color: var(--muted); margin: 0 0 24px; }
    .note {
      border-left: 4px solid var(--accent);
      background: var(--panel);
      padding: 12px 16px;
      margin: 16px 0;
    }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; }
    th, td { border: 1px solid var(--line); padding: 8px 10px; vertical-align: top; }
    th { background: var(--panel); text-align: left; }
    code, pre { font-family: Consolas, "Courier New", monospace; }
    pre { background: #101827; color: #eef5ff; padding: 14px; overflow: auto; }
    figure { margin: 20px 0; }
    figcaption { color: var(--muted); font-size: 14px; margin-top: 8px; }
  </style>
</head>
<body>
<main>
  <h1>__TITLE__</h1>
  <p class="subtitle">__SUBJECT__</p>

  <section id="scope">
    <h2>1. Scope And Mental Model</h2>
    <div class="note">
      State what this design teaches, what it intentionally omits, and the smallest useful mental model.
    </div>
  </section>

  <section id="principle">
    <h2>2. Principle First</h2>
    <p>Explain the mechanism before naming RTL signals. Add diagrams or animation when behavior changes over time.</p>
  </section>

  <section id="interfaces">
    <h2>3. Interfaces And Topology</h2>
    <table>
      <thead><tr><th>Block</th><th>Interface</th><th>Direction</th><th>Handshake / Flow Control</th><th>Fields</th></tr></thead>
      <tbody>
        <tr><td>TODO</td><td>TODO</td><td>TODO</td><td>TODO</td><td>TODO</td></tr>
      </tbody>
    </table>
  </section>

  <section id="rtl-mapping">
    <h2>4. Principle-To-RTL Mapping</h2>
    <table>
      <thead><tr><th>Principle</th><th>RTL realization</th><th>Signals / modules to inspect</th></tr></thead>
      <tbody>
        <tr><td>TODO</td><td>TODO</td><td>TODO</td></tr>
      </tbody>
    </table>
  </section>

  <section id="verification">
    <h2>5. Verification And Waveform Evidence</h2>
    <table>
      <thead><tr><th>Case</th><th>Stimulus</th><th>Proves</th><th>Expected waveform evidence</th><th>Artifacts</th></tr></thead>
      <tbody>
        <tr><td>TODO</td><td>TODO</td><td>TODO</td><td>TODO</td><td>TODO</td></tr>
      </tbody>
    </table>
  </section>

  <section id="notes">
    <h2>6. Tool / Synthesis Notes</h2>
    <p>Include only notes that matter for using or interpreting this demo.</p>
  </section>
</main>
</body>
</html>
'@

$html = $template.Replace("__TITLE__", (HtmlEncode $Title)).Replace("__SUBJECT__", (HtmlEncode $Subject))
$dir = Split-Path -Parent $outPath
if ($dir) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outPath, $html, $utf8NoBom)
Write-Host "Wrote $outPath"
