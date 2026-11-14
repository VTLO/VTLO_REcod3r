#!/usr/bin/env python3
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args"], "sortie": "json", "familles": ["text", "fs"], "ia": false}
"""google-analytics-data-api-basics — bases de l'API Google Analytics Data (7 langages) + construction de rapports (version script du skill « google-analytics-data-api-basics »).

Sert les guides du skill (code, étapes, sections) SANS passer par l'IA : 0 token.
Les guides sont lus dans data/google-analytics-data-api-basics/ (copie du skill d'origine, à côté du dossier scripts/).

Usage :
  google-analytics-data-api-basics.py --liste                         guides disponibles
  google-analytics-data-api-basics.py GUIDE [--code] [--etapes] [--section TITRE] [--set CLE=VAL ...] [--ecrire DOSSIER] [--json]
  google-analytics-data-api-basics.py --placeholders [GUIDE]          valeurs à remplacer (ex. identifiants à renseigner)

Contrat : 0 ok · 1 échec (message sur stderr) · 2 usage · 3 décision IA requise (jamais utilisé ici).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SLUG = "google-analytics-data-api-basics"
EXT = {"kotlin": "kt", "java": "java", "swift": "swift", "objectivec": "m", "objc": "m", "csharp": "cs", "cs": "cs", "python": "py",
       "py": "py", "javascript": "js", "js": "js", "typescript": "ts", "ts": "ts", "go": "go", "php": "php", "ruby": "rb", "perl": "pl",
       "xml": "xml", "gradle": "gradle", "groovy": "gradle", "bash": "sh", "sh": "sh", "shell": "sh", "json": "json", "yaml": "yaml",
       "yml": "yaml", "c#": "cs", "powershell": "ps1", "ps1": "ps1", "kts": "kts", "sql": "sql", "html": "html", "brightscript": "brs", "text": "txt", "": "txt"}
PLACEHOLDER_RX = re.compile(
    r"<[A-Z][A-Z0-9_]*PLACEHOLDER>|\bINSERT_[A-Z_]+(?:_HERE)?\b|\bYOUR_[A-Z_]+\b|\{[a-z_]+\}|ca-app-pub-\d+[~/]\d+|<[A-Z][A-Z_ ]{3,}>")
FENCE_RX = re.compile(r"^(?P<ind>[ \t]*)```(?P<lang>[\w+#.-]*)[^\n]*\n(?P<body>.*?)^(?P=ind)```[ \t]*$", re.S | re.M)


def fail(msg: str, code: int = 1):
    print(f"{SLUG} : {msg}", file=sys.stderr)
    raise SystemExit(code)


def data_dir() -> Path:
    cands = [os.environ.get("RECOD3R_DATA"), Path(__file__).resolve().parent.parent / "data" / SLUG]
    for c in cands:
        if c and (Path(c) / "SKILL.md").is_file():
            return Path(c)
    fail("dossier de données introuvable (data/%s/ à côté de scripts/ ; ou variable RECOD3R_DATA)" % SLUG)


def guides() -> dict:
    d = data_dir()
    out = {"skill": d / "SKILL.md"}
    for f in sorted(d.rglob("*.md")):
        if f.name != "SKILL.md":
            out[f.stem] = f
    return out


def trouver(nom: str) -> Path:
    g = guides()
    if nom in g:
        return g[nom]
    cand = [k for k in g if nom.lower() in k.lower()]
    if len(cand) == 1:
        return g[cand[0]]
    fail(("guide ambigu : " + ", ".join(cand)) if cand else ("guide inconnu : %s (voir --liste)" % nom), 2)


def titre(txt: str) -> str:
    m = re.search(r"^#{1,2}\s+(.+)$", txt, re.M)
    return m.group(1).strip() if m else ""


def deviner(code: str) -> str:
    """Langage probable d'un bloc sans étiquette."""
    r = lambda p: re.search(p, code, re.M)
    if r(r"^<\?xml|<manifest|<dependencies|<resources"):
        return "xml"
    if r(r"import GoogleMobileAds|^\s*func\s+\w+|^\s*let\s+\w+\s*[=:]"):
        return "swift"
    if r(r"#import|@interface|@implementation"):
        return "objectivec"
    if r(r"^\s*using\s+[\w.]+;|^\s*namespace\s"):
        return "csharp"
    if r(r"^\s*(import|package)\s+(com|org)\.|\bfun\s+\w+\(|^\s*(val|var)\s+\w+\s*[=:]"):
        return "kotlin"
    if r(r"^\s*(implementation|api|dependencies|exclude)\b"):
        return "gradle"
    if r(r"^\s*def\s+\w+\(|^from\s+[\w.]+\s+import|^import\s+\w+$"):
        return "python"
    if r(r"^\s*(\$ |pip |pipx |curl |gcloud |export |brew |sudo )"):
        return "bash"
    if r(r'^\s*[{\[]\s*$|"mcpServers"'):
        return "json"
    return ""


