"""VTLO_REcod3r — orchestrateur de workflows : le code pilote le flux, l'IA n'intervient qu'aux points de décision
(code de sortie 3) et sa réponse est REVALIDÉE par le script au relancement."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import engine as E
from . import forge as F

TPL = re.compile(r"\{([a-zA-Z_][\w-]*)((?:\.[\w-]+)*)\}")
STAGE = {"http": 0, "fs": 0, "browser": 0, "json": 1, "tabular": 1, "text": 1, "doc": 1, "generique": 1,
         "code-analysis": 2, "security": 2, "git": 3, "windows": 3, "perf": 1}


def flow_dir() -> Path:
    d = F.state_dir() / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lookup(ctx: dict, name: str, path: str):
    if name not in ctx:
        raise KeyError(f"variable inconnue : {name}")
    v = ctx[name]
    for part in [p for p in path.split(".") if p]:
        if part == "json" and isinstance(v, dict) and "json" in v:
            v = v["json"]
        elif isinstance(v, dict) and part in v:
            v = v[part]
        else:
            raise KeyError(f"chemin introuvable : {name}{path}")
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) if not isinstance(v, (int, float)) else str(v)


def render(s: str, ctx: dict) -> str:
    return os.path.expanduser(TPL.sub(lambda m: _lookup(ctx, m.group(1), m.group(2)), s))


def _extract_json(text: str):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def ask_agent(agent: str | None, question: str, contexte) -> dict | None:
    """Point de décision : interroge l'agent en mode non interactif. Retourne un dict JSON ou None."""
    from . import agents as A
    prompt = ("Réponds UNIQUEMENT par un objet JSON valide, sans commentaire.\nQuestion : " + question +
              "\nContexte : " + json.dumps(contexte, ensure_ascii=False)[:4000])
    code, out = A.drive(agent or "claude", prompt, cwd=os.getcwd(), timeout=300)
    return _extract_json(out) if code == 0 else None


def run_workflow(wf: dict, variables: dict | None = None, dry: bool = False, agent: str | None = None,
                 depuis: str | None = None, log=print) -> dict:
    ctx = dict(wf.get("variables") or {})
    ctx.update(variables or {})
    res = {"nom": wf.get("nom"), "statut": "ok", "etapes": [], "appels_ia": 0}
    ctx["precedent"] = {"stdout": "", "json": None}
    started = depuis is None
    for st in wf["etapes"]:
        sid = st["id"]
        if not started:
            if sid != depuis:
                continue
            started = True
        try:
            cmd = [render(str(x), ctx) for x in st["cmd"]]
            stdin = render(st["stdin"], ctx) if st.get("stdin") else None
        except KeyError as e:
            res.update(statut="erreur", erreur=str(e))
            log(f"✘ {sid} : {e}")
            return res
        rec = {"id": sid, "cmd": cmd, "rc": None, "duree": 0.0}
        res["etapes"].append(rec)
        if dry:
            rec["rc"] = "simulation"
            log(f"… {sid} (simulation) : {' '.join(cmd)}")
            continue
        env = dict(os.environ)
        tentatives = max(1, int(st.get("essais", 1)))
        answered = False
        for essai in range(tentatives + 1):
            t0 = time.time()
            try:
                p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=st.get("delai", 300), env=env)
                rc, out, err = p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired:
                rc, out, err = 124, "", "délai dépassé"
            except FileNotFoundError as e:
                rc, out, err = 127, "", str(e)
            rec.update(rc=rc, duree=round(time.time() - t0, 2), stderr=err[-300:])
            if rc == 3:
                q = _extract_json(out) or {}
                rec["question_ia"] = q.get("needs_ai")
                if answered or not (agent or os.environ.get("RECOD3R_AGENT_CMD")):
                    res.update(statut="pause_ia", question=q.get("needs_ai"), contexte=q.get("context"), etape=sid)
                    log(f"⏸ {sid} : décision requise → {q.get('needs_ai')}")
                    return res
                ans = ask_agent(agent, str(q.get("needs_ai")), q.get("context"))
                res["appels_ia"] += 1
                if ans is None:
                    res.update(statut="echec_ia", etape=sid)
                    log(f"✘ {sid} : l'agent n'a pas fourni de réponse JSON exploitable")
                    return res
                env["RECOD3R_AI_ANSWER"] = json.dumps(ans, ensure_ascii=False)
                answered = True
                continue                     # relance : le SCRIPT revalide la réponse
            if rc in (0,):
                break
            if rc != 3 and essai < tentatives:
                continue
            break
        rec["stdout"] = out[-600:]
        if rc != 0:
            if st.get("continuer_sur_echec"):
                log(f"⚠ {sid} : échec (code {rc}), on continue")
                continue
            res.update(statut="echec", etape=sid)
            log(f"✘ {sid} : code {rc} — {err.strip()[-160:]}")
            return res
        j = _extract_json(out) if out.strip().startswith("{") else None
        ctx[sid] = {"stdout": out.strip(), "json": j}
        ctx["precedent"] = ctx[sid]
        log(f"✔ {sid} ({rec['duree']}s)")
    return res


