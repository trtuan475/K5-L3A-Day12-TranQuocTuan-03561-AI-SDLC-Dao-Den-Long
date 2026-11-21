"""Deterministic game core for Dao Den Long (Lantern Island).

Pure stdlib, no rendering. Used by both headless.py (Test Contract) and play.py (Ursina).
All timers are integer ticks (60 ticks = 1 s). See docs/notes/phase-1-spec.md for assumptions.
"""
import json
import math
import os
import random

TPS = 60
DT = 1.0 / TPS

_CONTRACT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def load_tuning():
    """Tuning comes from game.contract.json so the declared numbers ARE the game numbers."""
    with open(_CONTRACT, encoding="utf-8") as f:
        return json.load(f)["tuning"]


# Non-contract constants (game defaults, documented in spec A8)
ISLAND_RADIUS = 40.0
LANTERN_RING = 25.0
GRAVITY = 20.0
JUMP_SPEED = 7.0
SHADE_Y = 1.0
INITIAL_MOTES = 30
MOTE_RESPAWN_S = 5
INITIAL_SHADES = 2
SHADE_SPAWN_EVERY_S = 30
MAX_SHADES = 6


class ScenarioError(ValueError):
    """Malformed scenario/inputs -> exit code 2."""


def r3(x):
    v = round(x, 3)
    return 0.0 if v == 0 else v


def dist_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def default_lantern_positions(n=5):
    out = []
    for k in range(n):
        a = math.radians(72.0 * k)
        out.append([r3(LANTERN_RING * math.sin(a)), 0.0, r3(LANTERN_RING * math.cos(a))])
    return out


class Inputs:
    """Holds current input state; tracks false->true edges for buttons."""
    BUTTONS = ("jump", "interact", "pulse", "dash")

    def __init__(self):
        self.move = [0.0, 0.0]
        self.cam_yaw_deg = 0.0
        self.buttons = {b: False for b in self.BUTTONS}

    def apply(self, frame):
        """Apply a frame dict; return set of buttons that went false->true."""
        edges = set()
        if "move" in frame:
            self.move = [float(frame["move"][0]), float(frame["move"][1])]
        if "cam_yaw_deg" in frame:
            self.cam_yaw_deg = float(frame["cam_yaw_deg"])
        for b in self.BUTTONS:
            if b in frame:
                v = bool(frame[b])
                if v and not self.buttons[b]:
                    edges.add(b)
                self.buttons[b] = v
        return edges


def validate_inputs(data):
    if not isinstance(data, dict) or not isinstance(data.get("frames"), list):
        raise ScenarioError("inputs: expected object with 'frames' array")
    last = -1
    for i, fr in enumerate(data["frames"]):
        if not isinstance(fr, dict):
            raise ScenarioError(f"inputs: frame {i} is not an object")
        t = fr.get("tick")
        if not isinstance(t, int) or isinstance(t, bool) or t < 0:
            raise ScenarioError(f"inputs: frame {i} has invalid tick")
        if t <= last:
            raise ScenarioError(f"inputs: frame ticks must strictly increase (frame {i})")
        last = t
        if "move" in fr:
            m = fr["move"]
            if (not isinstance(m, list) or len(m) != 2
                    or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in m)
                    or not all(-1.0 <= v <= 1.0 for v in m)):
                raise ScenarioError(f"inputs: frame {i} has invalid move")
        if "cam_yaw_deg" in fr and (not isinstance(fr["cam_yaw_deg"], (int, float)) or isinstance(fr["cam_yaw_deg"], bool)):
            raise ScenarioError(f"inputs: frame {i} has invalid cam_yaw_deg")
        for b in Inputs.BUTTONS:
            if b in fr and not isinstance(fr[b], bool):
                raise ScenarioError(f"inputs: frame {i} has non-boolean '{b}'")
    return {fr["tick"]: fr for fr in data["frames"]}


def _vec3(v, what):
    if (not isinstance(v, list) or len(v) != 3
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)):
        raise ScenarioError(f"scenario: {what} must be [x, y, z]")
    return [float(x) for x in v]


