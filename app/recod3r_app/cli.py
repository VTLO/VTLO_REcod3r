"""Interface visuelle locale (127.0.0.1) + commandes terminal. Python 3.8+, aucune dépendance."""
import json
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import engine, forge, integrate
from .api import App, open_path

UI = Path(__file__).with_name("ui") / "index.html"
GLYPHS = [["███", "█ █", "█ █", "█ █", "███"], ["  █", "  █", "  █", "  █", "  █"], ["███", "  █", "███", "█  ", "███"], ["███", "  █", "███", "  █", "███"],
          ["█ █", "█ █", "███", "  █", "  █"], ["███", "█  ", "███", "  █", "███"], ["███", "█  ", "███", "█ █", "███"], ["███", "  █", "  █", "  █", "  █"],
          ["███", "█ █", "███", "█ █", "███"], ["███", "█ █", "███", "  █", "███"], ["█ █", "  █", " █ ", "█  ", "█ █"]]


def big(n):
    idx = [int(c) if c.isdigit() else 10 for c in "%d%%" % n]
    return "\n".join("  ".join(GLYPHS[i][r] for i in idx) for r in range(5))


def arg_val(a, k):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None


def params_from(a):
    extra = [a[i + 1] for i, x in enumerate(a) if x in ("--dir", "--add") and i + 1 < len(a)]
    p = {"extra": extra}
    for k, f in (("users", "--users"), ("eur_per_mtok", "--price"), ("uses_per_month", "--uses")):
        v = arg_val(a, f)
        try:
            if v is not None:
                p[k] = float(v)
        except ValueError:
            pass
    # scan global du système : par défaut en commande terminal explicite, sauf si des ajouts manuels sont donnés (--add) ; --global le force
    return {"params": p, "global": ("--global" in a) or not extra}


def print_report(st):
    t = st["totals"]
    print("\n  VTLO_REcod3r %s — rapport" % st["version"])
    print("  %s éléments analysés · %s convertibles en script" % (t["assets"], t["scripts"]))
    print("  ≈ %s tokens/mois (−%.0f %%) · ≈ %.2f €/mois · ≈ %.1f h/mois\n" % (forge.fmt_n(t["tokens_month"]), t["pct"], t["eur_month"], t["hours_month"]))
    for i in [i for i in st["items"] if i["convertible"]][:12]:
        print("  %-44s %7s tok/usage  [%s]" % (i["name"][:44], forge.fmt_n(i["save_per_use"]), i["lang"]))


def convert_terminal(app, agent, orch):
    app.handle("convert", {"agent": agent})
    last = 1000
    while True:
        time.sleep(0.3)
        st = app.handle("state")
        pct = st["progress"]["pct"]
        if pct != last:
            print("\x1b[2J\x1b[H\n%s\n\n  %s" % (big(pct), st["progress"]["message"]))
            last = pct
        if st["phase"] == "done":
            print("\n  IA sur le banc de touche !! Place au c0d3 pour la frappe décisive !!!!\n")
            print("  Dossier créé : %s" % (st["out"] or "?"))
            print("  %d script(s) prêt(s), %d à compléter" % (len(st["done"]), len(st["todo"])))
            if st["error"]:
                print("  ! %s" % st["error"], file=sys.stderr)
            if not st["done"]:
                return 0
            yes = orch  # proposition : pipeline complet prêt à l'emploi
            if not orch and sys.stdin.isatty():
                yes = input("\n  Générer l'orchestration (pipeline complet prêt à l'emploi) ? [O/n] ").strip().lower() not in ("n", "non", "no")
            if yes:
                r = app.handle("orchestrer")
                if r.get("error"):
                    print("  ! %s" % r["error"], file=sys.stderr)
                else:
                    print("\n  Pipeline généré dans %s — lancez-le avec :  %s" % (r["dir"], r["run"]))
            else:
                print("\n  Pipeline complet : recod3r orchestrer")
            return 0


def make_handler(app, tok, html):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype):
            b = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path.split("?")[0] == "/":
                self._send(200, html, "text/html; charset=utf-8")
            else:
                self._send(404, "introuvable", "text/plain; charset=utf-8")

        def do_POST(self):
            if not self.path.startswith("/api/"):
                return self._send(404, "introuvable", "text/plain; charset=utf-8")
            if not secrets.compare_digest(self.headers.get("X-Token", ""), tok):
                return self._send(403, '{"error":"jeton invalide"}', "application/json")
            try:
                n = int(self.headers.get("Content-Length") or 0)
                v = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            except (ValueError, OSError):
                v = {}
            self._send(200, json.dumps(app.handle(self.path[5:], v), ensure_ascii=False), "application/json")
    return H


