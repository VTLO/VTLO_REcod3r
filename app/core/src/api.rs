//! API unique (HTTP local, Tauri, CLI) : état partagé + routes.
use crate::agents;
use crate::engine::{self, Asset, Item, Params};
use crate::forge::{self, Forged};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

#[derive(Default)]
struct Inner {
    phase: String, params: Params, assets: Vec<Asset>, items: Vec<Item>,
    pct: u32, written: usize, total: usize, started: Option<Instant>, finished_secs: f64, message: String,
    item_done: HashMap<String, bool>, order: Vec<(String, String)>, out: Option<String>, todo: Vec<String>, done: Vec<String>,
    agent_used: Option<String>, err: Option<String>, manual: bool, orch: Option<String>,
}

#[derive(Clone)]
pub struct App { st: Arc<Mutex<Inner>> }

impl Default for App { fn default() -> Self { Self::new() } }

fn totals(items: &[Item], p: &Params) -> Value {
    let sel: Vec<&Item> = items.iter().filter(|i| i.selected).collect();
    let tok: f64 = sel.iter().map(|i| i.save_per_use * p.uses_per_month * p.users).sum();
    let sec: f64 = sel.iter().map(|i| (i.ai_sec_per_use - i.script_sec_per_use).max(0.0) * p.uses_per_month * p.users).sum();
    let before: f64 = sel.iter().map(|i| i.before_tokens * p.uses_per_month * p.users).sum();
    json!({"scripts": sel.len(), "assets": items.len(), "tokens_month": tok.round(), "eur_month": tok / 1e6 * p.eur_per_mtok, "hours_month": sec / 3600.0,
           "before_month": before.round(), "pct": if before > 0.0 { tok / before * 100.0 } else { 0.0 }, "instruction_tokens": items.iter().map(|i| i.tokens).sum::<f64>().round()})
}

pub fn open_path(target: &str) {
    let mut c = if cfg!(target_os = "macos") { let mut c = std::process::Command::new("open"); c.arg(target); c }
        else if cfg!(windows) { let mut c = std::process::Command::new("explorer"); c.arg(target); c }
        else if engine::which("termux-open") { let mut c = std::process::Command::new("termux-open"); c.arg(target); c }
        else { let mut c = std::process::Command::new("xdg-open"); c.arg(target); c };
    let _ = c.stdin(std::process::Stdio::null()).stdout(std::process::Stdio::null()).stderr(std::process::Stdio::null()).spawn();
}

impl App {
    pub fn new() -> Self { let mut i = Inner::default(); i.phase = "idle".into(); App { st: Arc::new(Mutex::new(i)) } }

    fn state(&self) -> Value {
        let g = self.st.lock().unwrap();
        let elapsed = match g.started { Some(t) if g.phase == "converting" => t.elapsed().as_secs_f64(), Some(_) => g.finished_secs, None => 0.0 };
        json!({
            "version": engine::VERSION, "os": std::env::consts::OS, "phase": g.phase, "params": g.params, "agents": agents::detect(),
            "items": g.items, "totals": totals(&g.items, &g.params),
            "orchestration": g.orch, "progress": {"pct": g.pct, "written": g.written, "total": g.total, "elapsed": elapsed, "message": g.message, "agent": g.agent_used,
                         "items": g.items.iter().filter(|i| i.selected).map(|i| json!({"slug": i.slug, "name": i.name, "done": g.item_done.get(&i.slug).copied().unwrap_or(false)})).collect::<Vec<_>>()},
            "out": g.out, "done": g.done, "todo": g.todo, "manual": g.manual, "error": g.err,
        })
    }

    fn do_scan(&self, mut p: Params, force: &[String]) -> Value {
        p.extra.retain(|e| !e.trim().is_empty());
        let cwd = std::env::current_dir().unwrap_or_default();
        let assets = engine::collect(&cwd, &p.extra);
        let mut items = engine::analyze_all(&assets, &p);
        { let mut g = self.st.lock().unwrap();
          let prev: HashMap<String, bool> = g.items.iter().map(|i| (i.id.clone(), i.selected)).collect();
          for i in items.iter_mut() { if let Some(s) = prev.get(&i.id) { i.selected = *s; } else if i.agent == "extra" && force.iter().any(|f| f == &i.path) { i.selected = true; } }
          g.params = p; g.assets = assets; g.items = items; g.phase = "scanned".into(); g.err = None; g.pct = 0; g.item_done.clear(); g.out = None; g.done.clear(); g.todo.clear(); g.orch = None; }
        self.state()
    }

