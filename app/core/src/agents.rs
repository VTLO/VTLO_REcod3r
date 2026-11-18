//! Détection des CLI d'IA et lancement non interactif (une seule tâche d'écriture).
//! Compatibles : Claude Code, Gemini CLI, Antigravity CLI (agy), Codex CLI — ou toute commande via RECOD3R_AGENT_CMD.
use crate::engine::{home, which};
use serde::Serialize;
use std::fs::File;
use std::path::Path;
use std::process::{Child, Command, Stdio};

#[derive(Clone, Serialize, Debug)]
pub struct AgentInfo { pub key: String, pub label: String, pub installed: bool, pub headless: bool, pub note: String }

/// (clé, libellé, binaires possibles, dossier de config, pilotable sans interface)
const AGENTS: &[(&str, &str, &[&str], &str, bool)] = &[
    ("claude", "Claude Code", &["claude"], ".claude", true),
    ("gemini", "Gemini CLI", &["gemini"], ".gemini/settings.json", true),
    ("agy", "Antigravity CLI (agy)", &["agy", "antigravity"], ".gemini/antigravity-cli", true),
    ("codex", "Codex CLI", &["codex"], ".codex", true),
];

/// Binaire réel d'un agent (agy peut s'appeler `antigravity` ; ANTIGRAVITY_CLI_ALIAS le force).
pub fn bin_of(key: &str) -> Option<String> {
    if key == "agy" { if let Ok(a) = std::env::var("ANTIGRAVITY_CLI_ALIAS") { if !a.trim().is_empty() && which(a.trim()) { return Some(a.trim().to_string()); } } }
    AGENTS.iter().find(|a| a.0 == key).and_then(|a| a.2.iter().find(|b| which(b)).map(|b| b.to_string()))
}

pub fn detect() -> Vec<AgentInfo> {
    AGENTS.iter().filter_map(|(k, l, _, dir, hl)| {
        let bin = bin_of(k);
        let installed = bin.is_some() || home().join(dir).exists();
        if !installed { return None; }
        let note = if *k == "agy" { "lancé avec --dangerously-skip-permissions, uniquement dans le dossier de travail de la conversion".to_string() } else { String::new() };
        Some(AgentInfo { key: k.to_string(), label: l.to_string(), installed, headless: *hl && bin.is_some(), note })
    }).collect()
}

/// Premier CLI capable de travailler sans interface, ou celui demandé. RECOD3R_AGENT_CMD force une commande.
pub fn pilotable(prefer: Option<&str>) -> Option<String> {
    if std::env::var("RECOD3R_AGENT_CMD").map(|v| !v.trim().is_empty()).unwrap_or(false) { return Some(prefer.unwrap_or("custom").to_string()); }
    detect().into_iter().filter(|a| a.headless && prefer.map(|p| p == a.key).unwrap_or(true)).map(|a| a.key).next()
}

fn shell(cmdline: &str) -> Command {
    if cfg!(windows) { let mut c = Command::new("cmd"); c.args(["/C", cmdline]); c } else { let mut c = Command::new("sh"); c.args(["-c", cmdline]); c }
}

/// Consigne courte passée en argument : le détail est dans PROMPT.md (pas de limite de longueur de ligne de commande).
pub fn short_prompt(prompt_file: &Path) -> String {
    format!("Lis le fichier {} puis exécute exactement ses instructions (écris les scripts demandés, rien d'autre).", prompt_file.display())
}

/// Lance l'agent dans `cwd`. La sortie va dans `agent.log` (diagnostic). `RECOD3R_AGENT_CMD` accepte {prompt_file}.
pub fn spawn(agent: &str, prompt_file: &Path, cwd: &Path) -> std::io::Result<Child> {
    let log = File::create(cwd.join("agent.log"))?;
    let err = log.try_clone()?;
    let prompt = short_prompt(prompt_file);
    let mut cmd = if let Ok(o) = std::env::var("RECOD3R_AGENT_CMD") {
        shell(&o.replace("{prompt_file}", &prompt_file.to_string_lossy()))
    } else {
        let bin = bin_of(agent).ok_or_else(|| std::io::Error::new(std::io::ErrorKind::NotFound, "CLI introuvable"))?;
        let mut c = Command::new(bin);
        match agent {
            "claude" => { c.args(["-p", &prompt, "--permission-mode", "acceptEdits", "--allowedTools", "Read,Write,Edit"]); }
            "gemini" => { c.args(["-p", &prompt, "--yolo"]); }
            // agy : sans cet indicateur, les approbations d'outils sont refusées en silence (code 0, rien d'écrit) ;
            // le prompt doit venir en dernier car -p consomme l'argument suivant.
            "agy" => {
                c.arg("--dangerously-skip-permissions");
                if std::env::var("RECOD3R_AGY_SANDBOX").map(|v| v == "1").unwrap_or(false) { c.arg("--sandbox"); }
                c.args(["-p", &prompt]);
            }
            "codex" => { c.args(["exec", &prompt]); }
            _ => return Err(std::io::Error::new(std::io::ErrorKind::Other, "agent non pilotable")),
        }
        c
    };
    cmd.current_dir(cwd).stdin(Stdio::null()).stdout(Stdio::from(log)).stderr(Stdio::from(err)).spawn()
}

/// Fin du journal de l'agent (diagnostic lisible).
pub fn log_tail(cwd: &Path, n: usize) -> String {
    let t = std::fs::read_to_string(cwd.join("agent.log")).unwrap_or_default();
    let t = crate::engine::redact(t.trim());
    let c: Vec<char> = t.chars().collect();
    c[c.len().saturating_sub(n)..].iter().collect()
}
