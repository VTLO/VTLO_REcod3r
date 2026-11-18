//! Analyse : lecture des skills/prompts, classification « code vs IA », économie.
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

pub const VERSION: &str = "2.0.0";
pub const MARK: &str = "RECOD3R:A_IMPLEMENTER";
const MAX_FILE: u64 = 400_000;
const STUB_TOKENS: f64 = 80.0;
const OUT_TOKENS: f64 = 60.0;
const STEP_OVERHEAD: f64 = 150.0;
const SKIP_DIRS: [&str; 8] = [".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target"];

macro_rules! rx {
    ($name:ident, $pat:expr) => {
        fn $name() -> &'static Regex {
            static R: OnceLock<Regex> = OnceLock::new();
            R.get_or_init(|| Regex::new(&$pat).unwrap())
        }
    };
}

const MECH_VERBS: &[&str] = &["pars", "extract", "extrai", "validat", "valid(?:er|ez|e)\\b", "convert", "format", "sort", "tri(?:er|ez|e)\\b", "filter", "filtr", "renam", "renomm", "count", "compt", "calculat", "calcul", "dedup", "dédoublon", "merg", "fusionn", "split", "divis", "grep", "diff", "lint", "execut", "exécut", "run\\b", "install", "compil", "deploy", "déploi", "copi", "mov(?:e|ing)\\b", "déplac", "delet", "supprim", "archiv", "upload", "download", "télécharg", "fetch", "schedul", "planifi", "normali[sz]", "sanitiz", "encod", "decod", "chmod", "mkdir", "rsync", "clone", "commit", "bump", "check\\b", "vérifi", "verif", "list(?:e|ing)?\\b", "lister", "scan", "trim", "strip", "replace", "remplac", "generat", "génér", "append", "ajout", "inject", "increment", "rotat", "compress", "unzip", "hash", "aggregat", "agrég", "group", "dump", "exit\\b", "abort", "skip", "drop", "print\\b", "emit", "affich", "ignor", "export", "import", "sync", "poll", "retry", "must output", "doit afficher"];
const MECH_NOUNS: &[&str] = &["csv", "json", "yaml", "yml", "toml", "xml", "sql", "sqlite", "sha\\d*", "md5", "regex", "regexp", "git", "npm", "pip", "docker", "make", "curl", "http", "https", "api", "webhook", "stdout", "stderr", "stdin", "glob", "path", "chemin", "fichiers?", "files?", "folders?", "dossiers?", "directory", "répertoire", "exit code", "env", "ssh", "cli", "script", "batch", "cron", "logs?", "threshold", "seuil", "template", "gabarit", "placeholder", "timestamp", "semver", "changelog", "checksum", "port", "url", "endpoint", "pdf", "xlsx", "docx", "tsv"];
const JUDG_STEMS: &[&str] = &["summar", "résum", "explain", "expliqu", "draft", "rédig", "rewrit", "réécri", "brainstorm", "creativ", "créati", "analy[sz]", "évalu", "evaluat", "recommend", "recommand", "decid", "décid", "judg", "jug(?:er|e)\\b", "critiq", "advis", "conseill", "persona", "empath", "nuanc", "interpr", "interprét", "reason", "raisonn", "understand", "compren", "comprend", "translat", "tradui", "traduc", "idea", "idée", "prioriti", "trade-?off", "strateg", "opinion", "feedback", "tutor", "teach", "enseign", "coach", "role-?play", "storytell", "narrat", "tone\\b", "voice", "ambig", "persuad", "convinc", "inspir", "imagin", "propos(?:e|er)\\b", "suggest", "sugg[eé]r", "réfléchi", "think", "consider", "weigh", "pondér", "empathi", "engag", "style\\b", "writing", "écriture", "compose", "polish", "improve", "amélior", "tailor", "adapt"];

