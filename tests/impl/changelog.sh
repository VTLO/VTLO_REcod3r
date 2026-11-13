#!/usr/bin/env bash
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args", "stdin"], "sortie": "json", "familles": ["git", "json"], "ia": false}
# changelog — commits depuis le dernier tag, groupés par type « conventional commit », sortie JSON.
# Contrat : 0 ok · 1 échec · 2 usage · 3 décision IA requise (JSON sur stdout) ; réponse IA : $RECOD3R_AI_ANSWER (à revalider).
set -euo pipefail
IFS=$'\n\t'

grouper() {  # stdin : un sujet de commit par ligne -> JSON {"feat":n,"fix":n,"autre":n,"breaking":bool}
  local feat=0 fix=0 autre=0 brk=false l
  while IFS= read -r l; do
    [ -z "$l" ] && continue
    case "$l" in
      feat*'!:'*|*'BREAKING CHANGE'*) brk=true; feat=$((feat+1));;
      feat*:*) feat=$((feat+1));;
      fix*:*) fix=$((fix+1));;
      *) autre=$((autre+1));;
    esac
  done
  printf '{"feat":%d,"fix":%d,"autre":%d,"breaking":%s}\n' "$feat" "$fix" "$autre" "$brk"
}

if [ "${1:-}" = "--selftest" ]; then
  r=$(printf 'feat: a\nfix: b\nfeat!: c\nchore: d\n' | grouper)
  [ "$r" = '{"feat":2,"fix":1,"autre":1,"breaking":true}' ] || { echo "échec grouper: $r" >&2; exit 1; }
  r=$(printf '' | grouper)
  [ "$r" = '{"feat":0,"fix":0,"autre":0,"breaking":false}' ] || { echo "échec vide: $r" >&2; exit 1; }
  echo "autotest : 2 cas ok"; exit 0
fi

if [ "${1:-}" = "--help" ]; then echo "usage : ${0##*/} [--json] [DEPOT_GIT]"; exit 0; fi
depot="."
for a in "$@"; do case "$a" in --json) ;; *) depot="$a";; esac; done
git -C "$depot" rev-parse --git-dir >/dev/null 2>&1 || { echo "échec : pas un dépôt git : $depot" >&2; exit 1; }
tag=$(git -C "$depot" describe --tags --abbrev=0 2>/dev/null || true)
if [ -n "$tag" ]; then plage="$tag..HEAD"; else plage="HEAD"; fi
git -C "$depot" log --format=%s "$plage" | grouper
