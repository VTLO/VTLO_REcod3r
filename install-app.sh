#!/bin/sh
# VTLO_REcod3r (application) — installation en une commande, à coller dans un terminal ou dans agy / Claude Code / Gemini CLI / Codex :
#   curl -fsSL https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install-app.sh | sh
set -eu
SRC="${RECOD3R_SRC:-$HOME/.vtlo_recod3r/src}"
BIN="${RECOD3R_BIN:-$HOME/.local/bin}"
die() { printf '✘ %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null 2>&1 || die "git est requis."
if ! command -v cargo >/dev/null 2>&1; then
  [ -x "$HOME/.cargo/bin/cargo" ] || { command -v curl >/dev/null 2>&1 || die "curl est requis pour installer Rust."; echo "→ installation de Rust (rustup)…"; curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal >/dev/null; }
  PATH="$HOME/.cargo/bin:$PATH"; export PATH
fi
if [ -d "$SRC/.git" ]; then git -C "$SRC" pull --ff-only -q; else mkdir -p "$(dirname "$SRC")"; git clone -q --depth 1 https://github.com/VTLO/VTLO_REcod3r.git "$SRC"; fi
echo "→ compilation (quelques minutes la première fois)…"
(cd "$SRC/app" && cargo build --release -p recod3r-app -q)
mkdir -p "$BIN"; cp "$SRC/app/target/release/recod3r" "$BIN/recod3r"; chmod +x "$BIN/recod3r"
"$BIN/recod3r" integrer || true
echo "∇TLO · VTLO_REcod3r installé : $BIN/recod3r"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "⚠ Ajoutez $BIN à votre PATH :  export PATH=\"$BIN:\$PATH\"" ;; esac
echo "✔ Tapez « recod3r » (application) ou /recod3r dans votre CLI d'IA."
