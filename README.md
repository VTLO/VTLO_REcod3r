# ∇TLO · VTLO_REcod3r

**Faire faire au code ce qui n'a pas besoin d'IA. Moins de tokens, plus de contrôle.**

VTLO_REcod3r analyse vos skills, commandes et prompts (Claude Code, Gemini CLI, agy, Codex, ChatGPT…), repère ce qui peut être remplacé par des scripts, puis les écrit en une seule tâche après une validation unique.

## Installation (cloner le dépôt)

```sh
git clone https://github.com/VTLO/VTLO_REcod3r.git ~/VTLO_REcod3r && sh ~/VTLO_REcod3r/install.sh
```

Le dépôt reste en local (mise à jour : `git pull`). Python 3.8+ suffit, aucune dépendance. La commande **`vtlorecod`** est créée.

## Utilisation

1. Tapez **`vtlorecod`** dans un terminal : l'analyse (lecture seule) ouvre automatiquement le **rapport** dans une fenêtre, avec le détail des économies.
2. Une seule validation globale : **OK** ou **IGNORER** (dans la fenêtre, ou `o` / `i` dans le terminal).
3. Si OK : tous les scripts sont écrits en une seule tâche, avec la progression de 0 à 100 % en gros chiffres dans le terminal. Puis : *« IA sur le banc de touche !! Place au c0d3 pour la frappe décisive !!!! »*
4. Le dossier **`~/vtlorecod_scripts/`** contient tout, prêt à lancer : `scripts/` (les scripts), `skills/` (skills convertis), `commandes/` (claude, gemini, codex-agy) et `LISEZMOI.md`.
5. Option : `vtlorecod orchestrer` génère l'orchestration scriptée automatique (workflows qui enchaînent les scripts ; l'IA n'est appelée qu'aux points de décision).

L'écriture des scripts utilise le CLI d'IA détecté (claude, gemini, codex) en mode non interactif, en **un seul appel**. Sans CLI utilisable, les briefs et une consigne unique (`PROMPT.md`) sont prêts : collez-la dans votre IA, puis `vtlorecod finaliser`.

| Commande | Rôle |
|---|---|
| `vtlorecod` | analyse, rapport, validation unique, écriture |
| `vtlorecod finaliser` | installe des scripts rédigés à la main |
| `vtlorecod orchestrer` | génère l'orchestration (option) |
| `vtlorecod flow` | exécute / liste les workflows |
| `vtlorecod restaurer` | annule tous les remplacements (sauvegardes) |
| `vtlorecod presentation` | présentation animée pour débutants |

Présentation : [`docs/presentation.html`](docs/presentation.html)

## Principe

Si la règle tient en quelques lignes « si… alors… », c'est du code. Sinon, c'est de l'IA. Le code pilote le flux ; l'IA n'intervient que sur un point de décision, et le code revalide sa réponse.

## Licence

GPL-3.0 — logiciel libre, copyleft : lire, modifier, partager, et le rester.

*∇TLO*
