"""VTLO_REcod3r — interface en ligne de commande (100 % français)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from . import agents as A
from . import engine as E
from . import flow as W
from . import forge as F
from . import server as S
from . import ui as U

TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
V = lambda s: f"\033[92m{s}\033[0m" if TTY else s
R_ = lambda s: f"\033[91m{s}\033[0m" if TTY else s
J = lambda s: f"\033[93m{s}\033[0m" if TTY else s
G = lambda s: f"\033[2m{s}\033[0m" if TTY else s


def bannière(sous=""):
    print(V("  (;‿ ) ") + "VTLO_REcod3r " + G(E.VERSION) + (G(" · " + sous) if sous else ""))


def ouvrir(cible: str) -> bool:
    try:
        if shutil.which("termux-open-url") and cible.startswith("http"):
            subprocess.Popen(["termux-open-url", cible], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if shutil.which("termux-open") and cible.startswith("file:"):
            subprocess.Popen(["termux-open", cible[7:]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        return bool(webbrowser.open(cible))
    except Exception:
        return False


# --------------------------------------------------------------------------- analyse
def rassembler(a):
    cwd = Path(a.cwd or os.getcwd())
    assets = [] if a.sans_defaut else E.collect_defaults(cwd)
    for spec in a.chemin or []:
        assets += E.collect_extra(spec)
    usage = {"uses": {}, "commands": [], "sessions_src": "assumed", "files": 0}
    if not a.sans_usage:
        usage = E.mine_claude_code(a.jours)
    P = {"uses": a.usages, "sessions": usage.get("sessions") or a.sessions, "price": a.prix, "days": a.jours}
    extra = []
    for spec in a.export or []:
        m = __import__("re").match(r"^(.*):(chatgpt|claude|gemini)$", spec)
        extra += E.recurring_assets(m.group(1) if m else spec, m.group(2) if m else "chatgpt")
    return assets, extra, usage, P


def resume_terminal(plan):
    T, items = plan["totaux"], plan["items"]
    eco = sum(i["analyse"]["save_month"] for i in items)
    print(f"\n  {V(str(T['assets']))} éléments analysés · {V(str(len(items)))} tâches de codage · "
          f"{V(E.fmt_n(eco))} tokens économisables / mois (≈ {round(eco * plan['params']['price'] / 1e6, 2)} $)")
    for i in items[:8]:
        r = i["analyse"]
        print(f"   {V('•')} {r['name']:<28} {r['verdict']:<7} {int((r['codeable'] or 0) * 100):>3} %  {r['lang']['primary']:<10} {E.fmt_n(r['save_month']):>9} tok/mois"
              f"  {G('(' + ('remplacement' if i['mode'] == 'remplacement' else 'script seul') + ')')}")
    if len(items) > 8:
        print(G(f"   … et {len(items) - 8} autre(s) dans le rapport"))


def cmd_rec0d(a):
    bannière("analyse")
    run = F.new_run()
    assets, extra, usage, P = rassembler(a)
    uniq, near = E.dedupe(assets)
    plan = F.build_plan(uniq, extra, near, usage, P, E.detect_env())
    F.jsave(run / "plan.json", plan)
    (run / "rapport1.html").write_text(U.rapport1(plan), encoding="utf-8")
    resume_terminal(plan)
    if a.decision:                                     # mode non interactif (CI / tests)
        d = "COD3FORM3" if a.decision.lower() == "cod3form3" else "IGNOR3"
        ids = [i["id"] for i in plan["items"]] if d == "COD3FORM3" else []
        F.jsave(run / "decision.json", {"decision": d, "ids": ids, "le": time.strftime("%Y-%m-%dT%H:%M:%S"), "mode": "ligne de commande"})
        return fin_decision(run, d, a)
    if a.bg:
        cmd = [sys.executable, "-m", "recod3r", "_servir", "--run", run.name, "--delai", str(a.delai)]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True,
                         env=dict(os.environ))
        t0 = time.time()
        while time.time() - t0 < 10 and not (run / "serveur.json").exists():
            time.sleep(0.1)
        info = F.jload(run / "serveur.json", {})
        if not info:
            print(R_("Le serveur local n'a pas démarré."))
            return 1
        print(f"\n  Rapport n°1 : {V(info['url'])}")
        if not a.sans_ouvrir:
            ouvrir(info["url"])
        print(G("  En attente de votre décision (COD3FORM3 ou IGNOR3) — `vtlo-recod3r attendre`"))
        return 0
    srv, dec, url = S.serve(run, lambda u: U.rapport1(plan), timeout=a.delai)
    print(f"\n  Rapport n°1 : {V(url)}")
    if not a.sans_ouvrir:
        ouvrir(url)
    poll = None
    if sys.stdin.isatty():
        import select
        print(f"  {V('[C]')} COD3FORM3 · {J('[I]')} IGNOR3 {G('(ou cliquez dans le navigateur)')} > ", end="", flush=True)

        def poll():
            if select.select([sys.stdin], [], [], 0)[0]:
                l = sys.stdin.readline().strip().lower()
                if l.startswith("c"):
                    return ("COD3FORM3", [i["id"] for i in plan["items"]])
                if l.startswith("i"):
                    return ("IGNOR3", [])
            return None
    value = S.wait_and_close(srv, dec, run, a.delai, poll)
    print()
    return fin_decision(run, value, a)


def fin_decision(run, value, a):
    if value == "COD3FORM3":
        print(f"  {V('✔ COD3FORM3')} — codage validé.")
        if getattr(a, "auto", False):
            return executer_tout(run, getattr(a, "agent", None), a)
        print(G("  Suite : `vtlo-recod3r forge` (préparer) puis l'agent code, ou `vtlo-recod3r forge --piloter` (non interactif)."))
        print("DECISION=COD3FORM3")
        return 0
    if value == "IGNOR3":
        print(f"  {J('IGNOR3')} — rien n'a été modifié.")
        print("DECISION=IGNOR3")
        return 1
    print(R_("  Aucune décision (délai dépassé) — rien n'a été modifié."))
    print("DECISION=EXPIRE")
    return 2


def cmd_servir(a):
    run = F.latest_run(a.run)
    plan = F.jload(run / "plan.json")
    srv, dec, url = S.serve(run, lambda u: U.rapport1(plan), timeout=a.delai)
    S.wait_and_close(srv, dec, run, a.delai)
    return 0


def cmd_attendre(a):
    run = F.latest_run(a.run)
    if run is None:
        print("Aucune analyse en cours : lancez `vtlo-recod3r rec0d`.")
        return 2
    t0 = time.time()
    while True:
        d = F.jload(run / "decision.json")
        if d:
            print(f"DECISION={d['decision']}")
            return {"COD3FORM3": 0, "IGNOR3": 1}.get(d["decision"], 2)
        if time.time() - t0 >= a.max:
            print("EN_ATTENTE")
            return 75
        time.sleep(0.5)


# --------------------------------------------------------------------------- forge
def cmd_forge(a):
    run = F.latest_run(a.run)
    dec = F.jload(run / "decision.json", {}) if run else {}
    if not run or dec.get("decision") != "COD3FORM3":
        print(R_("Pas de décision COD3FORM3 : lancez d'abord `vtlo-recod3r rec0d` et validez."))
        return 1
    etat = F.forge(run, a.ids, a.langage)
    todo = [(s, i) for s, i in etat["items"].items() if i["statut"] == "a_faire"]
    print(f"{V(str(len(todo)))} tâche(s) de codage prêtes :")
    for s, i in todo:
        print(f"  • {s:<26} {i['langage']:<7} {F.short(i['dossier'])}/BRIEF.md")
    if a.piloter:
        return executer_tout(run, a.agent, a)
    print(G("\nPour chaque tâche : lire BRIEF.md, implémenter le script, puis `vtlo-recod3r verifier <slug>` et `vtlo-recod3r deployer <slug>`."))
    return 0


def executer_tout(run, agent, a):
    """Pilote l'agent détecté, tâche par tâche, en mode non interactif ; le code vérifie et déploie."""
    F.forge(run, None, None)
    agent = agent or (A.detect() or ["claude"])[0]
    etat = F.jload(run / "etat.json")
    print(f"Pilotage de {V(A.AGENTS.get(agent, {}).get('label', agent))} — une tâche à la fois, vérification par le code.")
    for slug, it in list(etat["items"].items()):
        if it["statut"] != "a_faire":
            continue
        feedback = ""
        for essai in range(1, 4):
            print(f"  ▶ {slug} (tentative {essai}/3)…", end=" ", flush=True)
            code, out = A.drive(agent, A.task_prompt(slug, it["dossier"]) + feedback, it["dossier"])
            if code in (127, 124) and essai == 1 and code == 127:
                print(R_(out))
                F.abandonner(run, slug, out)
                break
            res = F.verifier(run, slug)
            if res["ok"]:
                F.deployer(run, slug)
                print(V("vérifié et déployé ✔"))
                break
            bad = " ; ".join(c["nom"] for c in res["checks"] if not c["ok"])
            feedback = f"\n\nLa vérification a échoué : " + "; ".join(f"{c['nom']} ({c['detail']})" for c in res["checks"] if not c["ok"]) + ". Corrige et recommence."
            print(J("à corriger : " + bad[:90]))
        else:
            F.abandonner(run, slug, "échec de vérification après 3 tentatives : " + (bad if 'bad' in dir() else "inconnu"))
            print(R_(f"  ✘ {slug} abandonné"))
    return cmd_rapport(argparse.Namespace(run=run.name, sans_ouvrir=getattr(a, "sans_ouvrir", False)))