    pub fn handle(&self, route: &str, body: &Value) -> Value {
        match route {
            "state" => self.state(),
            "scan" => {
                let p: Params = body.get("params").and_then(|v| serde_json::from_value(v.clone()).ok()).unwrap_or_default();
                self.do_scan(p, &[])
            }
            // l'utilisateur ajoute lui-même des skills : chemins (fichier, dossier, .zip)
            "ajouter" => {
                let mut p = self.st.lock().unwrap().params.clone();
                let add: Vec<String> = body.get("paths").and_then(|v| v.as_array()).map(|a| a.iter().filter_map(|x| x.as_str().map(|s| s.trim().trim_matches('"').to_string())).filter(|s| !s.is_empty()).collect()).unwrap_or_default();
                for a in &add { if !p.extra.contains(a) { p.extra.push(a.clone()); } }
                self.do_scan(p, &add)
            }
            // téléversement depuis l'interface web : un skill collé ou un fichier lu par le navigateur
            "televerser" => {
                let name = body.get("name").and_then(|v| v.as_str()).unwrap_or("skill");
                let text = body.get("text").and_then(|v| v.as_str()).unwrap_or("");
                if text.trim().is_empty() { return json!({"error": "contenu vide"}); }
                let safe: String = name.chars().map(|c| if c.is_alphanumeric() || c == '-' || c == '_' || c == '.' { c } else { '-' }).collect();
                let safe = if safe.contains('.') { safe } else { format!("{safe}.md") };
                let dir = forge::state_dir().join("ajouts");
                if std::fs::create_dir_all(&dir).is_err() { return json!({"error": "dossier d'ajout inaccessible"}); }
                let f = dir.join(safe);
                if let Err(e) = std::fs::write(&f, text) { return json!({"error": e.to_string()}); }
                let mut p = self.st.lock().unwrap().params.clone();
                let s = f.to_string_lossy().into_owned();
                if !p.extra.contains(&s) { p.extra.push(s.clone()); }
                self.do_scan(p, &[s])
            }
            // sélection manuelle : {id,on} · {all:"auto"|"tous"|"aucun"} · {only:[slug…]}
            "selection" => {
                { let mut g = self.st.lock().unwrap();
                  if let Some(m) = body.get("all").and_then(|v| v.as_str()) { for i in g.items.iter_mut() { i.selected = match m { "tous" => true, "aucun" => false, _ => i.convertible }; } }
                  if let Some(o) = body.get("only").and_then(|v| v.as_array()) { let k: Vec<String> = o.iter().filter_map(|x| x.as_str().map(String::from)).collect(); for i in g.items.iter_mut() { i.selected = k.iter().any(|s| s == &i.slug || s == &i.name); } }
                  if let (Some(id), Some(on)) = (body.get("id").and_then(|v| v.as_str()), body.get("on").and_then(|v| v.as_bool())) { if let Some(i) = g.items.iter_mut().find(|i| i.id == id) { i.selected = on; } } }
                self.state()
            }
            "convert" => {
                { let mut g = self.st.lock().unwrap();
                  if g.phase == "converting" { drop(g); return self.state(); }
                  if g.phase != "scanned" { return json!({"error": "aucune analyse : lancez d'abord le scan"}); }
                  if !g.items.iter().any(|i| i.selected) { return json!({"error": "aucun skill sélectionné : cochez au moins un élément"}); }
                  if let Some(p) = body.get("params").and_then(|v| serde_json::from_value::<Params>(v.clone()).ok()) { let extra = g.params.extra.clone(); g.params = Params { extra, ..p }; }
                  g.phase = "converting".into(); g.orch = None; g.pct = 0; g.written = 0; g.started = Some(Instant::now()); g.err = None; g.message = "Préparation…".into(); }
                let (st, pref) = (self.st.clone(), body.get("agent").and_then(|v| v.as_str()).map(String::from));
                std::thread::spawn(move || run_conversion(st, pref));
                self.state()
            }
            "ignore" => { self.st.lock().unwrap().phase = "ignored".into(); self.state() }
            "reset" => { let mut g = self.st.lock().unwrap(); g.phase = "idle".into(); drop(g); self.state() }
            "orchestrer" => {
                let (out, order) = { let g = self.st.lock().unwrap(); (forge::out_dir(), g.order.clone()) };
                if order.is_empty() { return json!({"error": "aucun script livré : lancez d'abord une conversion"}); }
                match forge::orchestrer(&out, &order) { Ok(_) => { self.st.lock().unwrap().orch = Some(forge::tilde(&out)); json!({"ok": true, "run": if cfg!(windows) { "powershell -File orchestrer.ps1" } else { "sh orchestrer.sh" }, "dir": forge::tilde(&out), "files": ["orchestrer.sh", "orchestrer.ps1", "orchestrer.txt"]}) }, Err(e) => json!({"error": e.to_string()}) }
            }
            "open" => { let out = forge::out_dir(); open_path(&out.to_string_lossy()); json!({"ok": true}) }
            _ => json!({"error": format!("route inconnue : {route}")}),
        }
    }
}

