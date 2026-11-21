"""Unit/scenario tests for the game core, Ticket-02 standard numbers.
Each test names its acceptance criterion (P2-x, docs/notes/phase-2-spec.md). Phase 1 tests that the
ticket changed were rewritten here (marked `Phase 2:`); unchanged behaviour keeps its Phase 1 test.
"""
import math
import unittest

from lantern_island.sim import Game, ScenarioError, load_tuning, validate_inputs

T = load_tuning()


def empty(night=1, **kw):
    sc = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
          "motes": [], "shades": [], "drifters": [], "charms": []}
    sc.update(kw)
    return Game(seed=1, night=night, scenario=sc)


def run(g, n, frames=None):
    frames = frames or {}
    ev = []
    for _ in range(n):
        ev += g.step(frames.get(g.tick))
        if g.over:
            break
    return ev


def names(ev):
    return [e[1] for e in ev]


def tap(tick, button):
    return {tick: {button: True}, tick + 1: {button: False}}


class TestStdMovement(unittest.TestCase):  # P2-1
    def test_initial_state(self):
        for n, count in ((1, 5), (2, 6), (3, 7)):
            s = Game(seed=7, night=n).snapshot()
            self.assertEqual(len(s["lanterns"]), count)
            self.assertEqual(s["motes_active"], 20)
            self.assertEqual(s["night"], n)
            self.assertEqual(s["time_left_s"], {1: 300, 2: 330, 3: 360}[n])
        self.assertEqual(Game(seed=1).snapshot()["player"]["pos"], [0.0, 0.0, 0.0])

    def test_std_speed_and_yaw(self):
        g = empty()
        run(g, 60, {0: {"move": [0, 1]}})
        self.assertAlmostEqual(g.player["pos"][2], 6.0, places=6)
        g = empty()
        run(g, 60, {0: {"move": [1, 1], "cam_yaw_deg": 90}})
        self.assertAlmostEqual(math.hypot(g.player["pos"][0], g.player["pos"][2]), 6.0, places=6)

    def test_std_jump(self):
        g = empty()
        peak = 0
        frames = tap(0, "jump")
        for _ in range(100):
            g.step(frames.get(g.tick))
            peak = max(peak, g.player["pos"][1])
        self.assertAlmostEqual(peak, 7 * 7 / 40, delta=0.07)
        self.assertTrue(g.player["grounded"])
        self.assertEqual(g.player["pos"][1], 0.0)

    def test_dash(self):  # 14 m/s x 12 ticks, facing +Z when idle, cooldown 90 from start
        g = empty()
        ev = run(g, 12, tap(0, "dash"))
        self.assertEqual(names(ev), ["dash"])
        self.assertAlmostEqual(g.player["pos"][2], 14 * 12 / 60, places=6)
        g = empty()
        frames = {**tap(0, "dash"), **tap(60, "dash"), **tap(88, "dash"), **tap(90, "dash")}
        ev = run(g, 95, frames)
        self.assertEqual([e[0] for e in ev if e[1] == "dash"], [1, 91])  # dash at tick 1 -> ready at 1+90

    def test_air_dash_keeps_height(self):
        g = empty()
        frames = {**tap(0, "jump"), **tap(10, "dash")}
        run(g, 11, frames)
        y0 = g.player["pos"][1]
        run(g, 10)
        self.assertAlmostEqual(g.player["pos"][1], y0, places=9)


class TestMotesLanterns(unittest.TestCase):
    def test_mote_pick_height(self):  # P2-2
        g = empty(motes=[[0, 0, 1.0], [0.5, 2.0, 0]])
        run(g, 1)
        self.assertEqual(g.player["carried"], 1)
        self.assertEqual(len(g.motes), 1)

    def test_mote_schedule(self):  # P2-2: +1 at 240, 480..., cap 30
        g = Game(seed=3, scenario={"random_shades": False})
        run(g, 239)
        self.assertEqual(len(g.motes), 20)
        run(g, 1)
        self.assertEqual(len(g.motes), 21)
        run(g, 240 * 20)
        self.assertLessEqual(len(g.motes), 24)  # Night 1 has only 24 spawn points -> skips when full

    def test_deposit_multi_and_score(self):  # P2-3
        g = empty(player={"carried": 6}, lanterns=[{"id": "L1", "pos": [0, 0, 1.5]}, {"id": "L2", "pos": [1.5, 0, 0]}])
        ev = run(g, 2, tap(0, "interact"))  # tie at 1.5 m -> L1 (smaller id)
        self.assertEqual(ev[0][2], {"lantern_id": "L1", "amount": 6, "deposited": 6})
        self.assertEqual(g.score, 60)
        g.player["carried"] = 9
        ev = run(g, 2, tap(g.tick, "interact"))
        self.assertEqual(names(ev), ["deposit", "lantern_lit"])
        self.assertEqual(g.player["carried"], 5)
        self.assertEqual(g.score, 100 + 100)

    def test_interact_radius(self):
        g = empty(player={"carried": 5}, lanterns=[{"id": "L1", "pos": [0, 0, 2.01]}])
        self.assertEqual(run(g, 2, tap(0, "interact")), [])


