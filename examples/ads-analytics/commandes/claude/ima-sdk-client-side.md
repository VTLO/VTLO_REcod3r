---
description: Supports Interactive Media Ads (IMA) SDK. Use this skill for client-side ad insertion when you are requesting video ads for websites, apps, 
allowed-tools: Bash(python3:*)
---
Résultat du script :
!`python3 ~/vtlorecod_scripts/scripts/ima-sdk-client-side.py $ARGUMENTS`

N'agis que sur cette sortie.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse).
