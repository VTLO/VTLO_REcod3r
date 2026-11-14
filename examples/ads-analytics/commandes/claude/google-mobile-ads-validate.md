---
description: Validates a project's Google Mobile Ads (GMA) SDK integration for iOS, Android, or Unity projects. Use when conducting a
allowed-tools: Bash(python3:*)
---
Résultat du script :
!`python3 ~/vtlorecod_scripts/scripts/google-mobile-ads-validate.py $ARGUMENTS`

N'agis que sur cette sortie.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - evaluate all checklist items.
  - Mediation adapter compatibility:
  - `references/mediation-adapter-compatibility.md`
  - | Mediation adapter compatibility | {{status_4}} | {{findings_4}} | {{next_steps_4}} |
  - (e.g., ad preloading), evaluate only the relevant check(s) without running