class TestSafeZone(unittest.TestCase):  # P2-4
    def test_safe_block(self):
        g = empty(player={"pos": [0, 0, 25]}, lanterns=[{"id": "L1", "lit": True}], shades=[{"id": "A", "pos": [0, 0, 15]}])
        run(g, 600)
        self.assertGreaterEqual(math.hypot(g.shades[0]["pos"][0], g.shades[0]["pos"][2] - 25), 6 - 1e-9)
        self.assertEqual(g.player["flames"], 3)

    def test_safe_evict(self):
        g = empty(player={"carried": 10}, lanterns=[{"id": "L1", "pos": [0, 0, 1]}],
                  shades=[{"id": "A", "pos": [0.5, 0, 0]}])
        ev = run(g, 30, tap(0, "interact"))
        self.assertNotIn("player_hit", names(ev))  # shade inside is being pushed: no damage
        self.assertGreaterEqual(math.hypot(g.shades[0]["pos"][0], g.shades[0]["pos"][2] - 1), 6 - 1e-6)


class TestPulse(unittest.TestCase):  # P2-5
    def test_pulse_3d_radius_push_stun(self):
        g = empty(player={"carried": 3}, shades=[{"id": "A", "pos": [0, 0, 4.9]}, {"id": "B", "pos": [5.0, 0, 0]}])
        ev = run(g, 1, tap(0, "pulse"))
        self.assertEqual(ev[0][2], {"stunned_ids": ["A"]})  # B: 3D distance sqrt(25+0.04) > 5
        self.assertEqual(g.player["carried"], 0)
        self.assertEqual(g.score, 5)
        run(g, 14)
        self.assertAlmostEqual(g.shades[0]["pos"][2], 4.9 + 4.0, places=6)
        run(g, 105)  # tick 120: stunned ticks 1..120
        self.assertEqual(g.snapshot()["shades"][0]["state"], "stunned")
        run(g, 1)  # tick 121 -> stun over
        self.assertNotEqual(g.snapshot()["shades"][0]["state"], "stunned")

    def test_pulse_cost_and_cooldown(self):
        g = empty(player={"carried": 2})
        self.assertEqual(run(g, 2, tap(0, "pulse")), [])
        g = empty(player={"carried": 9})
        ev = run(g, 200, {**tap(0, "pulse"), **tap(100, "pulse"), **tap(180, "pulse")})
        self.assertEqual([e[0] for e in ev if e[1] == "pulse"], [1, 181])

    def test_pulse_coincident_pushes_plus_x(self):
        g = empty(player={"carried": 3}, shades=[{"id": "A", "pos": [0, 0, 0], "state": "spawning"}])
        run(g, 15, tap(0, "pulse"))
        self.assertAlmostEqual(g.shades[0]["pos"][0], 4.0, places=6)


class TestShades(unittest.TestCase):  # P2-6
    def test_detect_and_lose(self):
        g = empty(shades=[{"id": "A", "pos": [11.9, 0, 0]}, {"id": "B", "pos": [-13, 0, 0]}])
        run(g, 1)
        self.assertEqual([s["state"] for s in g.snapshot()["shades"]], ["chase", "wander"])
        g = empty(shades=[{"id": "A", "pos": [17.9, 0, 0], "state": "chase"}, {"id": "B", "pos": [18.1, 0, 0], "state": "chase"}])
        run(g, 1)
        self.assertEqual([s["state"] for s in g.snapshot()["shades"]], ["chase", "wander"])

    def test_chase_speed(self):
        g = empty(shades=[{"id": "A", "pos": [11, 0, 0]}])
        run(g, 60)
        self.assertAlmostEqual(g.shades[0]["pos"][0], 7.0, places=6)
        g = empty(night=3, player={"pos": [0, 0, -30]}, shades=[{"id": "A", "pos": [11, 0, -30]}])
        run(g, 60)
        self.assertAlmostEqual(g.shades[0]["pos"][0], 6.5, places=6)

    def test_spawn_schedule(self):
        g = Game(seed=2, scenario={"random_motes": False})
        ev = run(g, 300 + 480 * 2)
        sp = [(e[0], e[2]["id"]) for e in ev if e[1] == "shade_spawned"]
        self.assertEqual(sp, [(300, "S1"), (300, "S2"), (780, "S3"), (1260, "S4")])
        self.assertEqual(g.snapshot()["shades"][3]["state"], "spawning")
        for s in g.shades:
            self.assertIn(s["state"], ("spawning", "wander", "chase", "recoil", "stunned"))

    def test_spawn_max(self):
        for n, mx in ((1, 6), (2, 8), (3, 10)):
            g = Game(seed=1, night=n, scenario={"random_motes": False, "random_drifters": False, "player": {"invuln_ticks": 10 ** 6}})
            run(g, 300 + 480 * 12)
            self.assertEqual(len(g.shades), mx)


