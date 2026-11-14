"""VTLO_REcod3r — détection du CLI d'IA utilisé et lancement non interactif (une seule tâche d'écriture)."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import engine as E

AGENTS = {
    "claude": {"label": "Claude Code", "bin": "claude", "dir": ".claude",
               "headless": ["claude", "-p", "{prompt}", "--permission-mode", "acceptEdits",
                            "--allowedTools", "Read,Write,Edit"]},
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


def pilotable(prefere: str | None = None) -> str | None:
    """Premier CLI détecté qui sait travailler sans interface (binaire réellement présent), ou celui demandé."""
    if os.environ.get("RECOD3R_AGENT_CMD"):
        return prefere or "claude"
    ordre = [prefere] if prefere else detect()
    for k in ordre:
        v = AGENTS.get(k or "")
        if v and v["headless"] and shutil.which(v["bin"]):
            return k
    return None


def headless_cmd(agent: str, prompt: str) -> list[str] | None:
    """Commande non interactive de l'agent. RECOD3R_AGENT_CMD="cmd {prompt_file}" permet de la surcharger."""
    override = os.environ.get("RECOD3R_AGENT_CMD")
    if override:
        return None if not override.strip() else ["__override__", override]
    tpl = (AGENTS.get(agent) or {}).get("headless")
    return [prompt if x == "{prompt}" else x for x in tpl] if tpl else None


def _argv(agent: str, prompt: str):
    cmd = headless_cmd(agent, prompt)
    if cmd is None:
        return None
    if cmd[0] == "__override__":
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(prompt)
        return shlex.split(cmd[1].replace("{prompt_file}", f.name))
    return cmd


def lancer(agent: str, prompt: str, cwd: str):
    """Démarre l'agent en arrière-plan (une seule tâche pour tout). Retourne le Popen, ou None."""
    argv = _argv(agent, prompt)
    if argv is None:
        return None
    try:
        return subprocess.Popen(argv, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, env=dict(os.environ))
    except FileNotFoundError:
        return None


def drive(agent: str, prompt: str, cwd: str, timeout: int = 900):
    """Lance l'agent et attend la fin (utilisé par l'orchestrateur aux points de décision). Retourne (code, sortie)."""
    argv = _argv(agent, prompt)
    if argv is None:
        return 127, f"pas de mode non interactif connu pour {agent}"
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=dict(os.environ), stdin=subprocess.DEVNULL)
        return p.returncode, (p.stdout + p.stderr)[-2000:]
    except FileNotFoundError:
        return 127, f"commande introuvable : {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, "délai dépassé"


def prompt_global(dossier: str, slugs: list[str]) -> str:
    """L'unique consigne : écrire tous les scripts d'un seul trait."""
    liste = ", ".join(slugs)
    return (f"Tu es dans le dossier {dossier}. Il contient {len(slugs)} sous-dossiers de tâches : {liste}. "
            f"UNE SEULE TÂCHE : pour chacun, dans l'ordre, lis son BRIEF.md puis écris entièrement le script de son dossier scripts/ "
            f"(qualité professionnelle) et supprime la ligne {E.UNIMPL_MARK}. N'écris aucun test, ne lance aucune commande, "
            f"ne demande aucune confirmation, ne modifie aucun autre fichier. Enchaîne jusqu'à la dernière tâche.")
