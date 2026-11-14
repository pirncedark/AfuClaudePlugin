# Windows PowerShell installer: runs install.sh through Git Bash
$bash = (Get-Command bash -ErrorAction SilentlyContinue).Source
if (-not $bash) { Write-Error "Git for Windows (bash) gerekli / required: https://git-scm.com"; exit 1 }
& $bash "$PSScriptRoot/install.sh"
