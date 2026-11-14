//! Forge : squelettes + briefs, progression, livraison (scripts, skills légers, commandes), orchestrateur.
use crate::engine::{home, redact, Asset, Item, MARK, VERSION};
use serde_json::json;
use std::fs;
use std::path::{Path, PathBuf};

pub fn state_dir() -> PathBuf { std::env::var_os("RECOD3R_DIR").map(PathBuf::from).unwrap_or_else(|| home().join(".vtlo_recod3r")) }
pub fn out_dir() -> PathBuf { std::env::var_os("RECOD3R_OUT").map(PathBuf::from).unwrap_or_else(|| home().join("vtlorecod_scripts")) }
pub fn tilde(p: &Path) -> String { let h = home(); let s = p.to_string_lossy().into_owned(); match p.strip_prefix(&h) { Ok(r) => format!("~/{}", r.to_string_lossy().replace('\\', "/")), Err(_) => s } }

const PY: &str = r#"#!/usr/bin/env python3
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
"#;
const SH: &str = r#"#!/usr/bin/env bash
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
# @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@).
# Contrat : 0 ok · 1 échec (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout) ; réponse IA : RECOD3R_AI_ANSWER (à REVALIDER).
set -euo pipefail
# Spec :
@@SPEC_C@@
printf '{"needs_ai":"script non implémenté : exécuter les étapes d origine à la main"}\n'
exit 3
"#;
const PS: &str = r#"#!/usr/bin/env pwsh
# RECOD3R-MANIFEST: @@MANIFEST@@
# RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
# @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@).
# Contrat : 0 ok · 1 échec (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout) ; réponse IA : $env:RECOD3R_AI_ANSWER (à REVALIDER).
$ErrorActionPreference = 'Stop'
# Spec :
@@SPEC_C@@
'{"needs_ai":"script non implémenté : exécuter les étapes d origine à la main"}'
exit 3
"#;
const JS: &str = r#"#!/usr/bin/env node
// RECOD3R-MANIFEST: @@MANIFEST@@
// RECOD3R:A_IMPLEMENTER   <- supprimez cette ligne quand le script est réellement implémenté
// @@SLUG@@ — remplaçant déterministe des étapes mécaniques de « @@TITLE@@ » (VTLO_REcod3r @@VERSION@@).
// Contrat : 0 ok · 1 échec (stderr) · 2 usage · 3 décision IA requise (JSON sur stdout) ; réponse IA : RECOD3R_AI_ANSWER (à REVALIDER).
const SPEC = @@SPEC@@;
console.log(JSON.stringify({ needs_ai: "script non implémenté : exécuter les étapes d'origine à la main", context: { etapes: SPEC } }));
process.exit(3);
"#;

pub fn fmt_n(x: f64) -> String { let s = format!("{:.0}", x); let mut o = String::new(); for (i, c) in s.chars().rev().enumerate() { if i > 0 && i % 3 == 0 { o.push(' '); } o.push(c); } o.chars().rev().collect() }
pub fn ext_for(lang: &str) -> &'static str { match lang { "powershell" => "ps1", "bash" => "sh", "node" => "mjs", _ => "py" } }
pub fn runner_for(ext: &str) -> &'static str { match ext { "ps1" => "pwsh -File", "sh" => "bash", "mjs" => "node", _ => "python3" } }

