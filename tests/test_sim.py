"""Unit tests for the game core. Each test names the acceptance criterion (AC) from docs/notes/phase-1-spec.md."""
import math
import unittest

from lantern_island.sim import Game, ScenarioError, load_tuning, validate_inputs

T = load_tuning()


def empty(**kw):
    sc = {"random_motes": False, "random_shades": False, "motes": [], "shades": []}
    sc.update(kw)
    return Game(seed=1, scenario=sc)


def run(g, n, frames=None):
    """Run n steps; frames = {tick: frame}. Returns all events (tick, name, data)."""
    frames = frames or {}
    ev = []
    for _ in range(n):
        ev += g.step(frames.get(g.tick))
        if g.state != "playing":
            break
    return ev


def names(ev):
    return [e[1] for e in ev]


class TestInit(unittest.TestCase):
    def test_initial_state(self):  # AC1
        g = Game(seed=7)
        s = g.snapshot()
        self.assertEqual(s["player"]["pos"], [0.0, 0.0, 0.0])
        self.assertEqual(len(s["lanterns"]), T["lantern_count_night1"])
        self.assertEqual([l["id"] for l in s["lanterns"]], ["L1", "L2", "L3", "L4", "L5"])
        self.assertEqual(s["state"], "playing")
        self.assertEqual(s["time_left_s"], T["night1_duration_s"])
        self.assertEqual(s["player"]["flames"], T["flames"])
        self.assertGreater(s["motes_active"], 0)

    def test_scenario_setup_no_events_no_score(self):
        g = empty(lanterns=[{"id": "L1", "lit": True}], player={"carried": 4, "flames": 2})
        self.assertEqual(g.score, 0)
        self.assertTrue(g.lanterns[0]["lit"])
        self.assertEqual(g.player["carried"], 4)

    def test_bad_night(self):
        with self.assertRaises(ScenarioError):
            Game(seed=1, night=2)


class TestMove(unittest.TestCase):
    def test_move_speed(self):  # AC2
        g = empty()
        run(g, 60, {0: {"move": [0, 1]}})
        self.assertAlmostEqual(g.player["pos"][2], T["player_speed"], places=6)
        self.assertAlmostEqual(g.player["pos"][0], 0.0, places=6)

    def test_cam_yaw(self):  # AC2: yaw 90 -> move z=1 maps to +X
        g = empty()
        run(g, 60, {0: {"move": [0, 1], "cam_yaw_deg": 90}})
        self.assertAlmostEqual(g.player["pos"][0], T["player_speed"], places=6)
        self.assertAlmostEqual(g.player["pos"][2], 0.0, places=6)

    def test_normalize(self):  # AC2
        g = empty()
        run(g, 60, {0: {"move": [1, 1]}})
        self.assertAlmostEqual(math.hypot(g.player["pos"][0], g.player["pos"][2]), T["player_speed"], places=6)

    def test_fields_persist(self):  # contract C: absent fields keep old value
        g = empty()
        run(g, 60, {0: {"move": [0, 1]}, 30: {"cam_yaw_deg": 0}})
        self.assertAlmostEqual(g.player["pos"][2], T["player_speed"], places=6)

    def test_jump(self):
        g = empty()
        run(g, 10, {0: {"jump": True}})
        self.assertGreater(g.player["pos"][1], 0)
        run(g, 120)
        self.assertEqual(g.player["pos"][1], 0.0)

    def test_fence(self):
        g = empty()
        run(g, 60 * 20, {0: {"move": [1, 0]}})
        self.assertLessEqual(math.hypot(g.player["pos"][0], g.player["pos"][2]), 40.0 + 1e-9)


