"""Forge : squelettes + briefs, progression, livraison (scripts, skills légers, commandes), orchestrateur."""
import json
import os
import shutil
import stat
from pathlib import Path

from .engine import MARK, VERSION, home, redact, state_dir  # noqa: F401


def out_dir():
    return Path(os.environ.get("RECOD3R_OUT") or (home() / "vtlorecod_scripts"))


def tilde(p):
    p = Path(p)
    try:
        return "~/" + p.relative_to(home()).as_posix()
    except ValueError:
        return str(p)


PY = r'''#!/usr/bin/env python3
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
"""@@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@).

Contrat : entrées = arguments/fichiers/stdin, jamais d'invite · sortie = texte court ou --json (UN objet)
          codes : 0 ok · 1 échec (stderr) · 2 usage · 3 décision IA requise (JSON needs_ai sur stdout)
          réponse de l'IA au relancement : RECOD3R_AI_ANSWER (JSON), REVALIDÉE par le script.
"""
import argparse, json, os, sys

SPEC = @@SPEC@@


def ia_requise(question, **contexte):
    print(json.dumps({"needs_ai": question, "context": contexte}, ensure_ascii=False))
    raise SystemExit(3)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("entrees", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.parse_args(argv)
    ia_requise("script non implémenté : exécuter les étapes d'origine à la main", etapes=SPEC)


if __name__ == "__main__":
    sys.exit(main())
'''
SH = r'''#!/usr/bin/env bash
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
# @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@).
# Contrat : 0 ok · 1 échec (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout) ; réponse IA : RECOD3R_AI_ANSWER (à REVALIDER).
set -euo pipefail
# Spec :
@@SPEC_C@@
printf '{"needs_ai":"script non implémenté : exécuter les étapes d origine à la main"}\n'
exit 3
'''
PS = r'''#!/usr/bin/env pwsh
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
# @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@).
# Contrat : 0 ok · 1 échec (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout) ; réponse IA : $env:RECOD3R_AI_ANSWER (à REVALIDER).
$ErrorActionPreference = 'Stop'
# Spec :
@@SPEC_C@@
'{"needs_ai":"script non implémenté : exécuter les étapes d origine à la main"}'
exit 3
'''
JS = r'''#!/usr/bin/env node
// RECOD3R-MANIFEST: @@MANIFEST@@
// RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
// @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@).
// Contrat : 0 ok · 1 échec (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout) ; réponse IA : RECOD3R_AI_ANSWER (à REVALIDER).
const SPEC = @@SPEC@@;
console.log(JSON.stringify({ needs_ai: "script non implémenté : exécuter les étapes d'origine à la main", context: { etapes: SPEC } }));
process.exit(3);
'''


def fmt_n(x):
    return "{:,.0f}".format(x).replace(",", " ")


def ext_for(lang):
    return {"powershell": "ps1", "bash": "sh", "node": "mjs"}.get(lang, "py")


def runner_for(ext):
    return {"ps1": "pwsh -File", "sh": "bash", "mjs": "node"}.get(ext, "python3")


def _chmod_x(p):
    try:
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def copy_annexes(a, dest):
    """Copie les annexes du skill (scripts, références, modèles…) dans `dest` en gardant l'arborescence. Retourne les chemins copiés."""
    src, done = a.get("annex_dir"), []
    if not src:
        return done
    src = Path(src)
    for r in a["refs"]:
        f = src / r
        t = (Path(dest) / r)
        if not f.is_file() or ".." in Path(r).parts:
            continue
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, t)
            if f.stat().st_mode & stat.S_IXUSR:
                _chmod_x(t)
            done.append(r)
        except OSError:
            pass
    return done


