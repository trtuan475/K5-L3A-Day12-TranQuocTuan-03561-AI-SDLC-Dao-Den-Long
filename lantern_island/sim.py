"""Deterministic game core for Dao Den Long (Lantern Island). Contract v1.2 / Ticket-03 (ADR 0001).

Pure stdlib, no rendering. Used by both headless.py (Test Contract) and play.py (Ursina).
All timers are integer ticks (60 ticks = 1 s). Step order follows Ticket-02 exactly (see Game.step).
Assumptions: docs/notes/phase-2-spec.md (B1..).
"""
import json
import math
import os
import random

from .maps import NIGHTS

TPS = 60
DT = 1.0 / TPS

_CONTRACT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def load_tuning():
    """Tuning comes from game.contract.json so the declared numbers ARE the game numbers."""
    with open(_CONTRACT, encoding="utf-8") as f:
        return json.load(f)["tuning"]


# Standard numbers from Ticket-02 that are not contract tuning keys
GRAVITY = 20.0
JUMP_SPEED = 7.0
STEP_UP = 0.35            # B3
FALL_Y = -10.0
RESPAWN_WAIT = 60
CHARM_SPEED = 7.2
CHARM_TICKS = 600
CHARM_RESPAWN = 2700
PICK_DY = 1.5
MOTES_START, MOTES_CAP, MOTE_EVERY = 20, 30, 240
DROP_TTL = 480
DROP_RING = (1.5, 2.5)
PULSE_CENTER_DY = 0.8
STUN_TICKS = 120
PUSH_TICKS = 15
SHADE_HOVER = 1.0
SHADE_DETECT, SHADE_LOSE = 12.0, 18.0
SHADE_FIRST, SHADE_FIRST_COUNT = 300, 2
SHADE_SPAWN_MIN_DIST = 15.0
SPAWNING_TICKS = 60       # B4
WANDER_SPEED = 2.0        # B4
RECOIL_M, RECOIL_TICKS = 2.0, 60
HIT_DY = 1.5
EVICT_TICKS = 30
DRIFTER_SPEED, DRIFTER_IDLE_SPEED = 7.0, 2.0
DRIFTER_EVERY, DRIFTER_MAX = 1200, 2
DRIFTER_CHASE_CARRY, DRIFTER_CHASE_DIST = 5, 15.0
DRIFTER_HIT = 1.2
DRIFTER_STEAL = 3
DRIFTER_FLEE, DRIFTER_DROP_VANISH = 240, 120
WIND_EVERY, WIND_TICKS, WIND_SPEED, WIND_WARN = 1800, 300, 2.0, 120
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned", "drain")
# Ticket-03 (ADR 0001): fuel is stored as integer units of 1/60 so "exactly 30" is exact
FUEL_SCALE = 60
DRAIN_RANGE, DRAIN_BREAK = 2.0, 6.0
FUEL_EVENT_EVERY = 60


class ScenarioError(ValueError):
    """Malformed scenario/inputs -> exit code 2."""


def r3(x):
    v = round(x, 3)
    return 0.0 if v == 0 else v


def dist_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def id_key(e):
    """Sort S2 before S10."""
    s = e["id"]
    digits = "".join(c for c in s if c.isdigit())
    return (s.rstrip("0123456789"), int(digits) if digits else 0, s)


def r1(x):
    v = round(x, 1)
    return 0.0 if v == 0 else v


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


class Inputs:
    """Holds current input state; tracks false->true edges for buttons."""
    BUTTONS = ("jump", "interact", "pulse", "dash", "pause")

    def __init__(self):
        self.move = [0.0, 0.0]
        self.cam_yaw_deg = 0.0
        self.buttons = {b: False for b in self.BUTTONS}

    def apply(self, frame):
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
        if not _int(t) or t < 0:
            raise ScenarioError(f"inputs: frame {i} has invalid tick")
        if t <= last:
            raise ScenarioError(f"inputs: frame ticks must strictly increase (frame {i})")
        last = t
        if "move" in fr:
            m = fr["move"]
            if (not isinstance(m, list) or len(m) != 2 or not all(_num(v) for v in m)
                    or not all(-1.0 <= v <= 1.0 for v in m)):
                raise ScenarioError(f"inputs: frame {i} has invalid move")
        if "cam_yaw_deg" in fr and not _num(fr["cam_yaw_deg"]):
            raise ScenarioError(f"inputs: frame {i} has invalid cam_yaw_deg")
        for b in Inputs.BUTTONS:
            if b in fr and not isinstance(fr[b], bool):
                raise ScenarioError(f"inputs: frame {i} has non-boolean '{b}'")
    return {fr["tick"]: fr for fr in data["frames"]}


def _vec3(v, what):
    if not isinstance(v, list) or len(v) != 3 or not all(_num(x) for x in v):
        raise ScenarioError(f"scenario: {what} must be [x, y, z]")
    return [float(x) for x in v]


def _nonneg_int(d, k, what):
    if k in d:
        if not _int(d[k]) or d[k] < 0:
            raise ScenarioError(f"scenario: {what}.{k} must be a non-negative int")
        return d[k]
    return None


