# Scripts VTLO_REcod3r

Chaque script remplace les étapes mécaniques d'un de vos skills/prompts. Lancez-les à la main ou depuis votre outil d'IA favori.

| Script | Langage | Lancer | Économie estimée |
|---|---|---|---|
| `google-ads-api-mcp-setup` | python | `python3 scripts/google-ads-api-mcp-setup.py <entrée>` | −97 % · 570 808 tokens/mois |
| `google-ads-api-quickstart` | python | `python3 scripts/google-ads-api-quickstart.py <entrée>` | −96 % · 347 584 tokens/mois |
| `data-manager-api-audience-ingestion` | python | `python3 scripts/data-manager-api-audience-ingestion.py <entrée>` | −94 % · 215 431 tokens/mois |
| `data-manager-api-event-ingestion` | python | `python3 scripts/data-manager-api-event-ingestion.py <entrée>` | −93 % · 212 773 tokens/mois |
| `google-mobile-ads-android-migrate-to-next-gen` | python | `python3 scripts/google-mobile-ads-android-migrate-to-next-gen.py <entrée>` | −74 % · 209 166 tokens/mois |
| `google-analytics-data-api-basics` | python | `python3 scripts/google-analytics-data-api-basics.py <entrée>` | −97 % · 197 360 tokens/mois |
| `google-analytics-admin-api-basics` | python | `python3 scripts/google-analytics-admin-api-basics.py <entrée>` | −96 % · 180 446 tokens/mois |
| `google-ads-api-account-diagnostics` | python | `python3 scripts/google-ads-api-account-diagnostics.py <entrée>` | −93 % · 169 143 tokens/mois |
| `google-mobile-ads-validate` | python | `python3 scripts/google-mobile-ads-validate.py <entrée>` | −81 % · 41 115 tokens/mois |
| `data-manager-api-setup` | python | `python3 scripts/data-manager-api-setup.py <entrée>` | −85 % · 36 947 tokens/mois |

Scripts complémentaires (petits skills « guides » : le contenu est servi par le script, l'IA n'est plus nécessaire) :

| Script | Langage | Lancer | Rôle |
|---|---|---|---|
| `google-mobile-ads-banner` | python | `python3 scripts/google-mobile-ads-banner.py --liste` | guide du skill (code, étapes, sections) |
| `google-mobile-ads-interstitial` | python | `python3 scripts/google-mobile-ads-interstitial.py --liste` | guide du skill (code, étapes, sections) |
| `google-mobile-ads-rewarded` | python | `python3 scripts/google-mobile-ads-rewarded.py --liste` | guide du skill (code, étapes, sections) |
| `google-mobile-ads-get-started` | python | `python3 scripts/google-mobile-ads-get-started.py --liste` | guide du skill (code, étapes, sections) |
| `ima-sdk-client-side` | python | `python3 scripts/ima-sdk-client-side.py --liste` | guide du skill (code, étapes, sections) |
| `ima-dai-sdk` | python | `python3 scripts/ima-dai-sdk.py --liste` | guide du skill (code, étapes, sections) |

## Contrat commun (compatible pipeline)

- entrées : arguments, fichiers ou stdin · sortie : texte court, ou `--json` (un objet JSON)
- codes : `0` ok · `1` échec · `2` usage · `3` décision IA requise (JSON `needs_ai`)
- au code 3, relancez avec la réponse de l'IA dans `RECOD3R_AI_ANSWER` : le script la revalide.

## Dans votre outil d'IA

- `skills/<nom>/SKILL.md` : skill léger prêt à copier (Claude Code, Gemini CLI, agy…).
- `commandes/claude/`, `commandes/gemini/`, `commandes/codex-agy/` : commandes slash prêtes à copier.

## Annuler

`vtlorecod restaurer` remet les fichiers d'origine remplacés depuis leur sauvegarde.

## Données

`data/<skill>/` contient le SKILL.md et les fichiers `references/` d'origine, lus par les scripts. Ne déplacez pas `scripts/` sans `data/`.
