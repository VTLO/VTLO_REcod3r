---
name: data-manager-api-setup
description: Guides developers through client library installation and authentication setup steps for the Data Manager API. Use this skill when a user is getting started with the Data Manager API and needs to setup their local environment, install the client library, or setup access to the API. Don't use for imp
---
Exécute `python3 ~/vtlorecod_scripts/scripts/data-manager-api-setup.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - these libraries is highly recommended to ensure that user identifier formatting