rx!(mech_verbs, format!(r"(?i)\b(?:{})\w*", MECH_VERBS.join("|")));
rx!(mech_nouns, format!(r"(?i)\b(?:{})\b", MECH_NOUNS.join("|")));
rx!(judg_stems, format!(r"(?i)\b(?:{})\w*", JUDG_STEMS.join("|")));
rx!(judg_phr, r"(?i)(use your (?:best )?judg|as appropriate|if appropriate|selon le contexte|si pertinent|si nécessaire|best practices?|bonnes pratiques|you are an?\b|you're an?\b|act as\b|tu es un|vous êtes un|agis comme|expert in|spécialiste|senior\b.*\b(?:engineer|developer|ingénieur))".to_string());
rx!(cond_rx, r"(?i)\b(?:if|when|unless|otherwise|else|then|whenever|si|alors|sinon|lorsque|quand)\b".to_string());
rx!(fmt_rx, r"(?i)\b(exactly|exact|strict(?:ly)?|schema|schéma|must (?:be|output|return)|format\s*:|doit (?:être|retourner|afficher)|one per line|par ligne|regex|json)\b".to_string());
rx!(cmd_rx, r"^\s*(?:\$ |> |!`|!\{|(?:sudo\s+)?(?:git|npm|npx|pip3?|python3?|node|bash|sh|curl|wget|jq|rg|grep|sed|awk|find|ls|cat|cp|mv|rm|mkdir|chmod|docker|make|cargo|go|gh|adb|ssh|scp|rsync|tar|unzip|zip|pnpm|yarn|uv|ruff|eslint|prettier)\s)".to_string());
rx!(secret_rx, r#"(?i)(sk-[a-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}|(?:api[_-]?key|token|secret|password)\s*[:=]\s*['"]?[A-Za-z0-9_\-./+]{12,})"#.to_string());

const FAMILIES: &[(&str, &str)] = &[
    ("json", r"\b(json|yaml|yml|toml|schema|manifest|jsonl)\b"),
    ("tabular", r"\b(csv|tsv|excel|xlsx|spreadsheet|tableur|table|sql|sqlite|database|base de données|pivot|aggregat)"),
    ("text", r"\b(logs?|grep|regex|lines?|lignes?|dedup|output|sortie|sort|trier|filter|filtrer|parse)\b"),
    ("fs", r"\b(renam|renomm|folder|directory|dossier|répertoire|glob|move|déplac|copy|copier|archive|zip|backup)"),
    ("git", r"\b(git|commit|branch|pull request|changelog|release|semver|pipeline)\b"),
    ("http", r"\b(api|http|https|webhook|endpoint|fetch|curl|rest|oauth|request|requête)\b"),
    ("security", r"\b(audit|hash|signature|cve|crypto|secret|vulnerab|vulnérab|scan)"),
    ("windows", r"\b(powershell|windows|registry|registre|\.ps1)\b"),
    ("doc", r"\b(docx|pdf|pptx|word|office)\b"),
];

pub fn home() -> PathBuf {
    std::env::var_os("RECOD3R_HOME").map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(PathBuf::from))
        .or_else(|| std::env::var_os("USERPROFILE").map(PathBuf::from))
        .unwrap_or_else(|| PathBuf::from("."))
}
pub fn est_tokens(s: &str) -> f64 { if s.is_empty() { 0.0 } else { (s.chars().count() as f64 / 3.8).round().max(1.0) } }
pub fn redact(s: &str) -> String { secret_rx().replace_all(s, "[SECRET MASQUÉ]").into_owned() }
pub fn slug(s: &str) -> String {
    let mut o = String::new();
    for c in s.to_lowercase().chars() { if c.is_alphanumeric() && c.is_ascii() { o.push(c) } else if !o.ends_with('-') { o.push('-') } }
    let t = o.trim_matches('-').to_string();
    if t.is_empty() { "script".into() } else { t.chars().take(60).collect() }
}