def serve(app, port, open_browser, window=False):
    tok = secrets.token_hex(8)
    html = UI.read_text(encoding="utf-8").replace("__TOKEN__", tok)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, tok, html))
    url = "http://127.0.0.1:%d/" % srv.server_address[1]
    print("VTLO_REcod3r %s — interface : %s  (Ctrl+C pour quitter)" % (engine.VERSION, url))
    if window:
        try:
            import webview  # fenêtre native si pywebview est installé (facultatif)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            webview.create_window("VTLO_REcod3r", url, width=1180, height=860)
            webview.start()
            return
        except ImportError:
            print("pywebview absent : ouverture dans le navigateur (pip install pywebview pour la fenêtre native).")
    if open_browser:
        open_path(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def update():
    """Met l'outil à jour (git pull dans le dossier des sources) puis rafraîchit /recod3r dans les CLI d'IA."""
    import subprocess
    root = Path(__file__).resolve().parents[2]
    if not (root / ".git").exists():
        print("Installation hors dépôt git (pipx ?) : relancez  pipx upgrade vtlo-recod3r  ou  curl -fsSL https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install-app.sh | sh")
        return 1
    git = lambda *a: subprocess.run(["git", "-C", str(root)] + list(a), capture_output=True, text=True)  # noqa: E731
    before = git("rev-parse", "--short", "HEAD").stdout.strip()
    r = git("pull", "--ff-only")
    if r.returncode != 0:
        print("Mise à jour impossible : %s" % (r.stderr.strip() or r.stdout.strip()), file=sys.stderr)
        return 1
    after = git("rev-parse", "--short", "HEAD").stdout.strip()
    print("VTLO_REcod3r déjà à jour (%s)." % after if before == after else "VTLO_REcod3r mis à jour : %s → %s" % (before, after))
    subprocess.run([sys.executable, "-m", "recod3r_app", "integrer"], cwd=str(root / "app"), env=dict(os.environ, PYTHONPATH=str(root / "app")))
    return 0


HELP = """VTLO_REcod3r %s

  recod3r                  ouvre l'application (interface visuelle)
  recod3r scan [--add D]   rapport dans le terminal (--json)
  recod3r convert --yes    analyse + conversion avec 0–100 %% en direct
  recod3r integrer         ajoute /recod3r dans agy, Claude Code, Gemini CLI, Codex
  recod3r update           met l'outil à jour (git pull) et rafraîchit /recod3r
  recod3r orchestrer       génère l'orchestration des scripts livrés

Options : --agent claude|gemini|agy|codex · --add FICHIER_DOSSIER_OU_ZIP (répétable, = --dir ; sans scan du système) · --global (scanner aussi le système) · --only skill1,skill2 (choix manuel)
          --all (tout convertir) · --orchestrer (pipeline sans question) · --out DOSSIER · --users N · --price EUR_PAR_MTOK · --uses N
          --port N · --no-open · --fenetre (fenêtre native si pywebview)
"""


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if arg_val(args, "--out"):
        os.environ["RECOD3R_OUT"] = arg_val(args, "--out")
    cmd = args[0] if args and not args[0].startswith("--") else "app"
    app = App()
    if cmd == "scan":
        st = app.handle("scan", params_from(args))
        if "--json" in args:
            print(json.dumps(st, indent=2, ensure_ascii=False))
        else:
            print_report(st)
    elif cmd == "convert":
        app.handle("scan", params_from(args))
        if "--all" in args:
            app.handle("selection", {"all": "tous"})
        if arg_val(args, "--only"):
            app.handle("selection", {"only": [x.strip() for x in arg_val(args, "--only").split(",")]})
        if "--yes" not in args:
            print_report(app.handle("state"))
            print("\nAjoutez --yes pour valider la conversion.", file=sys.stderr)
            return 2
        return convert_terminal(app, arg_val(args, "--agent"), "--orchestrer" in args)
    elif cmd == "integrer":
        r = integrate.integrer(arg_val(args, "--agent"))
        if not r:
            print("Aucun CLI d'IA détecté (claude, gemini, agy, codex). Utilisez --agent NOM pour forcer.")
        else:
            print("recod3r est maintenant disponible dans vos CLI d'IA :")
            for f in r:
                print("  ✔ %s" % f)
            print("Tapez /recod3r dans l'outil (ou « convertis mes skills en scripts »).")
    elif cmd == "orchestrer":
        out = forge.out_dir()
        entries = sorted((p.stem, p.suffix.lstrip(".")) for p in (out / "scripts").glob("*.*")) if (out / "scripts").is_dir() else []
        try:
            forge.orchestrer(out, entries)
        except OSError as e:
            print(e, file=sys.stderr)
            return 1
        print("Orchestration générée dans %s : orchestrer.sh / orchestrer.ps1 / orchestrer.txt (%d scripts)" % (forge.tilde(out), len(entries)))
    elif cmd in ("update", "upgrade", "maj"):
        return update()
    elif cmd in ("version", "--version", "-v"):
        print("VTLO_REcod3r %s" % engine.VERSION)
    elif cmd in ("help", "--help", "-h"):
        print(HELP % engine.VERSION)
    else:
        try:
            port = int(arg_val(args, "--port") or 0)
        except ValueError:
            port = 0
        serve(app, port, "--no-open" not in args, "--fenetre" in args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
