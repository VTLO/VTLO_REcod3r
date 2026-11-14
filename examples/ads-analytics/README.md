# Preuve par l'exemple — Google Ads & Analytics

16 skills Google (publicité mobile, Ads API, Data Manager API, Analytics, IMA) analysés puis convertis en 16 scripts par VTLO_REcod3r.

| | |
|---|---|
| `scripts/` | les 16 scripts (Python, bibliothèque standard), contrat commun : 0 ok · 1 échec · 2 usage · 3 décision IA requise |
| `skills/` | un skill léger par script (≈ 80 tokens au lieu de milliers) |
| `commandes/` | commandes prêtes à copier pour Claude, Gemini CLI, Codex / agy |
| `LISEZMOI.md` | mode d'emploi des scripts |

## Ce que fait le moteur, ce que fait l'IA

1. **VTLO_REcod3r** (analyse, économie, squelettes, briefs, livraison) classe chaque skill, découpe les étapes « code » / « IA » et prépare un brief par script.
2. **L'agent IA** détecté écrit les scripts en une seule tâche, d'après ces briefs.
3. Les scripts tournent ensuite pour 0 token ; l'IA n'est rappelée qu'aux décisions (code 3).

## Reproduire l'analyse

```sh
recod3r scan --dir chemin/vers/ads.zip          # rapport dans le terminal
recod3r convert --yes --dir chemin/vers/ads.zip  # conversion avec 0–100 % en direct
```

## Données des skills

Les scripts « guides » lisent le contenu des skills d'origine dans `data/<nom-du-skill>/` (à côté de `scripts/`) ou via la variable `RECOD3R_DATA`. Ces textes appartiennent à leurs auteurs : ils ne sont pas redistribués ici. Copiez-y vos skills (`SKILL.md` et `references/`).

## Limites connues

- Les appels réels aux API Google (envoi Data Manager, etc.) n'ont pas été exécutés contre des comptes réels.
- `google-ads-api-account-diagnostics` ne contacte pas l'API : il génère les requêtes GAQL et analyse des exports (le skill d'origine interdit d'interroger le compte autrement).
- `google-mobile-ads-android-migrate-to-next-gen` automatise imports et Gradle ; le refactor des appels est listé fichier:ligne pour l'IA.