// ------------------------------------------------------------------ paramètres et modèle
#[derive(Clone, Serialize, Deserialize, Debug)]
#[serde(default)]
pub struct Params {
    pub uses_per_month: f64,   // usages mensuels supposés d'un skill
    pub users: f64,            // nombre d'utilisateurs / équipes
    pub eur_per_mtok: f64,     // prix du million de tokens, en €
    pub ai_sec_per_ktok: f64,  // secondes d'IA par millier de tokens
    pub script_sec: f64,       // durée d'un script
    pub extra: Vec<String>,    // dossiers / archives supplémentaires à analyser
}
impl Default for Params {
    fn default() -> Self { Params { uses_per_month: 20.0, users: 1.0, eur_per_mtok: 2.8, ai_sec_per_ktok: 1.5, script_sec: 0.5, extra: vec![] } }
}

#[derive(Clone, Serialize, Debug)]
pub struct Asset {
    pub agent: String, pub kind: String, pub name: String, pub path: String, pub description: String,
    pub body: String, pub tokens: f64, pub has_scripts: bool, pub refs: Vec<String>,
}

#[derive(Clone, Serialize, Debug)]
pub struct Item {
    pub id: String, pub slug: String, pub agent: String, pub kind: String, pub name: String, pub path: String,
    pub tokens: f64, pub codeable: Option<f64>, pub verdict: String, pub n_code: usize, pub n_mixed: usize, pub n_ai: usize,
    pub code_steps: Vec<String>, pub ai_steps: Vec<String>, pub lang: String, pub lang_why: String,
    pub before_tokens: f64, pub after_tokens: f64, pub save_per_use: f64, pub payback_uses: Option<u32>,
    pub ai_sec_per_use: f64, pub script_sec_per_use: f64, pub convertible: bool, pub selected: bool, pub has_scripts: bool, pub secrets: bool,
    pub families: Vec<String>,
}

// ------------------------------------------------------------------ analyse d'un texte
pub fn split_units(body: &str) -> Vec<(String, bool)> {
    let mut out = vec![];
    let (mut in_fence, mut fence_n) = (false, 0);
    let bullet = Regex::new(r"^(?:[-*+]|\d+[.)]|\[[ xX]\])\s+").unwrap();
    let sent = Regex::new(r"[.!?;:]\s+").unwrap();
    for raw in body.lines() {
        let s = raw.trim();
        if s.starts_with("```") || s.starts_with("~~~") { in_fence = !in_fence; fence_n = 0; continue; }
        if s.is_empty() || (s.starts_with('#') && !in_fence) { continue; }
        if in_fence { fence_n += 1; if fence_n <= 3 { out.push((s.to_string(), true)); } continue; }
        let s = bullet.replace(s, "").to_string();
        if s.chars().count() > 220 {
            let mut last = 0;
            for m in sent.find_iter(&s) { let p = s[last..m.start() + 1].trim(); if !p.is_empty() { out.push((p.to_string(), false)); } last = m.end(); }
            let p = s[last..].trim(); if !p.is_empty() { out.push((p.to_string(), false)); }
        } else { out.push((s, false)); }
    }
    out
}

pub fn classify_unit(text: &str, in_fence: bool) -> &'static str {
    if in_fence || cmd_rx().is_match(text) { return "code"; }
    let verbs = mech_verbs().find_iter(text).count();
    let nouns = mech_nouns().find_iter(text).count();
    let j = judg_stems().find_iter(text).count() + 2 * judg_phr().find_iter(text).count();
    let (cond, fmt) = (cond_rx().is_match(text), fmt_rx().is_match(text));
    let mut m = verbs.min(3) as f64 + 0.5 * nouns.min(3) as f64;
    if verbs >= 1 || nouns >= 2 || (nouns >= 1 && cond) { if cond { m += 0.5 } if fmt { m += 0.5 } } else { m = 0.0 }
    let j = j.min(3) as f64;
    if m == 0.0 && j == 0.0 { "neutral" } else if j == 0.0 { "code" } else if m == 0.0 { "ai" } else if m >= 2.0 * j { "code" } else if m >= j { "mixed" } else { "ai" }
}

