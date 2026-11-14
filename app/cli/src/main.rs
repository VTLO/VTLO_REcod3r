//! VTLO_REcod3r — application autonome : interface visuelle locale (127.0.0.1) + commandes terminal.
use recod3r_core::{api::{open_path, App}, engine};
use serde_json::{json, Value};
use std::collections::hash_map::RandomState;
use std::hash::{BuildHasher, Hasher};
use tiny_http::{Header, Method, Response, Server};

const UI: &str = include_str!("../../ui/index.html");
const GLYPHS: [[&str; 5]; 11] = [
    ["███", "█ █", "█ █", "█ █", "███"], ["  █", "  █", "  █", "  █", "  █"], ["███", "  █", "███", "█  ", "███"], ["███", "  █", "███", "  █", "███"],
    ["█ █", "█ █", "███", "  █", "  █"], ["███", "█  ", "███", "  █", "███"], ["███", "█  ", "███", "█ █", "███"], ["███", "  █", "  █", "  █", "  █"],
    ["███", "█ █", "███", "█ █", "███"], ["███", "█ █", "███", "  █", "███"], ["█ █", "  █", " █ ", "█  ", "█ █"],
];

fn big(n: u32) -> String {
    let s = format!("{n}%");
    let idx: Vec<usize> = s.chars().map(|c| c.to_digit(10).map(|d| d as usize).unwrap_or(10)).collect();
    (0..5).map(|r| idx.iter().map(|&i| GLYPHS[i][r]).collect::<Vec<_>>().join("  ")).collect::<Vec<_>>().join("\n")
}

fn token() -> String { let mut h = RandomState::new().build_hasher(); h.write_u128(std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0)); h.write_u32(std::process::id()); format!("{:016x}", h.finish()) }

fn arg_val(a: &[String], k: &str) -> Option<String> { a.iter().position(|x| x == k).and_then(|i| a.get(i + 1).cloned()) }

fn params_from(a: &[String]) -> Value {
    let mut p = json!({});
    let dirs: Vec<String> = a.iter().enumerate().filter(|(i, x)| *x == "--dir" && a.get(i + 1).is_some()).map(|(i, _)| a[i + 1].clone()).collect();
    p["extra"] = json!(dirs);
    for (k, f) in [("users", "--users"), ("eur_per_mtok", "--price"), ("uses_per_month", "--uses")] { if let Some(v) = arg_val(a, f).and_then(|v| v.parse::<f64>().ok()) { p[k] = json!(v); } }
    json!({"params": p})
}

fn fmt_n(x: f64) -> String { let s = format!("{:.0}", x); let mut o = String::new(); for (i, c) in s.chars().rev().enumerate() { if i > 0 && i % 3 == 0 { o.push(' '); } o.push(c); } o.chars().rev().collect() }

fn print_report(st: &Value) {
    let t = &st["totals"];
    println!("\n  VTLO_REcod3r {} — rapport", st["version"].as_str().unwrap_or(""));
    println!("  {} éléments analysés · {} convertibles en script", t["assets"], t["scripts"]);
    println!("  ≈ {} tokens/mois (−{:.0} %) · ≈ {:.2} €/mois · ≈ {:.1} h/mois\n", fmt_n(t["tokens_month"].as_f64().unwrap_or(0.0)), t["pct"].as_f64().unwrap_or(0.0), t["eur_month"].as_f64().unwrap_or(0.0), t["hours_month"].as_f64().unwrap_or(0.0));
    for i in st["items"].as_array().unwrap().iter().filter(|i| i["convertible"] == true).take(12) {
        println!("  {:<44} {:>7} tok/usage  [{}]", i["name"].as_str().unwrap_or("").chars().take(44).collect::<String>(), fmt_n(i["save_per_use"].as_f64().unwrap_or(0.0)), i["lang"].as_str().unwrap_or(""));
    }
}

fn convert_terminal(app: &App) -> i32 {
    app.handle("convert", &json!({}));
    let mut last = 1000u32;
    loop {
        std::thread::sleep(std::time::Duration::from_millis(300));
        let st = app.handle("state", &json!({}));
        let pct = st["progress"]["pct"].as_u64().unwrap_or(0) as u32;
        if pct != last { print!("\x1b[2J\x1b[H\n{}\n\n  {}\n", big(pct), st["progress"]["message"].as_str().unwrap_or("")); last = pct; }
        if st["phase"] == "done" {
            println!("\n  IA sur le banc de touche !! Place au c0d3 pour la frappe décisive !!!!\n");
            println!("  Dossier créé : {}", st["out"].as_str().unwrap_or("?"));
            println!("  {} script(s) prêt(s), {} à compléter", st["done"].as_array().map(|a| a.len()).unwrap_or(0), st["todo"].as_array().map(|a| a.len()).unwrap_or(0));
            if let Some(e) = st["error"].as_str() { eprintln!("  ! {e}"); }
            println!("  Option : recod3r orchestrer");
            return 0;
        }
    }
}

