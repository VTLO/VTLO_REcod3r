---
name: ima-dai-sdk
description: Integrates the Google Interactive Media Ads (IMA) Dynamic Ad Insertion (DAI) SDK into websites, web apps, mobile apps, or TV apps. Use when:
---
Exécute `python3 ~/vtlorecod_scripts/scripts/ima-dai-sdk.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse).