class TestHitFall(unittest.TestCase):
    def test_hit(self):  # P2-7
        g = empty(player={"carried": 5}, shades=[{"id": "S2", "pos": [0.5, 0, 0]}, {"id": "S10", "pos": [-0.5, 0, 0]}])
        ev = run(g, 1)
        x_hit = g.shades[0]["pos"][0]  # S2 already moved toward Mây in step 8 of tick 1
        self.assertEqual(names(ev), ["player_hit"])  # max one flame per tick
        self.assertEqual(ev[0][2], {"by": "shade", "flames": 2, "dropped": 2})
        drops = [m for m in g.motes if m["kind"] == "dropped"]
        self.assertEqual(len(drops), 2)
        for m in drops:
            self.assertTrue(1.5 - 1e-9 <= math.hypot(m["pos"][0], m["pos"][2]) <= 2.5 + 1e-9)
        s = g.snapshot()
        self.assertEqual(s["shades"][0]["state"], "recoil")
        self.assertTrue(s["player"]["invuln"])
        self.assertEqual(s["motes"][0]["ttl_s"], 8.0)
        run(g, 60)
        self.assertAlmostEqual(g.shades[0]["pos"][0], x_hit + 2.0, places=6)  # recoil 2 m in 60 ticks

    def test_invuln_90(self):
        g = empty(shades=[{"id": "A", "pos": [0.5, 0, 0]}, {"id": "B", "pos": [-0.5, 0, 0]}])
        ev = run(g, 200)
        hits = [e[0] for e in ev if e[1] == "player_hit"]
        self.assertEqual(hits[1] - hits[0], 90)

    def test_fall_and_respawn(self):  # P2-8
        g = empty(player={"pos": [39.5, 0, 0], "carried": 4})
        ev = run(g, 200, {0: {"move": [1, 0]}})
        hit = [e for e in ev if e[1] == "player_hit"][0]
        self.assertEqual(hit[2], {"by": "fall", "flames": 2, "dropped": 0, "lost": 4})
        g2 = empty(player={"pos": [39.5, 0, 0], "carried": 4})
        run(g2, hit[0], {0: {"move": [1, 0]}})
        g2.inputs.move = [0, 0]
        run(g2, 59)
        self.assertLess(g2.player["pos"][1], -10)
        run(g2, 1)
        self.assertEqual(g2.player["pos"], [0.0, 0.0, 0.0])
        self.assertTrue(g2.snapshot()["player"]["invuln"])

    def test_fall_last_flame_loses(self):
        g = empty(player={"pos": [39.5, 0, 0], "flames": 1})
        ev = run(g, 300, {0: {"move": [1, 0]}})
        self.assertEqual(ev[-1][2], {"result": "lost", "reason": "no_flames"})


class TestEnd(unittest.TestCase):  # P2-9
    def test_win_score(self):
        lit = [{"id": f"L{i}", "lit": True} for i in (2, 3, 4, 5)]
        g = empty(player={"carried": 10}, lanterns=[{"id": "L1", "pos": [0, 0, 1]}] + lit, time_left_s=100)
        ev = run(g, 3, tap(0, "interact"))
        self.assertEqual(names(ev), ["deposit", "lantern_lit", "game_over"])
        self.assertEqual(g.score, 100 + 100 + 99 * 2 + 50 * 3)

    def test_win_on_last_tick(self):
        lit = [{"id": f"L{i}", "lit": True} for i in (2, 3, 4, 5)]
        g = empty(player={"carried": 10}, lanterns=[{"id": "L1", "pos": [0, 0, 1]}] + lit, time_left_s=1 / 60)
        ev = run(g, 3, tap(0, "interact"))
        self.assertEqual(ev[-1][2], {"result": "won", "reason": "all_lit"})

    def test_dawn(self):
        g = empty(time_left_s=1)
        ev = run(g, 100)
        self.assertEqual(ev[-1], (60, "game_over", {"result": "lost", "reason": "dawn"}))