def blocs(txt: str):
    out = []
    for m in FENCE_RX.finditer(txt):
        code = re.sub(r"^" + re.escape(m.group("ind")), "", m.group("body"), flags=re.M)
        out.append(((m.group("lang") or deviner(code)).lower(), code))
    return out


def etapes(txt: str):
    return [re.sub(r"\s+", " ", m.group(1)).strip() for m in re.finditer(r"^\s*[-*]\s+\[[ xX]\]\s+(.+(?:\n(?!\s*[-*]\s|\s*\n|#).+)*)", txt, re.M)]


def section(txt: str, motif: str) -> str:
    lignes, out, niveau = txt.splitlines(), [], None
    for l in lignes:
        m = re.match(r"^(#{1,6})\s+(.*)$", l)
        if m:
            if niveau is not None and len(m.group(1)) <= niveau:
                niveau = None
            if niveau is None and motif.lower() in m.group(2).lower():
                niveau = len(m.group(1))
        if niveau is not None:
            out.append(l)
    if not out:
        fail("section introuvable : %s" % motif)
    return "\n".join(out)


def appliquer(txt: str, sets: dict) -> str:
    for k, v in sets.items():
        txt = txt.replace(k, v)
    return txt


def main_guide(a) -> int:
    g = guides()
    if a.liste:
        res = [{"guide": k, "titre": titre(p.read_text(encoding="utf-8")), "blocs_code": len(blocs(p.read_text(encoding="utf-8")))} for k, p in g.items()]
        print(json.dumps(res, ensure_ascii=False) if a.json else "\n".join(f"{r['guide']:<45} {r['blocs_code']:>3} bloc(s)  {r['titre']}" for r in res))
        return 0
    if a.placeholders:
        cibles = [trouver(a.guide)] if a.guide else list(g.values())
        trouves = {}
        for p in cibles:
            for m in PLACEHOLDER_RX.findall(p.read_text(encoding="utf-8")):
                trouves.setdefault(m, set()).add(p.stem)
        res = {k: sorted(v) for k, v in sorted(trouves.items())}
        print(json.dumps(res, ensure_ascii=False) if a.json else "\n".join(f"{k}  ← {', '.join(v)}" for k, v in res.items()))
        return 0
    if not a.guide:
        fail("indiquez un GUIDE (ou --liste)", 2)
    p = trouver(a.guide)
    txt = p.read_text(encoding="utf-8")
    sets = {}
    for s in a.set or []:
        if "=" not in s:
            fail("--set attend CLE=VALEUR", 2)
        k, v = s.split("=", 1)
        sets[k] = v
    if a.section:
        txt = section(txt, a.section)
    if a.ecrire:
        dest = Path(a.ecrire)
        dest.mkdir(parents=True, exist_ok=True)
        ecrits = []
        for i, (lang, code) in enumerate(blocs(txt), 1):
            f = dest / f"{p.stem}-{i:02d}.{EXT.get(lang, lang or 'txt')}"
            f.write_text(appliquer(code, sets), encoding="utf-8")
            ecrits.append(str(f))
        print(json.dumps({"ecrits": ecrits}, ensure_ascii=False) if a.json else "\n".join(ecrits) or "aucun bloc de code")
        return 0
    if a.etapes:
        res = etapes(txt)
        print(json.dumps(res, ensure_ascii=False) if a.json else "\n".join(f"[ ] {e}" for e in res))
        return 0
    if a.code:
        res = [{"langage": l, "code": appliquer(c, sets)} for l, c in blocs(txt)]
        print(json.dumps(res, ensure_ascii=False) if a.json else "\n\n".join(f"# --- {r['langage'] or 'texte'}\n{r['code']}" for r in res))
        return 0
    print(json.dumps({"guide": p.stem, "texte": appliquer(txt, sets)}, ensure_ascii=False) if a.json else appliquer(txt, sets))
    return 0


