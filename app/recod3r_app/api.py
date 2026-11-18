"""API unique (HTTP local, fenêtre, CLI) : état partagé + routes."""
import os
import platform
import subprocess
import threading
import time
from pathlib import Path

from . import agents, engine, forge

_OS = {"darwin": "macos"}.get(platform.system().lower(), platform.system().lower())


def open_path(target):
    if _OS == "macos":
        cmd = ["open", target]
    elif _OS == "windows":
        cmd = ["explorer", target]
    elif engine.which("termux-open"):
        cmd = ["termux-open", target]
    else:
        cmd = ["xdg-open", target]
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def totals(items, p):
    sel = [i for i in items if i["selected"]]
    m = p["uses_per_month"] * p["users"]
    tok = sum(i["save_per_use"] * m for i in sel)
    sec = sum(max(i["ai_sec_per_use"] - i["script_sec_per_use"], 0.0) * m for i in sel)
    before = sum(i["before_tokens"] * m for i in sel)
    return {"scripts": len(sel), "assets": len(items), "tokens_month": float(engine.rnd(tok)), "eur_month": tok / 1e6 * p["eur_per_mtok"],
            "hours_month": sec / 3600.0, "before_month": float(engine.rnd(before)), "pct": tok / before * 100.0 if before > 0 else 0.0,
            "instruction_tokens": float(engine.rnd(sum(i["tokens"] for i in items)))}