class Game:
    def __init__(self, seed=0, night=1, scenario=None, tuning=None, bench=False):
        if night not in NIGHTS:
            raise ScenarioError(f"night {night} not available (1, 2, 3)")
        self.t = tuning or load_tuning()
        self.night = night
        self.map = NIGHTS[night]
        self.rng = random.Random(seed * 1000 + night)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False
        self.over = None  # None | "won" | "lost"
        self.result_reason = None
        self.score = 0
        self.events = []
        self.time_left_ticks = int(round(self.t[f"night{night}_duration_s"] * TPS))
        self.player = {"pos": list(map(float, self.map["start"])), "vel": [0.0, 0.0, 0.0], "grounded": True,
                       "facing": (0.0, 1.0), "flames": int(self.t["flames"]), "carried": 0,
                       "invuln": 0, "dash_cd": 0, "pulse_cd": 0, "charm": 0,
                       "dash_ticks": 0, "dash_dir": (0.0, 1.0), "dash_air": False, "launch": None, "respawn": 0,
                       "successful_lights": 0}
        self.lanterns = [{"id": f"L{i + 1}", "pos": [float(c) for c in p], "lit": False, "deposited": 0,
                          "fuel": 0, "ever_lit": False, "relit_count": 0}
                         for i, p in enumerate(self.map["lanterns"])]
        t = self.t
        self.FUEL_MAX = int(round(t["fuel_max"] * FUEL_SCALE))
        self.FUEL_LOW = int(round(t["low_fuel_threshold"] * FUEL_SCALE))
        self.FUEL_PER_MOTE = int(round(t["fuel_per_mote"] * FUEL_SCALE))
        self.FUEL_DECAY = int(round(t["fuel_decay_per_s"] * FUEL_SCALE / TPS))
        self.FUEL_DRAIN = int(round(t["drain_per_s"] * FUEL_SCALE / TPS))
        self.motes, self.mote_seq = [], 0
        self.shades, self.shade_seq = [], 0
        self.drifters, self.drifter_seq = [], 0
        self.charms = [{"id": f"C{i + 1}", "pos": [float(c) for c in p], "available": True, "respawn": 0}
                       for i, p in enumerate(self.map["charms"])]
        self.random_motes = True
        self.random_shades = True
        self.random_drifters = self.map["drifters"]
        self.wind_enabled = self.map["wind"]
        self.wind_ticks, self.wind_dir = 0, 0.0
        self.inputs = Inputs()
        self.stats = {"motes": 0, "stuns": 0, "hits": 0, "falls": 0, "steals": 0}
        self._newly_safe = []
        # Ticket-04 benchmark scene: no spawning, damage, pickups, fuel decay or end of night (shades still move)
        self.bench = bench

        if scenario is not None:
            self._apply_scenario(scenario)
        if self.random_motes and not (scenario and "motes" in scenario):
            pts = self.rng.sample(range(len(self.map["mote_points"])), MOTES_START)
            for i in sorted(pts):
                self._add_mote(self.map["mote_points"][i], "random", point=i)

    # ---------- geometry ----------
    def ground(self, x, z):
        return self.map["ground"](x, z)

    def ground_or(self, x, z, default):
        h = self.ground(x, z)
        return default if h is None else h

    # ---------- entity helpers ----------
    def _add_mote(self, pos, kind, point=None, ttl=None):
        self.mote_seq += 1
        y = pos[1] if kind == "random" else pos[1]
        m = {"id": f"M{self.mote_seq}", "pos": [float(pos[0]), float(y), float(pos[2])], "kind": kind,
             "ttl": ttl, "point": point, "born": self.sim_tick}
        self.motes.append(m)
        return m

    def _drop_motes(self, n, center):
        gy = self.ground_or(center[0], center[2], max(center[1], 0.0))
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            r = self.rng.uniform(*DROP_RING)
            x, z = center[0] + r * math.cos(a), center[2] + r * math.sin(a)
            self._add_mote([x, self.ground_or(x, z, gy), z], "dropped", ttl=DROP_TTL)

    def _shade_y(self, x, z):
        return self.ground_or(x, z, 0.0) + SHADE_HOVER

    def _add_shade(self, pos, sid=None, state="spawning", ticks=SPAWNING_TICKS):
        self.shade_seq += 1
        s = {"id": sid or f"S{self.shade_seq}", "pos": [pos[0], self._shade_y(pos[0], pos[2]), pos[2]],
             "state": state, "spawn": 0, "stun": 0, "push": 0, "push_dir": (1.0, 0.0), "recoil": 0,
             "recoil_dir": (1.0, 0.0), "evict": 0, "evict_dir": (1.0, 0.0), "evict_step": 0.0, "target": None}
        if state == "spawning":
            s["spawn"] = ticks
        elif state == "stunned":
            s["stun"] = ticks
        elif state == "recoil":
            s["recoil"] = ticks
        self.shades.append(s)
        return s

    def _add_drifter(self, pos, did=None, state="idle", stolen=0):
        self.drifter_seq += 1
        d = {"id": did or f"D{self.drifter_seq}", "pos": [pos[0], self._shade_y(pos[0], pos[2]), pos[2]],
             "state": state, "stolen": stolen, "has_stolen": stolen > 0, "flee": DRIFTER_FLEE if state == "flee" else 0,
             "target": None}
        self.drifters.append(d)
        return d

    def _apply_scenario(self, sc):
        if not isinstance(sc, dict):
            raise ScenarioError("scenario: expected JSON object")
        P = self.player
        p = sc.get("player", {})
        if not isinstance(p, dict):
            raise ScenarioError("scenario: player must be object")
        if "pos" in p:
            P["pos"] = _vec3(p["pos"], "player.pos")
            h = self.ground(P["pos"][0], P["pos"][2])
            P["grounded"] = h is not None and abs(P["pos"][1] - h) < 1e-6
        for k in ("carried", "flames"):
            v = _nonneg_int(p, k, "player")
            if v is not None:
                P[k] = v
        v = _nonneg_int(p, "successful_lights", "player")
        if v is not None:
            P["successful_lights"] = v
        for k, attr in (("invuln_ticks", "invuln"), ("dash_cd_ticks", "dash_cd"), ("pulse_cd_ticks", "pulse_cd"),
                        ("charm_ticks", "charm")):
            v = _nonneg_int(p, k, "player")
            if v is not None:
                P[attr] = v
        for k in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
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
                    kind = m.get("kind", "random")
                    if kind not in ("random", "dropped"):
                        raise ScenarioError("scenario: mote.kind must be random|dropped")
                    ttl = m.get("ttl_ticks", DROP_TTL if kind == "dropped" else None)
                    mm = self._add_mote(_vec3(m.get("pos"), "mote.pos"), kind, ttl=ttl)
                    if "id" in m:
                        mm["id"] = str(m["id"])
                    mm["born"] = -1
                else:
                    self._add_mote(_vec3(m, "mote"), "random")["born"] = -1
        if "shades" in sc:
            if not isinstance(sc["shades"], list):
                raise ScenarioError("scenario: shades must be array")
            self.shades = []
            for s in sc["shades"]:
                if not isinstance(s, dict):
                    raise ScenarioError("scenario: shade must be object")
                st = s.get("state", "wander")
                if st not in SHADE_STATES:
                    raise ScenarioError(f"scenario: bad shade state {st!r}")
                ticks = s.get("state_ticks_left", {"spawning": SPAWNING_TICKS, "stunned": STUN_TICKS,
                                                   "recoil": RECOIL_TICKS}.get(st, 0))
                if not _int(ticks) or ticks < 0:
                    raise ScenarioError("scenario: state_ticks_left must be a non-negative int")
                if st in ("spawning", "stunned", "recoil") and ticks == 0:
                    st = "wander"
                sh = self._add_shade(_vec3(s.get("pos"), "shade.pos"), s.get("id"), st, ticks)
                sh["target_lantern"] = s.get("target_lantern_id")
        if "drifters" in sc:
            if not isinstance(sc["drifters"], list):
                raise ScenarioError("scenario: drifters must be array")
            self.drifters = []
            for d in sc["drifters"]:
                if not isinstance(d, dict):
                    raise ScenarioError("scenario: drifter must be object")
                st = d.get("state", "idle")
                if st not in ("idle", "chase", "flee", "removed"):
                    raise ScenarioError(f"scenario: bad drifter state {st!r}")
                self._add_drifter(_vec3(d.get("pos"), "drifter.pos"), d.get("id"), st, int(d.get("stolen", 0)))
        if "charms" in sc:
            if not isinstance(sc["charms"], list):
                raise ScenarioError("scenario: charms must be array")
            self.charms = []
            for i, c in enumerate(sc["charms"]):
                if not isinstance(c, dict):
                    raise ScenarioError("scenario: charm must be object")
                rs = c.get("respawn_ticks", 0)
                self.charms.append({"id": c.get("id", f"C{i + 1}"), "pos": _vec3(c.get("pos"), "charm.pos"),
                                    "available": bool(c.get("available", True)), "respawn": rs})
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
                    if not _int(l["deposited"]):
                        raise ScenarioError("scenario: lantern.deposited must be int")
                    L["deposited"] = l["deposited"]
                if "ever_lit" in l:
                    if not isinstance(l["ever_lit"], bool):
                        raise ScenarioError("scenario: lantern.ever_lit must be boolean")
                    L["ever_lit"] = l["ever_lit"]
                if "lit" in l:
                    if not isinstance(l["lit"], bool):
                        raise ScenarioError("scenario: lantern.lit must be boolean")
                    L["lit"] = l["lit"]
                    if l["lit"]:  # C4
                        L["fuel"] = self.FUEL_MAX
                        if "ever_lit" not in l:
                            L["ever_lit"] = True
                        if "deposited" not in l:
                            L["deposited"] = self._lantern_cost(L)
                    else:
                        L["fuel"] = 0
                if "fuel" in l:
                    if not _num(l["fuel"]) or l["fuel"] < 0:
                        raise ScenarioError("scenario: lantern.fuel must be a non-negative number")
                    if L["lit"]:
                        L["fuel"] = min(self.FUEL_MAX, int(round(l["fuel"] * FUEL_SCALE)))
        if "time_left_s" in sc:
            v = sc["time_left_s"]
            if not _num(v) or v < 0:
                raise ScenarioError("scenario: time_left_s must be a non-negative number")
            self.time_left_ticks = int(round(v * TPS))

    # ---------- lantern helpers (ADR 0001) ----------
    def _lantern_cost(self, L):
        return int(self.t["relight_cost"]) if L["ever_lit"] else int(self.t["lantern_cost"])

    def _safe(self, L):
        return L["lit"] and L["fuel"] >= self.FUEL_LOW

    def _lantern(self, lid):
        for L in self.lanterns:
            if L["id"] == lid:
                return L
        return None

    @property
    def capacity(self):
        t = self.t
        return min(int(t["capacity_max"]), int(t["carry_capacity"]) + 2 * self.player["successful_lights"])

    # ---------- step ----------
    def _emit(self, name, data):
        self.events.append((self.tick, name, data))

    @property
    def state(self):
        if self.over:
            return self.over
        return "paused" if self.paused else "playing"

    def step(self, frame=None):
        """Advance one tick (Ticket-02 order). frame: optional input frame dict (contract C format)."""
        self.events = []
        if self.over:
            return self.events
        edges = self.inputs.apply(frame) if frame else set()
        self.tick += 1
        # 1. input / pause
        if "pause" in edges:
            self.paused = not self.paused
            self._emit("paused" if self.paused else "resumed", {})
            if self.paused:
                return self.events
        elif self.paused:
            return self.events
        self.sim_tick += 1
        self._newly_safe = []
        self._counters()                       # 2 (+ fuel decay / drain)
        if self.bench:
            self._move_player(edges)
            self._move_shades()
            return self.events
        self._lanterns_out()                   # right after 2
        self._move_player(edges)               # 3
        self._pickups()                        # 4
        self._interact(edges)                  # 5
        self._safe_zones()                     # 6
        self._pulse(edges)                     # 7
        self._move_shades()                    # 8
        self._move_drifters()
        self._collisions()                     # 9
        self._spawns()                         # 10
        self._check_end()                      # 11
        return self.events

    # 2
    def _counters(self):
        P = self.player
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        for k in ("dash_cd", "pulse_cd", "invuln", "charm"):
            if P[k] > 0:
                P[k] -= 1
        for s in self.shades:
            if s["stun"] > 0:
                s["stun"] -= 1
                if s["stun"] == 0:
                    s["state"] = "wander"
                    s["push"] = 0
            if s["spawn"] > 0:
                s["spawn"] -= 1
                if s["spawn"] == 0 and s["state"] == "spawning":
                    s["state"] = "wander"
        kept = []
        for m in self.motes:
            if m["ttl"] is not None:
                m["ttl"] -= 1
                if m["ttl"] <= 0:
                    continue
            kept.append(m)
        self.motes = kept
        for c in self.charms:
            if not c["available"] and c["respawn"] > 0:
                c["respawn"] -= 1
                if c["respawn"] == 0:
                    c["available"] = True
        for L in self.lanterns:
            if not L["lit"] or self.bench:  # bench scene: no fuel decay
                continue
            drainers = [s for s in sorted(self.shades, key=id_key)
                        if s["state"] == "drain" and s.get("target_lantern") == L["id"]]
            L["fuel"] -= self.FUEL_DECAY + self.FUEL_DRAIN * len(drainers)
            for s in drainers:
                s["drain_ticks"] = s.get("drain_ticks", 0) + 1
                if s["drain_ticks"] % FUEL_EVENT_EVERY == 0:
                    self._emit("fuel_drain", {"lantern_id": L["id"], "shade_id": s["id"],
                                              "fuel": r1(max(0, L["fuel"]) / FUEL_SCALE)})
        if self.wind_enabled:
            if self.wind_ticks > 0:
                self.wind_ticks -= 1
            if self.sim_tick % WIND_EVERY == 0:
                self.wind_ticks = WIND_TICKS
                self.wind_dir = float(self.rng.randrange(360))
        if P["respawn"] > 0:
            P["respawn"] -= 1
            if P["respawn"] == 0:
                P.update(pos=list(map(float, self.map["start"])), vel=[0.0, 0.0, 0.0], grounded=True,
                         facing=(0.0, 1.0), invuln=int(round(self.t["invuln_s"] * TPS)), launch=None,
                         dash_ticks=0)

    def _lanterns_out(self):
        for L in self.lanterns:
            if L["lit"] and L["fuel"] <= 0:
                L.update(lit=False, fuel=0, deposited=0, ever_lit=True)
                self._emit("lantern_out", {"lantern_id": L["id"]})

    @property
    def wind_active(self):
        return self.wind_enabled and self.wind_ticks > 0

    @property
    def wind_warning(self):
        return self.wind_enabled and not self.wind_active and self.sim_tick % WIND_EVERY >= WIND_EVERY - WIND_WARN

    # 3
    def _move_player(self, edges):
        P = self.player
        if P["respawn"] > 0:
            return
        t = self.t
        mx, mz = self.inputs.move
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(self.inputs.cam_yaw_deg)
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        moving = math.hypot(wx, wz) > 1e-9
        if moving:
            wl = math.hypot(wx, wz)
            P["facing"] = (wx / wl, wz / wl)
        x, y, z = P["pos"]
        vy = P["vel"][1]
        grounded = P["grounded"]
        # dash
        if "dash" in edges and P["dash_ticks"] == 0 and (P["dash_cd"] == 0 or P["charm"] > 0):
            P["dash_dir"] = P["facing"]
            P["dash_ticks"] = int(round(t["dash_duration_s"] * TPS))
            P["dash_cd"] = 0 if P["charm"] > 0 else int(round(t["dash_cooldown_s"] * TPS))
            P["dash_air"] = not grounded
            self._emit("dash", {})
        if "jump" in edges and grounded:
            vy = JUMP_SPEED
            grounded = False
        if P["dash_ticks"] > 0:
            hx, hz = P["dash_dir"][0] * t["dash_speed"], P["dash_dir"][1] * t["dash_speed"]
            P["dash_ticks"] -= 1
            dashing = True
        elif P["launch"] is not None:
            hx, hz = P["launch"]
            dashing = False
        else:
            sp = CHARM_SPEED if P["charm"] > 0 else t["player_speed"]
            hx, hz = wx * sp, wz * sp
            dashing = False
        if self.wind_active:
            a = math.radians(self.wind_dir)
            hx += math.cos(a) * WIND_SPEED
            hz += math.sin(a) * WIND_SPEED
        # horizontal with walls (B3)
        nx, nz = x + hx * DT, z + hz * DT
        lim = y + (STEP_UP if grounded else 1e-6)
        for cx, cz in ((nx, nz), (nx, z), (x, nz), (x, z)):
            h = self.ground(cx, cz)
            if h is None or h <= lim:
                x, z = cx, cz
                break
        # vertical
        h = self.ground(x, z)
        prev_y = y
        if dashing and P["dash_air"]:
            vy = 0.0
        elif grounded and vy <= 0 and h is not None and abs(y - h) <= STEP_UP:
            y, vy = h, 0.0
        else:
            vy -= GRAVITY * DT
            y += vy * DT
            grounded = False
            if h is not None and vy <= 0 and y <= h and prev_y >= h - 1e-6:
                y, vy, grounded = h, 0.0, True
                P["launch"] = None
        P["pos"] = [x, y, z]
        P["vel"] = [hx, vy, hz]
        P["grounded"] = grounded
        # bounce pads
        if grounded and P["launch"] is None:
            for pad in self.map["pads"]:
                if dist_xz(P["pos"], pad["pos"]) <= 1.0 and abs(y - pad["pos"][1]) < 0.05:
                    P["vel"][1] = pad["vy"]
                    P["launch"] = tuple(pad["h"])
                    P["grounded"] = False
                    break
        # fall off the island
        if P["pos"][1] < FALL_Y:
            lost = P["carried"]
            P["carried"] = 0
            P["flames"] -= 1
            P["vel"] = [0.0, 0.0, 0.0]
            P["launch"] = None
            P["dash_ticks"] = 0
            self.stats["falls"] += 1
            self._emit("player_hit", {"by": "fall", "flames": P["flames"], "dropped": 0, "lost": lost})
            if P["flames"] > 0:
                P["respawn"] = RESPAWN_WAIT

    # 4
    def _can_pick(self, pos):
        P = self.player
        return dist_xz(P["pos"], pos) <= self.t["pickup_radius"] and abs(P["pos"][1] - pos[1]) <= PICK_DY

    def _pickups(self):
        P = self.player
        if P["respawn"] > 0:
            return
        cap = self.capacity
        kept = []
        for m in self.motes:
            if P["carried"] < cap and m["born"] < self.sim_tick and self._can_pick(m["pos"]):
                P["carried"] += 1
                self.stats["motes"] += 1
                self._emit("mote_picked", {"carried": P["carried"]})
            else:
                kept.append(m)
        self.motes = kept
        for c in self.charms:
            if c["available"] and self._can_pick(c["pos"]):
                c["available"] = False
                c["respawn"] = CHARM_RESPAWN
                P["charm"] = CHARM_TICKS
                self._emit("charm_picked", {"charm_id": c["id"], "charm_ticks": CHARM_TICKS})

    # 5
    def _interact(self, edges):
        P, t = self.player, self.t
        if "interact" not in edges or P["respawn"] > 0 or P["carried"] <= 0:
            return
        cands = [L for L in self.lanterns if dist_xz(P["pos"], L["pos"]) <= t["interact_radius"]
                 and (not L["lit"] or L["fuel"] < self.FUEL_MAX)]
        if not cands:
            return
        L = min(cands, key=lambda L: (dist_xz(P["pos"], L["pos"]), id_key(L)))
        sc = t["score"]
        if L["lit"]:  # refuel
            used = min(P["carried"], -(-(self.FUEL_MAX - L["fuel"]) // self.FUEL_PER_MOTE))
            before = L["fuel"]
            L["fuel"] = min(self.FUEL_MAX, L["fuel"] + self.FUEL_PER_MOTE * used)
            P["carried"] -= used
            self.score += sc["per_mote"] * used
            self._emit("refuel", {"lantern_id": L["id"], "amount": used, "fuel": r1(L["fuel"] / FUEL_SCALE)})
            if before < self.FUEL_LOW <= L["fuel"]:
                self._newly_safe.append(L)  # C5
            return
        cost = self._lantern_cost(L)
        amt = min(P["carried"], max(0, cost - L["deposited"]))
        if amt > 0:
            P["carried"] -= amt
            L["deposited"] += amt
            self.score += sc["per_mote"] * amt
            self._emit("deposit", {"lantern_id": L["id"], "amount": amt, "deposited": L["deposited"]})
        if L["deposited"] >= cost:
            relight = L["ever_lit"]
            L.update(lit=True, fuel=self.FUEL_MAX, ever_lit=True)
            if relight:
                L["relit_count"] += 1
                self.score += sc["per_relight"]
            else:
                self.score += sc["per_lantern"]
            P["successful_lights"] += 1
            self._emit("lantern_lit", {"lantern_id": L["id"], "relight": relight})
            self._newly_safe.append(L)

    # 6
    def _safe_zones(self):
        R = self.t["safe_radius"]
        for L in self._newly_safe:
            for s in self.shades:
                d = dist_xz(s["pos"], L["pos"])
                if d < R:
                    dx, dz = s["pos"][0] - L["pos"][0], s["pos"][2] - L["pos"][2]
                    s["evict_dir"] = (dx / d, dz / d) if d > 1e-9 else (1.0, 0.0)
                    s["evict"] = EVICT_TICKS
                    s["evict_step"] = (R - d) / EVICT_TICKS
                    s["evict_lantern"] = L
        for s in self.shades:
            if s["evict"] > 0:
                s["pos"][0] += s["evict_dir"][0] * s["evict_step"]
                s["pos"][2] += s["evict_dir"][1] * s["evict_step"]
                s["evict"] -= 1
                if s["evict"] == 0:
                    self._keep_out(s)
                s["pos"][1] = self._shade_y(s["pos"][0], s["pos"][2])

    def _keep_out(self, s):
        """Project a shade out of lit safe zones and the bell tower. Returns True if it was blocked."""
        R = self.t["safe_radius"]
        blocked = False
        for L in self.lanterns:
            if not self._safe(L):
                continue
            dx, dz = s["pos"][0] - L["pos"][0], s["pos"][2] - L["pos"][2]
            d = math.hypot(dx, dz)
            if d < R - 1e-9:
                if d < 1e-9:
                    dx, dz, d = 1.0, 0.0, 1.0
                s["pos"][0] = L["pos"][0] + dx / d * R
                s["pos"][2] = L["pos"][2] + dz / d * R
                blocked = True
        if self.night == 3:
            d = math.hypot(s["pos"][0], s["pos"][2])
            if d < 2.0:
                k = 2.0 / d if d > 1e-9 else 1.0
                s["pos"][0] = s["pos"][0] * k if d > 1e-9 else 2.0
                s["pos"][2] = s["pos"][2] * k if d > 1e-9 else 0.0
                blocked = True
        return blocked

    # 7
    def _pulse(self, edges):
        P, t = self.player, self.t
        if ("pulse" not in edges or P["respawn"] > 0 or P["pulse_cd"] > 0
                or P["carried"] < t["pulse_cost"]):
            return
        P["carried"] -= int(t["pulse_cost"])
        P["pulse_cd"] = int(round(t["pulse_cooldown_s"] * TPS))
        c = (P["pos"][0], P["pos"][1] + PULSE_CENTER_DY, P["pos"][2])
        hit = []
        for s in sorted(self.shades, key=id_key):
            if math.dist(c, s["pos"]) <= t["pulse_radius"]:
                dx, dz = s["pos"][0] - P["pos"][0], s["pos"][2] - P["pos"][2]
                d = math.hypot(dx, dz)
                s["push_dir"] = (dx / d, dz / d) if d > 1e-9 else (1.0, 0.0)
                self.score += t["score"]["per_stun_drain"] if s["state"] == "drain" else t["score"]["per_stun"]
                s["state"] = "stunned"
                s["stun"] = int(round(t["pulse_stun_s"] * TPS))
                s["push"] = PUSH_TICKS
                s["recoil"] = 0
                s["spawn"] = 0
                hit.append(s["id"])
                self.stats["stuns"] += 1
        for d in sorted(self.drifters, key=id_key):
            if d["state"] in ("idle", "removed") or math.dist(c, d["pos"]) > t["pulse_radius"]:
                continue
            if d["state"] == "chase":
                d["state"], d["flee"] = "flee", DRIFTER_FLEE
            elif d["state"] == "flee" and d["stolen"] > 0:
                amt = d["stolen"]
                d["stolen"] = 0
                for _ in range(amt):
                    self._add_mote([d["pos"][0], self.ground_or(d["pos"][0], d["pos"][2], 0.0), d["pos"][2]],
                                   "dropped", ttl=DROP_TTL)
                d["flee"] = DRIFTER_DROP_VANISH
                self._emit("drifter_drop", {"drifter_id": d["id"], "amount": amt})
        self._emit("pulse", {"stunned_ids": hit})

    # 8
    def _player_visible(self):
        return self.player["respawn"] == 0

    def _wander_target(self, e):
        if e["target"] is None or dist_xz(e["pos"], e["target"]) < 0.5:
            e["target"] = self.rng.choice(self.map["mote_points"])
        return e["target"]

    def _step_toward(self, e, tx, tz, speed, away=False):
        dx, dz = tx - e["pos"][0], tz - e["pos"][2]
        d = math.hypot(dx, dz)
        if d < 1e-9:
            if not away:
                return
            dx, dz, d = 1.0, 0.0, 1.0
        k = speed * DT
        if away:
            e["pos"][0] -= dx / d * k
            e["pos"][2] -= dz / d * k
        else:
            k = min(k, d)
            e["pos"][0] += dx / d * k
            e["pos"][2] += dz / d * k

    def _move_shades(self):
        P = self.player
        for s in sorted(self.shades, key=id_key):
            if s["evict"] > 0:
                continue
            if s["state"] == "stunned":
                if s["push"] > 0:
                    step = self.t["pulse_push_m"] / PUSH_TICKS
                    s["pos"][0] += s["push_dir"][0] * step
                    s["pos"][2] += s["push_dir"][1] * step
                    s["push"] -= 1
                    if self._keep_out(s):
                        s["push"] = 0
            elif s["state"] == "spawning":
                pass
            elif s["state"] == "recoil":
                step = RECOIL_M / RECOIL_TICKS
                s["pos"][0] += s["recoil_dir"][0] * step
                s["pos"][2] += s["recoil_dir"][1] * step
                self._keep_out(s)
                s["recoil"] -= 1
                if s["recoil"] <= 0:
                    s["state"] = "wander"
            else:
                d = dist_xz(s["pos"], P["pos"])
                vis = self._player_visible()
                if s["state"] == "drain":
                    L = self._lantern(s.get("target_lantern"))
                    if vis and d <= DRAIN_BREAK:
                        s["state"] = "chase"
                    elif (L is None or not L["lit"] or L["fuel"] >= self.FUEL_LOW
                          or dist_xz(s["pos"], L["pos"]) > DRAIN_RANGE):
                        s["state"], s["target_lantern"] = "wander", None
                    else:
                        s["pos"][1] = self._shade_y(s["pos"][0], s["pos"][2])
                        continue  # stands still while draining (fuel is taken in step 2)
                if s["state"] == "wander" and vis and d <= SHADE_DETECT:
                    s["state"] = "chase"
                elif s["state"] == "chase" and (not vis or d > SHADE_LOSE):
                    s["state"] = "wander"
                    s["target"] = None
                if s["state"] == "chase":
                    self._step_toward(s, P["pos"][0], P["pos"][2], self.map["shade_speed"])
                else:
                    self._wander(s)
                self._keep_out(s)
            s["pos"][1] = self._shade_y(s["pos"][0], s["pos"][2])

    def _wander(self, s):
        """Weak lantern (lit, fuel < 30) first, else nearest unlit lantern (C1), else a random point."""
        key = lambda L: (dist_xz(s["pos"], L["pos"]), id_key(L))  # noqa: E731
        weak = [L for L in self.lanterns if L["lit"] and L["fuel"] < self.FUEL_LOW]
        if weak:
            L = min(weak, key=key)
            s["target_lantern"] = L["id"]
            self._step_toward(s, L["pos"][0], L["pos"][2], WANDER_SPEED)
            if dist_xz(s["pos"], L["pos"]) <= DRAIN_RANGE:
                s["state"], s["drain_ticks"] = "drain", 0
            return
        s["target_lantern"] = None
        dark = [L for L in self.lanterns if not L["lit"]]
        if dark:
            L = min(dark, key=key)
            self._step_toward(s, L["pos"][0], L["pos"][2], WANDER_SPEED)
            return
        tg = self._wander_target(s)
        self._step_toward(s, tg[0], tg[2], WANDER_SPEED)

    def _move_drifters(self):
        P = self.player
        for d in sorted(self.drifters, key=id_key):
            if d["state"] == "removed":
                continue
            dist = dist_xz(d["pos"], P["pos"])
            want = (self._player_visible() and not d["has_stolen"] and P["carried"] >= DRIFTER_CHASE_CARRY
                    and dist <= DRIFTER_CHASE_DIST)
            if d["state"] == "idle" and want:
                d["state"] = "chase"
            elif d["state"] == "chase" and not want:
                d["state"] = "idle"
                d["target"] = None
            if d["state"] == "chase":
                self._step_toward(d, P["pos"][0], P["pos"][2], DRIFTER_SPEED)
            elif d["state"] == "flee":
                self._step_toward(d, P["pos"][0], P["pos"][2], DRIFTER_SPEED, away=True)
                d["flee"] -= 1
                if d["flee"] <= 0:
                    d["state"] = "removed"
            else:
                tg = self._wander_target(d)
                self._step_toward(d, tg[0], tg[2], DRIFTER_IDLE_SPEED)
            d["pos"][1] = self._shade_y(d["pos"][0], d["pos"][2])

    # 9
    def _collisions(self):
        P = self.player
        if P["respawn"] > 0:
            return
        for d in sorted(self.drifters, key=id_key):
            if (d["state"] in ("idle", "chase") and not d["has_stolen"] and P["carried"] > 0
                    and dist_xz(d["pos"], P["pos"]) <= DRIFTER_HIT):
                amt = min(DRIFTER_STEAL, P["carried"])
                P["carried"] -= amt
                d.update(stolen=amt, has_stolen=True, state="flee", flee=DRIFTER_FLEE)
                self.stats["steals"] += 1
                self._emit("drifter_steal", {"drifter_id": d["id"], "amount": amt, "carried": P["carried"]})
        if P["invuln"] > 0:
            return
        for s in sorted(self.shades, key=id_key):
            if s["state"] in ("spawning", "stunned", "recoil") or s["evict"] > 0:  # drain still hurts (C3)
                continue
            if dist_xz(s["pos"], P["pos"]) <= self.t["shade_hit_radius"] and abs(s["pos"][1] - P["pos"][1]) <= HIT_DY:
                P["flames"] -= 1
                dropped = P["carried"] // 2
                P["carried"] -= dropped
                self._drop_motes(dropped, P["pos"])
                P["invuln"] = int(round(self.t["invuln_s"] * TPS))
                dx, dz = s["pos"][0] - P["pos"][0], s["pos"][2] - P["pos"][2]
                dd = math.hypot(dx, dz)
                s["recoil_dir"] = (dx / dd, dz / dd) if dd > 1e-9 else (1.0, 0.0)
                s["state"], s["recoil"] = "recoil", RECOIL_TICKS
                self.stats["hits"] += 1
                self._emit("player_hit", {"by": "shade", "flames": P["flames"], "dropped": dropped})
                break  # at most one flame per tick

    # 10
    def _spawns(self):
        st = self.sim_tick
        if self.random_motes and st % MOTE_EVERY == 0 and len(self.motes) < MOTES_CAP:
            used = {m["point"] for m in self.motes if m["kind"] == "random" and m["point"] is not None}
            free = [i for i in range(len(self.map["mote_points"])) if i not in used]
            if free:
                i = self.rng.choice(free)
                self._add_mote(self.map["mote_points"][i], "random", point=i)
        if self.random_shades:
            n = 0
            if st == SHADE_FIRST:
                n = SHADE_FIRST_COUNT
            elif st > SHADE_FIRST and (st - SHADE_FIRST) % self.map["shade_every"] == 0:
                n = 1
            for _ in range(n):
                if len(self.shades) >= self.map["shade_max"]:
                    break
                pts = [p for p in self.map["shade_points"] if dist_xz(p, self.player["pos"]) >= SHADE_SPAWN_MIN_DIST]
                if not pts:
                    break
                s = self._add_shade(list(self.rng.choice(pts)))
                self._emit("shade_spawned", {"id": s["id"]})
        if self.random_drifters and self.map["drifters"] and st % DRIFTER_EVERY == 0:
            alive = sum(1 for d in self.drifters if d["state"] != "removed")
            if alive < DRIFTER_MAX:
                self._add_drifter(list(self.rng.choice(self.map["shade_points"])))

    # 11
    def _check_end(self):
        P, t = self.player, self.t
        if P["flames"] <= 0:
            self._end("lost", "no_flames")
        elif self.time_left_ticks <= 0:
            lit = [L for L in self.lanterns if L["lit"]]
            if len(lit) >= math.ceil(t["win_ratio"] * len(self.lanterns) - 1e-9):
                sc = t["score"]
                self.score += sum(sc["per_lit_at_dawn"] + L["fuel"] // FUEL_SCALE for L in lit)
                self.score += sc["per_flame_left"] * P["flames"]
                self._end("won", "dawn_survived")
            else:
                self._end("lost", "dawn")

    def _end(self, result, reason):
        self.over = result
        self.result_reason = reason
        self._emit("game_over", {"result": result, "reason": reason})

    # ---------- output ----------
    @property
    def time_left_s(self):
        return self.time_left_ticks / TPS

    def snapshot(self):
        P = self.player
        sec = lambda n: r3(n / TPS)  # noqa: E731
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "state": self.state,
            "night": self.night, "time_left_s": r3(self.time_left_s), "score": self.score,
            "wind": {"active": self.wind_active, "dir_deg": r3(self.wind_dir)},
            "player": {"pos": [r3(v) for v in P["pos"]], "vel": [r3(v) for v in P["vel"]],
                       "grounded": P["grounded"], "flames": P["flames"], "carried": P["carried"],
                       "capacity": self.capacity,
                       "invuln": P["invuln"] > 0, "dash_cd_s": sec(P["dash_cd"]), "pulse_cd_s": sec(P["pulse_cd"]),
                       "charm_s": sec(P["charm"])},
            "lanterns": [{"id": L["id"], "pos": [r3(v) for v in L["pos"]], "lit": L["lit"],
                          "deposited": L["deposited"], "fuel": r1(L["fuel"] / FUEL_SCALE) if L["lit"] else 0.0,
                          "ever_lit": L["ever_lit"], "relit_count": L["relit_count"]} for L in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(v) for v in s["pos"]], "state": s["state"],
                        "target_lantern_id": s.get("target_lantern")} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(v) for v in m["pos"]], "kind": m["kind"],
                       "ttl_s": None if m["ttl"] is None else sec(m["ttl"])} for m in self.motes],
            "drifters": [{"id": d["id"], "pos": [r3(v) for v in d["pos"]], "state": d["state"],
                          "stolen": d["stolen"]} for d in self.drifters],
            "charms": [{"id": c["id"], "pos": [r3(v) for v in c["pos"]], "available": c["available"],
                        "respawn_s": sec(c["respawn"])} for c in self.charms],
        }