fn clip(s: &str, n: usize) -> String {
    let t = redact(s).split_whitespace().collect::<Vec<_>>().join(" ");
    if t.chars().count() <= n { t } else { format!("{}…", t.chars().take(n - 1).collect::<String>()) }
}

pub fn which(bin: &str) -> bool {
    let exts: Vec<String> = if cfg!(windows) { vec![".exe".into(), ".cmd".into(), ".bat".into(), "".into()] } else { vec!["".into()] };
    std::env::var_os("PATH").map(|p| std::env::split_paths(&p).any(|d| exts.iter().any(|e| d.join(format!("{bin}{e}")).is_file()))).unwrap_or(false)
}

fn pick_lang(text: &str) -> (String, String) {
    let t = text.to_lowercase();
    if (t.contains("powershell") || t.contains(".ps1") || t.contains("windows")) && (which("pwsh") || cfg!(windows)) {
        return ("powershell".into(), "instructions orientées Windows / PowerShell".into());
    }
    if which("python3") || which("python") { return ("python".into(), "Python présent : bibliothèque standard riche (json, csv, hashlib, http)".into()); }
    if which("node") { return ("node".into(), "Node.js présent : JSON et HTTP natifs".into()); }
    if cfg!(windows) { return ("powershell".into(), "PowerShell est présent sur tout Windows".into()); }
    ("bash".into(), "aucun autre runtime détecté : shell POSIX".into())
}

pub fn analyze(a: &Asset, p: &Params) -> Item {
    let (mut code, mut ai, mut mixed, mut neutral) = (vec![], vec![], vec![], 0usize);
    for (u, f) in split_units(&a.body) {
        match classify_unit(&u, f) { "code" => code.push((u, f)), "ai" => ai.push(u), "mixed" => mixed.push(u), _ => neutral += 1 }
    }
    let _ = neutral;
    let n_code = code.len(); let n_mixed = mixed.len(); let n_ai = ai.len();
    let n = n_code + n_mixed + n_ai;
    let codeable = if n > 0 { Some((n_code as f64 + 0.5 * n_mixed as f64) / n as f64) } else { None };
    let min_n = 3;
    let verdict = match codeable { Some(c) if n >= min_n && c >= 0.70 => "CODE", Some(c) if n >= min_n && c >= 0.40 => "HYBRID", _ => "AI" };
    let eff_code = n_code as f64 + n_mixed as f64 / 2.0;
    let c = codeable.unwrap_or(0.0);
    let before = a.tokens + STEP_OVERHEAD * eff_code;
    let after = STUB_TOKENS + OUT_TOKENS + (1.0 - c) * a.tokens;
    let save = if verdict != "AI" && a.tokens >= 40.0 { (before - after).max(0.0) } else { 0.0 };
    let (lang, why) = pick_lang(&format!("{} {}", a.body, a.description));
    let ft = format!("{} {}", a.body, a.description).to_lowercase();
    let families = FAMILIES.iter().filter(|(_, r)| Regex::new(&format!("(?i){r}")).map(|x| x.is_match(&ft)).unwrap_or(false)).map(|(k, _)| k.to_string()).collect();
    Item {
        id: format!("{}:{}:{}", a.agent, a.kind, a.name), slug: slug(&a.name), agent: a.agent.clone(), kind: a.kind.clone(), name: a.name.clone(), path: a.path.clone(),
        tokens: a.tokens, codeable: codeable.map(|x| (x * 100.0).round() / 100.0), verdict: verdict.into(), n_code, n_mixed, n_ai,
        code_steps: code.iter().filter(|(_, f)| !*f).take(6).map(|(s, _)| clip(s, 110)).collect(),
        ai_steps: ai.iter().chain(mixed.iter()).take(6).map(|s| clip(s, 110)).collect(),
        lang, lang_why: why, before_tokens: before.round(), after_tokens: after.round(), save_per_use: save.round(),
        payback_uses: if save > 0.0 { Some(((2500.0 + 2.0 * a.tokens) / save).ceil() as u32) } else { None },
        ai_sec_per_use: before / 1000.0 * p.ai_sec_per_ktok,
        script_sec_per_use: after / 1000.0 * p.ai_sec_per_ktok + p.script_sec,
        convertible: save > 0.0 && !a.has_scripts, selected: save > 0.0 && !a.has_scripts, has_scripts: a.has_scripts, secrets: secret_rx().is_match(&a.body), families,
    }
}

