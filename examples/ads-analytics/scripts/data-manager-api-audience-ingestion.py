#!/usr/bin/env python3
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args", "fichier", "stdin"], "sortie": "json", "familles": ["security", "data", "text"], "ia": false}
"""data-manager-api-audience-ingestion — ingestion / retrait de membres d'audience (Customer Match…) (Data Manager API), sans IA.

Lit un CSV ou un JSONL (fichier ou stdin), NORMALISE et HASHE (SHA-256) les identifiants (e-mail, téléphone, nom),
construit les requêtes IngestAudienceMembers / RemoveAudienceMembers / RemoveAll avec les pièges du skill déjà traités, les valide, puis (option) les envoie.

Colonnes reconnues : email, phone, given_name, family_name, region_code, postal_code, consent_ad_user_data, consent_ad_personalization
Usage : data-manager-api-audience-ingestion.py [ENTREE] --destination-id ID --compte-id ID [--compte-type GOOGLE_ADS] [--login-id ID] [--encodage HEX|BASE64]
                    [--region-defaut FR] [--lot 2000] [--valider-seulement] [--envoyer] [--statut REQUEST_ID] [--json]
                    [--operation ajouter|retirer|tout-retirer] [--cgu-acceptees]
Jeton OAuth pour --envoyer / --statut : variable GOOGLE_ACCESS_TOKEN (jamais en argument).
Contrat : 0 ok · 1 échec/entrée invalide (message sur stderr) · 2 usage · 3 décision IA requise (jamais utilisé ici).
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

BASE = "https://datamanager.googleapis.com/v1"
ENDPOINTS = {"ajouter": "audienceMembers:ingest", "retirer": "audienceMembers:remove", "retirer_tout": "audienceMembers:removeAll", "envoi": "audienceMembers:ingest", "statut": "requestStatus:retrieve"}   # à ajuster si l'API évolue
CONSENT = {"granted": "CONSENT_GRANTED", "consent_granted": "CONSENT_GRANTED", "true": "CONSENT_GRANTED", "1": "CONSENT_GRANTED", "oui": "CONSENT_GRANTED",
           "denied": "CONSENT_DENIED", "consent_denied": "CONSENT_DENIED", "false": "CONSENT_DENIED", "0": "CONSENT_DENIED", "non": "CONSENT_DENIED"}
REGIONS_TEL = {"FR": "33", "US": "1", "GB": "44", "DE": "49", "ES": "34", "IT": "39", "BE": "32", "CH": "41", "CA": "1", "NL": "31", "PT": "351"}


def fail(msg: str, code: int = 1):
    print(f"data-manager-api-audience-ingestion : {msg}", file=sys.stderr)
    raise SystemExit(code)


# ------------------------------------------------------------------ normalisation + hachage
def hacher(valeur: str, encodage: str) -> str:
    h = hashlib.sha256(valeur.encode("utf-8")).digest()
    return h.hex() if encodage == "HEX" else base64.b64encode(h).decode("ascii")


def norm_email(e: str) -> str | None:
    e = (e or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e):
        return None
    local, dom = e.rsplit("@", 1)
    if dom in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
        dom = "gmail.com"
    return f"{local}@{dom}"


def norm_tel(t: str, region: str) -> str | None:
    t = (t or "").strip()
    if not t:
        return None
    chiffres = re.sub(r"\D", "", t)
    if t.startswith("+"):
        pass
    elif chiffres.startswith("00"):
        chiffres = chiffres[2:]
    elif region in REGIONS_TEL and chiffres.startswith("0"):
        chiffres = REGIONS_TEL[region] + chiffres[1:]
    elif region in REGIONS_TEL and not chiffres.startswith(REGIONS_TEL[region]):
        chiffres = REGIONS_TEL[region] + chiffres
    return "+" + chiffres if 8 <= len(chiffres) <= 15 else None


def norm_nom(n: str) -> str:
    return re.sub(r"[\s\.,;:!?\-_'\"]+", "", (n or "").strip().lower()) if n and n.strip() else ""


def identifiants(ligne: dict, encodage: str, region: str, ctx: str):
    ids, erreurs = [], []
    if ligne.get("email"):
        e = norm_email(ligne["email"])
        (ids.append({"emailAddress": hacher(e, encodage)}) if e else erreurs.append(f"{ctx} : e-mail invalide"))
    if ligne.get("phone"):
        t = norm_tel(ligne["phone"], region)
        (ids.append({"phoneNumber": hacher(t, encodage)}) if t else erreurs.append(f"{ctx} : téléphone invalide (E.164 attendu)"))
    adr = {k: (ligne.get(k) or "").strip() for k in ("given_name", "family_name", "region_code", "postal_code")}
    if any(adr.values()):
        if all(adr.values()):   # piège : un `address` incomplet fait échouer toute la requête
            ids.append({"address": {"givenName": hacher(norm_nom(adr["given_name"]), encodage), "familyName": hacher(norm_nom(adr["family_name"]), encodage),
                                    "regionCode": adr["region_code"].upper(), "postalCode": adr["postal_code"]}})
        else:
            erreurs.append(f"{ctx} : adresse incomplète ignorée (prénom, nom, région et code postal requis)")
    return ids, erreurs


def consentement(ligne: dict, ctx: str):
    c, erreurs = {}, []
    for col, cle in (("consent_ad_user_data", "adUserData"), ("consent_ad_personalization", "adPersonalization")):
        v = (ligne.get(col) or "").strip().lower()
        if v:
            if v in CONSENT:
                c[cle] = CONSENT[v]
            else:
                erreurs.append(f"{ctx} : consentement « {v} » invalide (CONSENT_GRANTED / CONSENT_DENIED)")
    return c, erreurs


def rfc3339(v: str) -> str | None:
    v = (v or "").strip()
    try:
        if re.fullmatch(r"\d{10}(\.\d+)?", v):
            d = dt.datetime.fromtimestamp(float(v), dt.timezone.utc)
        else:
            d = dt.datetime.fromisoformat(v.replace("Z", "+00:00").replace(" ", "T"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


# ------------------------------------------------------------------ lecture
def lire(entree: str | None):
    f = open(entree, encoding="utf-8-sig", newline="") if entree else sys.stdin
    try:
        premier = f.readline()
        if not premier:
            fail("entrée vide")
        reste = f.read()
        txt = premier + reste
    finally:
        if entree:
            f.close()
    if premier.lstrip().startswith("{"):
        out = []
        for i, l in enumerate(txt.splitlines(), 1):
            if l.strip():
                try:
                    out.append(json.loads(l))
                except json.JSONDecodeError as e:
                    fail(f"ligne {i} : JSON invalide ({e.msg})")
        return out
    return list(csv.DictReader(txt.splitlines()))


def destination(a) -> dict:
    if not (a.destination_id or "").isdigit():
        fail("--destination-id doit être une chaîne numérique (ce n'est PAS un nom de ressource)", 2)
    if not (a.compte_id or "").isdigit():
        fail("--compte-id : identifiant numérique attendu", 2)
    d = {"operatingAccount": {"accountType": a.compte_type, "accountId": a.compte_id}, "productDestinationId": a.destination_id}
    if a.login_id:
        d["loginAccount"] = {"accountType": a.compte_type, "accountId": a.login_id}
    return d


def _http(methode: str, url: str, corps=None):
    import urllib.request, urllib.error
    jeton = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if not jeton:
        fail("variable GOOGLE_ACCESS_TOKEN absente")
    req = urllib.request.Request(url, method=methode, data=None if corps is None else json.dumps(corps).encode(),
                                 headers={"Authorization": "Bearer " + jeton, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        fail("HTTP %s : %s" % (e.code, e.read().decode("utf-8", "replace")[:500]))
    except urllib.error.URLError as e:
        fail("réseau : %s" % e.reason)


def construire(a, lignes, dest):
    requetes, erreurs, membres = [], [], []
    if a.operation == "tout-retirer":
        r = {"destinations": [dest]}
        if a.valider_seulement:
            r["validateOnly"] = True
        return [dict(r, _op="retirer_tout", audienceMembers=[])], erreurs
    for i, l in enumerate(lignes, 1):
        ctx = f"ligne {i}"
        ids, e2 = identifiants(l, a.encodage, a.region_defaut, ctx)
        c, e3 = consentement(l, ctx)
        erreurs += e2 + e3
        if not ids:
            erreurs.append(f"{ctx} : aucun identifiant exploitable — ligne ignorée")
            continue
        m = {"userData": {"userIdentifiers": ids}}
        if c:
            m["consent"] = c
        membres.append(m)
    op = "ajouter" if a.operation == "ajouter" else "retirer"
    for k in range(0, len(membres), a.lot):
        r = {"destinations": [dest], "audienceMembers": membres[k:k + a.lot], "encoding": a.encodage, "_op": op}
        if op == "ajouter":
            if a.compte_type == "GOOGLE_ADS" and not a.cgu_acceptees:
                fail("Customer Match : --cgu-acceptees requis (terms_of_service)", 2)
            if a.cgu_acceptees:
                r["termsOfService"] = {"customerMatchTermsOfServiceStatus": "ACCEPTED"}   # piège : obligatoire à l'ajout
        if a.valider_seulement:
            r["validateOnly"] = True
        requetes.append(r)
    return requetes, erreurs



def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("entree", nargs="?", help="CSV ou JSONL (stdin si absent)")
    ap.add_argument("--destination-id", help="product_destination_id (numérique)")
    ap.add_argument("--compte-type", default="GOOGLE_ADS", help="operating_account.account_type (GOOGLE_ADS, GOOGLE_ANALYTICS_PROPERTY, FLOODLIGHT_CONFIG, DISPLAY_VIDEO_ADVERTISER…)")
    ap.add_argument("--compte-id", help="identifiant du compte opérant (numérique)")
    ap.add_argument("--login-id", help="compte de connexion (gestionnaire / partenaire de données)")
    ap.add_argument("--encodage", choices=["HEX", "BASE64"], default="HEX")
    ap.add_argument("--region-defaut", default="FR", help="région pour normaliser les téléphones sans indicatif")
    ap.add_argument("--lot", type=int, default=2000, help="éléments par requête")
    ap.add_argument("--valider-seulement", action="store_true", help="validate_only=true : rien n'est appliqué")
    ap.add_argument("--envoyer", action="store_true", help="envoie les requêtes (jeton dans GOOGLE_ACCESS_TOKEN)")
    ap.add_argument("--statut", metavar="REQUEST_ID", help="interroge le statut d'une requête (interdit avec validate_only)")
    ap.add_argument("--sortie", help="écrit les requêtes (un JSON par ligne) dans ce fichier")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--operation", choices=["ajouter", "retirer", "tout-retirer"], default="ajouter")
    ap.add_argument("--cgu-acceptees", action="store_true", help="confirme l'acceptation des conditions Customer Match (terms_of_service)")
    a = ap.parse_args(argv)
    try:
        if a.statut:
            if a.valider_seulement:
                fail("ne pas interroger le statut avec validate_only", 2)
            print(json.dumps(_http("GET", f"{BASE}/{ENDPOINTS['statut']}?requestId={a.statut}"), ensure_ascii=False))
            return 0
        if a.lot < 1 or a.lot > 10000:
            fail("--lot entre 1 et 10000", 2)
        lignes = lire(a.entree)
        dest = destination(a)
        requetes, erreurs = construire(a, lignes, dest)
    except BrokenPipeError:
        return 0
    if erreurs:
        for e in erreurs[:30]:
            print(e, file=sys.stderr)
        if not requetes:
            return 1
    if a.sortie:
        Path(a.sortie).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in requetes) + "\n", encoding="utf-8")
    ids = []
    if a.envoyer:
        for r in requetes:
            rep = _http("POST", f"{BASE}/{ENDPOINTS[r['_op']] if '_op' in r else ENDPOINTS['envoi']}", {k: v for k, v in r.items() if k != "_op"})
            ids.append(rep.get("requestId", ""))
    resume = {"requetes": len(requetes), "elements": sum(len(r.get("audienceMembers", [])) for r in requetes), "avertissements": len(erreurs),
              "valider_seulement": a.valider_seulement, "request_ids": ids,
              "apercu": None if (a.sortie or a.envoyer) else [{k: v for k, v in r.items() if k != "_op"} for r in requetes[:1]]}
    print(json.dumps(resume, ensure_ascii=False) if a.json else "\n".join(f"{k}: {v}" for k, v in resume.items() if v not in (None, [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