def _http(methode: str, url: str, corps=None):
    import urllib.request, urllib.error
    jeton = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if not jeton:
        fail("variable GOOGLE_ACCESS_TOKEN absente (ex. : export GOOGLE_ACCESS_TOKEN=$(gcloud auth application-default print-access-token))")
    req = urllib.request.Request(url, method=methode, data=None if corps is None else json.dumps(corps).encode(),
                                 headers={"Authorization": "Bearer " + jeton, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        fail("HTTP %s : %s" % (e.code, e.read().decode("utf-8", "replace")[:400]))
    except urllib.error.URLError as e:
        fail("réseau : %s" % e.reason)

def cmd_rapport(a) -> int:
    if not (a.property and a.property.isdigit()):
        fail("--property : identifiant numérique de la propriété GA4 requis", 2)
    noms = lambda s: [x for x in (s or "").split(",") if x]
    for n in noms(a.dimensions) + noms(a.metrics):
        if not re.fullmatch(r"[A-Za-z0-9_:]+", n):
            fail("nom de dimension/métrique invalide : %s" % n, 2)
    corps = {"dateRanges": [{"startDate": a.debut, "endDate": a.fin}], "dimensions": [{"name": n} for n in noms(a.dimensions)],
             "metrics": [{"name": n} for n in noms(a.metrics)], "limit": str(a.limite)}
    url = "https://analyticsdata.googleapis.com/v1beta/properties/%s:runReport" % a.property
    if not a.envoyer:
        print(json.dumps({"url": url, "corps": corps}, ensure_ascii=False))
        return 0
    rep = _http("POST", url, corps)
    cols = [h["name"] for h in rep.get("dimensionHeaders", [])] + [h["name"] for h in rep.get("metricHeaders", [])]
    lignes = [[v.get("value", "") for v in r.get("dimensionValues", [])] + [v.get("value", "") for v in r.get("metricValues", [])] for r in rep.get("rows", [])]
    print(json.dumps({"colonnes": cols, "lignes": lignes, "total": rep.get("rowCount", len(lignes))}, ensure_ascii=False) if a.json
          else "\t".join(cols) + "\n" + "\n".join("\t".join(l) for l in lignes))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("guide", nargs="?", help="nom (ou partie du nom) d'un guide")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--code", action="store_true", help="uniquement les blocs de code")
    ap.add_argument("--etapes", action="store_true", help="uniquement les cases à cocher du workflow")
    ap.add_argument("--section", help="uniquement la section dont le titre contient ce texte")
    ap.add_argument("--set", action="append", metavar="CLE=VAL", help="remplace CLE par VAL dans la sortie")
    ap.add_argument("--ecrire", metavar="DOSSIER", help="écrit chaque bloc de code dans un fichier")
    ap.add_argument("--placeholders", action="store_true")
    ap.add_argument("--json", action="store_true")
    g = ap.add_argument_group("rapport GA4 (runReport)")
    g.add_argument("--rapport", action="store_true", help="construit (et avec --envoyer, exécute) un runReport")
    g.add_argument("--property", help="identifiant numérique de la propriété")
    g.add_argument("--dimensions", default="date", help="liste séparée par des virgules")
    g.add_argument("--metrics", default="activeUsers", help="liste séparée par des virgules")
    g.add_argument("--debut", default="7daysAgo")
    g.add_argument("--fin", default="today")
    g.add_argument("--limite", type=int, default=100)
    g.add_argument("--envoyer", action="store_true", help="appelle l'API (jeton dans GOOGLE_ACCESS_TOKEN)")
    a = ap.parse_args(argv)
    try:
        if a.rapport:
            return cmd_rapport(a)
        return main_guide(a)
    except BrokenPipeError:
        return 0
    except OSError as e:
        fail(str(e))


if __name__ == "__main__":
    sys.exit(main())