class Game:
    def __init__(self, seed=0, night=1, scenario=None, tuning=None):
        if night != 1:
            raise ScenarioError(f"night {night} not available (Phase 1 has night 1 only)")
        self.t = tuning or load_tuning()
        self.rng = random.Random(seed)
        self.tick = 0
        self.state = "playing"
        self.result_reason = None
        self.score = 0
        self.events = []  # events emitted during the last step: (tick, name, data)
        t = self.t
        self.time_left_ticks = int(round(t["night1_duration_s"] * TPS))
        self.player = {"pos": [0.0, 0.0, 0.0], "vy": 0.0, "flames": int(t["flames"]), "carried": 0}
        self.invuln_ticks = 0
        self.pulse_cd_ticks = 0
        self.lanterns = [{"id": f"L{i + 1}", "pos": p, "lit": False, "deposited": 0}
                         for i, p in enumerate(default_lantern_positions(int(t["lantern_count_night1"])))]
        self.motes = []
        self.mote_seq = 0
        self.mote_respawns = []  # list of ticks at which a mote respawns
        self.shades = []
        self.shade_seq = 0
        self.random_motes = True
        self.random_shades = True
        self.shade_spawn_timer = SHADE_SPAWN_EVERY_S * TPS
        self.inputs = Inputs()
        self.stats = {"motes": 0, "stuns": 0, "hits": 0}

        if scenario is not None:
            self._apply_scenario(scenario)
        if self.random_motes and not (scenario and "motes" in scenario):
            for _ in range(INITIAL_MOTES):
                self._add_mote(self._random_ground_point(3.0, ISLAND_RADIUS - 2.0))
        if self.random_shades and not (scenario and "shades" in scenario):
            for _ in range(INITIAL_SHADES):
                self._add_shade(self._random_edge_point())

    # ---------- setup helpers ----------
    def _random_ground_point(self, rmin, rmax):
        a = self.rng.uniform(0, 2 * math.pi)
        r = math.sqrt(self.rng.uniform(rmin * rmin, rmax * rmax))
        return [r3(r * math.sin(a)), 0.0, r3(r * math.cos(a))]

    def _random_edge_point(self):
        a = self.rng.uniform(0, 2 * math.pi)
        r = ISLAND_RADIUS - 2.0
        return [r3(r * math.sin(a)), SHADE_Y, r3(r * math.cos(a))]

    def _add_mote(self, pos, mid=None):
        self.mote_seq += 1
        self.motes.append({"id": mid or f"M{self.mote_seq}", "pos": [pos[0], 0.0, pos[2]]})

    def _add_shade(self, pos, sid=None):
        self.shade_seq += 1
        s = {"id": sid or f"S{self.shade_seq}", "pos": [pos[0], SHADE_Y if pos[1] == 0 else pos[1], pos[2]],
             "state": "chase", "stun_ticks": 0}
        self.shades.append(s)
        return s

    def _apply_scenario(self, sc):
        if not isinstance(sc, dict):
            raise ScenarioError("scenario: expected JSON object")
        p = sc.get("player", {})
        if not isinstance(p, dict):
            raise ScenarioError("scenario: player must be object")
        if "pos" in p:
            self.player["pos"] = _vec3(p["pos"], "player.pos")
        for k in ("carried", "flames"):
            if k in p:
                if not isinstance(p[k], int) or isinstance(p[k], bool) or p[k] < 0:
                    raise ScenarioError(f"scenario: player.{k} must be a non-negative int")
                self.player[k] = p[k]
        for k in ("random_motes", "random_shades"):
            if k in sc:
                if not isinstance(sc[k], bool):
                    raise ScenarioError(f"scenario: {k} must be boolean")
                setattr(self, k, sc[k])
        if "motes" in sc:
            if not isinstance(sc["motes"], list):
                raise ScenarioError("scenario: motes must be array")
            self.motes = []
            for m in sc["motes"]:
                if isinstance(m, dict):
                    self._add_mote(_vec3(m.get("pos"), "mote.pos"), m.get("id"))
                else:
                    self._add_mote(_vec3(m, "mote"))
        if "shades" in sc:
            if not isinstance(sc["shades"], list):
                raise ScenarioError("scenario: shades must be array")
            self.shades = []
            for s in sc["shades"]:
                if not isinstance(s, dict):
                    raise ScenarioError("scenario: shade must be object")
                pos = _vec3(s.get("pos"), "shade.pos")
                self._add_shade(pos, s.get("id"))
        if "lanterns" in sc:
            if not isinstance(sc["lanterns"], list):
                raise ScenarioError("scenario: lanterns must be array")
            by_id = {L["id"]: L for L in self.lanterns}
            for l in sc["lanterns"]:
                if not isinstance(l, dict) or l.get("id") not in by_id:
                    raise ScenarioError(f"scenario: unknown lantern {l!r}")
                L = by_id[l["id"]]
                if "pos" in l:
                    L["pos"] = _vec3(l["pos"], "lantern.pos")
                if "deposited" in l:
                    if not isinstance(l["deposited"], int) or isinstance(l["deposited"], bool):
                        raise ScenarioError("scenario: lantern.deposited must be int")
                    L["deposited"] = l["deposited"]
                if "lit" in l:
                    if not isinstance(l["lit"], bool):
                        raise ScenarioError("scenario: lantern.lit must be boolean")
                    L["lit"] = l["lit"]
                    if l["lit"] and "deposited" not in l:
                        L["deposited"] = int(self.t["lantern_cost"])
        if "time_left_s" in sc:
            v = sc["time_left_s"]
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                raise ScenarioError("scenario: time_left_s must be a non-negative number")
            self.time_left_ticks = int(round(v * TPS))

    # ---------- step ----------
    def _emit(self, name, data):
        self.events.append((self.tick, name, data))

    def _end(self, result, reason):
        self.state = result
        self.result_reason = reason
        self._emit("game_over", {"result": result, "reason": reason})

    def step(self, frame=None):
        """Advance one tick. frame: optional input frame dict (contract C format)."""
        self.events = []
        if self.state != "playing":
            return self.events
        edges = self.inputs.apply(frame) if frame else set()
        self.tick += 1
        # contract: time_left_s = duration - steps_run / 60 (also on the step that ends the game)
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        t = self.t
        P = self.player

        # 1. movement
        mx, mz = self.inputs.move
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(self.inputs.cam_yaw_deg)
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        step = t["player_speed"] * DT
        P["pos"][0] += wx * step
        P["pos"][2] += wz * step
        d = math.hypot(P["pos"][0], P["pos"][2])
        if d > ISLAND_RADIUS:  # invisible fence (fall_enabled = false)
            P["pos"][0] *= ISLAND_RADIUS / d
            P["pos"][2] *= ISLAND_RADIUS / d
        if "jump" in edges and P["pos"][1] <= 0.0:
            P["vy"] = JUMP_SPEED
        if P["pos"][1] > 0.0 or P["vy"] > 0.0:
            P["vy"] -= GRAVITY * DT
            P["pos"][1] += P["vy"] * DT
            if P["pos"][1] <= 0.0:
                P["pos"][1] = 0.0
                P["vy"] = 0.0

        # 2. pickups (list order = deterministic)
        cap = int(t["carry_capacity"])
        kept = []
        for m in self.motes:
            if P["carried"] < cap and dist_xz(P["pos"], m["pos"]) <= t["pickup_radius"]:
                P["carried"] += 1
                self.score += t["score"]["per_mote"]
                self.stats["motes"] += 1
                self._emit("mote_picked", {"carried": P["carried"]})
                if self.random_motes:
                    self.mote_respawns.append(self.tick + MOTE_RESPAWN_S * TPS)
            else:
                kept.append(m)
        self.motes = kept

        # 3. interact / deposit
        if "interact" in edges and P["carried"] > 0:
            cands = [(dist_xz(P["pos"], L["pos"]), i, L) for i, L in enumerate(self.lanterns)
                     if not L["lit"] and dist_xz(P["pos"], L["pos"]) <= t["interact_radius"]]
            if cands:
                L = min(cands, key=lambda c: (c[0], c[1]))[2]
                need = max(0, int(t["lantern_cost"]) - L["deposited"])
                amt = min(P["carried"], need)
                if amt > 0:
                    P["carried"] -= amt
                    L["deposited"] += amt
                    self._emit("deposit", {"lantern_id": L["id"], "amount": amt, "deposited": L["deposited"]})
                if L["deposited"] >= t["lantern_cost"]:
                    L["lit"] = True
                    self.score += t["score"]["per_lantern"]
                    self._emit("lantern_lit", {"lantern_id": L["id"]})
                    for s in self.shades:
                        self._keep_out_of_safe(s)
                    if all(x["lit"] for x in self.lanterns):
                        secs = self.time_left_ticks // TPS
                        self.score += t["score"]["per_second_left"] * secs + t["score"]["per_flame_left"] * P["flames"]
                        self._end("won", "all_lit")
                        return self.events

        # 4. pulse
        stunned_now = set()
        if self.pulse_cd_ticks > 0:
            self.pulse_cd_ticks -= 1
        if "pulse" in edges and self.pulse_cd_ticks == 0 and P["carried"] >= t["pulse_cost"]:
            P["carried"] -= int(t["pulse_cost"])
            self.pulse_cd_ticks = int(round(t["pulse_cooldown_s"] * TPS))
            stunned = []
            for s in self.shades:
                if dist_xz(P["pos"], s["pos"]) <= t["pulse_radius"]:
                    s["state"] = "stunned"
                    s["stun_ticks"] = int(round(t["pulse_stun_s"] * TPS))
                    dx, dz = s["pos"][0] - P["pos"][0], s["pos"][2] - P["pos"][2]
                    dl = math.hypot(dx, dz)
                    if dl < 1e-9:
                        dx, dz, dl = 0.0, 1.0, 1.0
                    s["pos"][0] += dx / dl * t["pulse_push_m"]
                    s["pos"][2] += dz / dl * t["pulse_push_m"]
                    self._keep_out_of_safe(s)
                    stunned.append(s["id"])
                    self.score += t["score"]["per_stun"]
                    self.stats["stuns"] += 1
            stunned_now = set(stunned)
            self._emit("pulse", {"stunned_ids": stunned})

        # 5. shades move + spawn
        # Stun lasts exactly pulse_stun_s: stunned at ticks p..p+N-1, chasing again from p+N.
        sstep = t["shade_speed"] * DT
        for s in self.shades:
            if s["id"] in stunned_now:
                continue
            if s["stun_ticks"] > 0:
                s["stun_ticks"] -= 1
                if s["stun_ticks"] > 0:
                    continue
                s["state"] = "chase"
            dx, dz = P["pos"][0] - s["pos"][0], P["pos"][2] - s["pos"][2]
            dl = math.hypot(dx, dz)
            if dl > 1e-9:
                k = min(sstep, dl) / dl
                s["pos"][0] += dx * k
                s["pos"][2] += dz * k
            self._keep_out_of_safe(s)
        if self.random_shades:
            self.shade_spawn_timer -= 1
            if self.shade_spawn_timer <= 0:
                self.shade_spawn_timer = SHADE_SPAWN_EVERY_S * TPS
                if len(self.shades) < MAX_SHADES:
                    s = self._add_shade(self._random_edge_point())
                    self._keep_out_of_safe(s)
                    self._emit("shade_spawned", {"id": s["id"]})
        if self.random_motes:
            due = [x for x in self.mote_respawns if x <= self.tick]
            self.mote_respawns = [x for x in self.mote_respawns if x > self.tick]
            for _ in due:
                self._add_mote(self._random_ground_point(3.0, ISLAND_RADIUS - 2.0))

        # 6. hits
        if self.invuln_ticks > 0:
            self.invuln_ticks -= 1
        if self.invuln_ticks == 0 and any(s["stun_ticks"] == 0 and dist_xz(P["pos"], s["pos"]) <= t["shade_hit_radius"] for s in self.shades):
            P["flames"] -= 1
            dropped = int(math.floor(P["carried"] * t["hit_drop_ratio"]))
            P["carried"] -= dropped
            self.invuln_ticks = int(round(t["invuln_s"] * TPS))
            self.stats["hits"] += 1
            self._emit("player_hit", {"by": "shade", "flames": P["flames"], "dropped": dropped})
            if P["flames"] <= 0:
                self._end("lost", "no_flames")
                return self.events

        # 7. clock
        if self.time_left_ticks <= 0:
            self._end("lost", "dawn")
        return self.events

    def _keep_out_of_safe(self, s):
        R = self.t["safe_radius"]
        for L in self.lanterns:
            if not L["lit"]:
                continue
            dx, dz = s["pos"][0] - L["pos"][0], s["pos"][2] - L["pos"][2]
            dl = math.hypot(dx, dz)
            if dl < R:
                if dl < 1e-9:
                    dx, dz, dl = 0.0, 1.0, 1.0
                s["pos"][0] = L["pos"][0] + dx / dl * R
                s["pos"][2] = L["pos"][2] + dz / dl * R

    # ---------- output ----------
    @property
    def time_left_s(self):
        return self.time_left_ticks / TPS

    def snapshot(self):
        P = self.player
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.tick, "state": self.state,
            "time_left_s": r3(self.time_left_s), "score": self.score,
            "player": {"pos": [r3(v) for v in P["pos"]], "flames": P["flames"], "carried": P["carried"]},
            "lanterns": [{"id": L["id"], "pos": [r3(v) for v in L["pos"]], "lit": L["lit"],
                          "deposited": L["deposited"]} for L in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(v) for v in s["pos"]], "state": s["state"]} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(v) for v in m["pos"]]} for m in self.motes],
        }