class TestNight2(unittest.TestCase):  # P2-10
    def test_bridge_walk(self):
        g = empty(night=2, player={"pos": [25, 0, 0]})
        run(g, 240, {0: {"move": [1, 0]}})
        self.assertAlmostEqual(g.player["pos"][0], 49.0, places=6)
        self.assertEqual(g.player["pos"][1], 0.0)

    def test_off_bridge_falls(self):
        g = empty(night=2, player={"pos": [35, 0, 1.5]})
        ev = run(g, 200, {0: {"move": [0, 1]}})
        self.assertIn("player_hit", names(ev))

    def test_bounce_pad(self):
        g = empty(night=2, player={"pos": [20, 0, 18]})
        landed = None
        for _ in range(200):
            g.step()
            if g.tick > 1 and g.player["grounded"] and landed is None:
                landed = g.tick
        self.assertAlmostEqual(landed, 84, delta=3)  # ~1.4 s
        self.assertLess(math.hypot(g.player["pos"][0] - 70, g.player["pos"][2]), 28)


class TestNight3(unittest.TestCase):  # P2-11
    def test_cliff_blocks(self):
        g = empty(night=3)
        run(g, 300, {0: {"move": [0, 1]}})
        self.assertAlmostEqual(g.player["pos"][2], -8.0, delta=0.11)
        self.assertEqual(g.player["pos"][1], 0.0)

    def test_ramp_up(self):
        a = math.radians(30)
        g = empty(night=3, player={"pos": [31 * math.cos(a), 0, 31 * math.sin(a)]})
        run(g, 100, {0: {"move": [-math.cos(a), -math.sin(a)]}})  # inward along the ramp
        self.assertAlmostEqual(g.player["pos"][1], 3.0, places=6)
        self.assertAlmostEqual(math.hypot(g.player["pos"][0], g.player["pos"][2]), 21.0, delta=0.01)

    def test_pad_to_tier2_and_tower(self):
        g = empty(night=3, player={"pos": [0, 3, 13]})
        run(g, 120)
        self.assertEqual(g.player["pos"][1], 6.0)
        self.assertLess(math.hypot(g.player["pos"][0], g.player["pos"][2]), 8)
        run(g, 120, {g.tick: {"move": [0, -1]}})  # walk into the tower
        self.assertGreaterEqual(math.hypot(g.player["pos"][0], g.player["pos"][2]), 2.0 - 1e-9)

    def test_wind(self):
        g = empty(night=3, wind_enabled=True)
        run(g, 1799)
        self.assertFalse(g.snapshot()["wind"]["active"])
        p0 = list(g.player["pos"])
        run(g, 1)
        s = g.snapshot()
        self.assertTrue(s["wind"]["active"])
        run(g, 299)
        moved = math.hypot(g.player["pos"][0] - p0[0], g.player["pos"][2] - p0[2])
        self.assertAlmostEqual(moved, 10.0, delta=0.05)  # 2 m/s for 5 s
        run(g, 1)
        self.assertFalse(g.snapshot()["wind"]["active"])