def _slug_or_exit(a):
    run = F.latest_run(getattr(a, "run", None))
    if run is None:
        print(R_("Aucune analyse trouvée."))
        raise SystemExit(1)
    return run


def cmd_verifier(a):
    run = _slug_or_exit(a)
    try:
        res = F.verifier(run, a.slug)
    except KeyError:
        print(R_(f"Tâche inconnue : {a.slug}"))
        return 1
    for c in res["checks"]:
        print(f"  {V('✔') if c['ok'] else R_('✘')} {c['nom']}" + ("" if c["ok"] or not c["detail"] else G(f" — {c['detail']}")))
    print(V("VÉRIFIÉ") if res["ok"] else R_("À CORRIGER"))
    return 0 if res["ok"] else 1


def cmd_deployer(a):
    run = _slug_or_exit(a)
    try:
        it = F.deployer(run, a.slug)
    except (KeyError, RuntimeError) as e:
        print(R_(str(e)))
        return 1
    print(f"{V('✔ déployé')} {a.slug} → {F.short(it['copies'][0])}" + (f" · fichier remplacé : {F.short(it['fichier_modifie'])}" if it.get("fichier_modifie") else " · script seul"))
    return 0


def cmd_abandonner(a):
    F.abandonner(_slug_or_exit(a), a.slug, a.raison)
    print(J(f"{a.slug} abandonné : {a.raison}"))
    return 0