class TestPickupDeposit(unittest.TestCase):
    def test_pickup_radius(self):  # AC3
        r = T["pickup_radius"]
        g = empty(motes=[[r, 0, 0], [r + 0.01, 0, 0]])
        ev = run(g, 1)
        self.assertEqual(names(ev), ["mote_picked"])
        self.assertEqual(ev[0][0], 1)  # event at tick k+1
        self.assertEqual(g.player["carried"], 1)
        self.assertEqual(g.score, T["score"]["per_mote"])

    def test_pickup_capacity(self):  # AC3
        cap = T["carry_capacity"]
        g = empty(player={"carried": cap - 1}, motes=[[0, 0, 0.1], [0, 0, 0.2]])
        run(g, 1)
        self.assertEqual(g.player["carried"], cap)
        self.assertEqual(len(g.motes), 1)

    def test_deposit_and_lit(self):  # AC4
        cost = T["lantern_cost"]
        g = empty(player={"carried": cost + 2}, lanterns=[{"id": "L1", "pos": [0, 0, 2]}])
        ev = run(g, 2, {0: {"interact": True}})
        self.assertEqual(names(ev), ["deposit", "lantern_lit"])
        self.assertEqual(ev[0][2], {"lantern_id": "L1", "amount": cost, "deposited": cost})
        self.assertEqual(g.player["carried"], 2)
        self.assertEqual(g.score, T["score"]["per_lantern"])

    def test_partial_deposit_and_edge(self):  # AC4: only false->true triggers
        g = empty(player={"carried": 2}, lanterns=[{"id": "L1", "pos": [0, 0, 2]}])
        ev = run(g, 5, {0: {"interact": True}})  # held, only one deposit
        self.assertEqual(names(ev), ["deposit"])
        self.assertEqual(g.lanterns[0]["deposited"], 2)
        self.assertFalse(g.lanterns[0]["lit"])

    def test_interact_out_of_range(self):
        g = empty(player={"carried": 5}, lanterns=[{"id": "L1", "pos": [0, 0, T["interact_radius"] + 0.1]}])
        self.assertEqual(run(g, 2, {0: {"interact": True}}), [])


class TestShades(unittest.TestCase):
    def test_shade_chase(self):  # AC5
        g = empty(shades=[{"id": "A", "pos": [10, 0, 0]}])
        run(g, 60)
        self.assertAlmostEqual(g.shades[0]["pos"][0], 10 - T["shade_speed"], places=6)
        self.assertEqual(g.snapshot()["shades"][0]["state"], "chase")

    def test_safe_radius(self):  # AC5
        g = empty(player={"pos": [0, 0, 25]}, lanterns=[{"id": "L1", "lit": True}],
                  shades=[{"id": "A", "pos": [0, 0, 10]}])
        run(g, 600)
        L = g.lanterns[0]["pos"]
        self.assertGreaterEqual(math.hypot(g.shades[0]["pos"][0] - L[0], g.shades[0]["pos"][2] - L[2]),
                                T["safe_radius"] - 1e-9)
        self.assertEqual(g.player["flames"], T["flames"])

    def test_hit(self):  # AC6
        g = empty(player={"carried": 5}, shades=[{"id": "A", "pos": [0.5, 0, 0]}])
        ev = run(g, 1)
        self.assertEqual(names(ev), ["player_hit"])
        dropped = math.floor(5 * T["hit_drop_ratio"])
        self.assertEqual(ev[0][2], {"by": "shade", "flames": T["flames"] - 1, "dropped": dropped})
        self.assertEqual(g.player["carried"], 5 - dropped)

    def test_invuln(self):  # AC6: next hit exactly invuln_s later
        g = empty(shades=[{"id": "A", "pos": [0.5, 0, 0]}])
        ev = run(g, 300)
        hits = [e[0] for e in ev if e[1] == "player_hit"]
        self.assertEqual(hits[1] - hits[0], int(T["invuln_s"] * 60))

    def test_lose_no_flames(self):  # AC8
        g = empty(player={"flames": 1}, shades=[{"id": "A", "pos": [0.5, 0, 0]}])
        ev = run(g, 5)
        self.assertEqual(names(ev), ["player_hit", "game_over"])
        self.assertEqual(ev[-1][2], {"result": "lost", "reason": "no_flames"})
        self.assertEqual(g.state, "lost")