class TestDrifter(unittest.TestCase):  # P2-12
    def test_chase_steal_flee_removed(self):
        g = empty(night=2, player={"carried": 6}, drifters=[{"id": "D1", "pos": [10, 0, 0]}])
        ev = run(g, 400)
        st = [e for e in ev if e[1] == "drifter_steal"]
        self.assertEqual(st[0][2], {"drifter_id": "D1", "amount": 3, "carried": 3})
        self.assertEqual(g.player["flames"], 3)
        self.assertEqual(g.snapshot()["drifters"][0]["state"], "removed")
        self.assertEqual(g.snapshot()["drifters"][0]["stolen"], 3)

    def test_idle_when_poor(self):
        g = empty(night=2, player={"carried": 4}, drifters=[{"id": "D1", "pos": [10, 0, 0]}])
        run(g, 1)
        self.assertEqual(g.snapshot()["drifters"][0]["state"], "idle")

    def test_pulse_chase_flees_without_steal(self):
        g = empty(night=2, player={"carried": 8}, drifters=[{"id": "D1", "pos": [4, 0, 0], "state": "chase"}])
        ev = run(g, 300, tap(0, "pulse"))
        self.assertNotIn("drifter_steal", names(ev))
        self.assertEqual(g.player["carried"], 5)

    def test_pulse_flee_drops(self):
        g = empty(night=2, player={"carried": 3}, drifters=[{"id": "D1", "pos": [3, 0, 0], "state": "flee", "stolen": 3}])
        ev = run(g, 1, tap(0, "pulse"))
        self.assertIn(("drifter_drop", {"drifter_id": "D1", "amount": 3}), [(e[1], e[2]) for e in ev])
        self.assertEqual(sum(m["kind"] == "dropped" for m in g.motes), 3)
        run(g, 120)
        self.assertEqual(g.snapshot()["drifters"][0]["state"], "removed")

    def test_drifter_schedule(self):
        g = Game(seed=4, night=2, scenario={"random_shades": False, "random_motes": False, "motes": []})
        run(g, 1200)
        self.assertEqual([d["id"] for d in g.drifters], ["D1"])
        self.assertEqual(Game(seed=1, night=1).map["drifters"], False)


class TestCharm(unittest.TestCase):  # P2-13
    def test_charm(self):
        g = empty(night=2, charms=[{"id": "C1", "pos": [0, 0, 0.5]}])
        ev = run(g, 1)
        self.assertEqual(ev[0][1:], ("charm_picked", {"charm_id": "C1", "charm_ticks": 600}))
        p = g.player["pos"][2]
        run(g, 60, {g.tick: {"move": [1, 0]}})
        self.assertAlmostEqual(g.player["pos"][0], 7.2, places=6)
        ev = run(g, 30, {**tap(g.tick, "dash"), **tap(g.tick + 13, "dash"), g.tick + 15: {"move": [0, 0]}})
        self.assertEqual(names(ev).count("dash"), 2)  # no cooldown
        self.assertEqual(g.snapshot()["charms"][0]["available"], False)
        run(g, 2700)
        self.assertEqual(g.snapshot()["charms"][0]["available"], True)
        self.assertEqual(p, 0.5 * 0 + p)

    def test_default_charm_positions(self):
        self.assertEqual([c["pos"] for c in Game(seed=1, night=2).charms], [[35.0, 0.0, 0.0]])
        self.assertEqual(len(Game(seed=1, night=3).charms), 2)
        self.assertEqual(Game(seed=1, night=1).charms, [])


class TestPause(unittest.TestCase):  # P2-14
    def test_pause(self):
        g = Game(seed=1)
        ev = run(g, 100, {**tap(10, "pause"), **tap(70, "pause")})
        self.assertEqual([(e[0], e[1]) for e in ev if e[1] in ("paused", "resumed")], [(11, "paused"), (71, "resumed")])
        self.assertEqual(g.tick, 100)
        self.assertEqual(g.sim_tick, 40)
        self.assertAlmostEqual(g.time_left_s, 300 - 40 / 60)
        g = Game(seed=1)
        run(g, 30, tap(10, "pause"))
        self.assertEqual(g.snapshot()["state"], "paused")


class TestDeterminismAndInputs(unittest.TestCase):
    def test_determinism(self):  # P2-15
        def trace(seed, night):
            g = Game(seed=seed, night=night)
            out = []
            for k in range(4000):
                out.append((g.step({"move": [math.sin(k / 50), 1], "pulse": k % 200 == 0, "dash": k % 90 == 0}), g.snapshot()))
            return out
        for n in (1, 2, 3):
            self.assertEqual(trace(42, n), trace(42, n))
        self.assertNotEqual(Game(seed=1).snapshot()["motes"], Game(seed=2).snapshot()["motes"])

    def test_bad_night(self):
        with self.assertRaises(ScenarioError):
            Game(seed=1, night=4)

    def test_inputs_validation(self):
        for bad in ({"frames": [{"tick": 5}, {"tick": 5}]}, {"frames": [{"tick": 0, "move": [2, 0]}]},
                    {"frames": [{"tick": 0, "dash": 1}]}, {"frames": "x"}, [], {"frames": [{"move": [0, 0]}]}):
            with self.assertRaises(ScenarioError):
                validate_inputs(bad)

    def test_bad_scenario(self):
        with self.assertRaises(ScenarioError):
            Game(seed=1, scenario={"shades": [{"pos": [1, 0, 0], "state": "angry"}]})


if __name__ == "__main__":
    unittest.main()
