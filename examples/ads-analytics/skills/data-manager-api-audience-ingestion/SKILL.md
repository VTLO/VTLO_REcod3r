---
name: data-manager-api-audience-ingestion
description: Guides developers through managing (adding, removing, and clearing) audience members for Google products using the Data Manager API and its associated client libraries. Use this skill when the user wants to upload audience members, remove specific users, or clear/replace an entire audience for Custo
---
Exécute `python3 ~/vtlorecod_scripts/scripts/data-manager-api-audience-ingestion.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - destination and use case. Do this before answering questions or writing code
  - `linked_account` (if you're a data partner accessing the account via a
  - partner link to a manager account). **STRONGLY RECOMMENDED**: Refer to the
  - each error's `reason` and `record_count` under
  - **Warning Details**: Inspect each warning's `reason` and `record_count`
