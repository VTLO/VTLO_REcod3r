---
description: Guides developers through client library installation and authentication setup steps for the Data Manager API. Use this 
allowed-tools: Bash(python3:*)
---
Résultat du script :
!`python3 ~/vtlorecod_scripts/scripts/data-manager-api-setup.py $ARGUMENTS`

N'agis que sur cette sortie.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - these libraries is highly recommended to ensure that user identifier formatting