// ------------------------------------------------------------------ lecture des sources
pub fn parse_frontmatter(text: &str) -> (Option<String>, String, String) {
    let t = text.trim_start_matches('\u{feff}');
    if !t.starts_with("---") { return (None, String::new(), t.to_string()); }
    let rest = &t[3..];
    let Some(end) = rest.find("\n---") else { return (None, String::new(), t.to_string()) };
    let fm = &rest[..end]; let body = rest[end + 4..].trim_start_matches(|c| c == '\r' || c == '\n').to_string();
    let (mut name, mut desc) = (None, String::new());
    let lines: Vec<&str> = fm.lines().collect();
    let mut i = 0;
    while i < lines.len() {
        let l = lines[i];
        if let Some(v) = l.strip_prefix("name:") { name = Some(v.trim().trim_matches(|c| c == '"' || c == '\'').to_string()); }
        else if let Some(v) = l.strip_prefix("description:") {
            let v = v.trim();
            if v.is_empty() || v.starts_with('>') || v.starts_with('|') {
                let mut parts = vec![];
                while i + 1 < lines.len() && (lines[i + 1].starts_with(' ') || lines[i + 1].starts_with('\t')) { i += 1; parts.push(lines[i].trim()); }
                desc = parts.join(" ");
            } else { desc = v.trim_matches(|c| c == '"' || c == '\'').to_string(); }
        }
        i += 1;
    }
    (name, desc, body)
}

