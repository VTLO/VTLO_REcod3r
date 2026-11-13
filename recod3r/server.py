"""VTLO_REcod3r — serveur local de décision (127.0.0.1) : les boutons COD3FORM3 / IGNOR3 du rapport 1 y répondent."""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import forge as F


class Decision:
    def __init__(self):
        self.value = None
        self.ids = None
        self.event = threading.Event()

    def set(self, value, ids):
        if self.value is None:
            self.value, self.ids = value, ids
            self.event.set()
            return True
        return False


def make_handler(token: str, html: str, dec: Decision, port_holder: dict):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _host_ok(self):
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost")

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            b = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, "{}")
            if self.path.rstrip("/") == f"/{token}":
                return self._send(200, html, "text/html; charset=utf-8")
            if self.path == f"/{token}/etat":
                return self._send(200, json.dumps({"decision": dec.value}))
            self._send(404, "{}")

        def do_POST(self):
            if not self._host_ok() or self.path != f"/{token}/decide":
                return self._send(403, "{}")
            origin = self.headers.get("Origin")
            if origin and origin.split("://")[-1].split(":")[0] not in ("127.0.0.1", "localhost"):
                return self._send(403, "{}")
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(min(n, 1_000_000)) or b"{}")
            except ValueError:
                return self._send(400, "{}")
            d = data.get("decision")
            if d not in ("COD3FORM3", "IGNOR3"):
                return self._send(400, json.dumps({"erreur": "décision invalide"}))
            ids = [str(x) for x in data.get("ids", [])] if d == "COD3FORM3" else []
            ok = dec.set(d, ids)
            self._send(200, json.dumps({"ok": ok, "decision": dec.value}))
    return H


def serve(run: Path, html_builder, timeout: int = 1800, port: int = 0):
    """Sert le rapport 1 et attend la décision. Écrit decision.json (+ etat serveur pour « attendre »)."""
    token = secrets.token_urlsafe(12)
    dec = Decision()
    holder = {}
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(token, "", dec, holder))
    p = srv.server_address[1]
    url = f"http://127.0.0.1:{p}/{token}/"
    srv.RequestHandlerClass = make_handler(token, html_builder(url), dec, holder)
    F.jsave(run / "serveur.json", {"url": url, "pid": os.getpid(), "debut": time.time(), "timeout": timeout})
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, dec, url


def wait_and_close(srv, dec: Decision, run: Path, timeout: int, poll=None):
    """Bloque jusqu'à la décision (ou délai). poll() : fonction optionnelle (saisie terminal) → renvoie décision ou None."""
    t0 = time.time()
    while time.time() - t0 < timeout and not dec.event.is_set():
        if poll:
            r = poll()
            if r:
                dec.set(*r)
                break
        dec.event.wait(0.3)
    time.sleep(0.4)  # laisse la réponse HTTP partir
    srv.shutdown()
    srv.server_close()
    value = dec.value or "EXPIRE"
    F.jsave(run / "decision.json", {"decision": value, "ids": dec.ids or [], "le": time.strftime("%Y-%m-%dT%H:%M:%S")})
    return value