def brief(a, it, ext):
    steps = "\n".join("- " + s for s in it["code_steps"])
    ai = "\n".join("- " + s for s in it["ai_steps"]) if it["ai_steps"] else "- aucune"
    refs = ("\n## Annexes du skill (dossier `annexes/` à côté de ce brief, lecture seule)\n"
            "Elles sont livrées automatiquement avec le skill : lis-les et intègre ce qui doit l'être (constantes, tables, schémas, gabarits) ; "
            "les scripts existants se réutilisent ou s'appellent depuis ton script plutôt que de les réécrire.\n"
            + "\n".join("- `annexes/%s`" % r for r in a["refs"]) + "\n") if a["refs"] else ""
    orig = redact(a["body"])[:9000]
    return (
        "# Brief de codage : transformer « {name} » en script de qualité professionnelle ({lang})\n\n"
        "Tu l'écris UNE fois, d'un seul jet ; il tournera ensuite pour 0 token. Économie estimée : {save:.0f} tokens par usage.\n\n"
        "## Fichiers\n- Script à compléter : `scripts/{slug}.{ext}` (squelette prêt, contrat de codes de sortie inclus).\n"
        "- Garde le manifeste `RECOD3R-MANIFEST` en tête.\n- **Supprime la ligne `{mark}`** quand le script est réellement implémenté : c'est le signal d'avancement.\n\n"
        "## Langage\n{lang} — {why}\n\n## Exigences\n- Déterministe, idempotent, sans invite interactive, délai borné.\n"
        "- Bibliothèque standard uniquement, sauf dépendance justifiée.\n"
        "- Entrées validées ; échec : une ligne sur stderr, code 1. Pas de `eval`/`shell=True`, pas de secret en argument.\n"
        "- Ce qui demande de la compréhension : sortie JSON `{{\"needs_ai\": question, \"context\": …}}` avec code 3 ; la réponse revient par `RECOD3R_AI_ANSWER` et le script la REVALIDE.\n"
        "- Sortie compacte (`--json` = UN objet).\n- Ne modifie AUCUN autre fichier que le script de ce dossier.\n\n"
        "## Étapes qui deviennent du code\n{steps}\n{refs}\n## Étapes qui restent à l'IA\n{ai}\n\n"
        "## Instructions d'origine (secrets masqués)\n```\n{orig}\n```\n\n## Quand tu as fini\nRien d'autre à lancer : pas de test. Passe à la tâche suivante.\n"
    ).format(name=a["name"], lang=it["lang"], save=it["save_per_use"], slug=it["slug"], ext=ext, mark=MARK, why=it["lang_why"], steps=steps, refs=refs, ai=ai, orig=orig)


def scaffold(run, a, it):
    ext = ext_for(it["lang"])
    d = Path(run) / "forge" / it["slug"]
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    manifest = json.dumps({"v": 1, "entree": ["args", "fichier", "stdin"], "sortie": "text+json", "familles": it["families"], "ia": "partielle"}, ensure_ascii=False, separators=(",", ":"))
    spec_json = json.dumps(it["code_steps"], ensure_ascii=False)
    spec_c = "\n".join("# - " + s.replace("\n", " ") for s in it["code_steps"])
    tpl = {"ps1": PS, "sh": SH, "mjs": JS}.get(ext, PY)
    txt = (tpl.replace("@@SLUG@@", it["slug"]).replace("@@TITLE@@", a["name"].replace('"', "'")).replace("@@VERSION@@", VERSION)
           .replace("@@MANIFEST@@", manifest).replace("@@SPEC@@", spec_json).replace("@@SPEC_C@@", spec_c))
    script = d / "scripts" / ("%s.%s" % (it["slug"], ext))
    script.write_text(txt, encoding="utf-8")
    _chmod_x(script)
    copy_annexes(a, d / "annexes")
    (d / "BRIEF.md").write_text(brief(a, it, ext), encoding="utf-8")
    return {"slug": it["slug"], "name": a["name"], "dir": d, "script": script, "ext": ext, "lang": it["lang"], "asset": a, "item": it}


def prompt(run, forged):
    lst = "\n".join("- forge/{0}/BRIEF.md → forge/{0}/scripts/{0}.{1}".format(f["slug"], f["ext"]) for f in forged)
    return ("Tu es le rédacteur de code de VTLO_REcod3r. Dossier de travail : {run}.\n\nEn UNE SEULE tâche, sans test ni commande intermédiaire, pour chacun des {n} éléments ci-dessous : "
            "lis son BRIEF.md puis complète le script indiqué (code complet de qualité professionnelle) et SUPPRIME la ligne `{mark}` quand il est réellement implémenté. "
            "Ne modifie aucun autre fichier.\n\n{lst}\n\nTermine quand tous les scripts sont écrits.\n").format(run=run, n=len(forged), mark=MARK, lst=lst)


def written(script):
    try:
        return MARK not in Path(script).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def thin(slug, rel, ext, desc, kind, annexes=()):
    body = ("- code 0 : rapporte le résultat.\n- code 1 : rapporte stderr et arrête.\n- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, "
            "puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse).\n")
    run = "%s %s" % (runner_for(ext), rel)
    d = desc.replace("\n", " ")[:150]
    if kind == "skill":
        ann = ("\nAnnexes du skill (dans ce dossier) : %s\n" % ", ".join("`%s`" % r for r in list(annexes)[:12])) if annexes else ""
        return "---\nname: %s\ndescription: %s\n---\nExécute `%s <args>` et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.\n%s%s" % (slug, d, run, body, ann)
    if kind == "claude":
        return "---\ndescription: %s\nallowed-tools: Bash(%s:*)\n---\nRésultat du script :\n!`%s $ARGUMENTS`\n\nN'agis que sur cette sortie.\n%s" % (d, runner_for(ext).split(" ")[0], run, body)
    return "---\ndescription: %s\n---\nExécute `%s $ARGUMENTS` et lis UNIQUEMENT sa sortie standard.\n%s" % (d, run, body)


