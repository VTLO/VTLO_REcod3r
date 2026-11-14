---
name: google-analytics-data-api-basics
description: Manages Google Analytics reporting data, enables the Analytics Data API via the Cloud CLI, and creates reports using the Google Analytics Data API (v1beta). Use when you need to interact with Google Analytics properties, run customized analytics reports, query metrics (like activeUsers, screenPageVi
---
Exécute `python3 ~/vtlorecod_scripts/scripts/google-analytics-data-api-basics.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - (aucun : le script fait tout le travail)
