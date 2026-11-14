#!/bin/sh
# VTLO_REcod3r — installation : cloner le dépôt en local, puis lancer ce script.
#   git clone https://github.com/VTLO/VTLO_REcod3r.git ~/VTLO_REcod3r && sh ~/VTLO_REcod3r/install.sh
# Le dépôt cloné reste en place (mise à jour : « git pull » dans le dossier). Commande créée : vtlorecod
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="${RECOD3R_BIN:-$HOME/.local/bin}"

die() { printf '✘ %s\n' "$*" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || die "python3 est requis (version 3.8 ou plus)."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || die "Python 3.8 ou plus est requis."
[ -d "$DIR/recod3r" ] || die "dossier du dépôt introuvable : lancez ce script depuis le dépôt cloné."

mkdir -p "$BIN"
cat > "$BIN/vtlorecod" <<LAUNCH
#!/bin/sh
PYTHONPATH="$DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m recod3r "\$@"
LAUNCH
chmod +x "$BIN/vtlorecod"

echo "∇TLO · VTLO_REcod3r installé (dépôt : $DIR)"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "⚠ Ajoutez $BIN à votre PATH :  export PATH=\"$BIN:\$PATH\"" ;; esac
echo "✔ Tapez « vtlorecod » dans un terminal pour lancer l'analyse."
