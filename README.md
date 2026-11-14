<p align="center"><img src="docs/img/hero.svg" alt="VTLO_REcod3r" width="100%"></p>

<p align="center">
<img alt="licence" src="https://img.shields.io/badge/licence-GPL--3.0-39ff88?style=for-the-badge">
<img alt="moteur" src="https://img.shields.io/badge/moteur-Rust-37d6ff?style=for-the-badge">
<img alt="plateformes" src="https://img.shields.io/badge/Linux%20%C2%B7%20Windows%20%C2%B7%20macOS%20%C2%B7%20Android%20%C2%B7%20iOS-a56bff?style=for-the-badge">
</p>

# ∇TLO · VTLO_REcod3r

> **Faites faire au code ce qui n'a pas besoin d'IA. Gardez l'IA pour ce qui demande vraiment de réfléchir.**

VTLO_REcod3r est **la prochaine grosse avancée de votre façon de coder et de raisonner avec « code + IA »** : plus performante, plus rapide, moins chère. C'est la méthode qui rend vos collègues numériques automatisés **prêts pour le réel** : le code exécute, l'IA décide, et le code revalide sa réponse. Pour tous ceux qui veulent des assistants de premier ordre, sans payer l'IA pour recopier la même liste tous les jours.

<p align="center"><img src="docs/img/demo.gif" alt="Démonstration de l'application" width="760"></p>

---

## 1 · L'application (version vitrine)

Une application **autonome et multiplateforme** : elle analyse votre système, vous montre ce que vous gagnez, puis convertit tout en **une seule validation**.

<p align="center"><img src="docs/img/flow.svg" alt="Flux en 5 étapes" width="100%"></p>

**Ce qu'elle fait**

1. **Scanne** votre machine avec les outils habituels : skills, commandes et prompts de Claude, Gemini CLI, Codex, agy… plus les dossiers ou archives `.zip` que vous ajoutez.
2. **Chiffre l'économie** pour chaque élément : **tokens, euros, durée**, nombre de scripts, amortissement. Les hypothèses (utilisateurs, usages par mois, prix du million de tokens) se règlent par curseurs et le rapport se recalcule en direct.
3. **Une seule validation** : **OK** ou **IGNORER**.
4. **Convertit tout d'un coup**, avec l'avancement de **0 à 100 % en direct**, jusqu'à ce que les livrables soient prêts.
5. **Livre** un dossier prêt à l'emploi : `scripts/` (code à lancer), `skills/` (skills légers), `commandes/` (Claude, Gemini, Codex/agy), `LISEZMOI.md`. Aucun test imposé : la vérification, c'est l'usage réel.
6. **Option : l'orchestration**, qui enchaîne les scripts ; l'IA n'est appelée qu'aux points de décision.

<table>
<tr><td><img src="docs/img/app-3-rapport-50.png" alt="Rapport d'économies"></td><td><img src="docs/img/app-4-conversion.png" alt="Conversion 0 à 100 %"></td></tr>
<tr><td align="center"><sub>Rapport : tokens · € · heures, curseurs en direct</sub></td><td align="center"><sub>Conversion : 0 → 100 % en temps réel</sub></td></tr>
<tr><td colspan="2"><img src="docs/img/app-5-livraison.png" alt="Livraison"></td></tr>
</table>

### Installer et lancer

Depuis les sources (Rust récent ; aucune autre dépendance côté moteur) :

```sh
git clone https://github.com/VTLO/VTLO_REcod3r.git && cd VTLO_REcod3r/app
cargo build --release -p recod3r-app
./target/release/recod3r            # ouvre l'application
```

En terminal pur : `recod3r scan` · `recod3r convert --yes` (0–100 % en gros chiffres) · `recod3r orchestrer`. Détails : [`app/README.md`](app/README.md).

Les binaires et l'application fenêtrée (Tauri 2) se construisent via le workflow [`build-app.yml`](.github/workflows/build-app.yml) (Linux, Windows, macOS) ; Android et iOS par `tauri android/ios build`.

### Pourquoi Rust + Tauri 2 ?

Un **moteur Rust unique** (rapide, sans runtime, un seul binaire) partagé par tous les environnements, et une **interface HTML** qui sert de vitrine. **Tauri 2** est la seule voie mature qui couvre à la fois Linux, Windows, macOS, Android et iOS avec le même code.

### Statut

| Plateforme | État |
|---|---|
| Linux | moteur et interface compilés et exécutés de bout en bout (analyse, conversion, livraison) |
| Windows · macOS | code portable ; compilation à valider par la CI fournie |
| Android | via Termux (binaire) ou Tauri ; sandbox système : l'IA ne se pilote que depuis Termux |
| iOS | via Tauri (Xcode) ; sandbox : analyse, rapport et squelettes, pas d'agent IA lancé localement |

---

## 2 · Preuve par l'exemple : Google Ads & Analytics