def cmd_restaurer(a):
    done = F.restaurer(_slug_or_exit(a), a.slugs or None)
    print(V(f"{len(done)} tâche(s) restaurée(s)") + (" : " + ", ".join(done) if done else ""))
    return 0


def cmd_rapport(a):
    run = _slug_or_exit(a)
    bil = F.bilan(run)
    props = W.proposer(bil)
    W.ecrire(props)
    F.jsave(run / "bilan.json", {**bil, "workflows": [w["nom"] for w in props]})
    (run / "rapport2.html").write_text(U.rapport2(bil, props), encoding="utf-8")
    T = bil["totaux"]
    print(f"\n  {V(str(T['deployes']))}/{T['prevus']} tâches déployées · {V(E.fmt_n(T['eco_mois']))} tokens économisés / mois "
          f"({int(T['taux_global'] * 100)} % sur ce périmètre) · ≈ {T['cout_mois']} $/mois · {len(props)} workflow(s) proposé(s)")
    for r in bil["items"]:
        mark = V("✔") if r["statut"] == "deploye" else (R_("✘") if r["statut"] == "abandonne" else J("…"))
        print(f"   {mark} {r['nom']:<28} {int(r['taux'] * 100):>3} % éco · {E.fmt_n(r['eco_mois']):>9} tok/mois")
    p = run / "rapport2.html"
    print(f"\n  Rapport n°2 : {V(str(p))}")
    if not a.sans_ouvrir:
        ouvrir(p.as_uri())
    return 0


# --------------------------------------------------------------------------- flow
def cmd_flow(a):
    if a.action == "proposer":
        run = F.latest_run(a.run)
        props = W.proposer(F.bilan(run)) if run else []
        for p in W.ecrire(props):
            print("  " + F.short(p))
        print(V(f"{len(props)} workflow(s) proposé(s)"))
        return 0
    if a.action == "lister":
        for p in sorted(W.flow_dir().glob("*.json")):
            w = json.loads(p.read_text(encoding="utf-8"))
            print(f"  {V(w['nom']):<30} {len(w['etapes'])} étape(s) — {w.get('description', '')}")
        return 0
    wf = W.charger(a.nom)
    variables = dict(kv.split("=", 1) for kv in a.var or [])
    res = W.run_workflow(wf, variables, a.dry, a.agent, a.depuis, log=print)
    out = F.state_dir() / "workflows" / "journaux"
    out.mkdir(parents=True, exist_ok=True)
    F.jsave(out / f"{wf['nom']}-{time.strftime('%Y%m%d-%H%M%S')}.json", res)
    print({"ok": V("TERMINÉ"), "pause_ia": J("PAUSE : décision IA requise"), "echec": R_("ÉCHEC")}.get(res["statut"], R_(res["statut"].upper())))
    return {"ok": 0, "pause_ia": 3}.get(res["statut"], 1)