#[derive(Clone)]
pub struct Forged { pub slug: String, pub name: String, pub dir: PathBuf, pub script: PathBuf, pub ext: &'static str, pub lang: String, pub asset: Asset, pub item: Item }

fn brief(a: &Asset, it: &Item, ext: &str) -> String {
    let steps = it.code_steps.iter().map(|s| format!("- {s}")).collect::<Vec<_>>().join("\n");
    let ai = if it.ai_steps.is_empty() { "- aucune".to_string() } else { it.ai_steps.iter().map(|s| format!("- {s}")).collect::<Vec<_>>().join("\n") };
    let refs = if a.refs.is_empty() { String::new() } else { format!("\n## Fichiers de référence du skill (à intégrer dans le script)\n{}\n", a.refs.iter().map(|r| format!("- {r}")).collect::<Vec<_>>().join("\n")) };
    let orig: String = redact(&a.body).chars().take(9000).collect();
    format!("# Brief de codage : transformer « {name} » en script de qualité professionnelle ({lang})\n\n\
Tu l'écris UNE fois, d'un seul jet ; il tournera ensuite pour 0 token. Économie estimée : {save:.0} tokens par usage.\n\n\
## Fichiers\n- Script à compléter : `scripts/{slug}.{ext}` (squelette prêt, contrat de codes de sortie inclus).\n- Garde le manifeste `RECOD3R-MANIFEST` en tête.\n- **Supprime la ligne `{mark}`** quand le script est réellement implémenté : c'est le signal d'avancement.\n\n\
## Langage\n{lang} — {why}\n\n## Exigences\n- Déterministe, idempotent, sans invite interactive, délai borné.\n- Bibliothèque standard uniquement, sauf dépendance justifiée.\n- Entrées validées ; échec : une ligne sur stderr, code 1. Pas de `eval`/`shell=True`, pas de secret en argument.\n- Ce qui demande de la compréhension : sortie JSON `{{\"needs_ai\": question, \"context\": …}}` avec code 3 ; la réponse revient par `RECOD3R_AI_ANSWER` et le script la REVALIDE.\n- Sortie compacte (`--json` = UN objet).\n- Ne modifie AUCUN autre fichier que le script de ce dossier.\n\n\
## Étapes qui deviennent du code\n{steps}\n{refs}\n## Étapes qui restent à l'IA\n{ai}\n\n## Instructions d'origine (secrets masqués)\n```\n{orig}\n```\n\n## Quand tu as fini\nRien d'autre à lancer : pas de test. Passe à la tâche suivante.\n",
        name = a.name, lang = it.lang, save = it.save_per_use, slug = it.slug, ext = ext, mark = MARK, why = it.lang_why, steps = steps, refs = refs, ai = ai, orig = orig)
}

pub fn scaffold(run: &Path, a: &Asset, it: &Item) -> std::io::Result<Forged> {
    let ext = ext_for(&it.lang);
    let dir = run.join("forge").join(&it.slug);
    fs::create_dir_all(dir.join("scripts"))?;
    let manifest = json!({"v": 1, "entree": ["args", "fichier", "stdin"], "sortie": "text+json", "familles": it.families, "ia": "partielle"}).to_string();
    let spec_json = serde_json::to_string(&it.code_steps).unwrap_or_else(|_| "[]".into());
    let spec_c = it.code_steps.iter().map(|s| format!("# - {}", s.replace('\n', " "))).collect::<Vec<_>>().join("\n");
    let tpl = match ext { "ps1" => PS, "sh" => SH, "mjs" => JS, _ => PY };
    let txt = tpl.replace("@@SLUG@@", &it.slug).replace("@@TITLE@@", &a.name.replace('"', "'")).replace("@@VERSION@@", VERSION)
        .replace("@@MANIFEST@@", &manifest).replace("@@SPEC@@", &spec_json).replace("@@SPEC_C@@", &spec_c);
    let script = dir.join("scripts").join(format!("{}.{}", it.slug, ext));
    fs::write(&script, txt)?;
    #[cfg(unix)] { use std::os::unix::fs::PermissionsExt; let _ = fs::set_permissions(&script, fs::Permissions::from_mode(0o755)); }
    fs::write(dir.join("BRIEF.md"), brief(a, it, ext))?;
    Ok(Forged { slug: it.slug.clone(), name: a.name.clone(), dir, script, ext, lang: it.lang.clone(), asset: a.clone(), item: it.clone() })
}

pub fn prompt(run: &Path, forged: &[Forged]) -> String {
    let list = forged.iter().map(|f| format!("- forge/{}/BRIEF.md → forge/{}/scripts/{}.{}", f.slug, f.slug, f.slug, f.ext)).collect::<Vec<_>>().join("\n");
    format!("Tu es le rédacteur de code de VTLO_REcod3r. Dossier de travail : {}.\n\nEn UNE SEULE tâche, sans test ni commande intermédiaire, pour chacun des {} éléments ci-dessous : lis son BRIEF.md puis complète le script indiqué (code complet de qualité professionnelle) et SUPPRIME la ligne `{}` quand il est réellement implémenté. Ne modifie aucun autre fichier.\n\n{}\n\nTermine quand tous les scripts sont écrits.\n",
        run.display(), forged.len(), MARK, list)
}

pub fn written(script: &Path) -> bool {
    fs::read_to_string(script).map(|t| !t.contains(MARK)).unwrap_or(false)
}

fn thin(slug: &str, rel: &str, ext: &str, desc: &str, kind: &str) -> String {
    let body = format!("- code 0 : rapporte le résultat.\n- code 1 : rapporte stderr et arrête.\n- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse).\n");
    let run = format!("{} {}", runner_for(ext), rel);
    let d: String = desc.replace('\n', " ").chars().take(150).collect();
    match kind {
        "skill" => format!("---\nname: {slug}\ndescription: {d}\n---\nExécute `{run} <args>` et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.\n{body}"),
        "claude" => format!("---\ndescription: {d}\nallowed-tools: Bash({}:*)\n---\nRésultat du script :\n!`{run} $ARGUMENTS`\n\nN'agis que sur cette sortie.\n{body}", runner_for(ext).split(' ').next().unwrap()),
        "gemini" => format!("description = \"{}\"\nprompt = \"\"\"\nRésultat du script :\n!{{{run} {{{{args}}}}}}\n\nN'agis que sur cette sortie.\n{body}\"\"\"\n", d.replace('"', "'")),
        _ => format!("---\ndescription: {d}\n---\nExécute `{run} $ARGUMENTS` et lis UNIQUEMENT sa sortie standard.\n{body}"),
    }
}

pub struct Delivery { pub out: PathBuf, pub done: Vec<String>, pub todo: Vec<String> }

/// Livre le dossier final : scripts écrits, skills légers, commandes, a_completer (non écrits), orchestrateur, LISEZMOI.
pub fn deliver(out: &Path, forged: &[Forged], p: &crate::engine::Params) -> std::io::Result<Delivery> {
    for sub in ["scripts", "skills", "commandes/claude", "commandes/gemini", "commandes/codex-agy"] { fs::create_dir_all(out.join(sub))?; }
    let (mut done, mut todo) = (vec![], vec![]);
    let outt = tilde(out);
    for f in forged {
        let a = &f.asset;
        if written(&f.script) {
            let rel = format!("{}/scripts/{}.{}", outt, f.slug, f.ext);
            let dest = out.join("scripts").join(format!("{}.{}", f.slug, f.ext));
            fs::copy(&f.script, &dest)?;
            #[cfg(unix)] { use std::os::unix::fs::PermissionsExt; let _ = fs::set_permissions(&dest, fs::Permissions::from_mode(0o755)); }
            fs::create_dir_all(out.join("skills").join(&f.slug))?;
            fs::write(out.join("skills").join(&f.slug).join("SKILL.md"), thin(&f.slug, &rel, f.ext, &a.description, "skill"))?;
            fs::write(out.join("commandes/claude").join(format!("{}.md", f.slug)), thin(&f.slug, &rel, f.ext, &a.description, "claude"))?;
            fs::write(out.join("commandes/gemini").join(format!("{}.toml", f.slug)), thin(&f.slug, &rel, f.ext, &a.description, "gemini"))?;
            fs::write(out.join("commandes/codex-agy").join(format!("{}.md", f.slug)), thin(&f.slug, &rel, f.ext, &a.description, "codex"))?;
            done.push(f.slug.clone());
        } else {
            let d = out.join("a_completer").join(&f.slug);
            fs::create_dir_all(d.join("scripts"))?;
            fs::copy(f.dir.join("BRIEF.md"), d.join("BRIEF.md"))?;
            fs::copy(&f.script, d.join("scripts").join(f.script.file_name().unwrap()))?;
            todo.push(f.slug.clone());
        }
    }
    let (mut tok, mut eur, mut sec) = (0.0, 0.0, 0.0);
    let mut rows = String::new();
    for f in forged.iter().filter(|f| done.contains(&f.slug)) {
        let it = &f.item;
        let m = it.save_per_use * p.uses_per_month * p.users;
        tok += m; eur += m / 1e6 * p.eur_per_mtok; sec += (it.ai_sec_per_use - it.script_sec_per_use).max(0.0) * p.uses_per_month * p.users;
        rows += &format!("| `{}` | {} | `{} scripts/{}.{}` | {} tokens/usage |\n", f.slug, f.lang, runner_for(f.ext), f.slug, f.ext, fmt_n(it.save_per_use));
    }
    let md = format!("# Scripts VTLO_REcod3r\n\nGénéré par VTLO_REcod3r {VERSION}. Chaque script remplace les étapes mécaniques d'un de vos skills ; l'IA n'intervient plus que pour les décisions (code de sortie 3).\n\n| Script | Langage | Lancer | Économie |\n|---|---|---|---|\n{rows}\n\
Estimation (hypothèses : {:.0} usages/mois, {:.0} utilisateur(s), {:.2} €/M tokens) : ≈ {:.0} tokens, ≈ {:.2} €, ≈ {:.1} h par mois.\n\n\
## Contrat commun\n- entrées : arguments, fichiers ou stdin · sortie : texte court, ou `--json`\n- codes : `0` ok · `1` échec · `2` usage · `3` décision IA requise (JSON `needs_ai`) ; relancez avec la réponse dans `RECOD3R_AI_ANSWER`.\n\n\
## Dans votre outil d'IA\n`skills/<nom>/SKILL.md` (skills légers) et `commandes/{{claude,gemini,codex-agy}}/` sont prêts à copier.\n\n## Orchestration (option)\nGénérée à la demande par l'application (`recod3r orchestrer`) : `orchestrer.sh` / `orchestrer.ps1` enchaînent les scripts de `orchestrer.txt` ; l'IA n'est sollicitée qu'au code 3.\n{}",
        p.uses_per_month, p.users, p.eur_per_mtok, tok, eur, sec / 3600.0,
        if todo.is_empty() { String::new() } else { format!("\n## À compléter\n{} script(s) non écrits : voir `a_completer/<nom>/BRIEF.md` (à donner à votre IA).\n", todo.len()) });
    fs::write(out.join("LISEZMOI.md"), md)?;
    Ok(Delivery { out: out.to_path_buf(), done, todo })
}

const ORCH_SH: &str = r#"#!/usr/bin/env bash
# VTLO_REcod3r — orchestrateur : enchaîne les scripts de orchestrer.txt ; l'IA n'est appelée qu'au code 3.
# Usage : ./orchestrer.sh [liste.txt]      (agent IA : variable RECOD3R_AGENT_CMD="cmd {prompt_file}" ou CLI détecté)
cd "$(dirname "$0")" || exit 1
LISTE="${1:-orchestrer.txt}"
run_ai() { # $1 = JSON needs_ai ; imprime la réponse
  local pf; pf="$(mktemp)"; printf 'Réponds UNIQUEMENT par la réponse JSON demandée, sans texte autour.\n%s\n' "$1" > "$pf"
  if [ -n "${RECOD3R_AGENT_CMD:-}" ]; then sh -c "${RECOD3R_AGENT_CMD//\{prompt_file\}/$pf}"
  elif command -v claude >/dev/null; then claude -p "$(cat "$pf")"
  elif command -v gemini >/dev/null; then gemini -p "$(cat "$pf")"
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
"#;
const ORCH_PS: &str = r#"# VTLO_REcod3r — orchestrateur (PowerShell) : enchaîne orchestrer.txt ; l'IA n'est appelée qu'au code 3.
param([string]$Liste = "orchestrer.txt")
Set-Location $PSScriptRoot
function Ask-Ai($json) {
  $pf = New-TemporaryFile; "Réponds UNIQUEMENT par la réponse JSON demandée.`n$json" | Set-Content $pf
  if ($env:RECOD3R_AGENT_CMD) { & cmd /C ($env:RECOD3R_AGENT_CMD -replace '\{prompt_file\}', $pf) }
  elseif (Get-Command claude -ErrorAction SilentlyContinue) { claude -p (Get-Content $pf -Raw) }
  elseif (Get-Command gemini -ErrorAction SilentlyContinue) { gemini -p (Get-Content $pf -Raw) }
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
"#;

pub fn orchestrer(out: &Path, entries: &[(String, String)]) -> std::io::Result<()> {
    fs::create_dir_all(out)?;
    let mut lst = String::from("# Une commande par ligne (modifiez l'ordre à volonté). Code 3 = l'IA tranche, puis relance.\n");
    for (slug, ext) in entries { lst += &format!("{} scripts/{}.{}\n", runner_for(ext), slug, ext); }
    fs::write(out.join("orchestrer.txt"), lst)?;
    fs::write(out.join("orchestrer.sh"), ORCH_SH)?;
    fs::write(out.join("orchestrer.ps1"), ORCH_PS)?;
    #[cfg(unix)] { use std::os::unix::fs::PermissionsExt; let _ = fs::set_permissions(out.join("orchestrer.sh"), fs::Permissions::from_mode(0o755)); }
    Ok(())
}
