#!/usr/bin/env python3
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args"], "sortie": "json", "familles": ["security", "text", "fs"], "ia": true}
"""google-mobile-ads-validate — audit d'un projet Google Mobile Ads (Android, iOS, Unity) sans IA.

Cinq contrôles : identifiant d'application, blocs d'annonces de test, SKAdNetwork, compatibilité des adaptateurs de médiation,
préchargement. Sortie : tableau Markdown (« Check | Status | Findings | Next Steps ») ou --json.

Usage : google-mobile-ads-validate.py [DOSSIER_PROJET] [--check app-id|ad-units|skadnetwork|mediation|preloading|all] [--json]

Contrat : 0 ok (aucun Fail) · 1 au moins un Fail · 2 usage · 3 décision IA requise (versions GMA exigées par les adaptateurs de médiation :
l'IA répond via RECOD3R_AI_ANSWER = {"nom_adaptateur": "major.minor.patch"} ; le script revalide et conclut).
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import sys
from pathlib import Path

SKIP = {".git", "node_modules", "build", "Pods", "DerivedData", ".gradle", ".idea", "Library", "Temp", "obj", "Carthage", ".build"}
SRC = (".kt", ".java", ".swift", ".m", ".mm", ".h", ".cs", ".plist", ".xml", ".gradle", ".kts", ".asset", ".json", ".yaml", ".yml", ".toml")
MAX_BYTES = 2_000_000
TEST_APP = {"ca-app-pub-3940256099942544~1458002511": "AdMob (iOS)", "ca-app-pub-3940256099942544~3347511713": "AdMob (Android)",
            "ca-app-pub-9939518381636264~1458516390": "Ad Manager"}
APP_RX = re.compile(r"^(ca-app-pub-[a-zA-Z0-9\-]+)~(.*)$")
ADMOB_UNIT_RX = re.compile(r"^(ca-app-pub-[a-zA-Z0-9\-]+)/([a-zA-Z0-9_\-]+)(/.*)?$")
GAM_UNIT_RX = re.compile(r"^/[0-9]*/.*|^/[0-9]*,[0-9]*/.*")
CHECKS = ["app-id", "ad-units", "skadnetwork", "mediation", "preloading"]
LIBELLE = {"app-id": "No test application ID is in the project, format correct", "ad-units": "No test ad units are in the project, format correct",
           "skadnetwork": "Implemented all Google SKAdNetwork IDs", "mediation": "Mediation adapter compatibility",
           "preloading": "Ad preloading validation checks"}


class Decision(Exception):
    """Le contrôle a besoin d'une réponse de l'IA : le reste de l'audit continue."""

    def __init__(self, question, contexte):
        self.question, self.contexte = question, contexte


def reponse_ia():
    brut = os.environ.get("RECOD3R_AI_ANSWER")
    return json.loads(brut) if brut else None


def fichiers(racine: Path):
    for dp, dn, fn in os.walk(racine):
        dn[:] = [d for d in dn if d not in SKIP and not d.startswith(".git")]
        for f in fn:
            p = Path(dp) / f
            if p.suffix.lower() in SRC and p.stat().st_size <= MAX_BYTES:
                yield p