# --------------------------------------------------------------------------- divers
def cmd_setup(a):
    cibles = None if a.agent in (None, "auto") else (list(A.AGENTS) if a.agent == "tous" else [a.agent])
    det = A.detect()
    if not (cibles or det):
        print(J("Aucun CLI d'IA détecté (claude, gemini, agy, codex). Utilisez `--agent claude|gemini|agy|codex|tous`."))
        return 1
    print(f"CLI détecté(s) : {V(', '.join(det) or 'aucun')}")
    for r in A.setup(cibles, a.simulation):
        print(f"  {V('✔') if r['ok'] else R_('✘')} {r.get('label', r['agent'])} : tapez {V(r.get('commande', ''))}  {G(F.short(r.get('fichier', r.get('detail', ''))))}")
    print(G("Dans un terminal simple (sans agent) : `rec0d`."))
    return 0


def cmd_desinstaller(a):
    for p in A.desinstaller():
        print("  retiré : " + F.short(p))
    return 0


def cmd_diagnostic(a):
    print("CLI détectés :", ", ".join(A.detect()) or "aucun")
    env = E.detect_env()
    print("Interpréteurs :", ", ".join(k for k, v in env["langs"].items() if v and k != "existing-tool"))
    print("Dossier d'état :", F.short(F.state_dir()))
    print("Python :", sys.version.split()[0])
    return 0


def cmd_presentation(a):
    from . import ui_presentation as P
    out = Path(a.sortie) if a.sortie else F.state_dir() / "presentation.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(P.presentation(), encoding="utf-8")
    print("Présentation : " + V(str(out)))
    if not a.sans_ouvrir:
        ouvrir(out.resolve().as_uri())
    return 0


def cmd_squeeze(a):
    data = Path(a.fichier).read_text(errors="replace") if a.fichier else sys.stdin.read()
    sys.stdout.write(E.squeeze(data, a.budget))
    return 0


def cmd_tokens(a):
    tot = 0
    for p in a.fichiers:
        t = E._read(Path(p))
        k = E.est_tokens(t or "")
        tot += k
        print(f"{k:>9}  {p}")
    print(f"{tot:>9}  total (estimation)")
    return 0