def deliver(out, forged, p):
    out = Path(out)
    for sub in ("scripts", "skills", "commandes/claude", "commandes/codex-agy"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    done, todo, n_annex = [], [], {}
    outt = tilde(out)
    for f in forged:
        a = f["asset"]
        if written(f["script"]):
            rel = "%s/scripts/%s.%s" % (outt, f["slug"], f["ext"])
            dest = out / "scripts" / ("%s.%s" % (f["slug"], f["ext"]))
            shutil.copyfile(f["script"], dest)
            _chmod_x(dest)
            (out / "skills" / f["slug"]).mkdir(parents=True, exist_ok=True)
            ann = copy_annexes(a, out / "skills" / f["slug"])  # scripts et références du skill, inclus automatiquement
            n_annex[f["slug"]] = len(ann)
            (out / "skills" / f["slug"] / "SKILL.md").write_text(thin(f["slug"], rel, f["ext"], a["description"], "skill", ann), encoding="utf-8")
            (out / "commandes/claude" / (f["slug"] + ".md")).write_text(thin(f["slug"], rel, f["ext"], a["description"], "claude"), encoding="utf-8")
            (out / "commandes/codex-agy" / (f["slug"] + ".md")).write_text(thin(f["slug"], rel, f["ext"], a["description"], "codex"), encoding="utf-8")
            done.append(f["slug"])
        else:
            d = out / "a_completer" / f["slug"]
            (d / "scripts").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f["dir"] / "BRIEF.md", d / "BRIEF.md")
            shutil.copyfile(f["script"], d / "scripts" / f["script"].name)
            copy_annexes(a, d / "annexes")
            todo.append(f["slug"])
    tok = eur = sec = 0.0
    rows = ""
    for f in forged:
        if f["slug"] not in done:
            continue
        it = f["item"]
        m = it["save_per_use"] * p["uses_per_month"] * p["users"]
        tok += m
        eur += m / 1e6 * p["eur_per_mtok"]
        sec += max(it["ai_sec_per_use"] - it["script_sec_per_use"], 0.0) * p["uses_per_month"] * p["users"]
        rows += "| `%s` | %s | `%s scripts/%s.%s` | %s tokens/usage | %s |\n" % (f["slug"], f["lang"], runner_for(f["ext"]), f["slug"], f["ext"], fmt_n(it["save_per_use"]), ("%d dans `skills/%s/`" % (n_annex.get(f["slug"], 0), f["slug"])) if n_annex.get(f["slug"]) else "—")
    todo_txt = ("\n## À compléter\n%d script(s) non écrits : voir `a_completer/<nom>/BRIEF.md` (à donner à votre IA).\n" % len(todo)) if todo else ""
    md = (
        "# Scripts VTLO_REcod3r\n\nGénéré par VTLO_REcod3r %s. Chaque script remplace les étapes mécaniques d'un de vos skills ; l'IA n'intervient plus que pour les décisions (code de sortie 3).\n\n"
        "| Script | Langage | Lancer | Économie | Annexes incluses |\n|---|---|---|---|---|\n%s\n"
        "Estimation (hypothèses : %.0f usages/mois, %.0f utilisateur(s), %.2f €/M tokens) : ≈ %.0f tokens, ≈ %.2f €, ≈ %.1f h par mois.\n\n"
        "## Contrat commun\n- entrées : arguments, fichiers ou stdin · sortie : texte court, ou `--json`\n- codes : `0` ok · `1` échec · `2` usage · `3` décision IA requise (JSON `needs_ai`) ; relancez avec la réponse dans `RECOD3R_AI_ANSWER`.\n\n"
        "## Dans votre outil d'IA\n`skills/<nom>/SKILL.md` (skills légers) et `commandes/{claude,codex-agy}/` sont prêts à copier. **Antigravity CLI (agy)** : copiez `skills/<nom>` dans `~/.gemini/antigravity-cli/skills/` (global) ou `<projet>/.agents/skills/` (projet).\n\n"
        "## Orchestration (option)\nGénérée à la demande par l'application (`recod3r orchestrer`) : `orchestrer.sh` / `orchestrer.ps1` enchaînent les scripts de `orchestrer.txt` ; l'IA n'est sollicitée qu'au code 3.\n%s"
    ) % (VERSION, rows, p["uses_per_month"], p["users"], p["eur_per_mtok"], tok, eur, sec / 3600.0, todo_txt)
    (out / "LISEZMOI.md").write_text(md, encoding="utf-8")
    return {"out": out, "done": done, "todo": todo}


