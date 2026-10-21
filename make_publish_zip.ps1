# Meclis Sanal Asistanı — cPanel publish zip
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$zipName = "MeclisSanalAsistani-publish.zip"
$outPath = Join-Path $root $zipName

if (Test-Path $outPath) { Remove-Item $outPath -Force }

$include = @(
  "app.py",
  "webapp.py",
  "passenger_wsgi.py",
  "config.py",
  "rag.py",
  "document_loader.py",
  "chat_store.py",
  "web_search.py",
  "requirements.txt",
  "YAYIN_CPANEL.md",
  "templates",
  "static",
  "kaynak"
)

$stage = Join-Path $env:TEMP ("msa-publish-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $stage | Out-Null

try {
  foreach ($item in $include) {
    $src = Join-Path $root $item
    if (-not (Test-Path $src)) { continue }
    $dest = Join-Path $stage $item
    if (Test-Path $src -PathType Container) {
      Copy-Item $src $dest -Recurse -Force
    } else {
      Copy-Item $src $dest -Force
    }
  }

  # sohbetler boş kalsın (sunucuda oluşur)
  New-Item -ItemType Directory -Path (Join-Path $stage "sohbetler") -Force | Out-Null
  Set-Content -Path (Join-Path $stage "sohbetler\.gitkeep") -Value ""

  Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $outPath -Force
  Write-Host "OK: $outPath"
}
finally {
  Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
}