def parser():
    ap = argparse.ArgumentParser(prog="vtlo-recod3r", description="VTLO_REcod3r — transforme en code ce qui n'a pas besoin d'IA (0 token).")
    ap.add_argument("--version", action="version", version=E.VERSION)
    sub = ap.add_subparsers(dest="cmd")

    def commun(p):
        p.add_argument("--chemin", action="append", metavar="CHEMIN[:agent]", help="dossier/fichier/.zip/.skill supplémentaire")
        p.add_argument("--export", action="append", metavar="FICHIER[:chatgpt|claude]", help="export ChatGPT/Claude.ai (prompts récurrents)")
        p.add_argument("--sans-defaut", action="store_true", help="ne pas scanner les dossiers par défaut")
        p.add_argument("--sans-usage", action="store_true", help="ne pas lire les transcripts Claude Code")
        p.add_argument("--cwd", help="dossier de projet à analyser")
        p.add_argument("--jours", type=int, default=90)
        p.add_argument("--usages", type=float, default=20, help="usages/mois supposés (défaut 20)")
        p.add_argument("--sessions", type=float, default=60, help="sessions/mois supposées (défaut 60)")
        p.add_argument("--prix", type=float, default=3.0, help="$ par million de tokens en entrée (défaut 3)")

    r = sub.add_parser("rec0d", help="analyse + rapport n°1 cliquable (COD3FORM3 / IGNOR3)")
    commun(r)
    r.add_argument("--bg", action="store_true", help="serveur en arrière-plan (pour les agents) ; suivre avec `attendre`")
    r.add_argument("--sans-ouvrir", action="store_true", help="ne pas ouvrir le navigateur")
    r.add_argument("--decision", choices=["cod3form3", "ignor3"], help="décider en ligne de commande (sans navigateur)")
    r.add_argument("--auto", action="store_true", help="après COD3FORM3, piloter l'agent détecté pour tout coder")
    r.add_argument("--agent", choices=list(A.AGENTS), help="agent à piloter avec --auto")
    r.add_argument("--delai", type=int, default=1800, help="secondes avant expiration (défaut 1800)")
    r.set_defaults(fn=cmd_rec0d)

    s = sub.add_parser("_servir")
    s.add_argument("--run")
    s.add_argument("--delai", type=int, default=1800)
    s.set_defaults(fn=cmd_servir)

    t = sub.add_parser("attendre", help="attend la décision (code 0 COD3FORM3 · 1 IGNOR3 · 75 pas encore)")
    t.add_argument("--max", type=int, default=90)
    t.add_argument("--run")
    t.set_defaults(fn=cmd_attendre)

    f = sub.add_parser("forge", help="prépare les tâches validées (squelettes + briefs)")
    f.add_argument("--ids", nargs="*")
    f.add_argument("--langage", choices=list(E.LANG_TPL))
    f.add_argument("--piloter", action="store_true", help="piloter l'agent détecté, tâche par tâche (non interactif)")
    f.add_argument("--agent", choices=list(A.AGENTS))
    f.add_argument("--run")
    f.add_argument("--sans-ouvrir", action="store_true")
    f.set_defaults(fn=cmd_forge)

    for nom, fn, h in (("verifier", cmd_verifier, "vérifie un script (autotests réels, contrat, sécurité)"),
                       ("deployer", cmd_deployer, "installe un script vérifié et remplace l'original (sauvegardé)")):
        p = sub.add_parser(nom, help=h)
        p.add_argument("slug")
        p.add_argument("--run")
        p.set_defaults(fn=fn)
    p = sub.add_parser("abandonner", help="abandonne une tâche")
    p.add_argument("slug")
    p.add_argument("--raison", required=True)
    p.add_argument("--run")
    p.set_defaults(fn=cmd_abandonner)
    p = sub.add_parser("restaurer", help="annule les remplacements (depuis les sauvegardes)")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_restaurer)
    p = sub.add_parser("rapport", help="rapport n°2 : bilan, économies, propositions de workflows")
    p.add_argument("--run")
    p.add_argument("--sans-ouvrir", action="store_true")
    p.set_defaults(fn=cmd_rapport)

    p = sub.add_parser("flow", help="orchestrateur de workflows")
    p.add_argument("action", choices=["lister", "proposer", "executer"])
    p.add_argument("nom", nargs="?")
    p.add_argument("--var", action="append", metavar="CLE=VALEUR")
    p.add_argument("--dry", action="store_true", help="simulation")
    p.add_argument("--agent", choices=list(A.AGENTS), help="agent consulté aux points de décision (code 3)")
    p.add_argument("--depuis", help="reprendre à cette étape")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_flow)

    p = sub.add_parser("setup", help="installe /rec0d dans le(s) CLI d'IA détecté(s)")
    p.add_argument("--agent", choices=["auto", "claude", "gemini", "agy", "codex", "tous"], default="auto")
    p.add_argument("--simulation", action="store_true")
    p.set_defaults(fn=cmd_setup)
    sub.add_parser("desinstaller", help="retire /rec0d des CLI").set_defaults(fn=cmd_desinstaller)
    sub.add_parser("diagnostic", help="état de l'installation").set_defaults(fn=cmd_diagnostic)
    p = sub.add_parser("presentation", help="présentation animée pour débutants (français)")
    p.add_argument("--sortie")
    p.add_argument("--sans-ouvrir", action="store_true")
    p.set_defaults(fn=cmd_presentation)
    p = sub.add_parser("squeeze", help="compacte une sortie de commande bruyante (stdin)")
    p.add_argument("fichier", nargs="?")
    p.add_argument("--budget", type=int, default=800)
    p.set_defaults(fn=cmd_squeeze)
    p = sub.add_parser("tokens", help="estime le nombre de tokens de fichiers")
    p.add_argument("fichiers", nargs="+")
    p.set_defaults(fn=cmd_tokens)
    return ap


def main(argv=None):
    ap = parser()
    a = ap.parse_args(argv)
    if not a.cmd:
        bannière("« /rec0d » lance l'analyse")
        ap.print_help()
        return 0
    if a.cmd == "flow" and a.action == "executer" and not a.nom:
        ap.error("flow executer : nom du workflow requis")
    try:
        return a.fn(a)
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
