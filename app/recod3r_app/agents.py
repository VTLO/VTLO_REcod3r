"""Détection des CLI d'IA et lancement non interactif (une seule tâche d'écriture).
Compatibles : Claude Code, Gemini CLI, Antigravity CLI (agy), Codex CLI — ou toute commande via RECOD3R_AGENT_CMD."""
import os
import shutil
import subprocess
from pathlib import Path

from .engine import home, redact, which

# (clé, libellé, binaires possibles, chemin de config, pilotable sans interface)
AGENTS = [
    ("claude", "Claude Code", ["claude"], ".claude", True),
    ("gemini", "Gemini CLI", ["gemini"], ".gemini/settings.json", True),
    ("agy", "Antigravity CLI (agy)", ["agy", "antigravity"], ".gemini/antigravity-cli", True),
    ("codex", "Codex CLI", ["codex"], ".codex", True),
]


def bin_of(key):
    """Binaire réel (agy peut s'appeler `antigravity` ; ANTIGRAVITY_CLI_ALIAS le force)."""
    if key == "agy":
        a = os.environ.get("ANTIGRAVITY_CLI_ALIAS", "").strip()
        if a and which(a):
            return shutil.which(a)
    for k, _l, bins, _d, _h in AGENTS:
        if k == key:
            for b in bins:
                if which(b):
                    return shutil.which(b)
    return None


def detect():
    out = []
    for k, label, _bins, d, hl in AGENTS:
        b = bin_of(k)
        installed = b is not None or (home() / d).exists()
        if not installed:
            continue
        note = "lancé avec --dangerously-skip-permissions, uniquement dans le dossier de travail de la conversion" if k == "agy" else ""
        out.append({"key": k, "label": label, "installed": True, "headless": bool(hl and b), "note": note})
    return out


def pilotable(prefer=None):
    if os.environ.get("RECOD3R_AGENT_CMD", "").strip():
        return prefer or "custom"
    for a in detect():
        if a["headless"] and (prefer is None or prefer == a["key"]):
            return a["key"]
    return None


def short_prompt(prompt_file):
    return "Lis le fichier %s puis exécute exactement ses instructions (écris les scripts demandés, rien d'autre)." % prompt_file


def spawn(agent, prompt_file, cwd):
    """Lance l'agent dans `cwd` ; la sortie va dans agent.log. RECOD3R_AGENT_CMD accepte {prompt_file}."""
    cwd = Path(cwd)
    log = open(cwd / "agent.log", "wb")
    prompt = short_prompt(prompt_file)
    custom = os.environ.get("RECOD3R_AGENT_CMD")
    kw = dict(cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    try:
        if custom:
            child = subprocess.Popen(custom.replace("{prompt_file}", str(prompt_file)), shell=True, **kw)
            log.close()
            return child
        b = bin_of(agent)
        if not b:
            raise FileNotFoundError("CLI introuvable")
        if agent == "claude":
            cmd = [b, "-p", prompt, "--permission-mode", "acceptEdits", "--allowedTools", "Read,Write,Edit"]
        elif agent == "gemini":
            cmd = [b, "-p", prompt, "--yolo"]
        elif agent == "agy":
            # sans cet indicateur, les approbations d'outils sont refusées en silence ; -p consomme l'argument suivant : prompt en dernier
            cmd = [b, "--dangerously-skip-permissions"] + (["--sandbox"] if os.environ.get("RECOD3R_AGY_SANDBOX") == "1" else []) + ["-p", prompt]
        elif agent == "codex":
            cmd = [b, "exec", prompt]
        else:
            raise OSError("agent non pilotable")
        child = subprocess.Popen(cmd, **kw)
        log.close()
        return child
    except Exception:
        log.close()
        raise


def log_tail(cwd, n):
    try:
        t = (Path(cwd) / "agent.log").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    t = redact(t.strip())
    return t[-n:]
