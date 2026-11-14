"""VTLO_REcod3r — plan, forge, déploiement, restauration, bilan."""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from . import engine as E

CODE_OK = ("CODE", "HYBRID")


# --------------------------------------------------------------------------- dossiers d'état
def state_dir() -> Path:
    return Path(os.environ.get("RECOD3R_DIR") or (E.home() / E.STATE_NAME))


def runs_dir() -> Path:
    return state_dir() / "runs"


def new_run() -> Path:
    d = runs_dir() / time.strftime("%Y%m%d-%H%M%S")
    n = 1
    while d.exists():
        n += 1
        d = runs_dir() / (time.strftime("%Y%m%d-%H%M%S") + f"-{n}")
    d.mkdir(parents=True)
    (runs_dir() / "latest.txt").write_text(d.name, encoding="utf-8")
    return d


def latest_run(name: str | None = None) -> Path | None:
    try:
        n = name or (runs_dir() / "latest.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    d = runs_dir() / n
    return d if d.is_dir() else None


def jload(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def jsave(p: Path, data):
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, p)


def short(p) -> str:
    p = str(p)
    h = str(E.home())
    return "~" + p[len(h):] if p.startswith(h) else p


# --------------------------------------------------------------------------- plan
def _inplace_possible(a: E.Asset) -> bool:
    return E.native_stub(a, {"skill": "x", "gemini_toml": "x", "claude_command": "x", "md_prompt": "x"}) is not None


def build_plan(assets, extra, near, usage, P, env):
    R = E.build_report(assets, extra, near, usage, P, env)
    by_id = {a.id: a for a in assets + extra}
    used: set = set()
    items, reco = [], {"memoire": [], "elagage": [], "doublons": R["duplicates"], "dormants": R["dormant"],
                       "commandes": R["commands"], "secrets": R["secrets"]}
    for r in R["items"]:
        a = by_id[r["id"]]
        if r["kind"] in ("memory", "rules"):
            if r["save_month"] > 0:
                (reco["memoire"] if r["action"] == "hooks" else reco["elagage"]).append(r)
            continue
        if r["save_month"] <= 0 or r["verdict"] not in CODE_OK:
            continue
        slug = E.unique_slug(a, used)
        used.add(slug)
        items.append({
            "slug": slug, "id": r["id"], "mode": "remplacement" if _inplace_possible(a) else "script_seul",
            "analyse": r,
            "asset": {"agent": a.agent, "kind": a.kind, "name": a.name, "path": a.path, "description": a.description,
                      "body": a.body, "has_scripts": a.has_scripts, "tokens": a.tokens, "extra": a.extra},
        })
    return {"version": E.VERSION, "genere": time.strftime("%Y-%m-%dT%H:%M:%S"), "params": P, "env": R["env"],
            "totaux": R["totals"], "usage": R["usage"], "items": items, "reco": reco,
            "tous": [{k: r[k] for k in ("id", "agent", "kind", "name", "verdict", "codeable", "tokens", "save_month")}
                     for r in R["items"]]}


# --------------------------------------------------------------------------- forge
def _asset_from(d: dict) -> E.Asset:
    a = E.Asset(id="", agent=d["agent"], kind=d["kind"], name=d["name"], path=d["path"], description=d["description"],
                body=d["body"], has_scripts=d.get("has_scripts", False))
    a.tokens, a.extra = d["tokens"], d.get("extra", {})
    return a


def forge(run: Path, ids: list[str] | None = None, lang: str | None = None) -> dict:
    plan = jload(run / "plan.json")
    etat = jload(run / "etat.json", {"items": {}})
    chosen = ids or None
    used = set(etat["items"])
    for it in plan["items"]:
        if chosen is not None and it["id"] not in chosen and it["slug"] not in chosen:
            continue
        if it["slug"] in etat["items"]:
            continue
        a, r = _asset_from(it["asset"]), it["analyse"]
        sc = E.write_scaffold(a, r, run / "forge", lang, used, slug=it["slug"])
        etat["items"][it["slug"]] = {"id": it["id"], "statut": "a_faire", "mode": it["mode"], "script": sc["script"],
                                     "ext": sc["ext"], "langage": sc["lang"], "dossier": sc["dir"], "raison": ""}
    jsave(run / "etat.json", etat)
    return etat


def _item(run: Path, slug: str):
    etat = jload(run / "etat.json", {"items": {}})
    plan = jload(run / "plan.json", {"items": []})
    pit = next((i for i in plan["items"] if i["slug"] == slug), None)
    if slug not in etat["items"] or pit is None:
        raise KeyError(slug)
    return etat, etat["items"][slug], pit


def sortie_dir() -> Path:
    """Dossier livré à l'utilisateur : scripts + skills convertis, prêts à l'emploi."""
    return Path(os.environ.get("RECOD3R_OUT") or (E.home() / "vtlorecod_scripts"))


def ecrit(run: Path, slug: str) -> bool:
    """Un script est « rédigé » quand le marqueur à implémenter a disparu (signal d'avancement, pas un test)."""
    etat = jload(run / "etat.json", {"items": {}})
    it = etat["items"].get(slug)
    if not it:
        return False
    script = Path(it["script"])
    if not script.is_file():
        return False
    return not E.MARK_RX.search(script.read_text(encoding="utf-8", errors="replace"))


def avancement(run: Path) -> tuple[int, int]:
    etat = jload(run / "etat.json", {"items": {}})
    todo = [s for s, i in etat["items"].items() if i["statut"] in ("a_faire", "pret")]
    return sum(1 for s in todo if ecrit(run, s)), len(todo)


def _tilde(p: Path) -> str:
    return short(p)


def deployer(run: Path, slug: str) -> dict:
    etat, it, pit = _item(run, slug)
    script = Path(it["script"])
    if not ecrit(run, slug):
        raise RuntimeError("script non rédigé")
    txt = script.read_text(encoding="utf-8", errors="replace")
    a, r = _asset_from(pit["asset"]), pit["analyse"]
    lang, ext = it["langage"], it["ext"]
    out = sortie_dir()
    (out / "scripts").mkdir(parents=True, exist_ok=True)
    target = out / "scripts" / f"{slug}.{ext}"
    shutil.copy2(script, target)
    target.chmod(0o755)
    it["copies"] = [str(target)]
    script_global = _tilde(target)
    bodies = E.stub_bodies(a, r, slug, script_global, script_global, lang)
    # skills et commandes convertis, prêts à copier dans l'outil d'IA de votre choix
    skill = out / "skills" / slug
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(bodies["skill"], encoding="utf-8")
    for sub, name, key in (("claude", f"{slug}.md", "claude_command"), ("gemini", f"{slug}.toml", "gemini_toml"),
                           ("codex-agy", f"{slug}.md", "md_prompt")):
        d = out / "commandes" / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(bodies[key], encoding="utf-8")
    stub = E.native_stub(a, bodies) if it["mode"] == "remplacement" else None
    it["stub_tokens"] = E.est_tokens(stub or bodies["skill"])
    if stub is not None:
        orig = Path(a.path)
        if not orig.is_file():
            raise RuntimeError(f"fichier d'origine introuvable : {orig}")
        bak = run / "sauvegardes" / slug
        bak.mkdir(parents=True, exist_ok=True)
        shutil.copy2(orig, bak / orig.name)
        it["sauvegarde"] = {"origine": str(orig), "copie": str(bak / orig.name)}
        tmp = orig.with_name(orig.name + ".recod3r.tmp")
        tmp.write_text(stub, encoding="utf-8")
        os.replace(tmp, orig)
        it["fichier_modifie"] = str(orig)
    it["statut"] = "deploye"
    it["lignes"] = sum(1 for l in txt.splitlines() if l.strip())
    it["manifeste"] = E.read_manifest(txt)
    it["deploye_le"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    jsave(run / "etat.json", etat)
    return it


def lisez_moi(run: Path) -> Path:
    """Écrit LISEZMOI.md dans le dossier livré : comment lancer chaque script à la main."""
    bil = bilan(run)
    out = sortie_dir()
    L = ["# Scripts VTLO_REcod3r", "",
         "Chaque script remplace les étapes mécaniques d'un de vos skills/prompts. Lancez-les à la main ou depuis votre outil d'IA favori.", "",
         "| Script | Langage | Lancer | Économie estimée |", "|---|---|---|---|"]
    for r in bil["items"]:
        if r["statut"] != "deploye":
            continue
        run_cmd = f"{' '.join(E.LANG_RUNNER[r['langage']])} scripts/{Path(r['bin']).name} <entrée>" if r["bin"] else "—"
        L.append(f"| `{r['slug']}` | {r['langage']} | `{run_cmd}` | −{int(r['taux'] * 100)} % · {E.fmt_n(r['eco_mois'])} tokens/mois |")
    L += ["", "## Contrat commun (compatible pipeline)", "",
          "- entrées : arguments, fichiers ou stdin · sortie : texte court, ou `--json` (un objet JSON)",
          "- codes : `0` ok · `1` échec · `2` usage · `3` décision IA requise (JSON `needs_ai`)",
          "- au code 3, relancez avec la réponse de l'IA dans `RECOD3R_AI_ANSWER` : le script la revalide.", "",
          "## Dans votre outil d'IA", "",
          "- `skills/<nom>/SKILL.md` : skill léger prêt à copier (Claude Code, Gemini CLI, agy…).",
          "- `commandes/claude/`, `commandes/gemini/`, `commandes/codex-agy/` : commandes slash prêtes à copier.", "",
          "## Annuler", "", "`vtlorecod restaurer` remet les fichiers d'origine remplacés depuis leur sauvegarde.", ""]
    p = out / "LISEZMOI.md"
    out.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L), encoding="utf-8")
    return p


