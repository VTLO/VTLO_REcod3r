# VTLO_REcod3r — application autonome

Cœur **Rust** (`core/`), interface visuelle **HTML** (`ui/`), coque **Tauri 2** (`src-tauri/`) pour Linux, Windows, macOS, Android et iOS.

```sh
cargo build --release -p recod3r-app     # binaire autonome : target/release/recod3r
./target/release/recod3r                 # ouvre l'interface (serveur local 127.0.0.1, jeton aléatoire)
./target/release/recod3r scan --dir mes-skills.zip
./target/release/recod3r convert --yes   # 0–100 % en direct dans le terminal
./target/release/recod3r orchestrer      # option : orchestration des scripts livrés
```

Application fenêtrée (Tauri 2) :

```sh
cd src-tauri && npx @tauri-apps/cli@2 icon icon-source.png && npx @tauri-apps/cli@2 build
npx @tauri-apps/cli@2 android init && npx @tauri-apps/cli@2 android build   # Android (SDK + NDK)
npx @tauri-apps/cli@2 ios init && npx @tauri-apps/cli@2 ios build          # iOS (macOS + Xcode)
```

Variables : `RECOD3R_OUT` (dossier livré), `RECOD3R_AGENT_CMD` (commande d'IA, `{prompt_file}`), `RECOD3R_HOME`, `RECOD3R_TIMEOUT`.
