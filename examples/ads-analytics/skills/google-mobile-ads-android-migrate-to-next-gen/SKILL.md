---
name: google-mobile-ads-android-migrate-to-next-gen
description: Migrates Android applications from the old, legacy Google Mobile
---
Exécute `python3 ~/vtlorecod_scripts/scripts/google-mobile-ads-android-migrate-to-next-gen.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - `com.google.android.gms.ads.mediation.Adapter` MUST continue using
  - | Adapter Response Info | `AdapterResponseInfo` | `common.AdSourceResponseInfo` |
  - | Add Network Extras (Ad Source Adapter) | `AdRequest.Builder().addNetworkExtrasBundle(Class<MediationExtrasR…
  - | Loaded Adapter Responses Info | `responseInfo.getLoadedAdapterResponseInfo()` | `responseInfo.loadedAdSourc…
  - | Get Adapter Responses | `responseInfo.getAdapterResponses()` | `responseInfo.adSourceResponses` |
  - | Get Mediation Adapter Class | `responseInfo.getMediationAdapterClassName()` | `responseInfo.adapterClassNam…
