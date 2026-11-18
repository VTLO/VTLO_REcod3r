# VTLO_REcod3r (application, Python) — Windows PowerShell, une commande :
#   irm https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install-app.ps1 | iex
# Prérequis : Python 3.8+ et git. Aucune dépendance, aucune compilation.
$ErrorActionPreference = 'Stop'
$src = Join-Path $HOME '.vtlo_recod3r\src'
$bin = Join-Path $HOME '.local\bin'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git est requis.' }
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py -3' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { throw 'Python 3.8+ est requis.' }
if (Test-Path "$src\.git") { git -C $src pull --ff-only -q } else { New-Item -ItemType Directory -Force (Split-Path $src) | Out-Null; git clone -q --depth 1 https://github.com/VTLO/VTLO_REcod3r.git $src }
New-Item -ItemType Directory -Force $bin | Out-Null
"@echo off`r`nset PYTHONPATH=$src\app;%PYTHONPATH%`r`n$py -m recod3r_app %*" | Set-Content -Encoding ASCII "$bin\recod3r.cmd"
& "$bin\recod3r.cmd" integrer
if ($env:Path -notlike "*$bin*") { [Environment]::SetEnvironmentVariable('Path', "$bin;" + [Environment]::GetEnvironmentVariable('Path','User'), 'User'); Write-Host "→ $bin ajouté au PATH (rouvrez le terminal)." }
Write-Host '✔ Tapez « recod3r » ou /recod3r dans votre CLI d''IA. Mise à jour : relancez cette commande.'
