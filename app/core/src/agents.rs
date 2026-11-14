//! Détection des CLI d'IA et lancement non interactif (une seule tâche d'écriture).
use crate::engine::{home, which};
use serde::Serialize;
use std::path::Path;
use std::process::{Child, Command, Stdio};

#[derive(Clone, Serialize, Debug)]
pub struct AgentInfo { pub key: String, pub label: String, pub installed: bool, pub headless: bool }

const AGENTS: &[(&str, &str, &str, &str, bool)] = &[
    ("claude", "Claude Code", "claude", ".claude", true),
    ("gemini", "Gemini CLI", "gemini", ".gemini", true),
    ("agy", "agy (Antigravity)", "agy", ".gemini/antigravity", false),
    ("codex", "Codex CLI", "codex", ".codex", true),
];

pub fn detect() -> Vec<AgentInfo> {
    AGENTS.iter().map(|(k, l, bin, dir, hl)| AgentInfo {
        key: k.to_string(), label: l.to_string(), installed: which(bin) || home().join(dir).is_dir(), headless: *hl && which(bin),
    }).filter(|a| a.installed).collect()
}

/// Premier CLI capable de travailler sans interface, ou celui demandé. RECOD3R_AGENT_CMD force une commande.
pub fn pilotable(prefer: Option<&str>) -> Option<String> {
    if std::env::var("RECOD3R_AGENT_CMD").map(|v| !v.trim().is_empty()).unwrap_or(false) { return Some(prefer.unwrap_or("custom").to_string()); }
    detect().into_iter().filter(|a| a.headless && prefer.map(|p| p == a.key).unwrap_or(true)).map(|a| a.key).next()
}

fn shell(cmdline: &str) -> Command {
    if cfg!(windows) { let mut c = Command::new("cmd"); c.args(["/C", cmdline]); c } else { let mut c = Command::new("sh"); c.args(["-c", cmdline]); c }
}

/// Lance l'agent dans `cwd` avec `prompt` (texte) ; `prompt_file` sert à RECOD3R_AGENT_CMD ({prompt_file}).
pub fn spawn(agent: &str, prompt: &str, prompt_file: &Path, cwd: &Path) -> std::io::Result<Child> {
    let mut cmd = if let Ok(o) = std::env::var("RECOD3R_AGENT_CMD") {
        shell(&o.replace("{prompt_file}", &prompt_file.to_string_lossy()))
    } else {
        let mut c = Command::new(agent);
        match agent {
            "claude" => { c.args(["-p", prompt, "--permission-mode", "acceptEdits", "--allowedTools", "Read,Write,Edit"]); }
            "gemini" => { c.args(["-p", prompt, "--yolo"]); }
            "codex" => { c.args(["exec", prompt]); }
            _ => return Err(std::io::Error::new(std::io::ErrorKind::Other, "agent non pilotable")),
        }
        c
    };
    cmd.current_dir(cwd).stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn()
}