# --------------------------------------------------------------------------- propositions
def _compatibles(items):
    out = []
    for r in items:
        if r["statut"] != "deploye":
            continue
        m = r.get("manifeste") or {}
        if m.get("sortie") == "json" and r.get("bin"):
            out.append(r)
    return out


def _step(r, premier: bool):
    inp = "{entree}" if premier else None
    cmd = E.LANG_RUNNER[r["langage"]] + [r["bin"]] if r["langage"] != "go" else [r["bin"]]
    st = {"id": r["slug"], "cmd": cmd + ([inp] if inp else []) + ["--json"], "delai": 300, "essais": 1}
    if not premier:
        st["stdin"] = "{precedent.stdout}"
    return st


def proposer(bil: dict) -> list[dict]:
    comp = _compatibles(bil["items"])
    props = []
    fam_of = lambda r: (r.get("manifeste", {}).get("familles") or ["generique"])
    groups: dict[str, list] = {}
    for r in comp:
        for f in fam_of(r):
            groups.setdefault(f, []).append(r)
    seen = set()
    for f, rs in sorted(groups.items()):
        if len(rs) < 2:
            continue
        key = tuple(sorted(r["slug"] for r in rs))
        if key in seen:
            continue
        seen.add(key)
        rs = sorted(rs, key=lambda r: (STAGE.get(f, 1), r["slug"]))[:5]
        props.append(_mk(f"chaine-{f}", f"Chaîne « {f} » : {len(rs)} scripts du même domaine enchaînés par le code", rs))
    if len(comp) >= 2:
        rs = sorted(comp, key=lambda r: (min(STAGE.get(f, 1) for f in fam_of(r)), r["slug"]))[:6]
        w = _mk("tournee-complete", "Tournée planifiable : tous les scripts compatibles, un échec n'arrête pas les suivants", rs)
        for st in w["etapes"]:
            st["continuer_sur_echec"] = True
            st.pop("stdin", None)
            st["cmd"] = [x for x in st["cmd"] if x != "{entree}"] + (["{entree}"] if "{entree}" in st["cmd"] else [])
        w["etapes"] = [dict(st, cmd=st["cmd"]) for st in w["etapes"]]
        props.append(w)
    for r in comp:
        if (r.get("manifeste") or {}).get("ia") or r["verdict"] == "HYBRID":
            w = _mk(f"garde-ia-{r['slug']}", f"« {r['nom']} » : le script mène, l'IA tranche seulement le point de décision, le script revalide", [r])
            w["etapes"][0]["si_ia"] = "agent"
            props.append(w)
    if not props and comp:
        props.append(_mk(f"solo-{comp[0]['slug']}", f"« {comp[0]['nom']} » exécutable par l'orchestrateur (journal, délai, reprise)", comp[:1]))
    return props


def _mk(nom: str, desc: str, rs: list) -> dict:
    steps = [_step(r, i == 0) for i, r in enumerate(rs)]
    runs = min([max(r["usages_mois"], 1) for r in rs] or [1])
    gain = max(0, len(rs) - 1) * E.STEP_OVERHEAD * runs
    wf = {"nom": nom, "description": desc, "variables": {"entree": "ENTREE.csv"}, "etapes": steps}
    wf["_meta"] = {"scripts": [r["slug"] for r in rs], "langages": sorted({r["langage"] for r in rs}),
                   "gain_relais_tokens_mois": round(gain), "executions_mois": round(runs, 1),
                   "compat": "sortie JSON + codes 0/1/2/3 + lecture stdin/fichier (manifeste vérifié)"}
    return wf


def ecrire(props: list[dict]) -> list[str]:
    out = []
    for w in props:
        p = flow_dir() / f"{w['nom']}.json"
        p.write_text(json.dumps(w, ensure_ascii=False, indent=2), encoding="utf-8")
        out.append(str(p))
    return out


def charger(nom: str) -> dict:
    p = Path(nom)
    if not p.is_file():
        p = flow_dir() / (nom if nom.endswith(".json") else nom + ".json")
    return json.loads(p.read_text(encoding="utf-8"))
