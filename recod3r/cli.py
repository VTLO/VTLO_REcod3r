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


# --------------------------------------------------------------------------- gros chiffres (progression 0 → 100 %)
_FONT = {
    "0": ["█████", "█   █", "█   █", "█   █", "█████"], "1": ["  █  ", " ██  ", "  █  ", "  █  ", "█████"],
    "2": ["█████", "    █", "█████", "█    ", "█████"], "3": ["█████", "    █", "█████", "    █", "█████"],
    "4": ["█   █", "█   █", "█████", "    █", "    █"], "5": ["█████", "█    ", "█████", "    █", "█████"],
    "6": ["█████", "█    ", "█████", "█   █", "█████"], "7": ["█████", "    █", "   █ ", "  █  ", "  █  "],
    "8": ["█████", "█   █", "█████", "█   █", "█████"], "9": ["█████", "█   █", "█████", "    █", "█████"],
    "%": ["██  █", "   █ ", "  █  ", " █   ", "█  ██"], " ": ["     "] * 5,
}


def gros(n: int) -> list[str]:
    txt = f"{n:>3}%"
    return ["  ".join(_FONT[c][r] for c in txt) for r in range(5)]


def dessiner(n: int, premier: bool):
    lignes = gros(n)
    if premier:
        print("\n" * 0, end="")
    else:
        sys.stdout.write("\033[6A")
    for l in lignes:
        sys.stdout.write("\r    " + V(l) + "\033[K\n")
    barre = "█" * (n // 2) + "░" * (50 - n // 2)
    sys.stdout.write("\r    " + V(barre) + "\033[K\n")
    sys.stdout.flush()


def suivre(run, proc, delai):
    """Progression réelle : part des scripts rédigés par l'unique tâche d'écriture, animée en gros chiffres."""
    total = max(1, F.avancement(run)[1])
    shown, t0, last_check, done = 0.0, time.time(), 0.0, 0
    anim = TTY
    printed = -10
    if anim:
        dessiner(0, True)
    while True:
        vivant = proc is None or proc.poll() is None
        if time.time() - last_check > 0.4:
            done, _ = F.avancement(run)
            last_check = time.time()
        cible = done / total * 100
        if vivant:
            plafond = min(99.0, (done + 0.9) / total * 100)
            if shown < cible:
                shown = min(cible, shown + max(1.2, (cible - shown) * 0.25))
            elif shown < plafond:
                shown += 0.06
            if time.time() - t0 > delai:
                proc.kill()
                break
        else:
            done, _ = F.avancement(run)
            cible = done / total * 100
            break
        if anim:
            dessiner(int(shown), False)
        elif int(shown) // 10 > printed // 10:
            printed = int(shown)
            print(f"  {int(shown)} %")
        time.sleep(0.1)
    while shown < cible - 0.01:                              # fin : rattrape la valeur réelle
        shown = min(cible, shown + max(1.5, (cible - shown) * 0.3))
        if anim:
            dessiner(int(round(shown)), False)
            time.sleep(0.03)
    final = int(round(cible))
    if anim:
        dessiner(final, False)
    else:
        print(f"  {final} %")
    return done, total


BANC = "IA sur le banc de touche !! Place au c0d3 pour la frappe décisive !!!!"


# --------------------------------------------------------------------------- lancement : analyse → validation unique → écriture
def cmd_run(a):
    bannière("analyse")
    run = F.new_run()
    assets, extra, usage, P = rassembler(a)
    uniq, near = E.dedupe(assets)
    plan = F.build_plan(uniq, extra, near, usage, P, E.detect_env())
    F.jsave(run / "plan.json", plan)
    (run / "rapport1.html").write_text(U.rapport1(plan), encoding="utf-8")
    resume_terminal(plan)
    if not plan["items"]:
        print(G("\n  Rien à recoder pour l'instant."))
        return 0
    if a.decision:
        value = "OK" if a.decision == "ok" else "IGNORER"
        F.jsave(run / "decision.json", {"decision": value, "ids": [], "le": time.strftime("%Y-%m-%dT%H:%M:%S")})
        return fin_decision(run, value, a)
    srv, dec, url = S.serve(run, lambda u: U.rapport1(plan), timeout=a.delai)
    print(f"\n  Rapport : {V(url)}")
    if not a.sans_ouvrir:
        ouvrir(url)
    poll = None
    if sys.stdin.isatty():
        import select
        print(f"  {V('[O]')} OK · {J('[I]')} IGNORER {G('(ou cliquez dans la fenêtre du navigateur)')} > ", end="", flush=True)

        def poll():
            if select.select([sys.stdin], [], [], 0)[0]:
                l = sys.stdin.readline().strip().lower()
                if l.startswith("o"):
                    return ("OK", [])
                if l.startswith("i"):
                    return ("IGNORER", [])
            return None
    value = S.wait_and_close(srv, dec, run, a.delai, poll)
    print()
    return fin_decision(run, value, a)


def fin_decision(run, value, a):
    if value == "OK":
        print(f"  {V('✔ OK')} — écriture de tous les scripts en une seule tâche.\n")
        return generer(run, a)
    if value == "IGNORER":
        print(f"  {J('IGNORER')} — rien n'a été modifié.")
        return 1
    print(R_("  Aucune décision (délai dépassé) — rien n'a été modifié."))
    return 2


def generer(run, a):
    etat = F.forge(run, None, None)
    slugs = [s for s, i in etat["items"].items() if i["statut"] == "a_faire"]
    forge_dir = run / "forge"
    prompt = A.prompt_global(str(forge_dir), slugs)
    (forge_dir / "PROMPT.md").write_text(prompt + "\n", encoding="utf-8")
    agent = A.pilotable(getattr(a, "agent", None))
    if agent is None:
        print(J("  Aucun CLI d'IA utilisable sans interface (claude, gemini, codex) n'a été trouvé."))
        print(f"  Les squelettes et les briefs sont prêts : {V(F.short(forge_dir))}")
        print(f"  Collez la consigne unique de {V(F.short(forge_dir / 'PROMPT.md'))} dans votre outil d'IA, puis lancez {V('vtlorecod finaliser')}.")
        return 0
    print(f"  Écriture par {V(A.AGENTS.get(agent, {}).get('label', agent))} — une seule tâche, {V(str(len(slugs)))} script(s) :\n")
    proc = A.lancer(agent, prompt, str(forge_dir))
    if proc is None:
        print(R_("  Impossible de démarrer l'agent."))
        return 1
    suivre(run, proc, getattr(a, "delai_ecriture", 3600))
    print()
    return finaliser(run, a)


def finaliser(run, a):
    """Installe les scripts rédigés : dossier livré, skills convertis, remplacements sauvegardés ; propose l'orchestration."""
    etat = F.jload(run / "etat.json", {"items": {}})
    manquants = []
    for slug, it in etat["items"].items():
        if it["statut"] == "deploye":
            continue
        try:
            F.deployer(run, slug)
        except (RuntimeError, KeyError, OSError):
            manquants.append(slug)
    bil = F.bilan(run)
    T = bil["totaux"]
    if T["deployes"] == 0:
        print(R_("  Aucun script rédigé pour l'instant.") + G(f" Consigne unique : {F.short(run / 'forge' / 'PROMPT.md')} — puis `vtlorecod finaliser`."))
        return 1
    F.lisez_moi(run)
    F.jsave(run / "bilan.json", bil)
    out = F.sortie_dir()
    if not manquants:
        print("\n  " + V(BANC) + "\n")
    else:
        print(J(f"  {len(manquants)} script(s) non rédigé(s) : {', '.join(manquants)}") + G(" — consigne : " + F.short(run / "forge" / "PROMPT.md") + " puis `vtlorecod finaliser`."))
    print(f"  {V(str(T['deployes']))}/{T['prevus']} scripts prêts · ≈ {V(E.fmt_n(T['eco_mois']))} tokens économisés / mois "
          f"({int(T['taux_global'] * 100)} %) · ≈ {T['cout_mois']} $/mois")
    print(f"\n  Dossier créé : {V(F.short(out))}")
    print(G("    scripts/      tous les scripts, à lancer directement"))
    print(G("    skills/       skills convertis (SKILL.md légers) · commandes/ : claude, gemini, codex-agy"))
    print(G("    LISEZMOI.md   comment lancer chaque script"))
    print(G("  Annuler les remplacements : vtlorecod restaurer"))
    proposer_orchestration(run)
    return 0


def proposer_orchestration(run):
    props = W.proposer(F.bilan(run))
    if not props:
        return
    print(f"\n  {J('Option')} : {len(props)} workflow(s) d'orchestration automatique possibles (les scripts enchaînés, l'IA seulement aux décisions).")
    if sys.stdin.isatty():
        print(f"  Les générer maintenant ? {V('[o]')} oui · {G('[Entrée] non')} > ", end="", flush=True)
        if not sys.stdin.readline().strip().lower().startswith("o"):
            print(G("  Plus tard : vtlorecod orchestrer"))
            return
    else:
        print(G("  Pour les générer : vtlorecod orchestrer"))
        return
    ecrire_orchestration(run, props)


def ecrire_orchestration(run, props):
    fichiers = W.ecrire(props)
    dest = F.sortie_dir() / "orchestration"
    dest.mkdir(parents=True, exist_ok=True)
    for p in fichiers:
        shutil.copy2(p, dest / Path(p).name)
    print(V(f"  ✔ {len(props)} workflow(s) générés") + G(f" → {F.short(dest)}"))
    for w in props:
        print(f"    vtlorecod flow executer {w['nom']} --var entree=FICHIER")


def cmd_finaliser(a):
    run = F.latest_run(getattr(a, "run", None))
    if run is None:
        print(R_("Aucune analyse trouvée : lancez d'abord `vtlorecod`."))
        return 1
    return finaliser(run, a)


def cmd_orchestrer(a):
    run = F.latest_run(getattr(a, "run", None))
    if run is None:
        print(R_("Aucune analyse trouvée : lancez d'abord `vtlorecod`."))
        return 1
    props = W.proposer(F.bilan(run))
    if not props:
        print(J("Pas assez de scripts compatibles pour proposer une orchestration."))
        return 0
    ecrire_orchestration(run, props)
    return 0


def cmd_restaurer(a):
    run = F.latest_run(getattr(a, "run", None))
    if run is None:
        print(R_("Aucune analyse trouvée."))
        return 1
    done = F.restaurer(run, a.slugs or None)
    print(V(f"{len(done)} tâche(s) restaurée(s)") + (" : " + ", ".join(done) if done else ""))
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
    ap = argparse.ArgumentParser(prog="vtlorecod", description="VTLO_REcod3r — transforme en code ce qui n'a pas besoin d'IA (0 token).")
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
        p.add_argument("--sans-ouvrir", action="store_true", help="ne pas ouvrir le navigateur")
        p.add_argument("--decision", choices=["ok", "ignorer"], help="décider en ligne de commande (sans navigateur)")
        p.add_argument("--agent", choices=list(A.AGENTS), help="CLI d'IA qui écrit les scripts (défaut : détecté)")
        p.add_argument("--delai", type=int, default=1800, help="secondes avant expiration de la validation (défaut 1800)")
        p.add_argument("--delai-ecriture", type=int, default=3600, help="durée maximale de l'écriture (défaut 3600 s)")

    commun(ap)
    ap.set_defaults(fn=cmd_run)
    r = sub.add_parser("analyser", help="analyse + rapport + validation unique (OK / IGNORER) — commande par défaut")
    commun(r)
    r.set_defaults(fn=cmd_run)

    p = sub.add_parser("finaliser", help="installe les scripts déjà rédigés (après une écriture manuelle)")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_finaliser)
    p = sub.add_parser("orchestrer", help="génère l'orchestration scriptée automatique (option)")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_orchestrer)
    p = sub.add_parser("restaurer", help="annule les remplacements (depuis les sauvegardes)")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_restaurer)

    p = sub.add_parser("flow", help="orchestrateur de workflows")
    p.add_argument("action", choices=["lister", "proposer", "executer"])
    p.add_argument("nom", nargs="?")
    p.add_argument("--var", action="append", metavar="CLE=VALEUR")
    p.add_argument("--dry", action="store_true", help="simulation")
    p.add_argument("--agent", choices=list(A.AGENTS), help="agent consulté aux points de décision (code 3)")
    p.add_argument("--depuis", help="reprendre à cette étape")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_flow)

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
