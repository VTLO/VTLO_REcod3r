---
description: Guides developers through client library installation and authentication setup steps for the Data Manager API. Use this 
---
Exécute `python3 ~/vtlorecod_scripts/scripts/data-manager-api-setup.py $ARGUMENTS` et lis UNIQUEMENT sa sortie standard (ne refais pas ses étapes à la main).
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - these libraries is highly recommended to ensure that user identifier formatting
