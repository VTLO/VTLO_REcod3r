#!/usr/bin/env python3
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args", "fichier"], "sortie": "text+json", "familles": ["refactor", "text", "mobile"], "ia": "partielle"}
"""google-mobile-ads-android-migrate-to-next-gen — migration Android GMA (play-services-ads) → GMA Next-Gen SDK.

Partie mécanique (sans IA) : renommage des imports d'après le tableau « API Mapping » du skill (data/<slug>/SKILL.md),
Gradle (dépendance, minSdk 24+, compileSdk 34+, exclusions globales), contrôle du meta-data APPLICATION_ID, repérage
des appels à refactorer (signatures, threads UI, mediation…). Les classes `Adapter` de mediation ne sont jamais touchées.
Partie réflexive (IA) : refactor structurel des appels (AdRequest.Builder(adUnitId), load() sans Context, callbacks…) — la liste
exacte fichier:ligne est fournie en JSON avec exit 3.

Usage : google-mobile-ads-android-migrate-to-next-gen.py PROJET [--appliquer] [--version X.Y.Z] [--sans-sauvegarde] [--json]
  (sans --appliquer : simulation, rien n'est écrit)
Version du SDK : --version, sinon maven-metadata.xml de Google, sinon réponse IA dans RECOD3R_AI_ANSWER (revalidée par regex).
Contrat : 0 ok · 1 échec · 2 usage · 3 décision IA requise (JSON {"needs_ai":…,"context":…} sur stdout).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

OLD_PKG = "com.google.android.gms.ads."
NEW_PKG = "com.google.android.libraries.ads.mobile.sdk."
NEW_DEP = "com.google.android.libraries.ads.mobile.sdk:ads-mobile-sdk"
META_URL = "https://dl.google.com/dl/android/maven2/com/google/android/libraries/ads/mobile/sdk/ads-mobile-sdk/maven-metadata.xml"
SKIP_DIRS = {"build", ".gradle", ".git", ".idea", "node_modules", "Pods"}
TOKEN = re.compile(r"^([a-z]+\.)*[A-Z]\w*(\.[A-Z]\w*)*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+([-.][\w.]+)?$")

# motifs d'appels Old SDK à refactorer (déduits des tables Method Mapping / Core Migration Rules)
APPELS = [
    (r"\bAdRequest\.Builder\(\s*\)", "AdRequest.Builder() → AdRequest.Builder(adUnitId) (ou BannerAdRequest / NativeAdRequest)"),
    (r"\b(InterstitialAd|RewardedAd|RewardedInterstitialAd|AppOpenAd)\.load\(\s*\w+\s*,", "load(Context, adUnitId, request, cb) → load(request, AdLoadCallback<…>) (plus de Context)"),
    (r"\.loadAd\(", "loadAd(AdRequest) → loadAd(BannerAdRequest, AdLoadCallback<BannerAd>) / NativeAdLoader.load"),
    (r"\bMobileAds\.initialize\(", "initialize : appeler hors thread UI, avec InitializationConfig(applicationId lu dans le manifeste)"),
    (r"\bMobileAds\.setRequestConfiguration\(", "setRequestConfiguration avant init interdit → InitializationConfig.Builder.setRequestConfiguration()"),
    (r"\bFullScreenContentCallback\b", "FullScreenContentCallback → <Format>AdEventCallback (onAdShowedFullScreenContent / onAdDismissedFullScreenContent)"),
    (r"\bAdListener\b", "AdListener → AdLoadCallback / BannerAdEventCallback / NativeAdEventCallback"),
    (r"\bOnPaidEventListener\b|\bsetOnPaidEventListener\b", "paid event → AdEventCallback.onAdPaid(value)"),
    (r"\.setNativeAd\(", "setNativeAd → registerNativeAd(nativeAd, mediaView)"),
    (r"\bNativeCustomFormatAd\b", "NativeCustomFormatAd → CustomNativeAd"),
    (r"\bAdManagerAdRequest\b|\bAdManagerAdView\b", "classes Ad Manager fusionnées dans AdRequest / banner.AdView"),
    (r"\bmuteThisAd\b|MuteThisAd", "« Mute This Ad » non supporté : supprimer la logique"),
    (r"\.(pause|resume)\(\)", "AdView.pause()/resume() n'existent plus"),
    (r"\bmediaView\b", "NativeAd n'a plus de variable mediaView"),
    (r"getMediationAdapterClassName|getAdapterResponses|getLoadedAdapterResponseInfo", "ResponseInfo : adapterClassName / adSourceResponses / loadedAdSourceResponseInfo"),
]


class Decision(Exception):
    def __init__(self, needs, context):
        self.needs, self.context = needs, context


def fail(msg, code=1):
    print(f"google-mobile-ads-android-migrate-to-next-gen : {msg}", file=sys.stderr)
    raise SystemExit(code)


# ---------------------------------------------------------------- tableau de correspondance
def skill_md() -> Path | None:
    home = Path(os.environ.get("RECOD3R_DATA", ""))
    cands = [home / "google-mobile-ads-android-migrate-to-next-gen" / "SKILL.md"] if str(home) else []
    here = Path(__file__).resolve().parent
    cands += [here.parent / "data" / "google-mobile-ads-android-migrate-to-next-gen" / "SKILL.md",
              here / "data" / "google-mobile-ads-android-migrate-to-next-gen" / "SKILL.md"]
    return next((c for c in cands if c.is_file()), None)


def _jetons(cell: str) -> list[str]:
    t = cell
    while True:                                   # retire les notes entre parenthèses (imbriquées)
        n = re.sub(r"\([^()]*\)", "", t)
        if n == t:
            break
        t = n
    t = t.replace("*Format specific*", "")
    return [x for x in re.findall(r"`([^`]+)`", t) if TOKEN.match(x)]


def charger_mapping() -> tuple[dict[str, str], list[str]]:
    p = skill_md()
    if not p:
        fail("SKILL.md introuvable (définir RECOD3R_DATA ou lancer depuis le dossier livré avec data/)")
    txt = p.read_text(encoding="utf-8")
    m = re.search(r"^## API Mapping\s*$(.*?)^## ", txt + "\n## ", re.S | re.M)
    if not m:
        fail("section « API Mapping » absente du SKILL.md")
    cands: dict[str, set[str]] = {}
    for ligne in m.group(1).splitlines():
        cells = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[1].strip("`"):
            continue
        olds, news = _jetons(cells[1]), _jetons(cells[2])
        for o in olds:
            simple = o.rsplit(".", 1)[-1]
            hit = [n for n in news if n.rsplit(".", 1)[-1] == simple]
            if len(hit) != 1 and len(olds) == 1 and len(news) == 1:
                hit = news
            if len(hit) == 1 and "." not in o.replace(o.split(".")[0] + ".", "", 1).replace(".", "") or len(hit) == 1:
                cands.setdefault(o, set()).add(hit[0])
    mapping, ambigus = {}, []
    for o, ns in cands.items():
        if len(ns) == 1 and not (o.count(".") >= 1 and o.split(".")[-2][:1].isupper()):   # classes imbriquées : manuel
            mapping[OLD_PKG + o] = NEW_PKG + next(iter(ns))
        else:
            ambigus.append(o)
    mapping.setdefault(OLD_PKG + "AdRequest", NEW_PKG + "common.AdRequest")   # la cellule du tableau ne le liste qu'entre parenthèses
    ambigus = [o for o in ambigus if OLD_PKG + o not in mapping]
    return mapping, ambigus


# ---------------------------------------------------------------- parcours
def fichiers(racine: Path):
    for d, ds, fs in os.walk(racine):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        for f in fs:
            yield Path(d) / f


def sauver(p: Path, nouveau: str, a):
    if a.appliquer and nouveau != p.read_text(encoding="utf-8", errors="replace"):
        if not a.sans_sauvegarde and not p.with_name(p.name + ".orig").exists():
            shutil.copy2(p, p.with_name(p.name + ".orig"))
        p.write_text(nouveau, encoding="utf-8")


def version_sdk(a) -> str:
    if a.version:
        if not VERSION.match(a.version):
            fail("--version invalide", 2)
        return a.version
    try:
        import urllib.request
        with urllib.request.urlopen(META_URL, timeout=15) as r:
            m = re.search(r"<latest>([^<]+)</latest>", r.read().decode("utf-8", "replace"))
        if m and VERSION.match(m.group(1)):
            return m.group(1)
    except Exception:
        pass
    rep = os.environ.get("RECOD3R_AI_ANSWER", "").strip()
    if rep:
        if VERSION.match(rep):
            return rep
        fail("RECOD3R_AI_ANSWER invalide : une version X.Y.Z est attendue")
    raise Decision("version_sdk", {"question": "Dernière version stable de com.google.android.libraries.ads.mobile.sdk:ads-mobile-sdk ? (réseau indisponible)",
                                   "format_reponse": "X.Y.Z dans RECOD3R_AI_ANSWER, ou relancer avec --version"})


def gradle(p: Path, a, ver: str, rapport: list):
    t = o = p.read_text(encoding="utf-8", errors="replace")
    kts = p.name.endswith(".kts")
    if re.search(r"com\.google\.android\.gms:play-services-ads(-lite)?", t):
        # remplace la ligne de dépendance par la nouvelle (une seule occurrence conservée)
        t = re.sub(r"(['\"])com\.google\.android\.gms:play-services-ads(?:-lite)?(?::[^'\"]*)?\1", lambda m: f"{m.group(1)}{NEW_DEP}:{ver}{m.group(1)}", t)
        rapport.append((str(p), "dépendance", f"play-services-ads → ads-mobile-sdk:{ver}"))
    for cle, mini in (("minSdk", 24), ("compileSdk", 34)):
        def bump(m):
            v = int(m.group(3))
            if v < mini:
                rapport.append((str(p), cle, f"{v} → {mini}"))
                return f"{m.group(1)}{m.group(2)}{mini}"
            return m.group(0)
        t = re.sub(rf"(\b{cle}(?:Version)?\b)(\s*=?\s*)(\d+)", bump, t)
    if (re.search(r"\bdependencies\s*\{", t) and NEW_DEP in t and "play-services-ads" not in t.split(NEW_DEP)[0][-0:] and
            not re.search(r"exclude\(?\s*(group\s*[:=]\s*)?['\"]com\.google\.android\.gms['\"]\s*,\s*(module\s*[:=]\s*)?['\"]play-services-ads['\"]", t)):
        bloc = ('\nconfigurations.all {\n    exclude(group = "com.google.android.gms", module = "play-services-ads")\n    exclude(group = "com.google.android.gms", module = "play-services-ads-lite")\n}\n' if kts else
                "\nconfigurations.all {\n    exclude group: 'com.google.android.gms', module: 'play-services-ads'\n    exclude group: 'com.google.android.gms', module: 'play-services-ads-lite'\n}\n")
        t += bloc
        rapport.append((str(p), "exclusions", "play-services-ads / -lite exclus globalement"))
    if t != o:
        sauver(p, t, a)


def toml(p: Path, a, ver: str, rapport: list):
    t = o = p.read_text(encoding="utf-8", errors="replace")
    if "play-services-ads" in t:
        t = re.sub(r"com\.google\.android\.gms:play-services-ads(?:-lite)?", NEW_DEP, t)
        t = re.sub(r"group\s*=\s*\"com\.google\.android\.gms\"(\s*,\s*)name\s*=\s*\"play-services-ads(?:-lite)?\"", f'group = "com.google.android.libraries.ads.mobile.sdk"\\1name = "ads-mobile-sdk"', t)
        rapport.append((str(p), "catalogue", f"module remplacé — vérifier la version du catalogue (attendue : {ver})"))
    if t != o:
        sauver(p, t, a)


def manifeste(p: Path, rapport: list, audit: list):
    t = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'com\.google\.android\.gms\.ads\.APPLICATION_ID"\s*android:value="([^"]+)"|android:value="([^"]+)"\s*[^>]*?com\.google\.android\.gms\.ads\.APPLICATION_ID', t, re.S)
    if m:
        audit.append(("ok", str(p), "APPLICATION_ID présent : " + (m.group(1) or m.group(2)) + " (à passer à InitializationConfig ; balise à CONSERVER)"))
    elif "AndroidManifest" in p.name and "<application" in t:
        audit.append(("avertissement", str(p), "meta-data com.google.android.gms.ads.APPLICATION_ID absent"))


def source(p: Path, a, mapping: dict, rapport: list, restes: list):
    t = p.read_text(encoding="utf-8", errors="replace")
    if "com.google.android.gms.ads" not in t and not any(re.search(rx, t) for rx, _ in APPELS):
        return
    adapter = re.search(r"com\.google\.android\.gms\.ads\.mediation\.(Adapter|MediationAdapter)\b", t) and re.search(r"[:\s](Adapter|MediationAdapter)\b", t)
    lignes, nb = t.splitlines(keepends=True), 0
    for i, l in enumerate(lignes):
        m = re.match(r"^(\s*import\s+)(com\.google\.android\.gms\.ads\.[\w.]+)(.*)$", l.rstrip("\n"))
        if not m or adapter or ".mediation." in m.group(2):
            continue
        cible = mapping.get(m.group(2))
        if cible:
            lignes[i] = f"{m.group(1)}{cible}{m.group(3)}" + ("\n" if l.endswith("\n") else "")
            nb += 1
        else:
            restes.append((str(p), i + 1, f"import sans correspondance automatique : {m.group(2)}"))
        if re.match(r"^\s*import\s+com\.google\.android\.gms\.ads\.\*", l):
            restes.append((str(p), i + 1, "import joker com.google.android.gms.ads.* : à remplacer import par import"))
    if nb:
        rapport.append((str(p), "imports", f"{nb} import(s) renommé(s)"))
        sauver(p, "".join(lignes), a)
    if adapter:
        rapport.append((str(p), "mediation", "classe Adapter : conservée sur com.google.android.gms.ads (règle du skill)"))
        return
    for i, l in enumerate(t.splitlines(), 1):
        for rx, msg in APPELS:
            if re.search(rx, l):
                restes.append((str(p), i, msg))
    if re.search(r"Toast|findViewById|\.visibility|setVisibility", t) and re.search(r"onAd(Loaded|FailedToLoad)", t) and "runOnUiThread" not in t and "Dispatchers.Main" not in t:
        restes.append((str(p), 1, "callbacks GMA sur thread d'arrière-plan : envelopper les opérations UI dans runOnUiThread {} / Dispatchers.Main"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("projet", help="dossier du projet Android")
    ap.add_argument("--appliquer", action="store_true", help="écrit les modifications (sinon simulation)")
    ap.add_argument("--version", help="version de ads-mobile-sdk (sinon détectée)")
    ap.add_argument("--sans-sauvegarde", action="store_true", help="ne crée pas de fichiers .orig")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    racine = Path(a.projet)
    if not racine.is_dir():
        fail(f"dossier introuvable : {racine}", 2)
    mapping, ambigus = charger_mapping()
    rapport, restes, audit = [], [], []
    tous = list(fichiers(racine))
    gr = [p for p in tous if p.name in ("build.gradle", "build.gradle.kts")]
    tm = [p for p in tous if p.name == "libs.versions.toml"]
    try:
        ver = version_sdk(a) if (gr or tm) else ""
    except Decision as d:
        print(json.dumps({"needs_ai": d.needs, "context": d.context}, ensure_ascii=False))
        return 3
    for p in gr:
        gradle(p, a, ver, rapport)
    for p in tm:
        toml(p, a, ver, rapport)
    for p in tous:
        if p.name == "AndroidManifest.xml":
            manifeste(p, rapport, audit)
        elif p.suffix in (".kt", ".java"):
            source(p, a, mapping, rapport, restes)
    res = {"mode": "appliqué" if a.appliquer else "simulation", "mapping_imports": len(mapping), "ambigus": sorted(ambigus), "modifications": [{"fichier": f, "type": t, "detail": d} for f, t, d in rapport],
           "audit": [{"niveau": n, "fichier": f, "detail": d} for n, f, d in audit], "a_refactorer": [{"fichier": f, "ligne": l, "action": m} for f, l, m in restes]}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"Migration GMA → Next-Gen ({res['mode']}) — {len(mapping)} correspondances d'imports chargées")
        for f, t, d in rapport:
            print(f"  ✔ {t:11} {f} : {d}")
        for n, f, d in audit:
            print(f"  {'✔' if n == 'ok' else '!'} manifeste   {f} : {d}")
        if restes:
            print(f"\nÀ refactorer ({len(restes)}) :")
            for f, l, m in restes[:60]:
                print(f"  - {f}:{l} — {m}")
    if restes and a.appliquer:
        ctx = {"fichiers": sorted({r["fichier"] for r in res["a_refactorer"]}), "a_refactorer": res["a_refactorer"][:200],
               "regles": "voir data/google-mobile-ads-android-migrate-to-next-gen/SKILL.md (Method Mapping, Core Migration Rules, Format Specifics)"}
        print(json.dumps({"needs_ai": "refactor_appels", "context": ctx}, ensure_ascii=False))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
