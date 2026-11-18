# VTLO_REcod3r (application) — Windows PowerShell, une commande :
#   irm https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install-app.ps1 | iex
$ErrorActionPreference = 'Stop'
$src = Join-Path $HOME '.vtlo_recod3r\src'
$bin = Join-Path $HOME '.local\bin'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git est requis.' }
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
  Write-Host '→ installation de Rust (rustup)…'
  $r = Join-Path $env:TEMP 'rustup-init.exe'
  Invoke-WebRequest https://win.rustup.rs/x86_64 -OutFile $r; & $r -y --profile minimal | Out-Null
  $env:Path = "$HOME\.cargo\bin;$env:Path"
}
if (Test-Path "$src\.git") { git -C $src pull --ff-only -q } else { New-Item -ItemType Directory -Force (Split-Path $src) | Out-Null; git clone -q --depth 1 https://github.com/VTLO/VTLO_REcod3r.git $src }
Write-Host '→ compilation…'
Push-Location "$src\app"; cargo build --release -p recod3r-app -q; Pop-Location
New-Item -ItemType Directory -Force $bin | Out-Null
Copy-Item "$src\app\target\release\recod3r.exe" "$bin\recod3r.exe" -Force
& "$bin\recod3r.exe" integrer
if ($env:Path -notlike "*$bin*") { [Environment]::SetEnvironmentVariable('Path', "$bin;" + [Environment]::GetEnvironmentVariable('Path','User'), 'User'); Write-Host "→ $bin ajouté au PATH (rouvrez le terminal)." }
Write-Host '✔ Tapez « recod3r » ou /recod3r dans votre CLI d''IA.'
