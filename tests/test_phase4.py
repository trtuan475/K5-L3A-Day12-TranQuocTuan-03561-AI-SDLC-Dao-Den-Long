"""Phase 4 (Ticket-04, contract v1.3): leaderboard, benchmark scene, soak. AC ids P4-x (docs/notes/phase-4-spec.md)."""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest

from lantern_island import leaderboard as lb
from lantern_island.bench_scene import bench_game
from lantern_island.sim import load_tuning

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestLeaderboard(unittest.TestCase):  # P4-3
    def setUp(self):
        self.p = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        os.unlink(self.p)

    def tearDown(self):
        if os.path.exists(self.p):
            os.unlink(self.p)

    def t(self, minute):
        return datetime.datetime(2026, 11, 21, 12, minute, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))

    def test_names(self):
        for ok in ("Tuan", "abc", "A_1_b2c3d4e5", "Mây_Đèn"):  # Vietnamese with diacritics: bonus
            self.assertTrue(lb.valid_name(ok), ok)
        for bad in ("ab", "x" * 13, "a b c", "a-b-c", "", "abc\n"):
            self.assertFalse(lb.valid_name(bad), bad)
        with self.assertRaises(ValueError):
            lb.add("a!", 1, 0, 1, p=self.p)

    def test_sort_ties_top10_persist(self):
        lb.add("first", 500, 1, 7, p=self.p, now=self.t(1))
        lb.add("second", 500, 2, 7, p=self.p, now=self.t(2))
        lb.add("best", 900, 3, 7, p=self.p, now=self.t(3))
        for i in range(10):
            lb.add(f"low{i:02d}", 10 + i, 0, 7, p=self.p, now=self.t(10 + i))
        entries = lb.load(self.p)  # reloaded from disk = survives restart
        self.assertEqual(len(entries), 10)
        self.assertEqual([e["name"] for e in entries[:3]], ["best", "first", "second"])  # tie: earlier first
        self.assertEqual(entries[-1]["name"], "low03")
        self.assertEqual(set(entries[0]), {"name", "score", "nights_won", "achieved_at", "seed"})
        self.assertTrue(entries[0]["achieved_at"].endswith("+07:00"))
        out = self.p + ".out.json"
        lb.export(out, p=self.p)
        with open(out) as f:
            self.assertEqual(json.load(f)["entries"], entries)
        os.unlink(out)

    def test_export_cli(self):  # run_cmd --export-leaderboard (no window is opened)
        lb.add("cliuser", 42, 1, 3, p=self.p)
        out = self.p + ".cli.json"
        env = dict(os.environ, DDL_LEADERBOARD=self.p)
        r = subprocess.run([sys.executable, "play.py", "--export-leaderboard", out], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out) as f:
            self.assertEqual([e["name"] for e in json.load(f)["entries"]], ["cliuser"])
        os.unlink(out)


class TestBenchScene(unittest.TestCase):  # P4-1
    def test_scene(self):
        g = bench_game(42)
        s = g.snapshot()
        self.assertEqual(len(s["shades"]), 200)
        self.assertTrue(all(x["state"] == "wander" for x in s["shades"]))
        self.assertEqual(s["motes_active"], 100)
        self.assertEqual([(L["lit"], L["fuel"]) for L in s["lanterns"][:3]], [(True, 100.0)] * 3)
        self.assertTrue(all(abs(x["pos"][0]) <= 40 and abs(x["pos"][2]) <= 40 for x in s["shades"]))
        self.assertEqual(bench_game(42).snapshot(), s)  # seed 42 -> same scene

    def test_bench_rules_off(self):
        g = bench_game(42)
        p0 = [list(x["pos"]) for x in g.shades]
        for _ in range(600):
            g.step()
        s = g.snapshot()
        self.assertEqual((len(s["shades"]), s["motes_active"]), (200, 100))  # no spawning, no pickups
        self.assertEqual(s["player"]["flames"], load_tuning()["flames"])  # no damage
        self.assertEqual([L["fuel"] for L in s["lanterns"][:3]], [100.0] * 3)  # no fuel decay
        self.assertEqual(s["state"], "playing")
        self.assertNotEqual([x["pos"] for x in g.shades], p0)  # shades still move


class TestSoak(unittest.TestCase):  # P4-2
    def test_soak_short(self):
        sys.path.insert(0, ROOT)
        import soak
        rep = soak.soak(seed=7, nights=3, max_ticks=1200)
        self.assertEqual(rep["crashes"], 0)
        self.assertEqual(len(rep["results"]), 3)
        self.assertLessEqual(rep["mem_end_mb"], 1.2 * rep["mem_start_mb"])


class TestContract13(unittest.TestCase):  # P4-6
    def test_contract(self):
        with open(os.path.join(ROOT, "game.contract.json")) as f:
            c = json.load(f)
        self.assertEqual(c["contract_version"], "1.3")
        self.assertIn("bench_cmd", c)
        self.assertIn("soak_cmd", c)


if __name__ == "__main__":
    unittest.main()
