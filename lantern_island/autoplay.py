"""Deterministic bot that plays a Game through the same input frames a human/test would send.

Evidence only: scripts/record_bot.py records its frames into an inputs.json and replays it via headless.py;
`play.py --demo` uses it to drive the 3D build. Navigation knows the standard maps (bridge, ramps, pad).
"""
import math

from .sim import dist_xz


def _ang(p):
    return math.degrees(math.atan2(p[2], p[0]))


def _polar(r, deg, y=0.0):
    a = math.radians(deg)
    return [r * math.cos(a), y, r * math.sin(a)]


def _ring_step(p, target, r, step):
    a0, a1 = _ang(p), _ang(target)
    d = (a1 - a0 + 180) % 360 - 180
    return _polar(r, a0 + max(-step, min(step, d)))


def _seg_min_dist_origin(a, b):
    ax, az, bx, bz = a[0], a[2], b[0], b[2]
    dx, dz = bx - ax, bz - az
    L = dx * dx + dz * dz
    t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + az * dz) / L))
    return math.hypot(ax + t * dx, az + t * dz)


def _level(y):
    return 0 if y < 1.5 else (1 if y < 4.5 else 2)


class Bot:
    def __init__(self):
        self.prev = {"interact": False, "pulse": False}

    # ---- navigation: returns next waypoint toward target ----
    def waypoint(self, g, target):
        p = g.player["pos"]
        if g.night == 2:
            side = lambda q: 0 if q[0] < 35 else 1  # noqa: E731
            if side(p) != side(target):
                a, b = ([25.0, 0, 0], [46.0, 0, 0]) if side(p) == 0 else ([45.0, 0, 0], [24.0, 0, 0])
                if abs(p[2]) > 0.6 or (side(p) == 0 and p[0] < 24.5) or (side(p) == 1 and p[0] > 45.5):
                    return a
                return b
            return target
        if g.night == 3:
            lp, lt = _level(p[1]), _level(target[1])
            r = math.hypot(p[0], p[2])
            if lp == 2:
                if lt == 2:
                    if _seg_min_dist_origin(p, target) < 2.6:
                        return _ring_step(p, target, 5.0, 50)
                    return target
                return [0.0, 6.0, -9.5]  # walk off the south edge of tier 2 (tier 0 below)
            if lp == 1:
                if lt == 1:
                    if _seg_min_dist_origin(p, target) < 13:
                        return _ring_step(p, target, 18.0, 35) if r > 14 else _polar(18, _ang(p), 3)
                    return target
                if lt == 2:
                    if abs(p[0]) > 0.4 or p[2] < 13.5 or p[2] > 19:
                        return [0.0, 3.0, 17.0] if abs(p[0]) > 0.4 else [0.0, 3.0, 13.0]
                    return [0.0, 3.0, 13.0]  # bounce pad
                return _polar(27, _ang(p))  # step off the outer edge
            # level 0
            if lt >= 1:
                ramp = 30.0 if _ang(target) < 90 and _ang(target) > -90 else 150.0
                bottom, top = _polar(31.5, ramp), _polar(21.0, ramp, 3)
                if dist_xz(p, bottom) < 0.6 or (abs(((_ang(p) - ramp + 180) % 360) - 180) < 3 and r < 31.6):
                    return top
                return self._ring0(p, bottom)
            return self._ring0(p, target)
        return target

    def _ring0(self, p, target):
        r = math.hypot(p[0], p[2])
        if _seg_min_dist_origin(p, target) >= 26.5:
            return target
        if r < 30:
            return _polar(32, _ang(p))
        return _ring_step(p, target, 32.0, 25)

    # ---- decisions ----
    def frame(self, g):
        t, P = g.t, g.player
        out = {"cam_yaw_deg": 0, "interact": False, "pulse": False, "jump": False, "dash": False, "move": [0, 0]}
        unlit = [L for L in g.lanterns if not L["lit"] or L["fuel"] < 45 * 60]
        if not unlit or P["respawn"] > 0:
            return self._edges(out)
        cost = lambda q: dist_xz(P["pos"], q) + 40 * abs(_level(P["pos"][1]) - _level(q[1]))  # noqa: E731
        # Phase 3: lanterns burn out -> also refuel lit lanterns that are getting low
        low = [L for L in g.lanterns if L["lit"] and L["fuel"] < 45 * 60]
        pool = low + [L for L in unlit if L not in low] if low else unlit
        target_L = min(pool, key=lambda L: cost(L["pos"]) - (60 if L["lit"] else 0))
        if target_L["lit"]:
            need = -(-(g.FUEL_MAX - target_L["fuel"]) // g.FUEL_PER_MOTE)
        else:
            need = g._lantern_cost(target_L) - target_L["deposited"]
        reserve = int(t["pulse_cost"])
        want = min(g.capacity, need + reserve)
        motes = [m for m in g.motes if m["born"] < g.sim_tick]
        if P["carried"] >= want or (P["carried"] >= need and not motes) or (not motes and P["carried"] > 0):
            target = target_L["pos"]
            if dist_xz(P["pos"], target) <= t["interact_radius"] - 0.4 and _level(P["pos"][1]) == _level(target[1]):
                out["interact"] = not self.prev["interact"]
                return self._edges(out)
        elif motes:
            target = min(motes, key=lambda m: cost(m["pos"]))["pos"]
        else:
            target = target_L["pos"]
        wp = self.waypoint(g, target)
        dx, dz = wp[0] - P["pos"][0], wp[2] - P["pos"][2]
        d = math.hypot(dx, dz)
        if d > 1e-6:
            out["move"] = [dx / d, dz / d] if d > 0.15 else [dx / 0.15, dz / 0.15]
        active = [s for s in g.shades if s["state"] in ("chase", "wander")
                  and abs(s["pos"][1] - P["pos"][1]) < 2.5]
        near = [s for s in active if dist_xz(P["pos"], s["pos"]) < 3.5]
        thief = [x for x in g.drifters if x["state"] == "chase" and dist_xz(P["pos"], x["pos"]) < 4.0]
        if (near or thief) and P["carried"] >= t["pulse_cost"] and P["pulse_cd"] == 0:
            out["pulse"] = not self.prev["pulse"]
        elif P["invuln"] == 0 and g.night != 3 or _level(P["pos"][1]) == 0:
            # steer away from shades that are close (inverse-square repulsion), dash out if very close
            ax = az = 0.0
            for s in active:
                ddx, ddz = P["pos"][0] - s["pos"][0], P["pos"][2] - s["pos"][2]
                dd = math.hypot(ddx, ddz)
                if 1e-6 < dd < 6.0:
                    w = 9.0 / (dd * dd)
                    ax += ddx / dd * w
                    az += ddz / dd * w
            if ax or az:
                mx, mz = out["move"][0] + ax, out["move"][1] + az
                ml = math.hypot(mx, mz)
                if ml > 1e-6 and self._safe_dir(g, mx / ml, mz / ml, 2.5):
                    out["move"] = [mx / ml, mz / ml]
                    if near and P["dash_cd"] == 0 and self._safe_dir(g, mx / ml, mz / ml, 5.0):
                        out["dash"] = True
        return self._edges(out)

    @staticmethod
    def _safe_dir(g, dx, dz, dist):
        """True if walking `dist` m in (dx, dz) never leaves the island or drops off a tier."""
        p = g.player["pos"]
        for k in range(1, 6):
            h = g.ground(p[0] + dx * dist * k / 5, p[2] + dz * dist * k / 5)
            if h is None or h < p[1] - 0.5:
                return False
        return True

    def _edges(self, out):
        self.prev["interact"] = out["interact"]
        self.prev["pulse"] = out["pulse"]
        return out
