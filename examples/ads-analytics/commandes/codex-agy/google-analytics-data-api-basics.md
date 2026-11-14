---
description: Manages Google Analytics reporting data, enables the Analytics Data API via the Cloud CLI, and creates reports using the
---
Exécute `python3 ~/vtlorecod_scripts/scripts/google-analytics-data-api-basics.py $ARGUMENTS` et lis UNIQUEMENT sa sortie standard (ne refais pas ses étapes à la main).
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - (aucun : le script fait tout le travail)
