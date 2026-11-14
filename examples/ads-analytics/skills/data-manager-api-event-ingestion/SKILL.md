---
name: data-manager-api-event-ingestion
description: Guides developers through implementing event and conversion ingestion to Google products using the Data Manager API /v1/events/ingest endpoint and its associated client libraries. Use this skill when the user wants to upload offline conversions, enhanced conversions for leads, click conversions, Goo
---
Exécute `python3 ~/vtlorecod_scripts/scripts/data-manager-api-event-ingestion.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - from the user's context, consider clarifying which destination events are
  - | **Google Analytics** (`GOOGLE_ANALYTICS_PROPERTY`) | Recommended and custom GA4 events | [Send events](http…
  - **Recommended and custom GA4 events** (migrating from the Google Analytics Measurement Protocol):
  - `linked_account` (if you're a data partner accessing the account via a
  - partner link to a manager account). **STRONGLY RECOMMENDED**: Refer to the
  - each error's `reason` and `record_count` under