class App:
    def __init__(self):
        self.lock = threading.RLock()
        self.phase, self.params, self.assets, self.items = "idle", engine.default_params(), [], []
        self.pct = self.written = self.total = 0
        self.started, self.finished_secs, self.message = None, 0.0, ""
        self.item_done, self.order, self.out, self.todo, self.done = {}, [], None, [], []
        self.agent_used, self.err, self.manual, self.orch = None, None, False, None

    # ------------------------------------------------------------ état
    def state(self):
        with self.lock:
            if self.phase == "converting" and self.started:
                elapsed = time.monotonic() - self.started
            else:
                elapsed = self.finished_secs if self.started else 0.0
            return {
                "version": engine.VERSION, "os": _OS, "phase": self.phase, "params": self.params, "agents": agents.detect(),
                "items": self.items, "totals": totals(self.items, self.params), "orchestration": self.orch,
                "progress": {"pct": self.pct, "written": self.written, "total": self.total, "elapsed": elapsed, "message": self.message, "agent": self.agent_used,
                             "items": [{"slug": i["slug"], "name": i["name"], "done": self.item_done.get(i["slug"], False)} for i in self.items if i["selected"]]},
                "out": self.out, "done": self.done, "todo": self.todo, "manual": self.manual, "error": self.err,
            }

    def do_scan(self, p, force=()):
        p = engine.make_params(p)
        p["extra"] = [e for e in p["extra"] if e.strip()]
        assets = engine.collect(Path.cwd(), p["extra"])
        items = engine.analyze_all(assets, p)
        with self.lock:
            prev = {i["id"]: i["selected"] for i in self.items}
            for i in items:
                if i["id"] in prev:
                    i["selected"] = prev[i["id"]]
                elif i["agent"] == "extra" and i["path"] in force:
                    i["selected"] = True
            self.params, self.assets, self.items, self.phase, self.err, self.pct = p, assets, items, "scanned", None, 0
            self.item_done, self.out, self.done, self.todo, self.orch = {}, None, [], [], None
        return self.state()

    # ------------------------------------------------------------ routes
    def handle(self, route, body=None):
        body = body if isinstance(body, dict) else {}
        h = getattr(self, "r_" + route, None)
        if route.startswith("_") or h is None:
            return {"error": "route inconnue : %s" % route}
        return h(body)

    def r_state(self, b):
        return self.state()

    def r_scan(self, b):
        return self.do_scan(b.get("params") or {})

    def r_ajouter(self, b):
        with self.lock:
            p = dict(self.params)
            p["extra"] = list(p["extra"])
        add = [str(x).strip().strip('"') for x in (b.get("paths") or []) if str(x).strip()]
        for a in add:
            if a not in p["extra"]:
                p["extra"].append(a)
        return self.do_scan(p, add)

    def r_televerser(self, b):
        name, text = str(b.get("name") or "skill"), str(b.get("text") or "")
        if not text.strip():
            return {"error": "contenu vide"}
        safe = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in name)
        if "." not in safe:
            safe += ".md"
        d = forge.state_dir() / "ajouts"
        try:
            d.mkdir(parents=True, exist_ok=True)
            f = d / safe
            f.write_text(text, encoding="utf-8")
        except OSError as e:
            return {"error": str(e)}
        with self.lock:
            p = dict(self.params)
            p["extra"] = list(p["extra"])
        if str(f) not in p["extra"]:
            p["extra"].append(str(f))
        return self.do_scan(p, [str(f)])

    def r_selection(self, b):
        with self.lock:
            m = b.get("all")
            if isinstance(m, str):
                for i in self.items:
                    i["selected"] = True if m == "tous" else (False if m == "aucun" else i["convertible"])
            if isinstance(b.get("only"), list):
                keep = [str(x) for x in b["only"]]
                for i in self.items:
                    i["selected"] = i["slug"] in keep or i["name"] in keep
            if isinstance(b.get("id"), str) and isinstance(b.get("on"), bool):
                for i in self.items:
                    if i["id"] == b["id"]:
                        i["selected"] = b["on"]
        return self.state()

    def r_convert(self, b):
        with self.lock:
            if self.phase == "converting":
                return self.state()
            if self.phase != "scanned":
                return {"error": "aucune analyse : lancez d'abord le scan"}
            if not any(i["selected"] for i in self.items):
                return {"error": "aucun skill sélectionné : cochez au moins un élément"}
            if isinstance(b.get("params"), dict):
                extra = self.params["extra"]
                self.params = engine.make_params(b["params"])
                self.params["extra"] = extra
            self.phase, self.orch, self.pct, self.written, self.started = "converting", None, 0, 0, time.monotonic()
            self.err, self.message = None, "Préparation…"
        pref = b.get("agent") if isinstance(b.get("agent"), str) else None
        threading.Thread(target=self._run_conversion, args=(pref,), daemon=True).start()
        return self.state()

    def r_ignore(self, b):
        with self.lock:
            self.phase = "ignored"
        return self.state()

    def r_reset(self, b):
        with self.lock:
            self.phase = "idle"
        return self.state()

    def r_orchestrer(self, b):
        out = forge.out_dir()
        with self.lock:
            order = list(self.order)
        if not order:
            return {"error": "aucun script livré : lancez d'abord une conversion"}
        try:
            forge.orchestrer(out, order)
        except OSError as e:
            return {"error": str(e)}
        with self.lock:
            self.orch = forge.tilde(out)
        return {"ok": True, "run": "powershell -File orchestrer.ps1" if os.name == "nt" else "sh orchestrer.sh", "dir": forge.tilde(out),
                "files": ["orchestrer.sh", "orchestrer.ps1", "orchestrer.txt"]}

    def r_open(self, b):
        open_path(str(forge.out_dir()))
        return {"ok": True}

    # ------------------------------------------------------------ conversion
    def _set(self, **kw):
        with self.lock:
            for k, v in kw.items():
                setattr(self, k, v)

    def _run_conversion(self, pref):
        with self.lock:
            items, assets, params = list(self.items), list(self.assets), dict(self.params)
        run = forge.state_dir() / "runs" / ("run-%d" % int(time.time()))
        forged = []
        for it in (i for i in items if i["selected"]):
            a = next((x for x in assets if x["path"] == it["path"] and x["name"] == it["name"]), None)
            if a is None:
                continue
            try:
                forged.append(forge.scaffold(run, a, it))
            except OSError as e:
                self._set(err="%s: %s" % (it["slug"], e))
        total = len(forged)
        self._set(total=total, message="%d script(s) à rédiger" % total)
        prompt = forge.prompt(run, forged)
        pfile = run / "PROMPT.md"
        try:
            run.mkdir(parents=True, exist_ok=True)
            pfile.write_text(prompt, encoding="utf-8")
        except OSError:
            pass
        agent = agents.pilotable(pref)
        self._set(agent_used=agent)
        manual = False
        if agent is None:
            manual = True
            self._set(message="Aucun CLI d'IA pilotable détecté : squelettes et briefs prêts à confier à votre IA")
        else:
            try:
                child = agents.spawn(agent, pfile, run)
            except Exception as e:  # noqa: BLE001
                manual = True
                self._set(err="lancement de %s impossible : %s" % (agent, e))
                child = None
            if child is not None:
                self._set(message="L'IA rédige les scripts en une seule tâche…")
                timeout = int(os.environ.get("RECOD3R_TIMEOUT", "3600") or 3600)
                t0, exit_ok = time.monotonic(), True
                while True:
                    time.sleep(0.4)
                    n = sum(1 for f in forged if forge.written(f["script"]))
                    with self.lock:
                        self.written = n
                        self.pct = 0 if total == 0 else min(n * 100 // total, 99)
                        for f in forged:
                            self.item_done[f["slug"]] = forge.written(f["script"])
                    rc = child.poll()
                    if rc is not None:
                        exit_ok = rc == 0
                        break
                    if time.monotonic() - t0 > timeout:
                        child.kill()
                        self._set(err="délai dépassé : l'IA a été arrêtée")
                        break
                n = sum(1 for f in forged if forge.written(f["script"]))
                with self.lock:
                    no_err = self.err is None
                if (not exit_ok or n < total) and no_err:
                    hint = " Pour agy : lancez `agy` une fois en interactif pour vous connecter, puis réessayez." if agent == "agy" else ""
                    tail = agents.log_tail(run, 240)
                    self._set(err="l'IA (%s) n'a écrit que %d script(s) sur %d.%s%s" % (agent, n, total, hint, (" Journal : " + tail) if tail else ""))
        out = forge.out_dir()
        try:
            d = forge.deliver(out, forged, params)
        except OSError as e:
            d, derr = None, "livraison : %s" % e
        if manual:
            try:
                (out / "a_completer").mkdir(parents=True, exist_ok=True)
                (out / "a_completer" / "PROMPT.md").write_text(prompt, encoding="utf-8")
            except OSError:
                pass
        with self.lock:
            if d is not None:
                self.written, self.done, self.todo = len(d["done"]), list(d["done"]), list(d["todo"])
                self.order = [(f["slug"], f["ext"]) for f in forged if f["slug"] in d["done"]]
                self.out = forge.tilde(d["out"])
                for f in forged:
                    self.item_done[f["slug"]] = f["slug"] in d["done"]
            else:
                self.err = derr
            self.manual, self.pct, self.phase = manual, 100, "done"
            self.finished_secs = time.monotonic() - self.started if self.started else 0.0
            self.message = "Squelettes prêts : confiez a_completer/PROMPT.md à votre IA" if manual else "Livrables prêts"