ORCH_SH = r'''#!/usr/bin/env bash
# VTLO_REcod3r — orchestrateur : enchaîne les scripts de orchestrer.txt ; l'IA n'est appelée qu'au code 3.
# Usage : ./orchestrer.sh [liste.txt]      (agent IA : variable RECOD3R_AGENT_CMD="cmd {prompt_file}" ou CLI détecté)
cd "$(dirname "$0")" || exit 1
LISTE="${1:-orchestrer.txt}"
run_ai() { # $1 = JSON needs_ai ; imprime la réponse
  local pf; pf="$(mktemp)"; printf 'Réponds UNIQUEMENT par la réponse JSON demandée, sans texte autour.\n%s\n' "$1" > "$pf"
  if [ -n "${RECOD3R_AGENT_CMD:-}" ]; then sh -c "${RECOD3R_AGENT_CMD//\{prompt_file\}/$pf}"
  elif command -v agy >/dev/null; then agy --dangerously-skip-permissions -p "$(cat "$pf")"
  elif command -v claude >/dev/null; then claude -p "$(cat "$pf")"
  elif command -v codex >/dev/null; then codex exec "$(cat "$pf")"
  else echo "aucun agent IA disponible" >&2; return 1; fi
}
while IFS= read -r ligne || [ -n "$ligne" ]; do
  case "$ligne" in ''|'#'*) continue;; esac
  echo "▶ $ligne"; out="$(eval "$ligne")"; code=$?
  if [ "$code" -eq 3 ]; then
    echo "  ↳ décision IA requise"; rep="$(run_ai "$out")" || exit 3
    out="$(RECOD3R_AI_ANSWER="$rep" eval "$ligne")"; code=$?
  fi
  printf '%s\n' "$out"; [ "$code" -eq 0 ] || { echo "✖ code $code : arrêt" >&2; exit "$code"; }
done < "$LISTE"
echo "✔ orchestration terminée"
'''
ORCH_PS = r'''# VTLO_REcod3r — orchestrateur (PowerShell) : enchaîne orchestrer.txt ; l'IA n'est appelée qu'au code 3.
param([string]$Liste = "orchestrer.txt")
Set-Location $PSScriptRoot
function Ask-Ai($json) {
  $pf = New-TemporaryFile; "Réponds UNIQUEMENT par la réponse JSON demandée.`n$json" | Set-Content $pf
  if ($env:RECOD3R_AGENT_CMD) { & cmd /C ($env:RECOD3R_AGENT_CMD -replace '\{prompt_file\}', $pf) }
  elseif (Get-Command agy -ErrorAction SilentlyContinue) { agy --dangerously-skip-permissions -p (Get-Content $pf -Raw) }
  elseif (Get-Command claude -ErrorAction SilentlyContinue) { claude -p (Get-Content $pf -Raw) }
  elseif (Get-Command codex -ErrorAction SilentlyContinue) { codex exec (Get-Content $pf -Raw) }
  else { throw "aucun agent IA disponible" }
}
foreach ($ligne in Get-Content $Liste) {
  if ($ligne -match '^\s*(#|$)') { continue }
  Write-Host "▶ $ligne"; $out = Invoke-Expression $ligne; $code = $LASTEXITCODE
  if ($code -eq 3) { Write-Host "  ↳ décision IA requise"; $env:RECOD3R_AI_ANSWER = (Ask-Ai $out); $out = Invoke-Expression $ligne; $code = $LASTEXITCODE; Remove-Item Env:RECOD3R_AI_ANSWER }
  $out; if ($code -ne 0) { Write-Error "code $code : arrêt"; exit $code }
}
Write-Host "✔ orchestration terminée"
'''


def orchestrer(out, entries):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lst = "# Une commande par ligne (modifiez l'ordre à volonté). Code 3 = l'IA tranche, puis relance.\n"
    for slug, ext in entries:
        lst += "%s scripts/%s.%s\n" % (runner_for(ext), slug, ext)
    (out / "orchestrer.txt").write_text(lst, encoding="utf-8")
    (out / "orchestrer.sh").write_text(ORCH_SH, encoding="utf-8", newline="\n")
    (out / "orchestrer.ps1").write_text(ORCH_PS, encoding="utf-8")
    _chmod_x(out / "orchestrer.sh")
