#!/usr/bin/env python3
# RECOD3R-MANIFEST: {"v": 1, "entree": ["args", "fichier", "stdin"], "sortie": "json", "familles": ["tabular", "json"], "ia": false}
"""csv-cleaner — nettoie un CSV : lignes de même largeur, tri par date, doublons retirés, dates ISO, `id` obligatoire.

Contrat : 0 ok · 1 contrôle échoué (stderr) · 2 usage · 3 décision IA requise ; réponse IA via RECOD3R_AI_ANSWER (revalidée).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path

FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


def iso(valeur: str):
    v = valeur.strip()
    for f in FORMATS:
        try:
            return datetime.strptime(v, f).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def nettoyer(texte: str) -> tuple[str, dict]:
    lignes = list(csv.reader(io.StringIO(texte)))
    if not lignes:
        raise ValueError("entrée vide")
    entete, corps = lignes[0], lignes[1:]
    if "id" not in entete or "date" not in entete:
        raise ValueError("colonnes « id » et « date » requises")
    largeur, ii, di = len(entete), entete.index("id"), entete.index("date")
    vus, gardes, stats = set(), [], {"lignes": len(corps), "id_vide": 0, "doublons": 0, "largeur": 0, "date_invalide": 0}
    for lg in corps:
        if len(lg) != largeur:
            stats["largeur"] += 1
            continue
        if not lg[ii].strip():
            stats["id_vide"] += 1
            continue
        d = iso(lg[di])
        if d is None:
            stats["date_invalide"] += 1
            continue
        lg = lg[:di] + [d] + lg[di + 1:]
        cle = tuple(lg)
        if cle in vus:
            stats["doublons"] += 1
            continue
        vus.add(cle)
        gardes.append(lg)
    gardes.sort(key=lambda lg: lg[di])
    sortie = io.StringIO()
    w = csv.writer(sortie, lineterminator="\n")
    w.writerow(entete)
    w.writerows(gardes)
    stats["gardees"] = len(gardes)
    return sortie.getvalue(), stats


def autotest() -> int:
    src = "id,date,nom\n1,03/02/2026,a\n,01/01/2026,b\n2,2026-01-05,c\n2,2026-01-05,c\n3,bad,d\n4,1/1\n"
    out, st = nettoyer(src)
    assert out == "id,date,nom\n2,2026-01-05,c\n1,2026-02-03,a\n", out
    assert (st["id_vide"], st["doublons"], st["date_invalide"], st["largeur"], st["gardees"]) == (1, 1, 1, 1, 2), st
    try:
        nettoyer("")
        raise AssertionError("entrée vide acceptée")
    except ValueError:
        pass
    try:
        nettoyer("a,b\n1,2\n")
        raise AssertionError("colonnes manquantes acceptées")
    except ValueError:
        pass
    print("autotest : 4 cas ok")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("entrees", nargs="*", help="fichiers CSV (stdin si absent)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return autotest()
    resultats = []
    try:
        if a.entrees:
            for f in a.entrees:
                p = Path(f)
                out, st = nettoyer(p.read_text(encoding="utf-8"))
                dest = p.with_suffix(".clean.csv")
                dest.write_text(out, encoding="utf-8")
                resultats.append({"fichier": str(dest), **st})
        else:
            out, st = nettoyer(sys.stdin.read())
            sys.stdout.write(out)
            resultats.append(st)
    except (ValueError, OSError) as e:
        print(f"échec : {e}", file=sys.stderr)
        return 1
    if a.entrees:
        print(json.dumps(resultats[0] if len(resultats) == 1 else resultats, ensure_ascii=False) if a.json
              else "\n".join(f"{r['fichier']} : {r['gardees']} gardées" for r in resultats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