fn serve(app: App, port: u16, open: bool) {
    let server = Server::http(format!("127.0.0.1:{port}")).expect("port indisponible");
    let port = server.server_addr().to_ip().map(|a| a.port()).unwrap_or(port);
    let tok = token();
    let url = format!("http://127.0.0.1:{port}/");
    println!("VTLO_REcod3r {} — interface : {url}  (Ctrl+C pour quitter)", engine::VERSION);
    if open { open_path(&url); }
    let html = UI.replace("__TOKEN__", &tok);
    for mut rq in server.incoming_requests() {
        let path = rq.url().split('?').next().unwrap_or("/").to_string();
        let ct = |v: &str| Header::from_bytes("Content-Type", v).unwrap();
        let resp = if rq.method() == &Method::Get && path == "/" {
            Response::from_string(html.clone()).with_header(ct("text/html; charset=utf-8")).with_header(Header::from_bytes("Cache-Control", "no-store").unwrap())
        } else if rq.method() == &Method::Post && path.starts_with("/api/") {
            let ok = rq.headers().iter().any(|h| h.field.equiv("X-Token") && h.value.as_str() == tok);
            if !ok { Response::from_string("{\"error\":\"jeton invalide\"}").with_status_code(403).with_header(ct("application/json")) } else {
                let mut b = String::new(); let _ = rq.as_reader().read_to_string(&mut b);
                let v: Value = serde_json::from_str(&b).unwrap_or(json!({}));
                Response::from_string(app.handle(&path[5..], &v).to_string()).with_header(ct("application/json"))
            }
        } else { Response::from_string("introuvable").with_status_code(404) };
        let _ = rq.respond(resp);
    }
}


fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if let Some(o) = arg_val(&args, "--out") { std::env::set_var("RECOD3R_OUT", o); }
    let cmd = args.first().filter(|a| !a.starts_with("--")).cloned().unwrap_or_else(|| "app".into());
    let app = App::new();
    match cmd.as_str() {
        "scan" => { let st = app.handle("scan", &params_from(&args)); if args.iter().any(|a| a == "--json") { println!("{}", serde_json::to_string_pretty(&st).unwrap()); } else { print_report(&st); } }
        "convert" => { app.handle("scan", &params_from(&args)); if !args.iter().any(|a| a == "--yes") { print_report(&app.handle("state", &json!({}))); eprintln!("\nAjoutez --yes pour valider la conversion."); std::process::exit(2); } std::process::exit(convert_terminal(&app)); }
        "orchestrer" => {
            let out = recod3r_core::forge::out_dir();
            let mut entries = vec![];
            if let Ok(rd) = std::fs::read_dir(out.join("scripts")) { for e in rd.flatten() { let p = e.path(); if let (Some(s), Some(x)) = (p.file_stem(), p.extension()) { entries.push((s.to_string_lossy().into_owned(), x.to_string_lossy().into_owned())); } } }
            entries.sort();
            match recod3r_core::forge::orchestrer(&out, &entries) { Ok(_) => println!("Orchestration générée dans {} : orchestrer.sh / orchestrer.ps1 / orchestrer.txt ({} scripts)", recod3r_core::forge::tilde(&out), entries.len()), Err(e) => { eprintln!("{e}"); std::process::exit(1); } }
        }
        "help" | "--help" | "-h" => println!("VTLO_REcod3r {}\n\n  recod3r                  ouvre l'application (interface visuelle)\n  recod3r scan [--dir D]   rapport dans le terminal (--json)\n  recod3r convert --yes    analyse + conversion avec 0–100 % en direct\n  recod3r orchestrer       génère l'orchestration des scripts livrés\n\nOptions : --dir DOSSIER_OU_ZIP (répétable) · --out DOSSIER · --users N · --price EUR_PAR_MTOK · --uses N · --port N · --no-open", engine::VERSION),
        _ => serve(app, arg_val(&args, "--port").and_then(|p| p.parse().ok()).unwrap_or(0), !args.iter().any(|a| a == "--no-open")),
    }
}
