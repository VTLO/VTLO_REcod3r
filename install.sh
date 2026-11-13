#!/bin/sh
# VTLO_REcod3r — installation en une ligne :
#   curl -fsSL https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install.sh | sh
set -eu
REPO="${RECOD3R_REPO:-VTLO/VTLO_REcod3r}"
BRANCH="${RECOD3R_BRANCH:-main}"
DEST="${RECOD3R_PREFIX:-$HOME/.vtlo_recod3r}"
BIN="${RECOD3R_BIN:-$HOME/.local/bin}"

say() { printf '%s\n' "$*"; }
die() { printf '✘ %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 est requis (version 3.8 ou plus)."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || die "Python 3.8 ou plus est requis."

say "∇TLO · installation de VTLO_REcod3r…"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
if [ -n "${RECOD3R_TARBALL:-}" ]; then
  cp "$RECOD3R_TARBALL" "$TMP/src.tgz"
elif command -v curl >/dev/null 2>&1; then
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" -o "$TMP/src.tgz" || die "téléchargement impossible."
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP/src.tgz" "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" || die "téléchargement impossible."
else
  die "curl ou wget est requis."
fi

mkdir -p "$TMP/x" "$DEST"
tar -xzf "$TMP/src.tgz" -C "$TMP/x"
SRC="$(find "$TMP/x" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -d "$SRC/recod3r" ] || die "archive inattendue."
rm -rf "$DEST/app"; mkdir -p "$DEST/app"
cp -R "$SRC/recod3r" "$DEST/app/recod3r"

mkdir -p "$BIN"
for nom in vtlo-recod3r rec0d; do
  if [ "$nom" = "rec0d" ]; then arg="rec0d"; else arg=""; fi
  cat > "$BIN/$nom" <<LAUNCH
#!/bin/sh
PYTHONPATH="$DEST/app\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m recod3r $arg "\$@"
LAUNCH
  chmod +x "$BIN/$nom"
done

"$BIN/vtlo-recod3r" setup || true

case ":$PATH:" in *":$BIN:"*) ;; *) say "⚠ Ajoutez $BIN à votre PATH :  export PATH=\"$BIN:\$PATH\"" ;; esac
say "✔ Installé. Tapez /rec0d dans votre CLI d'IA (ou « rec0d » dans un terminal)."