def abandonner(run: Path, slug: str, raison: str):
    etat, it, _ = _item(run, slug)
    it["statut"], it["raison"] = "abandonne", raison
    jsave(run / "etat.json", etat)


def restaurer(run: Path, slugs: list[str] | None = None) -> list[str]:
    etat = jload(run / "etat.json", {"items": {}})
    done = []
    for slug, it in etat["items"].items():
        if slugs and slug not in slugs:
            continue
        if it["statut"] != "deploye":
            continue
        sv = it.get("sauvegarde")
        if sv and Path(sv["copie"]).is_file():
            shutil.copy2(sv["copie"], sv["origine"])
        for c in it.get("copies", []):
            try:
                Path(c).unlink()
            except OSError:
                pass
        it["statut"] = "restaure"
        done.append(slug)
    jsave(run / "etat.json", etat)
    return done


# --------------------------------------------------------------------------- bilan (économies)
def bilan(run: Path) -> dict:
    plan, etat = jload(run / "plan.json"), jload(run / "etat.json", {"items": {}})
    dec = jload(run / "decision.json", {})
    P = plan["params"]
    rows, tot_av, tot_ap, tot_mois = [], 0.0, 0.0, 0.0
    for pit in plan["items"]:
        r = pit["analyse"]
        it = etat["items"].get(pit["slug"])
        if it is None:
            continue
        n_code = r["n_code"] + r["n_mixed"] / 2
        avant = r["tokens"] + E.STEP_OVERHEAD * n_code + (E.RESPONSE_TOKENS if r["kind"] == "recurring" else 0)
        row = {"slug": pit["slug"], "nom": r["name"], "agent": r["agent"], "kind": r["kind"], "mode": pit["mode"],
               "statut": it["statut"], "raison": it.get("raison", ""), "langage": it["langage"],
               "lignes": it.get("lignes", 0), "script": it.get("script"), "verdict": r["verdict"],
               "usages_mois": r["uses_month"], "usages_src": r["uses_src"], "avant": round(avant), "apres": 0,
               "taux": 0.0, "eco_usage": 0, "eco_mois": 0, "fichier_modifie": it.get("fichier_modifie"),
               "sauvegarde": (it.get("sauvegarde") or {}).get("copie"), "manifeste": it.get("manifeste", {}),
               "bin": (it.get("copies") or [None])[0]}
        if it["statut"] == "deploye":
            apres = it.get("stub_tokens", E.STUB_TOKENS) + E.OUT_TOKENS + (1 - (r["codeable"] or 0)) * r["tokens"]
            row.update(apres=round(apres), taux=round(max(0.0, 1 - apres / avant), 3) if avant else 0,
                       eco_usage=round(max(0, avant - apres)), eco_mois=round(max(0, avant - apres) * r["uses_month"]))
            tot_av += avant * r["uses_month"]
            tot_ap += apres * r["uses_month"]
            tot_mois += row["eco_mois"]
        rows.append(row)
    n = lambda s: sum(1 for x in rows if x["statut"] == s)
    T = {"prevus": len(rows), "deployes": n("deploye"), "abandonnes": n("abandonne"), "a_faire": n("a_faire") + n("pret"),
         "restaures": n("restaure"), "eco_mois": round(tot_mois), "eco_an": round(tot_mois * 12),
         "taux_global": round(1 - tot_ap / tot_av, 3) if tot_av else 0.0,
         "cout_mois": round(tot_mois * P["price"] / 1e6, 2), "minutes_mois": round(tot_mois / 1000 * E.SECONDS_PER_KTOK / 60, 1),
         "prevu_mois": plan["totaux"]["saved_tokens_month"]}
    return {"genere": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": run.name, "decision": dec, "items": rows, "totaux": T,
            "params": P, "reco": plan["reco"]}
