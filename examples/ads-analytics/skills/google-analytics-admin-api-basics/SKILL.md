---
name: google-analytics-admin-api-basics
description: Manages Google Analytics account and property settings, enables the Analytics Admin API via the Cloud CLI, lists accounts and properties, and manages data streams, custom dimensions, conversion events, and integrations. Use when you need to programmatically configure Google Analytics accounts, provi
---
Exécute `python3 ~/vtlorecod_scripts/scripts/google-analytics-admin-api-basics.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - Create Account summaries
  - latest features, consider using `v1alpha`.
