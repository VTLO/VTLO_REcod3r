---
name: ima-sdk-client-side
description: Supports Interactive Media Ads (IMA) SDK. Use this skill for client-side ad insertion when you are requesting video ads for websites, apps, 
---
Exécute `python3 ~/vtlorecod_scripts/scripts/ima-sdk-client-side.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse).