fn parse_toml_cmd(text: &str) -> (String, String) {
    let desc = Regex::new(r#"(?m)^description\s*=\s*"((?:[^"\\]|\\.)*)""#).unwrap().captures(text).map(|c| c[1].to_string()).unwrap_or_default();
    let body = if let Some(i) = text.find("prompt = \"\"\"") { let r = &text[i + 13..]; r[..r.find("\"\"\"").unwrap_or(r.len())].to_string() } else { String::new() };
    (desc, body)
}

fn make_asset(agent: &str, kind: &str, name: String, path: String, text: &str, has_scripts: bool, refs: Vec<String>) -> Option<Asset> {
    let (fname, desc, body) = if path.ends_with(".toml") { let (d, b) = parse_toml_cmd(text); (None, d, b) } else { parse_frontmatter(text) };
    if body.trim().is_empty() { return None; }
    let name = fname.filter(|n| !n.is_empty()).unwrap_or(name);
    Some(Asset { agent: agent.into(), kind: kind.into(), tokens: est_tokens(&body) + est_tokens(&desc), name, path, description: desc, body, has_scripts, refs })
}

fn read(p: &Path) -> Option<String> {
    let m = std::fs::metadata(p).ok()?; if m.len() > MAX_FILE { return None; }
    std::fs::read(p).ok().map(|b| String::from_utf8_lossy(&b).into_owned())
}

fn skill_dir_info(md: &Path) -> (bool, Vec<String>) {
    let d = md.parent().unwrap_or(Path::new("."));
    let has_scripts = d.join("scripts").is_dir() && std::fs::read_dir(d.join("scripts")).map(|r| r.count() > 0).unwrap_or(false);
    let mut refs = vec![];
    for sub in ["references", "resources", "assets", "templates", "examples"] {
        if let Ok(rd) = std::fs::read_dir(d.join(sub)) { for e in rd.flatten() { refs.push(format!("{sub}/{}", e.file_name().to_string_lossy())); } }
    }
    refs.sort(); refs.truncate(60);
    (has_scripts, refs)
}

fn sources(cwd: &Path) -> Vec<(&'static str, &'static str, PathBuf, &'static [&'static str])> {
    let h = home();
    vec![
        ("claude", "skill", h.join(".claude/skills"), &["*/SKILL.md"]), ("claude", "command", h.join(".claude/commands"), &["**/*.md"]),
        ("claude", "agent", h.join(".claude/agents"), &["**/*.md"]), ("claude", "skill", h.join(".claude/plugins"), &["**/skills/*/SKILL.md"]),
        ("claude", "command", h.join(".claude/plugins"), &["**/commands/*.md"]), ("claude", "skill", cwd.join(".claude/skills"), &["*/SKILL.md"]),
        ("claude", "command", cwd.join(".claude/commands"), &["**/*.md"]),
        ("gemini", "command", h.join(".gemini/commands"), &["**/*.toml"]), ("gemini", "skill", h.join(".gemini/skills"), &["*/SKILL.md"]),
        ("gemini", "skill", h.join(".gemini/extensions"), &["*/skills/*/SKILL.md"]), ("gemini", "command", cwd.join(".gemini/commands"), &["**/*.toml"]),
        ("agy", "skill", h.join(".gemini/antigravity-cli/skills"), &["*/SKILL.md"]), ("agy", "skill", h.join(".gemini/antigravity-cli/plugins"), &["*/skills/*/SKILL.md"]),
        ("agy", "skill", h.join(".gemini/config/skills"), &["*/SKILL.md"]), ("agy", "skill", h.join(".gemini/skills"), &["*/SKILL.md"]), ("agy", "skill", cwd.join(".agents/skills"), &["*/SKILL.md"]),
        ("agy", "skill", h.join(".gemini/antigravity/skills"), &["*/SKILL.md"]), ("agy", "workflow", h.join(".gemini/antigravity/global_workflows"), &["*.md"]),
        ("agy", "skill", cwd.join(".agent/skills"), &["*/SKILL.md"]), ("agy", "workflow", cwd.join(".agent/workflows"), &["*.md"]),
        ("codex", "prompt", h.join(".codex/prompts"), &["*.md"]), ("codex", "skill", h.join(".codex/skills"), &["*/SKILL.md"]),
        ("shared", "skill", h.join(".agents/skills"), &["*/SKILL.md"]),
    ]
}

fn from_file(agent: &str, kind: &str, base: &Path, f: &Path, out: &mut Vec<Asset>, seen: &mut HashSet<PathBuf>) {
    let key = f.canonicalize().unwrap_or_else(|_| f.to_path_buf());
    if !seen.insert(key) { return; }
    let Some(text) = read(f) else { return };
    let is_skill = f.file_name().map(|n| n == "SKILL.md").unwrap_or(false);
    let (name, hs, refs) = if is_skill {
        let (hs, refs) = skill_dir_info(f);
        (f.parent().and_then(|p| p.file_name()).map(|s| s.to_string_lossy().into_owned()).unwrap_or_default(), hs, refs)
    } else {
        (f.strip_prefix(base).unwrap_or(f).with_extension("").to_string_lossy().replace(['/', '\\'], ":"), false, vec![])
    };
    if let Some(a) = make_asset(agent, if is_skill { "skill" } else { kind }, name, f.to_string_lossy().into_owned(), &text, hs, refs) { out.push(a); }
}

fn walk(dir: &Path, depth: usize, out: &mut Vec<PathBuf>) {
    if depth > 6 { return; }
    let Ok(rd) = std::fs::read_dir(dir) else { return };
    for e in rd.flatten() {
        let p = e.path(); let n = e.file_name().to_string_lossy().into_owned();
        if p.is_dir() { if !SKIP_DIRS.contains(&n.as_str()) { walk(&p, depth + 1, out); } } else { out.push(p); }
    }
}

fn kind_from_path(p: &Path) -> Option<&'static str> {
    let comps: Vec<String> = p.components().map(|c| c.as_os_str().to_string_lossy().to_lowercase()).collect();
    for (k, v) in [("commands", "command"), ("prompts", "prompt"), ("workflows", "workflow"), ("agents", "agent")] { if comps.iter().any(|c| c == k) { return Some(v); } }
    None
}

