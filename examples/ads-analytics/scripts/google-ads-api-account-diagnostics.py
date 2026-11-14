#!/usr/bin/env python3
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args", "fichier", "stdin"], "sortie": "text+json", "familles": ["data", "analytics", "ads"], "ia": false}
"""google-ads-api-account-diagnostics — requêtes GAQL de diagnostic + analyse des lignes exportées, sans IA.

Le SKILL.md d'origine interdit d'écrire des scripts qui interrogent l'API DANS le bac à sable MCP : ce script ne fait donc PAS d'appel API.
Il (1) génère les requêtes GAQL validées, (2) analyse les résultats exportés (CSV, JSON ou JSONL ; clés `campaign.name`, `metrics.clicks`… ou JSON imbriqué).

Usage :
  google-ads-api-account-diagnostics.py requete NOM [--debut AAAA-MM-JJ] [--fin AAAA-MM-JJ] [--json]
  google-ads-api-account-diagnostics.py analyser NOM [FICHIER|-] [--coupure AAAA-MM-JJ] [--seuil 0.2] [--json]
NOM : clients · conversions · parts-impression · uploads · modifications · flux-leads
Contrat : 0 ok · 1 échec/entrée invalide (stderr) · 2 usage · 3 décision IA requise (non utilisé ici).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from collections import defaultdict

Q = {
    "clients": "SELECT\n  customer_client.id,\n  customer_client.descriptive_name,\n  customer_client.status,\n  customer_client.manager\nFROM customer_client\nWHERE customer_client.status = 'ENABLED' AND customer_client.manager = FALSE",
    "conversions": "SELECT\n  campaign.name,\n  metrics.conversions,\n  metrics.conversions_value,\n  metrics.cost_micros,\n  segments.date,\n  segments.device,\n  segments.conversion_action\nFROM campaign\nWHERE segments.date >= '{debut}' AND segments.date <= '{fin}'",
    "parts-impression": "SELECT\n  campaign.name,\n  metrics.search_impression_share,\n  metrics.search_rank_lost_impression_share,\n  metrics.search_budget_lost_impression_share\nFROM campaign\nWHERE segments.date >= '{debut}' AND segments.date <= '{fin}'",
    "uploads": "SELECT\n  offline_conversion_upload_conversion_action_summary.conversion_action_name,\n  offline_conversion_upload_conversion_action_summary.successful_event_count,\n  offline_conversion_upload_conversion_action_summary.total_event_count,\n  offline_conversion_upload_conversion_action_summary.status\nFROM offline_conversion_upload_conversion_action_summary",
    "modifications": "SELECT\n  change_event.change_date_time,\n  change_event.change_resource_name,\n  change_event.resource_change_operation,\n  change_event.changed_fields\nFROM change_event\nWHERE change_event.change_date_time >= '{debut}' AND change_event.change_date_time <= '{fin}'\nLIMIT 10000",
    "flux-leads": "SELECT\n  campaign.name,\n  metrics.impressions,\n  metrics.clicks,\n  metrics.conversions,\n  segments.date,\n  segments.device,\n  segments.conversion_action\nFROM campaign\nWHERE segments.date >= '{debut}' AND segments.date <= '{fin}'",
}
NOTES = {
    "clients": "N'interroger ensuite QUE ces comptes (pas de gestionnaires ni de comptes désactivés : erreurs API).",
    "conversions": "metrics.cost_micros / 1 000 000 = devise. Comparer la période de baisse à la précédente.",
    "parts-impression": "Les parts sont des décimaux (0.35 = 35 %) ou des chaînes « < 0.10 ».",
    "uploads": "Résultat vide = aucun upload hors-ligne : arrêter et le dire, ne pas réessayer.",
    "modifications": "change_event : LIMIT ≤ 10000, filtre de date dans les 30 derniers jours, aucune métrique.",
    "flux-leads": "Distinguer baisse de trafic (clics/impressions) et baisse de taux de conversion.",
}


def fail(msg, code=1):
    print(f"google-ads-api-account-diagnostics : {msg}", file=sys.stderr)
    raise SystemExit(code)


def jour(s, nom):
    try:
        return dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        fail(f"{nom} : date AAAA-MM-JJ attendue", 2)


# ------------------------------------------------------------------ lecture / aplatissement
def aplatir(o, pre=""):
    out = {}
    for k, v in o.items():
        c = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", k).lower()      # camelCase (REST) → snake_case (GAQL)
        c = f"{pre}.{c}" if pre else c
        if isinstance(v, dict):
            out.update(aplatir(v, c))
        else:
            out[c] = v
    return out


def lire(chemin):
    txt = sys.stdin.read() if chemin in (None, "-") else open(chemin, encoding="utf-8-sig").read()
    if not txt.strip():
        return []
    s = txt.lstrip()
    try:
        if s[0] == "[":
            rows = json.loads(txt)
        elif s[0] == "{":
            try:
                d = json.loads(txt)
                rows = d.get("results", d.get("rows", [d])) if isinstance(d, dict) else d
            except json.JSONDecodeError:
                rows = [json.loads(l) for l in txt.splitlines() if l.strip()]
        else:
            return [{k.strip().lower(): v for k, v in r.items()} for r in csv.DictReader(txt.splitlines())]
    except json.JSONDecodeError as e:
        fail(f"JSON invalide ({e.msg}, ligne {e.lineno})")
    return [aplatir(r) for r in rows]


def num(v):
    """Nombre depuis décimal, pourcentage, « < 0.10 », « 12,5 » ; None si absent."""
    if v is None or v == "" or v == "--":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(",", ".").replace("%", "")
    t = t.lstrip("<>≤≥= ")
    try:
        x = float(t)
    except ValueError:
        return None
    return x / 100 if "%" in str(v) and x > 1 else x


def col(r, *noms):
    for n in noms:
        for k in (n, n.split(".")[-1]):
            if k in r:
                return r[k]
    return None


def pct(x):
    return "n/d" if x is None else f"{x * 100:.1f} %"


# ------------------------------------------------------------------ analyses
def a_conversions(rows, a):
    dates = sorted({str(col(r, "segments.date")) for r in rows if col(r, "segments.date")})
    if len(dates) < 2:
        fail("au moins 2 dates (segments.date) sont nécessaires pour comparer deux périodes")
    cut = a.coupure or dates[len(dates) // 2]
    def agr(cle):
        d = defaultdict(lambda: [defaultdict(float), defaultdict(float)])
        for r in rows:
            dd = str(col(r, "segments.date") or "")
            p = 1 if dd >= cut else 0
            k = str(col(r, cle) or "(vide)")
            d[k][p]["conv"] += num(col(r, "metrics.conversions")) or 0
            d[k][p]["val"] += num(col(r, "metrics.conversions_value")) or 0
            d[k][p]["cout"] += (num(col(r, "metrics.cost_micros")) or 0) / 1e6   # piège : micros → devise
        return d
    res = {"coupure": cut, "dimensions": {}, "alertes": []}
    for cle in ("segments.device", "segments.conversion_action", "campaign.name"):
        d = agr(cle)
        lignes = []
        for k, (av, ap) in sorted(d.items()):
            delta = (ap["conv"] - av["conv"]) / av["conv"] if av["conv"] else None
            lignes.append({"valeur": k, "conv_avant": av["conv"], "conv_apres": ap["conv"], "variation": delta, "cout_avant": round(av["cout"], 2), "cout_apres": round(ap["cout"], 2)})
            if delta is not None and delta <= -a.seuil and av["conv"] >= 1:
                res["alertes"].append(f"{cle} = {k} : conversions {pct(delta)} (de {av['conv']:.1f} à {ap['conv']:.1f})")
        res["dimensions"][cle] = lignes
    return res


def a_parts(rows, a):
    out = []
    for r in rows:
        ims, rang, bud = (num(col(r, "metrics.search_impression_share")), num(col(r, "metrics.search_rank_lost_impression_share")),
                          num(col(r, "metrics.search_budget_lost_impression_share")))
        cause = None
        if (bud or 0) >= max(rang or 0, a.seuil / 2) and (bud or 0) > 0.05:
            cause = "budget"
        elif (rang or 0) > 0.05:
            cause = "rang (enchères / qualité)"
        out.append({"campagne": col(r, "campaign.name"), "part_impression": ims, "perdue_rang": rang, "perdue_budget": bud, "cause_principale": cause})
    out.sort(key=lambda x: -((x["perdue_rang"] or 0) + (x["perdue_budget"] or 0)))
    return {"campagnes": out, "alertes": [f"{o['campagne']} : cause principale {o['cause_principale']} (rang {pct(o['perdue_rang'])}, budget {pct(o['perdue_budget'])})" for o in out if o["cause_principale"]][:15]}


def a_uploads(rows, a):
    if not rows:
        return {"vide": True, "message": "Aucun upload de conversion hors-ligne n'existe pour ce compte : diagnostic arrêté.", "alertes": []}
    out, al = [], []
    for r in rows:
        ok, tot = num(col(r, "offline_conversion_upload_conversion_action_summary.successful_event_count")), num(col(r, "offline_conversion_upload_conversion_action_summary.total_event_count"))
        nom, st = col(r, "offline_conversion_upload_conversion_action_summary.conversion_action_name"), col(r, "offline_conversion_upload_conversion_action_summary.status")
        taux = (ok / tot) if (ok is not None and tot) else None
        out.append({"action": nom, "reussis": ok, "total": tot, "taux": taux, "statut": st})
        if taux is not None and taux < 1 - a.seuil:
            al.append(f"{nom} : seulement {pct(taux)} d'événements réussis ({ok:.0f}/{tot:.0f}), statut {st}")
        elif st and str(st).upper() not in ("EXCELLENT", "GOOD", "OK", "ENABLED"):
            al.append(f"{nom} : statut {st}")
    return {"vide": False, "actions": out, "alertes": al}


def a_modifs(rows, a):
    if len(rows) > 10000:
        fail("change_event est limité à 10000 lignes : l'export dépasse cette limite")
    par = defaultdict(lambda: defaultdict(int))
    for r in rows:
        d = str(col(r, "change_event.change_date_time") or "")[:10]
        par[d][f"{col(r, 'change_event.resource_change_operation')}"] += 1
    champs = defaultdict(int)
    for r in rows:
        for f in re.split(r"[,\s]+", str(col(r, "change_event.changed_fields") or "")):
            if f:
                champs[f] += 1
    sensibles = [f for f in champs if re.search(r"bid|budget|target|status|keyword", f, re.I)]
    return {"par_jour": {d: dict(v) for d, v in sorted(par.items())}, "champs_modifies": dict(sorted(champs.items(), key=lambda x: -x[1])[:15]),
            "alertes": [f"champ sensible modifié : {f} ({champs[f]}×)" for f in sensibles[:10]]}


def a_flux(rows, a):
    dates = sorted({str(col(r, "segments.date")) for r in rows if col(r, "segments.date")})
    if len(dates) < 2:
        fail("au moins 2 dates (segments.date) sont nécessaires")
    cut = a.coupure or dates[len(dates) // 2]
    t = [defaultdict(float), defaultdict(float)]
    for r in rows:
        p = 1 if str(col(r, "segments.date")) >= cut else 0
        for m in ("impressions", "clicks", "conversions"):
            t[p][m] += num(col(r, "metrics." + m)) or 0
    cvr = [(x["conversions"] / x["clicks"]) if x["clicks"] else None for x in t]
    var = lambda m: ((t[1][m] - t[0][m]) / t[0][m]) if t[0][m] else None
    res = {"coupure": cut, "avant": dict(t[0]), "apres": dict(t[1]), "taux_conv_avant": cvr[0], "taux_conv_apres": cvr[1],
           "variation": {m: var(m) for m in ("impressions", "clicks", "conversions")}, "alertes": []}
    v = res["variation"]
    if v["clicks"] is not None and v["clicks"] <= -a.seuil:
        res["alertes"].append(f"TRAFIC en baisse ({pct(v['clicks'])} de clics) → vérifier les parts d'impression (budget / rang) : `analyser parts-impression`")
    if cvr[0] and cvr[1] is not None and (cvr[1] - cvr[0]) / cvr[0] <= -a.seuil:
        res["alertes"].append(f"TAUX DE CONVERSION en baisse ({pct(cvr[0])} → {pct(cvr[1])}) → ventiler par appareil / action de conversion : `analyser conversions`")
    if not res["alertes"]:
        res["alertes"].append("pas de rupture nette sur trafic ni taux de conversion avec ce seuil ; consulter `analyser modifications`")
    return res


def a_clients(rows, a):
    ok = [r for r in rows if str(col(r, "customer_client.status") or "").upper() == "ENABLED" and str(col(r, "customer_client.manager")).lower() != "true"]
    return {"comptes_a_interroger": [{"id": col(r, "customer_client.id"), "nom": col(r, "customer_client.descriptive_name")} for r in ok],
            "alertes": [] if ok else ["aucun compte client actif (hors gestionnaires)"]}


ANALYSES = {"clients": a_clients, "conversions": a_conversions, "parts-impression": a_parts, "uploads": a_uploads, "modifications": a_modifs, "flux-leads": a_flux}


def texte(nom, r):
    L = [f"Diagnostic « {nom} »"]
    if r.get("vide"):
        L.append(r["message"])
    for cle, v in r.items():
        if cle in ("alertes", "vide", "message"):
            continue
        L.append(f"\n{cle} :")
        L.append(json.dumps(v, ensure_ascii=False, indent=1, default=lambda x: round(x, 4))[:3000])
    L.append("\nAlertes :" if r.get("alertes") else "\nAucune alerte.")
    L += [f"  ! {x}" for x in r.get("alertes", [])]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("requete", help="affiche la requête GAQL validée")
    r.add_argument("nom", choices=sorted(Q))
    r.add_argument("--debut")
    r.add_argument("--fin")
    r.add_argument("--json", action="store_true")
    n = sp.add_parser("analyser", help="analyse des lignes exportées")
    n.add_argument("nom", choices=sorted(Q))
    n.add_argument("fichier", nargs="?", default="-")
    n.add_argument("--coupure", help="date charnière AAAA-MM-JJ (par défaut : milieu de la plage)")
    n.add_argument("--seuil", type=float, default=0.2, help="variation relative jugée significative (0.2 = 20 %%)")
    n.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "requete":
            if "{debut}" in Q[a.nom]:
                if not (a.debut and a.fin):
                    fail("--debut et --fin requis pour cette requête", 2)
                d, f = jour(a.debut, "--debut"), jour(a.fin, "--fin")
                if d > f:
                    fail("--debut postérieur à --fin", 2)
                if a.nom == "modifications" and (dt.date.today() - d).days > 30:
                    fail("change_event : la date de début doit être dans les 30 derniers jours", 2)
                q = Q[a.nom].format(debut=a.debut, fin=a.fin)
            else:
                q = Q[a.nom]
            print(json.dumps({"requete": q, "note": NOTES[a.nom]}, ensure_ascii=False) if a.json else q + "\n-- " + NOTES[a.nom])
            return 0
        rows = lire(a.fichier)
        if not rows and a.nom != "uploads":
            fail("aucune ligne en entrée")
        res = ANALYSES[a.nom](rows, a)
        print(json.dumps(res, ensure_ascii=False, default=lambda x: round(x, 4)) if a.json else texte(a.nom, res))
        return 0
    except BrokenPipeError:
        return 0
    except FileNotFoundError as e:
        fail(f"fichier introuvable : {e.filename}")


if __name__ == "__main__":
    sys.exit(main())
