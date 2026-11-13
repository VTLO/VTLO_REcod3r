import json, os, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from recod3r import flow as W  # noqa: E402

SCRIPT = '''import json, os, sys
r = os.environ.get("RECOD3R_AI_ANSWER")
if not r:
    print(json.dumps({"needs_ai": "a ou b ?", "context": {"x": 1}})); sys.exit(3)
a = json.loads(r)
if a.get("choix") not in ("a", "b"):
    print("réponse IA refusée", file=sys.stderr); sys.exit(1)       # revalidation par le code
print(json.dumps({"retenu": a["choix"]}))
'''


class Flow(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.s = Path(self.td.name) / "decide.py"
        self.s.write_text(SCRIPT)
        self.wf = {"nom": "t", "variables": {}, "etapes": [
            {"id": "choisir", "cmd": [sys.executable, str(self.s)]},
            {"id": "suite", "cmd": [sys.executable, "-c", "import sys,json;print(json.load(sys.stdin)['retenu'])"], "stdin": "{choisir.stdout}"}]}

    def tearDown(self):
        self.td.cleanup()
        os.environ.pop("RECOD3R_AGENT_CMD", None)

    def test_pause_sans_agent(self):
        r = W.run_workflow(self.wf, log=lambda *_: None)
        self.assertEqual(r["statut"], "pause_ia")
        self.assertEqual(r["question"], "a ou b ?")

    def test_ia_aux_points_de_decision_puis_revalidation(self):
        os.environ["RECOD3R_AGENT_CMD"] = f"{sys.executable} {ROOT}/tests/fake_ai.py {{prompt_file}}"
        r = W.run_workflow(self.wf, log=lambda *_: None)
        self.assertEqual(r["statut"], "ok", r)
        self.assertEqual(r["appels_ia"], 1)
        self.assertEqual(r["etapes"][1]["stdout"].strip(), "b")

    def test_variables_inconnues_et_reprise(self):
        wf = {"nom": "v", "etapes": [{"id": "a", "cmd": ["echo", "{absente}"]}]}
        self.assertEqual(W.run_workflow(wf, log=lambda *_: None)["statut"], "erreur")
        wf = {"nom": "v", "etapes": [{"id": "a", "cmd": ["false"]}, {"id": "b", "cmd": ["true"]}]}
        self.assertEqual(W.run_workflow(wf, log=lambda *_: None)["statut"], "echec")
        self.assertEqual(W.run_workflow(wf, depuis="b", log=lambda *_: None)["statut"], "ok")

    def test_json_chemin(self):
        wf = {"nom": "j", "etapes": [{"id": "a", "cmd": [sys.executable, "-c", "print('{\"k\":{\"v\":42}}')"]},
                                     {"id": "b", "cmd": ["echo", "{a.json.k.v}"]}]}
        r = W.run_workflow(wf, log=lambda *_: None)
        self.assertEqual(r["etapes"][1]["stdout"].strip(), "42")


if __name__ == "__main__":
    unittest.main()
