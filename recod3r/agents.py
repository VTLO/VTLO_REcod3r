"""VTLO_REcod3r — détection du CLI d'IA utilisé et installation de la commande /rec0d."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import engine as E

# Invites de la commande /rec0d (le protocole que l'agent suit en session)
PROTOCOLE = """Tu pilotes VTLO_REcod3r. Tout ce que tu affiches à l'utilisateur est en FRANÇAIS. Suis ce protocole à la lettre :

1. Lance `vtlo-recod3r rec0d --bg` (analyse + rapport interactif ouvert dans le navigateur). Annonce en une phrase que le rapport est ouvert.
2. Attends la décision de l'utilisateur : répète `vtlo-recod3r attendre --max 90` jusqu'à ce qu'il affiche `DECISION=COD3FORM3` ou `DECISION=IGNOR3`
   (code de sortie 75 = pas encore de décision : relance). Pendant l'attente, NE MODIFIE RIEN.
3. Si `DECISION=IGNOR3` : dis que rien n'a été modifié et arrête-toi.
4. Si `DECISION=COD3FORM3` : lance `vtlo-recod3r forge`. Il liste les tâches (dossier, BRIEF.md, squelette de script).
   Pour CHAQUE tâche, dans l'ordre :
   a. lis son `BRIEF.md` ; b. implémente le script en entier (qualité professionnelle, vrais tests dans --selftest, supprime la ligne
   `RECOD3R:A_IMPLEMENTER`) ; c. lance `vtlo-recod3r verifier <slug>` et corrige jusqu'au vert (3 tentatives maximum, sinon
   `vtlo-recod3r abandonner <slug> --raison "<pourquoi>"`) ; d. si vert : `vtlo-recod3r deployer <slug>`.
   Ne touche à aucun autre fichier que ceux du dossier de la tâche.
5. Termine par `vtlo-recod3r rapport` (ouvre le second rapport) et résume en 3 lignes : tâches faites, tokens économisés par mois, commande de restauration.
"""

AGENTS = {
    "claude": {"label": "Claude Code", "bin": "claude", "dir": ".claude",
               "headless": ["claude", "-p", "{prompt}", "--permission-mode", "acceptEdits",
                            "--allowedTools", "Read,Write,Edit,Bash"]},
    "gemini": {"label": "Gemini CLI", "bin": "gemini", "dir": ".gemini", "headless": ["gemini", "-p", "{prompt}", "--yolo"]},
    "agy": {"label": "agy (Antigravity)", "bin": "agy", "dir": ".gemini/antigravity", "headless": None},
    "codex": {"label": "Codex CLI", "bin": "codex", "dir": ".codex", "headless": ["codex", "exec", "{prompt}"]},
}


def detect() -> list[str]:
    """CLI présents : binaire dans le PATH ou dossier de configuration existant."""
    h = E.home()
    found = []
    for k, v in AGENTS.items():
        if shutil.which(v["bin"]) or (h / v["dir"]).is_dir():
            found.append(k)
    if "agy" in found and "gemini" in found and not shutil.which("agy") and not (h / ".gemini/antigravity").is_dir():
        found.remove("agy")
    return found


def _install_files(agent: str):
    h = E.home()
    desc = "VTLO_REcod3r : analyse tes skills/prompts, propose ce qui peut devenir du code (0 token), puis le code après validation."
    if agent == "claude":
        yield h / ".claude/commands/rec0d.md", f"---\ndescription: {desc}\nallowed-tools: Bash(vtlo-recod3r:*), Read, Write, Edit\n---\n{PROTOCOLE}"
    elif agent == "gemini":
        yield h / ".gemini/commands/rec0d.toml", f'description = {json.dumps(desc, ensure_ascii=False)}\nprompt = """\n{PROTOCOLE}"""\n'
    elif agent == "agy":
        yield h / ".gemini/antigravity/global_workflows/rec0d.md", f"---\ndescription: {desc}\n---\n{PROTOCOLE}"
    elif agent == "codex":
        yield h / ".codex/prompts/rec0d.md", f"---\ndescription: {desc}\n---\n{PROTOCOLE}"


def setup(targets: list[str] | None = None, dry: bool = False) -> list[dict]:
    """Installe /rec0d dans les CLI détectés (ou ciblés). Ne modifie jamais un fichier étranger sans sauvegarde."""
    targets = targets or detect()
    out = []
    for ag in targets:
        if ag not in AGENTS:
            out.append({"agent": ag, "ok": False, "detail": "CLI inconnu"})
            continue
        for path, content in _install_files(ag):
            if path.exists() and "VTLO_REcod3r" not in path.read_text(encoding="utf-8", errors="replace"):
                bak = path.with_name(path.name + ".avant-recod3r")
                if not dry:
                    shutil.copy2(path, bak)
            if not dry:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            invoke = {"codex": "/prompts:rec0d"}.get(ag, "/rec0d")
            out.append({"agent": ag, "label": AGENTS[ag]["label"], "ok": True, "fichier": str(path), "commande": invoke})
    return out


def desinstaller() -> list[str]:
    done = []
    for ag in AGENTS:
        for path, _ in _install_files(ag):
            if path.exists() and "VTLO_REcod3r" in path.read_text(encoding="utf-8", errors="replace"):
                path.unlink()
                bak = path.with_name(path.name + ".avant-recod3r")
                if bak.exists():
                    shutil.move(str(bak), str(path))
                done.append(str(path))
    return done


# --------------------------------------------------------------------------- pilotage « sans tête » (hors session)
def headless_cmd(agent: str, prompt: str) -> list[str] | None:
    """Commande non interactive de l'agent. RECOD3R_AGENT_CMD="cmd {prompt_file}" permet de la surcharger."""
    override = os.environ.get("RECOD3R_AGENT_CMD")
    if override:
        return None if not override.strip() else ["__override__", override]
    tpl = (AGENTS.get(agent) or {}).get("headless")
    return [prompt if x == "{prompt}" else x for x in tpl] if tpl else None


def drive(agent: str, prompt: str, cwd: str, timeout: int = 900):
    """Lance l'agent sur UNE tâche. Retourne (code, sortie)."""
    cmd = headless_cmd(agent, prompt)
    if cmd is None:
        return 127, f"pas de mode non interactif connu pour {agent} : lancez /rec0d dans la session de l'agent"
    env = dict(os.environ)
    if cmd[0] == "__override__":
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(prompt)
        argv = shlex.split(cmd[1].replace("{prompt_file}", f.name))
    else:
        argv = cmd
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL)
        return p.returncode, (p.stdout + p.stderr)[-2000:]
    except FileNotFoundError:
        return 127, f"commande introuvable : {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, "délai dépassé"


def task_prompt(slug: str, dossier: str) -> str:
    return (f"Tu es dans le dossier de la tâche « {slug} » ({dossier}). Lis BRIEF.md puis implémente entièrement le script "
            f"dans scripts/ (qualité professionnelle, vrais tests dans --selftest, supprime la ligne {E.UNIMPL_MARK}). "
            f"Ne modifie aucun autre fichier. Quand c'est fini, arrête-toi (la vérification est faite ensuite par du code).")
