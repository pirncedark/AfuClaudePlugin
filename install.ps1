# Usage: .\install.ps1 [-Target claude|codex|both]   (default: both)
# Copies every skill in skills\ into ~\.claude\skills and/or ~\.agents\skills (Codex).
param([ValidateSet('claude','codex','both')][string]$Target = 'both')
function Put($dest) {
  New-Item -ItemType Directory -Force $dest | Out-Null
  Get-ChildItem "$PSScriptRoot\skills" -Directory | ForEach-Object {
    $to = Join-Path $dest $_.Name
    if (Test-Path $to) { Remove-Item -Recurse -Force $to }
    Copy-Item -Recurse $_.FullName $to
    Write-Host "ok  $to"
  }
}
if ($Target -ne 'codex')  { Put "$HOME\.claude\skills" }
if ($Target -ne 'claude') { Put "$HOME\.agents\skills" }
Write-Host "Done. Next: copy .env.example to .env (Telegram only) and read docs\ORKESTRASYON.md"