class TestPulse(unittest.TestCase):
    def test_pulse_stun_push(self):  # AC7
        g = empty(player={"carried": 3}, shades=[{"id": "A", "pos": [4, 0, 0]}, {"id": "B", "pos": [20, 0, 0]}])
        ev = run(g, 1, {0: {"pulse": True}})
        self.assertEqual(ev[0][1], "pulse")
        self.assertEqual(ev[0][2], {"stunned_ids": ["A"]})
        self.assertEqual(g.player["carried"], 3 - T["pulse_cost"])
        self.assertAlmostEqual(g.shades[0]["pos"][0], 4 + T["pulse_push_m"], places=6)
        self.assertEqual(g.score, T["score"]["per_stun"])
        # pulse at tick p=1 -> stunned at ticks 1..n, chasing from tick n+1
        n = int(T["pulse_stun_s"] * 60)
        run(g, n - 1)
        self.assertEqual(g.tick, n)
        self.assertEqual(g.snapshot()["shades"][0]["state"], "stunned")
        x = g.shades[0]["pos"][0]
        run(g, 1)
        self.assertEqual(g.snapshot()["shades"][0]["state"], "chase")
        self.assertLess(g.shades[0]["pos"][0], x)

    def test_pulse_needs_light(self):  # A1
        g = empty(player={"carried": 0}, shades=[{"id": "A", "pos": [4, 0, 0]}])
        self.assertEqual(run(g, 1, {0: {"pulse": True}}), [])

    def test_pulse_cooldown(self):  # AC7
        cd = int(T["pulse_cooldown_s"] * 60)
        g = empty(player={"carried": 5})
        frames = {0: {"pulse": True}, 1: {"pulse": False}, cd - 1: {"pulse": True}, cd: {"pulse": False},
                  cd + 1: {"pulse": True}}
        ev = run(g, cd + 3, frames)
        self.assertEqual([e[0] for e in ev if e[1] == "pulse"], [1, cd + 2])


class TestEnd(unittest.TestCase):
    def test_win(self):  # AC8
        lit = [{"id": f"L{i}", "lit": True} for i in (2, 3, 4, 5)]
        g = empty(player={"carried": 5}, lanterns=[{"id": "L1", "pos": [0, 0, 1]}] + lit, time_left_s=100)
        ev = run(g, 3, {0: {"interact": True}})
        self.assertEqual(names(ev), ["deposit", "lantern_lit", "game_over"])
        self.assertEqual(ev[-1][2], {"result": "won", "reason": "all_lit"})
        sc = T["score"]
        expected = sc["per_lantern"] + sc["per_second_left"] * 99 + sc["per_flame_left"] * T["flames"]
        self.assertEqual(g.score, expected)  # time_left 100 - 1/60 -> floor 99

    def test_lose_dawn(self):  # AC8
        g = empty(time_left_s=1)
        ev = run(g, 100)
        self.assertEqual(ev[-1], (60, "game_over", {"result": "lost", "reason": "dawn"}))

    def test_determinism(self):  # AC9
        def trace(seed):
            g = Game(seed=seed)
            out = []
            for k in range(3000):
                out.append((g.step({"move": [math.sin(k / 50), 1]} if k % 100 == 0 else None), g.snapshot()))
            return out
        self.assertEqual(trace(42), trace(42))
        self.assertNotEqual(Game(seed=1).snapshot()["motes"], Game(seed=2).snapshot()["motes"])


class TestInputsValidation(unittest.TestCase):
    def test_strictly_increasing(self):
        with self.assertRaises(ScenarioError):
            validate_inputs({"frames": [{"tick": 5}, {"tick": 5}]})

    def test_bad_types(self):
        for bad in ({"frames": [{"tick": 0, "move": [2, 0]}]}, {"frames": [{"tick": 0, "jump": 1}]},
                    {"frames": "x"}, [], {"frames": [{"move": [0, 0]}]}):
            with self.assertRaises(ScenarioError):
                validate_inputs(bad)


if __name__ == "__main__":
    unittest.main()
