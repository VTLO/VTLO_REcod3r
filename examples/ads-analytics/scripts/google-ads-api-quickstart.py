#!/usr/bin/env python3
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args"], "sortie": "json", "familles": ["text", "fs"], "ia": false}
"""google-ads-api-quickstart — démarrage de l'API Google Ads (6 langages + REST) + fichier google-ads.yaml (version script du skill « google-ads-api-quickstart »).

Sert les guides du skill (code, étapes, sections) SANS passer par l'IA : 0 token.
Les guides sont lus dans data/google-ads-api-quickstart/ (copie du skill d'origine, à côté du dossier scripts/).

Usage :
  google-ads-api-quickstart.py --liste                         guides disponibles
  google-ads-api-quickstart.py GUIDE [--code] [--etapes] [--section TITRE] [--set CLE=VAL ...] [--ecrire DOSSIER] [--json]
  google-ads-api-quickstart.py --placeholders [GUIDE]          valeurs à remplacer (ex. identifiants à renseigner)

Contrat : 0 ok · 1 échec (message sur stderr) · 2 usage · 3 décision IA requise (jamais utilisé ici).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SLUG = "google-ads-api-quickstart"
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


def cmd_yaml(a) -> int:
    champs = [("developer_token", "GOOGLE_ADS_DEVELOPER_TOKEN", "INSERT_DEVELOPER_TOKEN_HERE"), ("client_id", "GOOGLE_ADS_CLIENT_ID", "INSERT_OAUTH_CLIENT_ID_HERE"),
              ("client_secret", "GOOGLE_ADS_CLIENT_SECRET", "INSERT_OAUTH_CLIENT_SECRET_HERE"), ("refresh_token", "GOOGLE_ADS_REFRESH_TOKEN", "INSERT_OAUTH_REFRESH_TOKEN_HERE")]
    lignes, manquants = [], []
    for cle, env, defaut in champs:
        v = os.environ.get(env)
        if not v:
            manquants.append(env)
        lignes.append("%s: %s" % (cle, v or defaut))
    login = re.sub(r"\D", "", os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""))
    if os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID") and len(login) != 10:
        fail("GOOGLE_ADS_LOGIN_CUSTOMER_ID : 10 chiffres attendus, sans tirets")
    if login:
        lignes.append("login_customer_id: %s" % login)
    lignes.append("use_proto_plus: True")
    dest = Path(a.sortie)
    if dest.exists() and not a.force:
        fail("%s existe déjà (--force pour écraser)" % dest)
    dest.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    os.chmod(dest, 0o600)
    print(json.dumps({"ecrit": str(dest), "a_renseigner": manquants}, ensure_ascii=False) if a.json else "écrit : %s (droits 600)%s" % (dest, ("\nà renseigner : " + ", ".join(manquants)) if manquants else ""))
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
    g = ap.add_argument_group("fichier google-ads.yaml")
    g.add_argument("--yaml", action="store_true", help="écrit google-ads.yaml depuis les variables GOOGLE_ADS_* (jamais de secret en argument)")
    g.add_argument("--sortie", default=str(Path.home() / "google-ads.yaml"))
    g.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.yaml:
            return cmd_yaml(a)
        return main_guide(a)
    except BrokenPipeError:
        return 0
    except OSError as e:
        fail(str(e))


if __name__ == "__main__":
    sys.exit(main())
