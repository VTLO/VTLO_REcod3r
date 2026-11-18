# VTLO_REcod3r — application autonome

Moteur et serveur en **Python (bibliothèque standard uniquement)**, interface visuelle **HTML** (`recod3r_app/ui/`). Python 3.8+.

```sh
python3 -m recod3r_app                       # ouvre l'interface (serveur local 127.0.0.1, jeton aléatoire)
python3 -m recod3r_app scan                  # scan global du système (jamais automatique au lancement de l'interface)
python3 -m recod3r_app scan --add mes-skills.zip   # uniquement vos ajouts manuels (annexes incluses)
python3 -m recod3r_app convert --yes         # 0–100 % en direct dans le terminal
python3 -m recod3r_app update                # met l'outil à jour (git pull) et rafraîchit /recod3r
python3 -m recod3r_app orchestrer            # orchestration des scripts livrés
python3 -m recod3r_app integrer              # ajoute /recod3r dans agy, Claude Code, Gemini CLI, Codex
```

Installation de la commande `recod3r` : `curl -fsSL https://raw.githubusercontent.com/VTLO/VTLO_REcod3r/main/install-app.sh | sh` (ou `pipx install "git+https://github.com/VTLO/VTLO_REcod3r#subdirectory=app"`).
Fenêtre native facultative : `pip install pywebview` puis `recod3r --fenetre`.

Options : `--agent claude|gemini|agy|codex` · `--add CHEMIN` (répétable) · `--only skill1,skill2` · `--all` · `--orchestrer` · `--out DOSSIER` · `--users N` · `--price EUR_PAR_MTOK` · `--uses N` · `--port N` · `--no-open`.

Variables : `RECOD3R_OUT` (dossier livré), `RECOD3R_AGENT_CMD` (commande d'IA, `{prompt_file}`), `RECOD3R_HOME`, `RECOD3R_DIR`, `RECOD3R_TIMEOUT`, `ANTIGRAVITY_CLI_ALIAS`.

Test : `python3 app/tests/test_app.py`.
