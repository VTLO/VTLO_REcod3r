---
description: Diagnoses Google Ads account performance issues such as conversion loss (value or volume), low lead flow/volume, and los
allowed-tools: Bash(python3:*)
---
Résultat du script :
!`python3 ~/vtlorecod_scripts/scripts/google-ads-api-account-diagnostics.py $ARGUMENTS`

N'agis que sur cette sortie.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - To identify lost opportunities due to ad rank, bids, or budgets, analyze impression share metrics.
  - **Analyze**:
  - **Analyze**:
  - Do not write or execute custom Python scripts or use the Google Ads client library to query the API, as they …
  - **Analyze**: Check if the loss is limited to certain devices (e.g., mobile vs desktop) or specific conversion…
