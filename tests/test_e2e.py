import json, os, re, subprocess, sys, tempfile, time, unittest, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import fixtures  # noqa: E402
from recod3r import engine as E, forge as F  # noqa: E402


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = Path(cls.tmp.name) / "home"
        (cls.home / "proj").mkdir(parents=True)
        fixtures.build(cls.home)
        cls.state = Path(cls.tmp.name) / "etat"
        cls.env = dict(os.environ, RECOD3R_HOME=str(cls.home), RECOD3R_DIR=str(cls.state), PYTHONPATH=str(ROOT), NO_COLOR="1",
                       RECOD3R_AGENT_CMD=f"{sys.executable} {ROOT}/tests/fake_agent.py {{prompt_file}}")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def last_run(self):
        return sorted(p for p in (self.state / "runs").iterdir() if p.is_dir())[-1]

    def cli(self, *a, timeout=120):
        return subprocess.run([sys.executable, "-m", "recod3r", *a], capture_output=True, text=True, env=self.env,
                              cwd=self.home / "proj", timeout=timeout)


class Parcours(Base):
    """Parcours complet : setup → rec0d (clic) → forge/pilotage → vérif → déploiement → rapport 2 → restauration."""

    def test_01_setup_installe_rec0d_dans_les_cli_detectes(self):
        r = self.cli("setup")
        self.assertEqual(r.returncode, 0, r.stderr)
        for rel in (".claude/commands/rec0d.md", ".gemini/commands/rec0d.toml", ".codex/prompts/rec0d.md", ".gemini/antigravity/global_workflows/rec0d.md"):
            t = (self.home / rel).read_text(encoding="utf-8")
            self.assertIn("COD3FORM3", t, rel)
            self.assertIn("vtlo-recod3r rec0d --bg", t)
        self.assertIn("/prompts:rec0d", r.stdout)

    def test_02_decision_par_clic_http_puis_pilotage(self):
        r = self.cli("rec0d", "--bg", "--sans-ouvrir", "--export", str(self.home / "chatgpt/conversations.json"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        url = re.search(r"(http://127\.0\.0\.1:\d+/[\w-]+/)", r.stdout).group(1)
        # 1) rien n'est décidé tant qu'on n'a pas cliqué
        w = self.cli("attendre", "--max", "1")
        self.assertEqual(w.returncode, 75)
        self.assertIn("EN_ATTENTE", w.stdout)
        # 2) la page est servie, en français, avec les 2 boutons
        page = urllib.request.urlopen(url).read().decode()
        for s in ("COD3FORM3", "IGNOR3", "Plan de codage", "puzzle(", "Rapport n°1"):
            self.assertIn(s, page)
        self.assertNotIn("Plan of", page)
        # 3) sécurité : mauvais hôte / mauvais jeton / décision invalide
        req = urllib.request.Request(url, headers={"Host": "evil.example"})
        with self.assertRaises(urllib.error.HTTPError) as c:
            urllib.request.urlopen(req)
        self.assertEqual(c.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as c:
            urllib.request.urlopen(url.rsplit("/", 2)[0] + "/mauvais/")
        self.assertEqual(c.exception.code, 404)
        bad = urllib.request.Request(url + "decide", data=b'{"decision":"PEUT-ETRE"}', method="POST")
        with self.assertRaises(urllib.error.HTTPError) as c:
            urllib.request.urlopen(bad)
        self.assertEqual(c.exception.code, 400)
        # 4) clic COD3FORM3 sur une sélection
        run = F.latest_run() if False else None
        plan = json.loads(next((self.state / "runs").glob("*/plan.json")).read_text())
        pick = [i["id"] for i in plan["items"] if i["asset"]["name"] in ("csv-cleaner", "changelog", "never-used")]
        post = urllib.request.Request(url + "decide", data=json.dumps({"decision": "COD3FORM3", "ids": pick}).encode(), method="POST",
                                      headers={"Content-Type": "application/json"})
        self.assertTrue(json.loads(urllib.request.urlopen(post).read())["ok"])
        w = self.cli("attendre", "--max", "5")
        self.assertEqual(w.returncode, 0, w.stdout)
        self.assertIn("DECISION=COD3FORM3", w.stdout)
        # 5) forge + pilotage par le faux agent
        before = (self.home / ".claude/skills/csv-cleaner/SKILL.md").read_text()
        f = self.cli("forge", "--piloter", "--agent", "claude", "--sans-ouvrir", timeout=300)
        self.assertEqual(f.returncode, 0, f.stdout + f.stderr)
        run = self.last_run()
        etat = json.loads((run / "etat.json").read_text())["items"]
        statuts = {k: v["statut"] for k, v in etat.items()}
        self.assertEqual(statuts.get("csv-cleaner"), "deploye", statuts)
        self.assertEqual(statuts.get("changelog"), "deploye", statuts)
        self.assertEqual(statuts.get("never-used"), "abandonne", statuts)       # le faux agent n'a rien su en faire
        self.assertNotIn("rename-photos", statuts)                               # non sélectionné
        # skill remplacé par un stub léger + sauvegarde + script installé
        after = (self.home / ".claude/skills/csv-cleaner/SKILL.md").read_text()
        self.assertLess(E.est_tokens(after), E.est_tokens(before))
        self.assertIn("RECOD3R_AI_ANSWER", after)
        self.assertTrue((self.home / ".claude/skills/csv-cleaner/scripts/csv-cleaner.py").is_file())
        self.assertTrue((self.state / "bin/csv-cleaner.py").is_file())
        self.assertTrue(any((run / "sauvegardes/csv-cleaner").glob("SKILL.md")))
        # 6) le script déployé fonctionne vraiment
        csvf = self.home / "d.csv"
        csvf.write_text("id,date,nom\n2,02/01/2026,b\n1,01/01/2026,a\n1,01/01/2026,a\n,03/01/2026,x\n", encoding="utf-8")
        p = subprocess.run([sys.executable, str(self.state / "bin/csv-cleaner.py"), str(csvf), "--json"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["gardees"], 2)
        self.assertEqual((self.home / "d.clean.csv").read_text(), "id,date,nom\n1,2026-01-01,a\n2,2026-01-02,b\n")
        # 7) rapport 2
        rap = run / "rapport2.html"
        self.assertTrue(rap.is_file())
        h = rap.read_text()
        for s in ("Ce qui a été fait", "Déployé", "Abandonné", "Proposition : des workflows", "restaurer", "puzzle("):
            self.assertIn(s, h)
        bil = json.loads((run / "bilan.json").read_text())
        self.assertGreater(bil["totaux"]["eco_mois"], 0)
        self.assertGreater(bil["totaux"]["taux_global"], 0.5)
        self.assertTrue(bil["workflows"], "au moins un workflow proposé")
        # 8) orchestrateur : simulation puis exécution réelle
        wfs = list(bil["workflows"])
        self.assertTrue(any(w.startswith("chaine-") for w in wfs), wfs)
        d = self.cli("flow", "executer", wfs[0], "--dry", "--var", f"entree={csvf}")
        self.assertEqual(d.returncode, 0, d.stdout + d.stderr)
        self.assertIn("simulation", d.stdout)
        solo = Path(self.tmp.name) / "solo.json"
        solo.write_text(json.dumps({"nom": "solo", "variables": {}, "etapes": [
            {"id": "nettoyer", "cmd": [sys.executable, str(self.state / "bin/csv-cleaner.py"), "{entree}", "--json"]},
            {"id": "verif", "cmd": [sys.executable, "-c", "import sys,json;d=json.load(sys.stdin);sys.exit(0 if d['gardees']==2 else 1)"],
             "stdin": "{nettoyer.stdout}"}]}))
        e = self.cli("flow", "executer", str(solo), "--var", f"entree={csvf}")
        self.assertEqual(e.returncode, 0, e.stdout + e.stderr)
        self.assertIn("TERMINÉ", e.stdout)
        # 9) restauration complète
        rs = self.cli("restaurer")
        self.assertEqual(rs.returncode, 0, rs.stderr)
        self.assertEqual((self.home / ".claude/skills/csv-cleaner/SKILL.md").read_text(), before)
        self.assertFalse((self.state / "bin/csv-cleaner.py").exists())


class Verification(Base):
    def test_verifier_refuse_les_squelettes_et_le_code_dangereux(self):
        self.cli("rec0d", "--decision", "cod3form3", "--sans-ouvrir")
        self.cli("forge")
        run = self.last_run()
        slug = next(iter(json.loads((run / "etat.json").read_text())["items"]))
        v = self.cli("verifier", slug)
        self.assertEqual(v.returncode, 1)
        self.assertIn("marqueur", v.stdout)
        with self.assertRaises(RuntimeError):
            F.deployer(run, slug)                       # jamais de déploiement sans vérification
        script = Path(json.loads((run / "etat.json").read_text())["items"][slug]["script"])
        t = script.read_text()
        if script.suffix == ".py":
            bad = "\n".join(l for l in t.splitlines() if E.UNIMPL_MARK not in l) + "\nimport os\nos.system('echo hi')\n"
            script.write_text(bad)
            v = self.cli("verifier", slug)
            self.assertEqual(v.returncode, 1)
            self.assertIn("dangereuses", v.stdout)


class Ignorer(Base):
    def test_ignor3_ne_modifie_rien(self):
        snap = {p: p.read_text() for p in self.home.rglob("SKILL.md")}
        r = self.cli("rec0d", "--decision", "ignor3", "--sans-ouvrir")
        self.assertEqual(r.returncode, 1)
        self.assertIn("DECISION=IGNOR3", r.stdout)
        self.assertEqual(self.cli("forge").returncode, 1)         # pas de forge sans COD3FORM3
        self.assertEqual(snap, {p: p.read_text() for p in self.home.rglob("SKILL.md")})


if __name__ == "__main__":
    unittest.main()