**16 skills Google** (publicité mobile, Ads API, Data Manager API, Analytics, IMA) passés dans VTLO_REcod3r : **16 scripts** prêts à lancer, dans [`examples/ads-analytics/`](examples/ads-analytics/).

| Skill converti | Économie par usage |
|---|---|
| `google-ads-api-mcp-setup` | ≈ 28 900 tokens |
| `google-ads-api-quickstart` | ≈ 17 700 tokens |
| `data-manager-api-audience-ingestion` | ≈ 11 100 tokens |
| `data-manager-api-event-ingestion` | ≈ 11 000 tokens |
| `google-mobile-ads-android-migrate-to-next-gen` | ≈ 10 800 tokens |
| `google-analytics-data-api-basics` | ≈ 10 200 tokens |
| `google-analytics-admin-api-basics` | ≈ 9 300 tokens |
| `google-ads-api-account-diagnostics` | ≈ 8 800 tokens |
| `google-mobile-ads-validate` | ≈ 2 300 tokens |
| `data-manager-api-setup` | ≈ 2 100 tokens |

**≈ 2,2 millions de tokens économisés par mois (−95 %)** pour un utilisateur à 20 usages par skill et par mois, soit **≈ 6 €/mois** à 2,80 € le million. Avec **50 utilisateurs : ≈ 314 €/mois**, plus de **3 700 € par an**. Chiffres reproductibles : `recod3r scan --dir ads.zip`. Les hypothèses sont modifiables dans l'application.

Ce que les scripts font vraiment, sans IA : audit d'une appli mobile en 5 points, migration Android vers le SDK Next-Gen (imports et Gradle), normalisation et hachage SHA-256 des données pour l'API Data Manager, analyse d'un compte Ads, requêtes GAQL validées, guides de code prêts à copier.

> **Note d'honnêteté.** Les scripts ont été rédigés par l'agent IA d'après les briefs générés par REcod3r (c'est précisément le flux du produit) et vérifiés en usage local ; les appels réels aux API Google n'ont pas été exécutés sur des comptes réels. Les économies sont des estimations.

**Ce que ça démontre :** un jeu de skills « lourds » devient un **outillage exécutable, instantané et gratuit à l'usage**, que l'IA n'ouvre plus que pour décider. C'est le modèle de travail à adopter dès maintenant : **coder mieux, raisonner plus vite, dépenser moins**.

---

## 3 · Version terminal (première itération)

Toujours disponible, en Python 3.8+ sans dépendance.

### Installation

```sh
git clone https://github.com/VTLO/VTLO_REcod3r.git ~/VTLO_REcod3r && sh ~/VTLO_REcod3r/install.sh
```

La commande **`vtlorecod`** est créée (mise à jour : `git pull`).


### Utilisation

1. Tapez **`vtlorecod`** dans un terminal : l'analyse (lecture seule) ouvre automatiquement le **rapport** dans une fenêtre, avec le détail des économies.
2. Une seule validation globale : **OK** ou **IGNORER** (dans la fenêtre, ou `o` / `i` dans le terminal).
3. Si OK : tous les scripts sont écrits en une seule tâche, avec la progression de 0 à 100 % en gros chiffres dans le terminal. Puis : *« IA sur le banc de touche !! Place au c0d3 pour la frappe décisive !!!! »*
4. Le dossier **`~/vtlorecod_scripts/`** contient tout, prêt à lancer : `scripts/` (les scripts), `skills/` (skills convertis), `commandes/` (claude, gemini, codex-agy) et `LISEZMOI.md`.
5. Option : `vtlorecod orchestrer` génère l'orchestration scriptée automatique (workflows qui enchaînent les scripts ; l'IA n'est appelée qu'aux points de décision).

L'écriture des scripts utilise le CLI d'IA détecté (claude, gemini, codex) en mode non interactif, en **un seul appel**. Sans CLI utilisable, les briefs et une consigne unique (`PROMPT.md`) sont prêts : collez-la dans votre IA, puis `vtlorecod finaliser`.

| Commande | Rôle |
|---|---|
| `vtlorecod` | analyse, rapport, validation unique, écriture |
| `vtlorecod finaliser` | installe des scripts rédigés à la main |
| `vtlorecod orchestrer` | génère l'orchestration (option) |
| `vtlorecod flow` | exécute / liste les workflows |
| `vtlorecod restaurer` | annule tous les remplacements (sauvegardes) |
| `vtlorecod presentation` | présentation animée pour débutants |

Présentation : [`docs/presentation.html`](docs/presentation.html)

### Principe

Si la règle tient en quelques lignes « si… alors… », c'est du code. Sinon, c'est de l'IA. Le code pilote le flux ; l'IA n'intervient que sur un point de décision, et le code revalide sa réponse.


---

## Licence

GPL-3.0 : logiciel libre, copyleft. Lire, modifier, partager, et le rester.

*∇TLO*
