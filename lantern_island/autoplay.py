"""Simple deterministic bot that plays the Game through the same input frames a human/test would send.

Used for evidence: scripts/make_proof.py records its frames into an inputs.json and replays it via headless.py,
and `play.py --demo` uses it to drive the 3D build for screenshots.
"""
import math

from .sim import dist_xz


class Bot:
    def __init__(self):
        self.prev = {"interact": False, "pulse": False}

    def frame(self, g):
        t = g.t
        P = g.player
        unlit = [L for L in g.lanterns if not L["lit"]]
        out = {"cam_yaw_deg": 0, "interact": False, "pulse": False, "jump": False}
        if not unlit:
            out["move"] = [0, 0]
            return self._edges(out)
        target_L = min(unlit, key=lambda L: dist_xz(P["pos"], L["pos"]))
        need = int(t["lantern_cost"]) - target_L["deposited"]
        want = min(int(t["carry_capacity"]), need + 1)  # keep 1 spare for a pulse
        go_lantern = P["carried"] >= want or (P["carried"] >= need and not g.motes) or not g.motes
        if go_lantern:
            target = target_L["pos"]
            if dist_xz(P["pos"], target) <= t["interact_radius"] - 0.5:
                out["move"] = [0, 0]
                out["interact"] = not self.prev["interact"]
                return self._edges(out)
        else:
            target = min(g.motes, key=lambda m: dist_xz(P["pos"], m["pos"]))["pos"]
        dx, dz = target[0] - P["pos"][0], target[2] - P["pos"][2]
        d = math.hypot(dx, dz) or 1.0
        out["move"] = [dx / d, dz / d]
        near = [s for s in g.shades if s["state"] != "stunned" and dist_xz(P["pos"], s["pos"]) < 3.0]
        if near and P["carried"] >= t["pulse_cost"] and g.pulse_cd_ticks == 0:
            out["pulse"] = not self.prev["pulse"]
        return self._edges(out)

    def _edges(self, out):
        self.prev["interact"] = out["interact"]
        self.prev["pulse"] = out["pulse"]
        return out
