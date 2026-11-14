---
name: google-ads-api-mcp-setup
description: Guides developers through downloading, configuring, and installing the official open-source Google Ads MCP Server. Use this skill when a user wants to connect their AI assistant (such as Gemini, Claude Code, or Cursor) to their Google Ads account to query campaigns or retrieve reporting metrics usin
---
Exécute `python3 ~/vtlorecod_scripts/scripts/google-ads-api-mcp-setup.py <args>` (chemin relatif au dossier de ce skill) et lis UNIQUEMENT sa sortie standard. Ne refais pas ses étapes à la main.
- code 0 : rapporte le résultat.
- code 1 : rapporte stderr et arrête.
- code 3 : stdout est un JSON `needs_ai` ; tranche UNIQUEMENT ce point, puis relance avec `RECOD3R_AI_ANSWER='<json>'` (le script revalide ta réponse). Points de décision :
  - If the environment is macOS, propose:
  - If the environment is Windows, propose:
  - If the environment is Linux, propose:
  - If the user explicitly requests the latest development version from GitHub, propose:
  - [ ] **Explain Stdio Transport:** You **MUST** explicitly explain the communication architecture using the exa…
  - To protect credential security, **do not recommend hardcoding credentials inside the MCP server's source Pyth…
