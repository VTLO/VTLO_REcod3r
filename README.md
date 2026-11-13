# ∇TLO · VTLO_REcod3r

**Faire faire au code ce qui n'a pas besoin d'IA. Moins de tokens, plus de contrôle.**

VTLO_REcod3r analyse vos skills, commandes et prompts (Claude Code, Gemini CLI, agy, Codex, ChatGPT…), repère ce qui peut être remplacé par des scripts fiables, puis les écrit, les teste et les installe — après votre validation.

## Installation (une ligne)

```sh
curl -fsSL https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install.sh | sh
```

Le CLI d'IA utilisé est détecté automatiquement. Python 3.8+ suffit (aucune dépendance).

## Utilisation

1. Tapez **`/rec0d`** dans votre CLI (ou `rec0d` dans un terminal) : l'analyse (lecture seule) produit le **rapport n°1**.
2. Étape obligatoire : cliquez **COD3FORM3** pour valider, ou **IGNOR3** pour tout laisser en l'état.
3. Après validation, chaque script est écrit, vérifié (vrais tests, contrôles de sécurité) puis déployé. Les originaux sont sauvegardés.
4. Le **rapport n°2** affiche ce qui a été fait, l'économie de tokens estimée par script, et des workflows proposés pour un orchestrateur.

| Commande | Rôle |
|---|---|
| `vtlo-recod3r rec0d` | analyse + rapport n°1 |
| `vtlo-recod3r rapport` | rapport n°2 |
| `vtlo-recod3r restaurer` | annule tous les remplacements |
| `vtlo-recod3r flow` | orchestrateur de workflows |
| `vtlo-recod3r presentation` | présentation animée pour débutants |
| `vtlo-recod3r diagnostic` / `desinstaller` | état / désinstallation |

Présentation : [`docs/presentation.html`](docs/presentation.html)

## Principe

Si la règle tient en quelques lignes « si… alors… », c'est du code. Sinon, c'est de l'IA. Le code pilote le flux ; l'IA n'intervient que sur un point de décision, et le code revalide sa réponse.

## Licence

GPL-3.0 — logiciel libre, copyleft : lire, modifier, partager, et le rester.

*∇TLO*
