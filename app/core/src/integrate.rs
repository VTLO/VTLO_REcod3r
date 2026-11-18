//! Intégration dans les CLI d'IA : dépose un skill / une commande « recod3r » là où chaque outil les lit.
use crate::engine::home;
use std::fs;
use std::path::{Path, PathBuf};

const SKILL: &str = "---\nname: recod3r\ndescription: Transforme en scripts exécutables les skills, prompts et workflows qui n'ont pas besoin d'IA (économie de tokens, d'argent et de temps). À utiliser quand l'utilisateur dit /recod3r, « convertis mes skills en scripts » ou « réduis ma consommation de tokens ».\n---\n\n# VTLO_REcod3r\n\n1. Lance `recod3r scan` et présente le rapport tel quel (éléments convertibles, tokens et euros économisés, durées).\n2. Demande une seule validation à l'utilisateur. Il peut choisir lui-même les skills : `--only nom1,nom2`, en ajouter avec `--add CHEMIN` (fichier, dossier ou .zip), ou tout prendre avec `--all`.\n3. Après accord : `recod3r convert --yes --agent AGENT` (AGENT = claude, gemini, agy ou codex selon l'outil courant). Les scripts sont livrés dans `~/vtlorecod_scripts/`.\n4. Une fois les scripts livrés, propose à l'utilisateur de lancer l'orchestration (`recod3r orchestrer`, ou `--orchestrer` avec la conversion) : c'est le pipeline complet prêt à l'emploi.\n\nNe réécris pas les scripts toi-même : l'outil pilote la conversion et affiche la progression de 0 à 100 %.\n";
const PROMPT: &str = "Exécute le skill recod3r : lance `recod3r scan`, présente le rapport, demande ma validation, puis `recod3r convert --yes --agent AGENT`. Livraison dans ~/vtlorecod_scripts/.";

fn put(p: PathBuf, txt: &str, done: &mut Vec<String>) {
    if let Some(d) = p.parent() { if fs::create_dir_all(d).is_err() { return; } }
    if fs::write(&p, txt).is_ok() { done.push(crate::forge::tilde(&p)); }
}
fn has(dir: &str, bin: &[&str]) -> bool { home().join(dir).exists() || bin.iter().any(|b| crate::engine::which(b)) }

/// Installe pour chaque CLI détecté (ou seulement `only`). Retourne les fichiers écrits.
pub fn integrer(only: Option<&str>) -> Vec<String> {
    let h = home();
    let mut done = vec![];
    let want = |k: &str| only.map(|o| o == k || o == "all").unwrap_or(true);
    let sk = |a: &str| SKILL.replace("AGENT", a);
    if want("claude") && (only.is_some() || has(".claude", &["claude"])) {
        put(h.join(".claude/skills/recod3r/SKILL.md"), &sk("claude"), &mut done);
        put(h.join(".claude/commands/recod3r.md"), &PROMPT.replace("AGENT", "claude"), &mut done);
    }
    if want("gemini") && (only.is_some() || has(".gemini/settings.json", &["gemini"])) {
        put(h.join(".gemini/skills/recod3r/SKILL.md"), &sk("gemini"), &mut done);
        put(h.join(".gemini/commands/recod3r.toml"), &format!("description = \"VTLO_REcod3r : skills vers scripts\"\nprompt = \"\"\"{}\"\"\"\n", PROMPT.replace("AGENT", "gemini")), &mut done);
    }
    if want("agy") && (only.is_some() || has(".gemini/antigravity-cli", &["agy", "antigravity"])) {
        put(h.join(".gemini/antigravity-cli/skills/recod3r/SKILL.md"), &sk("agy"), &mut done);
    }
    if want("codex") && (only.is_some() || has(".codex", &["codex"])) {
        put(h.join(".codex/prompts/recod3r.md"), &PROMPT.replace("AGENT", "codex"), &mut done);
    }
    let _ = Path::new("");
    done
}
