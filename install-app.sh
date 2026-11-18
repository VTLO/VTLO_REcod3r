#!/bin/sh
# VTLO_REcod3r (application, Python) — installation en une commande, à coller dans un terminal ou dans agy (Antigravity CLI) / Claude Code / Codex :
#   curl -fsSL https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install-app.sh | sh
# Prérequis : python3 (3.8+) et git. Aucune dépendance à installer, aucune compilation.
set -eu
SRC="${RECOD3R_SRC:-$HOME/.vtlo_recod3r/src}"
BIN="${RECOD3R_BIN:-$HOME/.local/bin}"
die() { printf '✘ %s\n' "$*" >&2; exit 1; }
command -v git >/dev/null 2>&1 || die "git est requis."
PY=python3; command -v "$PY" >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || die "python3 est requis (3.8 ou plus)."
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || die "Python 3.8 ou plus est requis."
if [ -d "$SRC/.git" ]; then git -C "$SRC" pull --ff-only -q; else mkdir -p "$(dirname "$SRC")"; git clone -q --depth 1 https://github.com/VTLO/VTLO_REcod3r.git "$SRC"; fi
mkdir -p "$BIN"
cat > "$BIN/recod3r" <<LAUNCH
#!/bin/sh
PYTHONPATH="$SRC/app\${PYTHONPATH:+:\$PYTHONPATH}" exec $PY -m recod3r_app "\$@"
LAUNCH
chmod +x "$BIN/recod3r"
"$BIN/recod3r" integrer || true
echo "∇TLO · VTLO_REcod3r installé : $BIN/recod3r (sources : $SRC)"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "⚠ Ajoutez $BIN à votre PATH :  export PATH=\"$BIN:\$PATH\"" ;; esac
echo "✔ Tapez « recod3r » (application) ou /recod3r dans votre CLI d'IA. Mise à jour : relancez cette commande."
