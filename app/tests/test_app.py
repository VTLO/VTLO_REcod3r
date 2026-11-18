"""Test de bout en bout : analyse, sélection manuelle, conversion par un agent factice, orchestration."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recod3r_app.api import App  # noqa: E402

SKILL = """---
name: rapport-hebdo
description: Génère le rapport hebdomadaire
---
1. Lister les fichiers du dossier `ventes/` triés par date.
2. Compter les lignes de chaque CSV avec `wc -l`.
3. Additionner les colonnes montant et écrire le total dans `total.txt`.
4. Copier le fichier `total.txt` vers `archive/`.
5. Rédiger un commentaire d'analyse sur les tendances.
"""
FAKE = """import re, sys, pathlib
p = pathlib.Path(sys.argv[1]); run = p.parent
for s in (run / "forge").glob("*/scripts/*"):
    s.write_text(re.sub(r".*RECOD3R:A_IMPLEMENTER.*\\n", "", s.read_text()) + "\\n# implémenté\\n")
"""


class Bout(unittest.TestCase):
    def test_flux_complet(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            sk = t / "mon-skill"
            (sk / "scripts").mkdir(parents=True)
            (sk / "references").mkdir()
            (sk / "SKILL.md").write_text(SKILL, encoding="utf-8")
            (sk / "scripts" / "ancien.sh").write_text("echo ancien\n", encoding="utf-8")
            (sk / "references" / "tva.md").write_text("TVA 20 %\n", encoding="utf-8")
            glob = t / "home/.claude/skills/global-skill"  # présent sur la machine : ne doit PAS être scanné sans demande explicite
            glob.mkdir(parents=True)
            (glob / "SKILL.md").write_text(SKILL.replace("rapport-hebdo", "global-skill"), encoding="utf-8")
            (t / "agent.py").write_text(FAKE, encoding="utf-8")
            os.environ.update(RECOD3R_HOME=str(t / "home"), RECOD3R_DIR=str(t / "etat"), RECOD3R_OUT=str(t / "out"),
                              RECOD3R_AGENT_CMD='"%s" "%s" {prompt_file}' % (sys.executable, t / "agent.py"))
            app = App()
            self.assertEqual(app.handle("state")["items"], [])  # rien n'est scanné au lancement
            st = app.handle("ajouter", {"paths": [str(sk / "SKILL.md")]})
            self.assertEqual([i["name"] for i in st["items"]], ["rapport-hebdo"])  # ajout manuel : pas de scan du système
            self.assertEqual(st["items"][0]["annexes"], ["references/tva.md", "scripts/ancien.sh"])
            self.assertTrue(st["items"][0]["selected"])
            st = app.handle("selection", {"all": "aucun"})
            self.assertEqual(app.handle("convert", {})["error"], "aucun skill sélectionné : cochez au moins un élément")
            app.handle("selection", {"only": ["rapport-hebdo"]})
            app.handle("convert", {})
            for _ in range(100):
                st = app.handle("state")
                if st["phase"] == "done":
                    break
                time.sleep(0.2)
            self.assertEqual(st["phase"], "done")
            self.assertEqual(st["done"], ["rapport-hebdo"])
            self.assertTrue((t / "out/scripts/rapport-hebdo.py").is_file())
            # les annexes (scripts, références) sont embarquées automatiquement dans le skill livré
            self.assertTrue((t / "out/skills/rapport-hebdo/references/tva.md").is_file())
            self.assertTrue((t / "out/skills/rapport-hebdo/scripts/ancien.sh").is_file())
            self.assertIn("references/tva.md", (t / "out/skills/rapport-hebdo/SKILL.md").read_text())
            st = app.handle("scan", {"global": True})  # scan global : seulement sur demande
            self.assertIn("global-skill", [i["name"] for i in st["items"]])
            r = app.handle("orchestrer", {})
            self.assertTrue(r["ok"])
            self.assertIn("scripts/rapport-hebdo.py", (t / "out/orchestrer.txt").read_text())


if __name__ == "__main__":
    unittest.main()
