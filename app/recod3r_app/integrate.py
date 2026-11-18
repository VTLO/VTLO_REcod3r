"""Intégration dans les CLI d'IA : dépose un skill / une commande « recod3r » là où chaque outil les lit."""
from .engine import home, which
from .forge import tilde

SKILL = """---
name: recod3r
description: Transforme en scripts exécutables les skills, prompts et workflows qui n'ont pas besoin d'IA (économie de tokens, d'argent et de temps). À utiliser quand l'utilisateur dit /recod3r, « convertis mes skills en scripts » ou « réduis ma consommation de tokens ».
---

# VTLO_REcod3r

1. Lance `recod3r scan` (scan global ; `recod3r scan --add CHEMIN` pour des skills précis) et présente le rapport tel quel (éléments convertibles, tokens et euros économisés, durées).
2. Demande une seule validation à l'utilisateur. Il peut choisir lui-même les skills : `--only nom1,nom2`, en ajouter avec `--add CHEMIN` (fichier, dossier ou .zip), ou tout prendre avec `--all`.
3. Après accord : `recod3r convert --yes --agent AGENT` (AGENT = claude, gemini, agy ou codex selon l'outil courant). Les scripts sont livrés dans `~/vtlorecod_scripts/`, avec les annexes (scripts, références) de chaque skill.
4. Une fois les scripts livrés, propose à l'utilisateur de lancer l'orchestration (`recod3r orchestrer`, ou `--orchestrer` avec la conversion) : c'est le pipeline complet prêt à l'emploi.

Ne réécris pas les scripts toi-même : l'outil pilote la conversion et affiche la progression de 0 à 100 %.
"""
PROMPT = "Exécute le skill recod3r : lance `recod3r scan`, présente le rapport, demande ma validation, puis `recod3r convert --yes --agent AGENT`. Livraison dans ~/vtlorecod_scripts/."


def _put(p, txt, done):
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
        done.append(tilde(p))
    except OSError:
        pass


def _has(d, bins):
    return (home() / d).exists() or any(which(b) for b in bins)


def integrer(only=None):
    """Installe pour chaque CLI détecté (ou seulement `only`). Retourne les fichiers écrits."""
    h, done = home(), []

    def want(k):
        return only is None or only == k or only == "all"

    def sk(a):
        return SKILL.replace("AGENT", a)

    if want("claude") and (only or _has(".claude", ["claude"])):
        _put(h / ".claude/skills/recod3r/SKILL.md", sk("claude"), done)
        _put(h / ".claude/commands/recod3r.md", PROMPT.replace("AGENT", "claude"), done)
    if want("gemini") and (only or _has(".gemini/settings.json", ["gemini"])):
        _put(h / ".gemini/skills/recod3r/SKILL.md", sk("gemini"), done)
        _put(h / ".gemini/commands/recod3r.toml", 'description = "VTLO_REcod3r : skills vers scripts"\nprompt = """%s"""\n' % PROMPT.replace("AGENT", "gemini"), done)
    if want("agy") and (only or _has(".gemini/antigravity-cli", ["agy", "antigravity"])):
        _put(h / ".gemini/antigravity-cli/skills/recod3r/SKILL.md", sk("agy"), done)
    if want("codex") and (only or _has(".codex", ["codex"])):
        _put(h / ".codex/prompts/recod3r.md", PROMPT.replace("AGENT", "codex"), done)
    return done