def lire(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def rel(p: Path, racine: Path) -> str:
    return str(p.relative_to(racine))


def plateformes(racine: Path) -> set:
    pf = set()
    for p in fichiers(racine):
        n = p.name
        if n in ("AndroidManifest.xml",) or n.startswith("build.gradle"):
            pf.add("android")
        elif n == "Info.plist" or p.suffix in (".swift", ".m", ".mm"):
            pf.add("ios")
    if (racine / "ProjectSettings").is_dir() or (racine / "Assets").is_dir():
        pf.add("unity")
    return pf


# ------------------------------------------------------------------ 1. identifiant d'application
def trouver_app_ids(racine: Path):
    ids = []  # (plateforme, id, fichier)
    rx_android = re.compile(r"InitializationConfig\.Builder\(\s*[\"']([^\"']*)[\"']")
    rx_manifest = re.compile(r"com\.google\.android\.gms\.ads\.APPLICATION_ID[\"']?\s+android:value=[\"']([^\"']*)[\"']")
    rx_unity = re.compile(r"^\s*(adMobAndroidAppId|adMobIOSAppId)\s*:\s*(.*)$", re.M)
    for p in fichiers(racine):
        t = lire(p)
        if p.suffix in (".kt", ".java"):
            ids += [("android", m.group(1), rel(p, racine)) for m in rx_android.finditer(t)]
        elif p.name == "AndroidManifest.xml":
            ids += [("android", m.group(1), rel(p, racine)) for m in rx_manifest.finditer(t)]
        elif p.name == "Info.plist":
            try:
                d = plistlib.loads(p.read_bytes())
                if "GADApplicationIdentifier" in d:
                    ids.append(("ios", str(d["GADApplicationIdentifier"]), rel(p, racine)))
            except Exception:
                m = re.search(r"<key>GADApplicationIdentifier</key>\s*<string>([^<]*)</string>", t)
                if m:
                    ids.append(("ios", m.group(1), rel(p, racine)))
        elif p.suffix == ".asset":
            for m in rx_unity.finditer(t):
                ids.append(("android" if "Android" in m.group(1) else "ios", m.group(2).strip().strip("'\""), rel(p, racine)))
    return ids


def check_app_id(racine: Path, pf: set):
    ids = trouver_app_ids(racine)
    if not ids:
        return "Fail", "No application ID found in the project.", "Set the application ID (InitializationConfig.Builder / GADApplicationIdentifier / Unity settings)."
    fails, warns = [], []
    for plat, v, f in ids:
        if not APP_RX.match(v):
            fails.append(f"{v or '(empty)'} in {f} does not match the required format")
        if v in TEST_APP:
            warns.append(f"official test application ID ({TEST_APP[v]}) in {f}")
    for plat in {p for p, _, _ in ids}:
        distincts = {v for p, v, _ in ids if p == plat}
        if len(distincts) > 1:
            fails.append(f"multiple distinct {plat} application IDs without flavor/environment separation: {', '.join(sorted(distincts))}")
    if fails:
        return "Fail", "; ".join(fails), "Fix the application ID format / keep a single ID per platform or separate by flavor."
    if warns:
        return "Warning", "; ".join(warns), "Replace the test application ID with your own before release."
    return "Pass", f"{len(ids)} application ID(s) valid.", "—"


# ------------------------------------------------------------------ 2. blocs d'annonces
def check_ad_units(racine: Path, pf: set):
    rx = re.compile(r"[\"'](ca-app-pub-[^\"'\s~]*/[^\"'\s]*|/[0-9]+(?:,[0-9]+)?/[^\"'\s]+)[\"']")
    mal, tests = [], []
    for p in fichiers(racine):
        if p.suffix in (".plist", ".asset", ".json", ".yaml", ".yml", ".toml", ".gradle", ".kts"):
            continue
        for m in rx.finditer(lire(p)):
            u = m.group(1)
            if u.startswith("ca-app-pub-"):
                if not ADMOB_UNIT_RX.match(u):
                    mal.append(f"{u} ({rel(p, racine)})")
                elif u.startswith("ca-app-pub-3940256099942544/"):
                    tests.append(f"{u} ({rel(p, racine)})")
            elif not GAM_UNIT_RX.match(u):
                mal.append(f"{u} ({rel(p, racine)})")
            elif u.startswith(("/6499/", "/21775744923/")):
                tests.append(f"{u} ({rel(p, racine)})")
    if mal:
        return "Fail", "malformed ad unit ID(s): " + "; ".join(sorted(set(mal))[:8]), "Correct the ad unit ID format."
    if tests:
        return "Warning", "test ad unit ID(s) found: " + "; ".join(sorted(set(tests))[:8]), "Replace test ad units with production ones (even if gated behind DEBUG)."
    return "Pass", "no test or malformed ad unit IDs.", "—"


# ------------------------------------------------------------------ 3. SKAdNetwork
def ids_google(racine: Path) -> set:
    """IDs Google : lus dans la référence du skill (data/<slug>/references/google-skadnetwork-ids.md), à côté de scripts/."""
    cands = [os.environ.get("RECOD3R_DATA"), Path(__file__).resolve().parent.parent / "data" / "google-mobile-ads-validate"]
    for c in cands:
        f = Path(c or "") / "references" / "google-skadnetwork-ids.md"
        if f.is_file():
            return set(re.findall(r"\"([a-z0-9]+\.skadnetwork)\"", f.read_text(encoding="utf-8")))
    print("google-mobile-ads-validate : référence SKAdNetwork introuvable (data/google-mobile-ads-validate/references/)", file=sys.stderr)
    raise SystemExit(1)


def check_skadnetwork(racine: Path, pf: set):
    if "ios" not in pf and "unity" not in pf:
        return "N/A", "project targets Android only.", "—"
    presents, trouve_liste = set(), False
    for p in fichiers(racine):
        if p.name == "Info.plist":
            try:
                d = plistlib.loads(p.read_bytes())
            except Exception:
                continue
            if "SKAdNetworkItems" in d:
                trouve_liste = True
                presents |= {str(i.get("SKAdNetworkIdentifier", "")).lower() for i in d["SKAdNetworkItems"] if isinstance(i, dict)}
        elif p.name == "GoogleMobileAdsSKAdNetworkItems.xml":
            trouve_liste = True
            presents |= set(re.findall(r"[a-z0-9]+\.skadnetwork", lire(p).lower()))
    if "ios" not in pf and not trouve_liste and not any(racine.rglob("Info.plist")):
        return "N/A", "Unity project targeting Android only (no iOS artefacts).", "—"
    if not trouve_liste:
        return "Fail", "SKAdNetworkItems array is missing.", "Add the SKAdNetworkItems array with all Google SKAdNetwork IDs."
    manquants = sorted(ids_google(racine) - presents)
    if manquants:
        return "Fail", f"{len(manquants)} Google SKAdNetwork ID(s) missing: {', '.join(manquants[:10])}{'…' if len(manquants) > 10 else ''}", "Add the missing SKAdNetwork IDs."
    return "Pass", "all Google SKAdNetwork IDs present.", "—"


# ------------------------------------------------------------------ 4. médiation
def versions(s: str):
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", s.strip())
    return tuple(int(x or 0) for x in m.groups()) if m else None


def check_mediation(racine: Path, pf: set):
    declare, adaptateurs = None, []
    for p in fichiers(racine):
        n = p.name
        t = lire(p) if (n.startswith("build.gradle") or n in ("Podfile", "Package.swift", "GoogleMobileAdsDependencies.xml") or p.suffix == ".podspec") else ""
        for m in re.finditer(r"com\.google\.android\.libraries\.ads\.mobile\.sdk:ads-mobile-sdk:([\w.\-]+)", t):
            declare = declare or m.group(1)
        for m in re.finditer(r"pod\s+['\"]Google-Mobile-Ads-SDK['\"]\s*,\s*['\"]~?>?\s*=?\s*([\d.]+)", t):
            declare = declare or m.group(1)
        for m in re.finditer(r"com\.google\.ads\.mediation:([\w\-]+):([\w.\-]+)", t):
            adaptateurs.append(("android", m.group(1), m.group(2)))
        for m in re.finditer(r"pod\s+['\"](GoogleMobileAdsMediation[\w]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?", t):
            adaptateurs.append(("ios", m.group(1), m.group(2) or ""))
    if not adaptateurs:
        return "N/A", "no mediation adapters in the project.", "—"
    noms = sorted({a[1] for a in adaptateurs})
    rep = reponse_ia()
    if rep is None:
        raise Decision("Pour chaque adaptateur de médiation, quelle version du SDK GMA exige-t-il (major.minor.patch) ? Répondre en JSON {adaptateur: version}.",
                       {"adaptateurs": noms, "version_gma_declaree": declare})
    if not isinstance(rep, dict) or not all(isinstance(k, str) and isinstance(v, str) and versions(v) for k, v in rep.items()):
        print("réponse IA invalide : attendu {adaptateur: 'x.y.z'}", file=sys.stderr)
        raise SystemExit(1)
    req = {k: versions(v) for k, v in rep.items() if k in noms}
    majeurs = {v[0] for v in req.values()}
    if declare and versions(declare):
        d = versions(declare)
        mauvais = [k for k, v in req.items() if v[0] != d[0]]
        if mauvais:
            return "Fail", f"adapter(s) requiring another GMA major than {declare}: {', '.join(mauvais)}", "Align adapter versions with the declared GMA SDK."
        if len(majeurs) > 1:
            return "Fail", "adapters require different GMA SDK majors.", "Align adapter versions."
        hauts = [k for k, v in req.items() if (v[0], v[1]) > (d[0], d[1])]
        if hauts:
            return "Warning", f"adapter(s) requiring a GMA minor higher than {declare}: {', '.join(hauts)}", "Raise the declared GMA SDK version."
        return "Pass", "adapters compatible with the declared GMA SDK version.", "—"
    if len(majeurs) > 1:
        return "Fail", "adapters require different GMA SDK majors.", "Align adapter versions."
    return "Warning", "GMA SDK version not declared explicitly (transitive dependency).", "Declare the GMA SDK dependency explicitly."


# ------------------------------------------------------------------ 5. préchargement
API = {"start": r"startPreload|\.preload\(|\bPreload\(", "stop": r"destroyAll|stopPreloadingAndRemoveAllAds|DestroyAll",
       "poll": r"pollAd|ad\(withPreloadID|DequeueAd", "cb": r"onAdPreloaded|onAdsExhausted|adAvailable\(forPreloadID|adsExhausted\(forPreloadID|OnAdPreloaded|OnAdsExhausted",
       "show": r"\.show\(|\.present\(|\.Show\(|\bshow\("}
FUNC_RX = re.compile(r"(?:fun|func|void|public|private|protected|override|internal)\s+[^\n{;=]*\([^)]*\)[^{;\n]*\{")


def corps_autour(t: str, pos: int):
    """Corps de la fonction qui contient pos (accolades équilibrées)."""
    for m in reversed([m for m in FUNC_RX.finditer(t) if m.start() <= pos]):
        i, d = m.end() - 1, 0
        for j in range(i, len(t)):
            d += (t[j] == "{") - (t[j] == "}")
            if d == 0:
                if j >= pos:
                    return m.group(0), t[i:j + 1]
                break
    return None, ""


def check_preloading(racine: Path, pf: set):
    fails, warns, utilise, ids = [], [], False, {}
    for p in fichiers(racine):
        if p.suffix not in (".kt", ".java", ".swift", ".m", ".mm", ".cs"):
            continue
        t = lire(p)
        if not re.search(API["start"] + "|" + API["poll"] + "|" + API["cb"], t):
            continue
        starts = [m for m in re.finditer(API["start"], t)]
        if starts and not re.search(r"PreloadConfiguration|PreloadId|preloadId|PreloadID", t):
            starts = []
        utilise = utilise or bool(starts) or bool(re.search(API["poll"], t))
        f = rel(p, racine)
        for m in re.finditer(API["poll"], t):
            _, c = corps_autour(t, m.start())
            if c and not re.search(API["show"], c):
                fails.append(f"ad polled without being shown in the same method ({f})")
        for m in re.finditer(r"(?:" + API["cb"] + r")[^{;\n]*\{", t):
            _, c = corps_autour(t, m.end() - 1)
            c = c or ""
            if re.search(API["start"], c):
                fails.append(f"preloading started inside a preloaded/exhausted callback ({f})")
            if re.search(API["stop"], c):
                fails.append(f"preloading stopped inside a preloaded/exhausted callback ({f})")
        for m in re.finditer(r"(?:startPreload|Preload)\(\s*(\"[^\"]*\"|null|nil)", t):
            v = m.group(1)
            if v in ('""', "null", "nil"):
                fails.append(f"empty/null preload ID ({f})")
            else:
                ids.setdefault(v, []).append(f)
        if p.suffix == ".cs":
            for m in re.finditer(r"void\s+Update\s*\(\s*\)\s*\{", t):
                _, c = corps_autour(t, m.end() - 1)
                if re.search(r"IsAdAvailable", c or ""):
                    fails.append(f"ad availability checked inside Update() ({f})")
    for v, fs in ids.items():
        if len(fs) > 1 and not any(re.search(API["stop"], lire(racine / x)) for x in fs):
            fails.append(f"preloading started {len(fs)} times for preload ID {v} without stopping first")
    if not utilise:
        return "N/A", "the project does not use the ad preloading APIs.", "—"
    if fails:
        return "Fail", "; ".join(sorted(set(fails))[:8]), "Fix the preloading patterns."
    if len(ids) > 1:
        return "Warning", f"{len(ids)} distinct preload IDs preloaded.", "Preload a single ad unit per ad format."
    return "Pass", "preloading usage looks correct.", "—"


FONCTIONS = {"app-id": check_app_id, "ad-units": check_ad_units, "skadnetwork": check_skadnetwork, "mediation": check_mediation, "preloading": check_preloading}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("projet", nargs="?", default=".", help="dossier du projet (défaut : .)")
    ap.add_argument("--check", action="append", choices=CHECKS + ["all"], help="contrôle(s) à exécuter (défaut : all)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    racine = Path(a.projet).resolve()
    if not racine.is_dir():
        print(f"google-mobile-ads-validate : dossier introuvable : {racine}", file=sys.stderr)
        return 2
    choix = CHECKS if not a.check or "all" in a.check else [c for c in CHECKS if c in a.check]
    pf = plateformes(racine)
    res, attente = [], None
    for c in choix:
        try:
            st, fi, ns = FONCTIONS[c](racine, pf)
        except Decision as d:
            attente = {"needs_ai": d.question, "context": d.contexte}
            st, fi, ns = "Pending", "waiting for the AI answer (see needs_ai)", "Relaunch with RECOD3R_AI_ANSWER."
        res.append({"check": LIBELLE[c], "status": st, "findings": fi, "next_steps": ns})
    if a.json:
        print(json.dumps({"plateformes": sorted(pf), "resultats": res, **(attente or {})}, ensure_ascii=False))
    else:
        print("| Check | Status | Findings | Next Steps |\n| :--- | :---: | :--- | :--- |")
        for r in res:
            print(f"| {r['check']} | {r['status']} | {r['findings'].replace('|', '/')} | {r['next_steps']} |")
        if attente:
            print(json.dumps(attente, ensure_ascii=False))
    if attente:
        return 3
    return 1 if any(r["status"] == "Fail" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