fn set(st: &Arc<Mutex<Inner>>, f: impl FnOnce(&mut Inner)) { f(&mut st.lock().unwrap()); }

fn run_conversion(st: Arc<Mutex<Inner>>, pref: Option<String>) {
    let (items, assets, params) = { let g = st.lock().unwrap(); (g.items.clone(), g.assets.clone(), g.params.clone()) };
    let secs = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let run = forge::state_dir().join("runs").join(format!("run-{secs}"));
    let mut forged: Vec<Forged> = vec![];
    for it in items.iter().filter(|i| i.selected) {
        let Some(a) = assets.iter().find(|a| a.path == it.path && a.name == it.name) else { continue };
        match forge::scaffold(&run, a, it) { Ok(f) => forged.push(f), Err(e) => { set(&st, |g| { g.err = Some(format!("{}: {e}", it.slug)); }); } }
    }
    let total = forged.len();
    set(&st, |g| { g.total = total; g.message = format!("{total} script(s) à rédiger"); });
    let prompt = forge::prompt(&run, &forged);
    let pfile = run.join("PROMPT.md");
    let _ = std::fs::write(&pfile, &prompt);
    let agent = agents::pilotable(pref.as_deref());
    set(&st, |g| g.agent_used = agent.clone());
    let mut manual = false;
    match agent {
        None => { manual = true; set(&st, |g| g.message = "Aucun CLI d'IA pilotable détecté : squelettes et briefs prêts à confier à votre IA".into()); }
        Some(ag) => match agents::spawn(&ag, &pfile, &run) {
            Err(e) => { manual = true; set(&st, |g| { g.err = Some(format!("lancement de {ag} impossible : {e}")); }); }
            Ok(mut child) => {
                set(&st, |g| g.message = "L'IA rédige les scripts en une seule tâche…".into());
                let timeout = std::env::var("RECOD3R_TIMEOUT").ok().and_then(|v| v.parse::<u64>().ok()).unwrap_or(3600);
                let t0 = Instant::now();
                let mut exit_ok = true;
                loop {
                    std::thread::sleep(Duration::from_millis(400));
                    let n = forged.iter().filter(|f| forge::written(&f.script)).count();
                    set(&st, |g| { g.written = n; g.pct = if total == 0 { 0 } else { ((n * 100 / total) as u32).min(99) };
                        for f in &forged { g.item_done.insert(f.slug.clone(), forge::written(&f.script)); } });
                    match child.try_wait() {
                        Ok(Some(status)) => { exit_ok = status.success(); break }
                        Err(_) => break,
                        Ok(None) => if t0.elapsed().as_secs() > timeout { let _ = child.kill(); set(&st, |g| g.err = Some("délai dépassé : l'IA a été arrêtée".into())); break; }
                    }
                }
                let n = forged.iter().filter(|f| forge::written(&f.script)).count();
                if (!exit_ok || n < total) && st.lock().unwrap().err.is_none() {
                    let hint = if ag == "agy" { " Pour agy : lancez `agy` une fois en interactif pour vous connecter, puis réessayez." } else { "" };
                    let tail = agents::log_tail(&run, 240);
                    set(&st, |g| g.err = Some(format!("l'IA ({ag}) n'a écrit que {n} script(s) sur {total}.{hint}{}", if tail.is_empty() { String::new() } else { format!(" Journal : {tail}") })));
                }
            }
        },
    }
    let out = forge::out_dir();
    let res = forge::deliver(&out, &forged, &params);
    if manual { let _ = std::fs::create_dir_all(out.join("a_completer")); let _ = std::fs::write(out.join("a_completer/PROMPT.md"), &prompt); }
    set(&st, |g| {
        match res {
            Ok(d) => {
                g.written = d.done.len(); g.done = d.done.clone(); g.todo = d.todo.clone();
                g.order = forged.iter().filter(|f| d.done.contains(&f.slug)).map(|f| (f.slug.clone(), f.ext.to_string())).collect();
                g.out = Some(forge::tilde(&d.out));
                for f in &forged { g.item_done.insert(f.slug.clone(), d.done.contains(&f.slug)); }
            }
            Err(e) => g.err = Some(format!("livraison : {e}")),
        }
        g.manual = manual; g.pct = 100; g.phase = "done".into();
        g.finished_secs = g.started.map(|t| t.elapsed().as_secs_f64()).unwrap_or(0.0);
        g.message = if manual { "Squelettes prêts : confiez a_completer/PROMPT.md à votre IA".into() } else { "Livrables prêts".into() };
    });
}