fn from_extra(spec: &str, out: &mut Vec<Asset>, seen: &mut HashSet<PathBuf>) {
    let p = PathBuf::from(spec.trim());
    if p.extension().map(|e| e.eq_ignore_ascii_case("zip")).unwrap_or(false) && p.is_file() {
        let Ok(f) = std::fs::File::open(&p) else { return };
        let Ok(mut z) = zip::ZipArchive::new(f) else { return };
        let names: Vec<String> = (0..z.len()).filter_map(|i| z.by_index(i).ok().map(|e| e.name().to_string())).collect();
        for n in &names {
            if !n.ends_with("SKILL.md") { continue; }
            let dir = n.trim_end_matches("SKILL.md");
            let mut txt = String::new();
            if let Ok(mut e) = z.by_name(n) { use std::io::Read; let mut b = vec![]; if e.read_to_end(&mut b).is_ok() { txt = String::from_utf8_lossy(&b).into_owned(); } }
            let mut refs: Vec<String> = names.iter().filter(|x| x.starts_with(dir) && !x.ends_with('/') && !x.ends_with("SKILL.md")).map(|x| x[dir.len()..].to_string()).collect();
            refs.sort(); refs.truncate(60);
            let name = dir.trim_end_matches('/').rsplit('/').next().unwrap_or("skill").to_string();
            if let Some(a) = make_asset("extra", "skill", name, format!("{}!{}", p.display(), n), &txt, false, refs) { out.push(a); }
        }
        return;
    }
    // fichier choisi à la main : toujours accepté comme skill (md, mdc, txt, toml)
    if p.is_file() {
        let ext = p.extension().map(|e| e.to_string_lossy().to_lowercase()).unwrap_or_default();
        if matches!(ext.as_str(), "md" | "mdc" | "txt" | "toml" | "markdown") { from_file("extra", "skill", p.parent().unwrap_or(Path::new(".")), &p, out, seen); }
        return;
    }
    let mut files = vec![];
    walk(&p, 0, &mut files);
    for f in files {
        let n = f.file_name().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
        let attached = f.components().any(|c| matches!(c.as_os_str().to_string_lossy().as_ref(), "references" | "resources" | "assets" | "templates" | "examples"));
        if attached { continue; }
        if n == "SKILL.md" { from_file("extra", "skill", &p, &f, out, seen); }
        else if let Some(k) = kind_from_path(&f) { if n.ends_with(".md") || n.ends_with(".toml") { from_file("extra", k, &p, &f, out, seen); } }
    }
}

pub fn collect(cwd: &Path, extra: &[String]) -> Vec<Asset> {
    let (mut out, mut seen) = (vec![], HashSet::new());
    for (agent, kind, base, pats) in sources(cwd) {
        for pat in pats {
            let full = format!("{}/{}", glob::Pattern::escape(&base.to_string_lossy()), pat);
            if let Ok(paths) = glob::glob(&full) { for f in paths.flatten() { from_file(agent, kind, &base, &f, &mut out, &mut seen); } }
        }
    }
    for e in extra.iter().filter(|e| !e.trim().is_empty()) { from_extra(e, &mut out, &mut seen); }
    out
}

pub fn analyze_all(assets: &[Asset], p: &Params) -> Vec<Item> {
    let mut used: HashSet<String> = HashSet::new();
    let mut items: Vec<Item> = assets.iter().map(|a| analyze(a, p)).collect();
    for it in items.iter_mut() {
        let base = it.slug.clone(); let mut s = base.clone(); let mut n = 2;
        while !used.insert(s.clone()) { s = format!("{base}-{n}"); n += 1; }
        it.slug = s;
    }
    items.sort_by(|a, b| b.save_per_use.partial_cmp(&a.save_per_use).unwrap_or(std::cmp::Ordering::Equal));
    items
}
