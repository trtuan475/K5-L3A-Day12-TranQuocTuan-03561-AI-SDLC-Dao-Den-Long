"""CLI tests for headless.py against Test Contract v1.0 (AC9, AC10) + own scenarios in tests/scenarios."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCN = os.path.join(ROOT, "tests", "scenarios")


def headless(*args):
    out = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False).name
    p = subprocess.run([sys.executable, "headless.py", *args, "--out", out], cwd=ROOT,
                       capture_output=True, text=True)
    lines = []
    if os.path.exists(out):
        with open(out) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        os.unlink(out)
    return p, lines


class TestCLI(unittest.TestCase):
    def test_cli_basic(self):  # AC10
        p, lines = headless("--seed", "1", "--night", "1", "--ticks", "100", "--snapshot-every", "25")
        self.assertEqual(p.returncode, 0, p.stderr)
        snaps = [l["tick"] for l in lines if l["type"] == "snapshot"]
        self.assertEqual(snaps, [0, 25, 50, 75, 100])
        self.assertEqual(lines[-1], {"type": "end", "ticks": 100, "state": "playing", "score": 0})

    def test_cli_bad_inputs_exit2(self):  # AC10
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write('{"frames": [{"tick": 3}, {"tick": 1}]}')
        p, _ = headless("--seed", "1", "--night", "1", "--ticks", "10", "--inputs", f.name)
        os.unlink(f.name)
        self.assertEqual(p.returncode, 2)
        self.assertIn("error", p.stderr)

    def test_cli_bad_json_exit2(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{not json")
        p, _ = headless("--seed", "1", "--night", "1", "--ticks", "10", "--scenario", f.name)
        os.unlink(f.name)
        self.assertEqual(p.returncode, 2)

    def test_cli_determinism(self):  # AC9
        a = headless("--seed", "9", "--night", "1", "--ticks", "3000",
                     "--inputs", os.path.join(SCN, "win_inputs.json"))[1]
        b = headless("--seed", "9", "--night", "1", "--ticks", "3000",
                     "--inputs", os.path.join(SCN, "win_inputs.json"))[1]
        self.assertEqual(a, b)

    def test_scenario_win(self):  # AC4 + AC8 end-to-end through the CLI
        p, lines = headless("--seed", "1", "--night", "1", "--ticks", "2000",
                            "--scenario", os.path.join(SCN, "win.json"),
                            "--inputs", os.path.join(SCN, "win_inputs.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        ev = [l for l in lines if l["type"] == "event"]
        self.assertEqual([e["name"] for e in ev].count("lantern_lit"), 5)
        self.assertEqual(ev[-1]["data"], {"result": "won", "reason": "all_lit"})
        self.assertEqual(lines[-1]["state"], "won")
        self.assertEqual(lines[-2]["type"], "snapshot")
        self.assertEqual(lines[-2]["tick"], lines[-1]["ticks"])


if __name__ == "__main__":
    unittest.main()
