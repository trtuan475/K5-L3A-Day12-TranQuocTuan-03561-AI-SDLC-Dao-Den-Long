"""Dao Den Long - 3D build (Ursina). All gameplay comes from lantern_island.sim (same core as headless).

python3 play.py                       menu -> 3 nights
python3 play.py --night 2             jump straight to a night (testing)
python3 play.py --demo [--night N] --shots DIR   bot plays, saves screenshots, quits
python3 play.py --bench 20 --night 3  measure average FPS at 1280x720 for 20 s (bot plays), writes --out file
"""
import argparse
import json
import math
import os
import time as utime

from ursina import (AmbientLight, Audio, Button, DirectionalLight, Entity, Mesh, Slider, Text, Ursina, Vec3,
                    application, camera, color, destroy, held_keys, mouse, scene, window)
from ursina.models.procedural.cone import Cone
from ursina.models.procedural.cylinder import Cylinder
from panda3d.core import CullFaceAttrib
from ursina.shaders import lit_with_shadows_shader

from lantern_island.autoplay import Bot
from lantern_island.maps import NIGHTS, RAMPS_N3
from lantern_island.sim import DT, TPS, Game, dist_xz

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--night", type=int, default=0)
ap.add_argument("--demo", action="store_true")
ap.add_argument("--shots")
ap.add_argument("--bench", type=float, default=0)
ap.add_argument("--out", default="fps.txt")
ap.add_argument("--colorblind", action="store_true", help="force colour-blind palette (screenshots)")
ARGS, _ = ap.parse_known_args()
AUTO = ARGS.demo or ARGS.bench > 0

# ---------------- palette (Ticket-02 part 3) ----------------
H = color.hex
PAL = dict(sky=H("#0E1430"), fog=H("#1B2350"), grass=H("#2F5D50"), sand=H("#C9B48A"), wood=H("#6B4A2F"),
           sea=H("#12384A"), lamp_on=H("#FFB347"), lamp_core=H("#FFE9B0"), lamp_off=H("#5B5F6E"),
           mote_core=H("#FFF6C2"), mote_halo=H("#FFE58A"), shade=H("#120A1A"), shade_rim=H("#7A3CFF"),
           shade_stun=H("#3A3450"), shirt=H("#E8E2D0"), red=H("#C8102E"), gold=H("#F2C14E"),
           drifter=H("#8FA3B8"), danger=H("#FF5A5F"), text=H("#F5F1E6"))


def rim_color():
    """Ticket-03 colour-blind palette: shade rim/eyes #7A3CFF -> #00B3FF, UI danger #FF5A5F -> #FFFFFF (+ warning icon)."""
    return H("#00B3FF") if SETTINGS["colorblind"] else PAL["shade_rim"]


def danger_color():
    return color.white if SETTINGS["colorblind"] else PAL["danger"]


def alpha(c, a):
    return color.rgba(c[0], c[1], c[2], a)


def shade_of(c, k):
    return color.rgba(min(1, c[0] * k), min(1, c[1] * k), min(1, c[2] * k), 1)


INTRO = {
    1: "Ông Đăng: \"Sương đen đã nuốt đèn Đảo Bến rồi, cháu à. Gom đom đóm, thắp lại năm ngọn đèn trước khi trời sáng.\"",
    2: "Ông Đăng: \"Đảo Cau có hai nửa, nối nhau bằng cây cầu tre. Coi chừng Gió Lạc, nó mê đom đóm lắm đó.\"",
    3: "Ông Đăng: \"Đảo Chuông cao và lộng gió. Lá bay là gió sắp tới, cháu bám chắc nghe. Ngọn đèn trên đỉnh tháp chờ cháu.\"",
}

# ---------------- settings (persisted) ----------------
SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".dao_den_long_settings.json")


def load_settings():
    s = {"volume": 0.7, "sensitivity": 1.0, "colorblind": False}
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            for k, v in json.load(f).items():
                if k in s:
                    s[k] = bool(v) if k == "colorblind" else float(v)
    except (OSError, ValueError):
        pass
    return s


def save_settings():
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f)
    except OSError:
        pass


SETTINGS = load_settings()
if ARGS.colorblind:
    SETTINGS["colorblind"] = True

app = Ursina(title="Dao Den Long", borderless=False, development_mode=False,
             size=(1280, 720) if ARGS.bench else None, vsync=not ARGS.bench)
window.color = PAL["sky"]
window.fps_counter.enabled = bool(ARGS.bench)
window.exit_button.visible = False
scene.fog_color = PAL["fog"]
scene.fog_density = (30, 110)
AMBIENT = AmbientLight(color=color.rgba(0.15, 0.15, 0.15, 1))
MOON = DirectionalLight(color=color.rgba(0.35, 0.38, 0.55, 1), shadows=False)
MOON.look_at(Vec3(0.4, -1, 0.6))

SFX = {}
for _n in ("pick", "lit", "pulse", "hit", "jump", "dash", "win", "lose", "shade", "tick", "wind", "charm", "steal"):
    SFX[_n] = Audio(f"assets/sfx/{_n}.wav", autoplay=False, loop=False)
MUSIC = Audio("assets/sfx/music.wav", autoplay=False, loop=True)


def sfx(name):
    a = SFX.get(name)
    if a and not ARGS.bench:
        a.volume = SETTINGS["volume"]
        a.play()


def lit_e(**kw):
    return Entity(shader=lit_with_shadows_shader, **kw)


def unlit_e(**kw):
    """Emissive / palette-exact parts: ignore scene lights so colours match the standard palette."""
    e = Entity(**kw)
    e.setLightOff()
    return e


# ---------------- world rendering ----------------
class World:
    def __init__(self, game):
        self.g = game
        self.root = Entity()
        n = game.night
        unlit_e(parent=self.root, model="plane", scale=600, y=-9, color=PAL["sea"])
        if n == 1:
            self._island(0, 40)
        elif n == 2:
            self._island(0, 28)
            self._island(70, 28)
            lit_e(parent=self.root, model="cube", position=(35, -0.15, 0), scale=(18, 0.3, 4), color=PAL["wood"])
            for x in range(27, 44, 2):
                lit_e(parent=self.root, model="cube", position=(x, 0.02, 0), scale=(0.3, 0.05, 4), color=PAL["sand"])
        else:
            self._island(0, 45)
            for i in range(24):  # tier 1: half annulus r 12-24, z > 0, Y = 3
                a = math.radians(3.75 + 7.5 * i)
                e = lit_e(parent=self.root, model="cube", color=shade_of(PAL["grass"], 1.15),
                          position=(18 * math.cos(a), 1.5, 18 * math.sin(a)), scale=(12, 3, 2.5))
                e.rotation_y = math.degrees(math.atan2(math.cos(a), math.sin(a))) + 90
            lit_e(parent=self.root, model=Cylinder(resolution=40, radius=8, height=6), color=shade_of(PAL["grass"], 1.3))
            lit_e(parent=self.root, model=Cylinder(resolution=24, radius=2, height=8), y=6, color=PAL["wood"])
            lit_e(parent=self.root, model=Cone(resolution=24, radius=2.6, height=2), y=14, color=PAL["red"])
            unlit_e(parent=self.root, model="sphere", y=12.5, scale=1.2, color=PAL["gold"])
            for deg in RAMPS_N3:
                a = math.radians(deg)
                e = lit_e(parent=self.root, model="cube", color=PAL["sand"],
                          position=(27 * math.cos(a), 1.5, 27 * math.sin(a)), scale=(3, 0.3, math.hypot(6, 3)))
                e.rotation_y = math.degrees(math.atan2(math.cos(a), math.sin(a)))
                e.rotation_x = math.degrees(math.atan2(3, 6))
        for pad in game.map["pads"]:
            unlit_e(parent=self.root, model=Cylinder(resolution=24, radius=1, height=0.12),
                    position=Vec3(*pad["pos"]) + Vec3(0, 0.01, 0), color=PAL["gold"])
        self.lanterns = {}
        for L in game.lanterns:
            base = Entity(parent=self.root, position=Vec3(*L["pos"]))
            lit_e(parent=base, model="cube", color=PAL["wood"], scale=(0.25, 3.2, 0.25), y=1.6)
            lit_e(parent=base, model="cube", color=PAL["wood"], scale=(1.2, 0.15, 0.15), y=3.2, x=0.3)
            lamp = unlit_e(parent=base, model="cube", scale=(0.8, 1.0, 0.8), y=2.6, x=0.6, color=PAL["lamp_off"])
            core = unlit_e(parent=base, model="sphere", scale=0.45, y=2.6, x=0.6, color=PAL["lamp_core"], enabled=False)
            halo = unlit_e(parent=base, model="sphere", y=2.6, x=0.6, scale=3.5, color=alpha(PAL["lamp_on"], 0.18),
                           enabled=False)
            safe = unlit_e(parent=base, model=Cylinder(resolution=48, radius=game.t["safe_radius"], height=0.03),
                           y=0.03, color=alpha(PAL["lamp_on"], 0.16), enabled=False)
            tear = unlit_e(parent=lamp, model="quad", color=color.rgb(0.12, 0.1, 0.12), scale=(0.35, 0.5),
                           position=(0.1, -0.1, -0.51), rotation_z=25)  # torn paper (visible when off)
            bar = Entity(parent=base, y=4.0, billboard=True)
            unlit_e(parent=bar, model="quad", scale=(1.6, 0.18), color=color.rgba(0, 0, 0, 0.7))
            fill = unlit_e(parent=bar, model="quad", scale=(1.5, 0.12), origin=(-0.5, 0), x=-0.75, z=-0.01,
                           color=PAL["lamp_on"])
            self.lanterns[L["id"]] = (lamp, core, halo, safe, tear, bar, fill)
        self.player = Entity(parent=self.root)
        unlit_e(parent=self.player, model="cube", color=PAL["shirt"], scale=(0.7, 0.9, 0.5), y=0.55)
        unlit_e(parent=self.player, model="cube", color=PAL["red"], scale=(0.75, 0.15, 0.55), y=1.0)
        unlit_e(parent=self.player, model="sphere", color=color.rgb(0.95, 0.8, 0.65), scale=0.55, y=1.25)
        unlit_e(parent=self.player, model=Cone(resolution=24, radius=0.75, height=0.45), color=PAL["sand"], y=1.42)
        unlit_e(parent=self.player, model="cube", color=PAL["wood"], scale=(0.03, 0.5, 0.03), position=(0.6, 1.2, 0))
        self.p_lamp = unlit_e(parent=self.player, model="sphere", color=PAL["lamp_on"], scale=0.22, position=(0.6, 0.9, 0))
        self.p_glow = unlit_e(parent=self.player, model="sphere", color=alpha(PAL["lamp_on"], 0.12), scale=2,
                              position=(0.6, 0.9, 0))
        self.motes, self.shades, self.drifters, self.charms = {}, {}, {}, {}
        self.pulse_fx = unlit_e(parent=self.root, model="sphere", color=alpha(PAL["lamp_core"], 0.25), enabled=False)
        self.pulse_t = 0.0
        self.leaves = [unlit_e(parent=self.root, model="quad", scale=0.25, color=color.rgb(0.45, 0.7, 0.35),
                               double_sided=True, enabled=False) for _ in range(24)]

    def _island(self, cx, r):
        lit_e(parent=self.root, model=Cylinder(resolution=64, radius=r + 0.8, height=3), position=(cx, -3.05, 0),
              color=PAL["sand"])
        lit_e(parent=self.root, model=Cylinder(resolution=64, radius=r, height=2), position=(cx, -2, 0),
              color=PAL["grass"])

    def sync(self, t_anim):
        g = self.g
        lit = sum(L["lit"] for L in g.lanterns)
        k = 0.15 + 0.55 * lit / len(g.lanterns)  # ambient intensity (Ticket-02)
        AMBIENT.color = color.rgba(k, k, k, 1)
        scene.fog_density = (30 + lit * 6, 110 + lit * 10)
        blink_off = int(t_anim * 2) % 2 == 1  # 1 Hz slow blink
        for L in g.lanterns:
            lamp, core, halo, safe, tear, bar, fill = self.lanterns[L["id"]]
            fuel = L["fuel"] / 60.0
            low = L["lit"] and fuel < g.t["low_fuel_threshold"]
            lamp.color = PAL["lamp_on"] if L["lit"] and not (low and blink_off) else PAL["lamp_off"]
            lamp.scale_y = 1.0 if L["lit"] else 0.8  # off lantern is squashed 20% (shape cue, not colour)
            tear.enabled = not L["lit"]
            core.enabled = halo.enabled = L["lit"] and not (low and blink_off)
            safe.enabled = g._safe(L)
            bar.enabled = L["lit"] and not (low and blink_off)
            fill.scale_x = 1.5 * max(0.0, min(1.0, fuel / g.t["fuel_max"]))
            fill.color = danger_color() if low else PAL["lamp_on"]
        p = g.player["pos"]
        self.player.position = Vec3(*p)
        self.player.rotation_y = math.degrees(math.atan2(*g.player["facing"]))
        self.player.visible = g.player["respawn"] == 0 and not (g.player["invuln"] > 0 and int(t_anim * 12) % 2 == 0)
        self.p_glow.scale = 1.5 + g.player["carried"] * 0.2
        self._sync_pool(self.motes, g.motes, self._new_mote, self._upd_mote, t_anim)
        self._sync_pool(self.shades, g.shades, self._new_shade, self._upd_shade, t_anim)
        self._sync_pool(self.drifters, [d for d in g.drifters if d["state"] != "removed"], self._new_drifter,
                        self._upd_drifter, t_anim)
        for c in g.charms:
            e = self.charms.get(c["id"])
            if e is None:
                e = self.charms[c["id"]] = Entity(parent=self.root, position=Vec3(*c["pos"]) + Vec3(0, 1, 0))
                unlit_e(parent=e, model="quad", color=PAL["gold"], scale=(0.75, 1.05), double_sided=True)
                unlit_e(parent=e, model="quad", color=PAL["red"], scale=(0.6, 0.9), z=-0.01, double_sided=True)
            e.enabled = c["available"]
            e.rotation_y = t_anim * 90
        if self.pulse_t > 0:
            self.pulse_t -= 1 / 60
            self.pulse_fx.enabled = True
            self.pulse_fx.position = Vec3(p[0], p[1] + 0.8, p[2])
            self.pulse_fx.scale = 2 * g.t["pulse_radius"] * (1 - self.pulse_t / 0.35)
        else:
            self.pulse_fx.enabled = False
        windy = g.wind_active or g.wind_warning
        a = math.radians(g.wind_dir)
        for i, leaf in enumerate(self.leaves):
            leaf.enabled = windy
            if windy:
                ph = (t_anim * (0.6 + i % 5 * 0.1) + i * 0.37) % 1.0
                side = (i * 7.3) % 16 - 8
                leaf.position = Vec3(p[0] + math.cos(a) * (ph * 24 - 12) - math.sin(a) * side,
                                     p[1] + 0.5 + (i % 4) * 0.7 + math.sin(t_anim * 5 + i),
                                     p[2] + math.sin(a) * (ph * 24 - 12) + math.cos(a) * side)
                leaf.rotation = Vec3(t_anim * 200 + i * 30, t_anim * 150, 0)

    def _sync_pool(self, pool, items, make, upd, t_anim):
        ids = set()
        for it in items:
            ids.add(it["id"])
            e = pool.get(it["id"])
            if e is None:
                e = pool[it["id"]] = make(it)
            upd(e, it, t_anim)
        for k in [k for k in pool if k not in ids]:
            destroy(pool.pop(k))

    def _new_mote(self, m):
        e = unlit_e(parent=self.root, model="sphere", color=PAL["mote_core"], scale=0.25)
        unlit_e(parent=e, model="sphere", color=alpha(PAL["mote_halo"], 0.25), scale=3)
        return e

    def _upd_mote(self, e, m, t_anim):
        ph = (hash(m["id"]) % 100) / 10
        e.position = Vec3(m["pos"][0], m["pos"][1] + 0.9 + 0.25 * math.sin(t_anim * 2.5 + ph), m["pos"][2])
        e.visible = not (m["ttl"] is not None and m["ttl"] < 120 and int(t_anim * 8) % 2 == 0)

    def _new_shade(self, s):
        e = unlit_e(parent=self.root, model="sphere", scale=(1.6, 1.9, 1.6), color=PAL["shade"])
        rim = unlit_e(parent=e, model="sphere", color=rim_color(), scale=1.12)
        rim.setAttrib(CullFaceAttrib.make_reverse())  # outline: only the back faces show around the silhouette
        for x in (-0.15, 0.15):
            unlit_e(parent=e, model="sphere", color=rim_color(), scale=0.12, position=(x, 0.15, 0.45))
        e.cb_parts = list(e.children)
        return e

    def _upd_shade(self, e, s, t_anim):
        p = self.g.player["pos"]
        e.position = Vec3(*s["pos"]) + Vec3(0, 0.15 * math.sin(t_anim * 3 + len(s["id"])), 0)
        e.color = PAL["shade_stun"] if s["state"] == "stunned" else PAL["shade"]
        rc = rim_color()
        for part in e.cb_parts:
            part.color = rc
        k = (0.4 + 0.6 * (1 - s["spawn"] / 60)) if s["state"] == "spawning" else 1.0
        e.scale = Vec3(1.6, 1.9, 1.6) * k
        e.look_at_2d(Vec3(p[0], 0, p[2]), "y")

    def _new_drifter(self, d):
        e = Entity(parent=self.root)
        for i in range(6):
            unlit_e(parent=e, model="quad", color=alpha(PAL["drifter"], 0.85 - i * 0.12), scale=(0.35, 0.9),
                    z=-i * 0.45, double_sided=True)
        return e

    def _upd_drifter(self, e, d, t_anim):
        e.position = Vec3(*d["pos"])
        for i, q in enumerate(e.children):
            q.y = 0.3 * math.sin(t_anim * 8 - i * 0.8)
        e.look_at_2d(Vec3(*self.g.player["pos"]), "y")

    def destroy(self):
        destroy(self.root)


# ---------------- HUD ----------------
def ui_text(**kw):
    kw.setdefault("color", PAL["text"])
    return Text(**kw)


class HUD:
    def __init__(self):
        self.root = Entity(parent=camera.ui)
        tl, tr = window.top_left, window.top_right
        ui_text(parent=self.root, text="Ngọn Lửa", position=tl + Vec3(0.03, -0.03, 0), scale=0.9)
        self.flames = [unlit_e(parent=self.root, model="circle", scale=0.035, color=PAL["lamp_on"],
                               position=tl + Vec3(0.05 + i * 0.045, -0.085, 0)) for i in range(3)]
        self.night = ui_text(parent=self.root, position=tl + Vec3(0.03, -0.115, 0), scale=0.75)
        self.timer = ui_text(parent=self.root, origin=(0, 0), position=(0, 0.46), scale=1.8)
        self.right = ui_text(parent=self.root, origin=(0.5, 0.5), position=tr + Vec3(-0.03, -0.03, 0), scale=1.0)
        self.score = ui_text(parent=self.root, origin=(0.5, 0.5), position=tr + Vec3(-0.03, -0.075, 0), scale=1.0,
                             color=PAL["gold"])
        self.slots, self.cells = [], []
        for i in range(20):  # capacity grows 10 -> 20 (Ticket-03)
            x = -0.418 + i * 0.044
            self.slots.append(unlit_e(parent=self.root, model="quad", scale=(0.034, 0.034),
                                      color=alpha(PAL["text"], 0.25), position=(x, -0.44)))
            self.cells.append(unlit_e(parent=self.root, model="quad", scale=(0.028, 0.028), color=PAL["mote_halo"],
                                      position=(x, -0.44, -0.01)))
        self.carry = ui_text(parent=self.root, origin=(0, 0), position=(0, -0.405), scale=0.7)
        self.warn = unlit_e(parent=self.root, model=Mesh(vertices=[(-0.5, -0.43, 0), (0.5, -0.43, 0), (0, 0.43, 0)],
                                                          triangles=[(0, 1, 2)]), color=color.white, scale=0.05,
                            position=(-0.09, 0.46), enabled=False)
        ui_text(parent=self.warn, text="!", origin=(0, 0), scale=18, color=color.black, z=-0.01, y=-0.08)
        self.goal = ui_text(parent=self.root, origin=(0.5, 0.5), position=tr + Vec3(-0.03, -0.12, 0), scale=0.75)
        br = window.bottom_right
        self.icons = {}
        for i, (key, label) in enumerate((("dash", "Lướt [Shift]"), ("pulse", "Tỏa sáng [F]"))):
            pos = br + Vec3(-0.21 + i * 0.11, 0.09, 0)
            unlit_e(parent=self.root, model="circle", scale=0.07, color=PAL["gold"] if key == "pulse" else PAL["drifter"],
                    position=pos)
            cover = unlit_e(parent=self.root, model="quad", scale=(0.075, 0.075), color=color.rgba(0, 0, 0, 0.6),
                            position=pos + Vec3(0, -0.0375, -0.01), origin=(0, -0.5))
            txt = ui_text(parent=self.root, origin=(0, 0), position=pos + Vec3(0, 0, -0.02), scale=0.8)
            ui_text(parent=self.root, text=label, origin=(0, 0), position=pos + Vec3(0, -0.055, 0), scale=0.6)
            self.icons[key] = (cover, txt)
        self.prompt = ui_text(parent=self.root, origin=(0, 0), position=(0, -0.3), scale=1.2)
        self.status = ui_text(parent=self.root, origin=(0, 0), position=(0, 0.39), scale=0.9)
        self.arrow = unlit_e(parent=self.root, model=Mesh(vertices=[(-0.5, -0.4, 0), (0.5, -0.4, 0), (0, 0.6, 0)],
                                                           triangles=[(0, 1, 2)]),
                             color=PAL["lamp_on"], scale=0.045, enabled=False)

    def sync(self, g, total, t_anim, yaw):
        P = g.player
        for i, f in enumerate(self.flames):
            f.color = PAL["lamp_on"] if i < P["flames"] else alpha(PAL["lamp_off"], 0.6)
        self.night.text = f"Đêm {g.night} - {g.map['name']}"
        s = int(math.ceil(g.time_left_s))
        self.timer.text = f"{s // 60:02d}:{s % 60:02d}"
        danger = g.time_left_s <= 30
        self.timer.color = danger_color() if danger else PAL["text"]
        self.timer.visible = not (danger and int(t_anim * 3) % 2 == 0)
        self.warn.enabled = danger and SETTINGS["colorblind"]
        lit = sum(L["lit"] for L in g.lanterns)
        self.right.text = f"Đèn {lit}/{len(g.lanterns)}"
        self.score.text = f"Điểm {total + g.score}"
        cap = g.capacity
        for i, (slot, c) in enumerate(zip(self.slots, self.cells)):
            slot.enabled = i < cap
            c.enabled = i < P["carried"]
        self.carry.text = f"Đom đóm {P['carried']}/{cap}"
        need = math.ceil(g.t["win_ratio"] * len(g.lanterns) - 1e-9)
        self.goal.text = f"Giữ ≥ {need} đèn sáng tới bình minh"
        for key, cd, full in (("dash", P["dash_cd"], g.t["dash_cooldown_s"] * TPS),
                              ("pulse", P["pulse_cd"], g.t["pulse_cooldown_s"] * TPS)):
            cover, txt = self.icons[key]
            frac = 0 if (key == "dash" and P["charm"] > 0) else min(1.0, cd / full)
            cover.scale_y = 0.075 * frac
            txt.text = f"{cd / TPS:.1f}" if frac > 0 else ""
        near = [L for L in g.lanterns if not L["lit"] and dist_xz(P["pos"], L["pos"]) <= g.t["interact_radius"]]
        near = [L for L in g.lanterns if dist_xz(P["pos"], L["pos"]) <= g.t["interact_radius"]
                and (not L["lit"] or L["fuel"] < g.FUEL_MAX)]
        if near:
            L = min(near, key=lambda L: dist_xz(P["pos"], L["pos"]))
            self.prompt.text = (f"E - Châm dầu ({L['fuel'] / 60:.0f}/100)" if L["lit"]
                                else f"E - Nạp ánh sáng ({L['deposited']}/{g._lantern_cost(L)})")
        else:
            self.prompt.text = ""
        bits = []
        if P["charm"] > 0:
            bits.append(f"Bùa Gió {P['charm'] / TPS:.0f}s")
        if g.wind_warning:
            bits.append("Lá bay... gió sắp tới!")
        elif g.wind_active:
            bits.append("Gió mạnh!")
        self.status.text = "   ".join(bits)
        # arrow to nearest unlit lantern when off-screen (outside the horizontal view cone)
        unlit = [L for L in g.lanterns if not L["lit"]]
        self.arrow.enabled = False
        if unlit:
            L = min(unlit, key=lambda L: dist_xz(P["pos"], L["pos"]))
            ang = math.degrees(math.atan2(L["pos"][0] - P["pos"][0], L["pos"][2] - P["pos"][2])) - yaw
            ang = (ang + 180) % 360 - 180
            half_fov = camera.fov * window.aspect_ratio / 2 * 0.85
            if abs(ang) > half_fov:
                self.arrow.enabled = True
                r = math.radians(ang)
                self.arrow.position = (math.sin(r) * 0.36, math.cos(r) * 0.3 - 0.05, -0.05)
                self.arrow.rotation_z = ang

    def destroy(self):
        destroy(self.root)


# ---------------- menus ----------------
def panel(title, buttons, subtitle=""):
    root = Entity(parent=camera.ui)
    unlit_e(parent=root, model="quad", scale=(2.2, 1.2), color=color.rgba(0.05, 0.07, 0.15, 0.82), z=0.1)
    ui_text(parent=root, text=title, origin=(0, 0), y=0.3, scale=2.6, color=PAL["gold"])
    if subtitle:
        ui_text(parent=root, text=subtitle, origin=(0, 0), y=0.18, scale=1.05, wordwrap=60)
    for i, (label, fn) in enumerate(buttons):
        Button(parent=root, text=label, scale=(0.42, 0.065), y=0.04 - i * 0.085, color=alpha(PAL["wood"], 0.95),
               highlight_color=PAL["lamp_on"], on_click=fn)
    return root


class Flow:
    """menu -> intro -> play -> result -> next night ... -> dawn."""

    def __init__(self):
        self.mode = None
        self.ui = None
        self.game = self.world = self.hud = None
        self.total = 0
        self.night = 1
        self.acc = 0.0
        self.yaw = 0.0
        self.anim = 0.0
        self.bot = None
        self.pending = {}
        self.last_sec = None
        self.mode_time = 0.0

    def clear_ui(self):
        if self.ui:
            destroy(self.ui)
            self.ui = None

    def clear_game(self):
        for x in (self.world, self.hud):
            if x:
                x.destroy()
        self.world = self.hud = self.game = None

    def set_mode(self, m):
        self.mode, self.mode_time = m, 0.0
        mouse.locked = (m == "play" and not AUTO)

    def menu(self):
        self.clear_ui()
        self.clear_game()
        MUSIC.stop()
        self.set_mode("menu")
        self.ui = panel("Đảo Đèn Lồng", [("Bắt đầu", lambda: self.new_run(1)), ("Đêm 2 - Đảo Cau", lambda: self.new_run(2)),
                                         ("Đêm 3 - Đảo Chuông", lambda: self.new_run(3)),
                                         ("Cài đặt", lambda: self.settings("menu")), ("Thoát", application.quit)],
                        "Giúp Mây thắp lại các Đèn Lồng Lớn")

    def new_run(self, night):
        self.total = 0
        self.intro(night)

    def intro(self, night):
        self.clear_ui()
        self.clear_game()
        self.night = night
        self.set_mode("intro")
        self.ui = panel(f"Đêm {night} - {NIGHTS[night]['name']}", [("Vào đảo", self.start_night)], INTRO[night])

    def start_night(self):
        self.clear_ui()
        self.clear_game()
        self.game = Game(seed=ARGS.seed, night=self.night)
        self.world = World(self.game)
        self.hud = HUD()
        self.bot = Bot() if AUTO else None
        self.acc = 0.0
        self.yaw = 0.0
        self.last_sec = None
        self.set_mode("play")
        MUSIC.volume = SETTINGS["volume"] * 0.5
        if not ARGS.bench:
            MUSIC.play()

    def pause_panel(self):
        self.ui = panel("Tạm dừng", [("Tiếp tục", self.toggle_pause), ("Chơi lại Đêm", self.start_night),
                                     ("Cài đặt", lambda: self.settings("pause")), ("Về menu", self.menu)])

    def toggle_pause(self):
        g = self.game
        if self.mode == "play":
            g.step({"pause": True})  # contract pause: logic frozen until the next pause edge
            self.set_mode("pause")
            self.pause_panel()
        elif self.mode == "pause":
            self.clear_ui()
            g.step({"pause": False})
            g.step({"pause": True})  # resume edge
            self.pending = {"pause": False}
            self.set_mode("play")

    def settings(self, back):
        self.clear_ui()
        self.set_mode("settings" if back == "menu" else "pause")
        self.ui = Entity(parent=camera.ui)
        unlit_e(parent=self.ui, model="quad", scale=(2.2, 1.2), color=color.rgba(0.05, 0.07, 0.15, 0.85), z=0.1)
        ui_text(parent=self.ui, text="Cài đặt", origin=(0, 0), y=0.3, scale=2.4, color=PAL["gold"])
        vol = Slider(0, 1, default=SETTINGS["volume"], step=0.05, text="Âm lượng", parent=self.ui, x=-0.25, y=0.12,
                     dynamic=True)
        sens = Slider(0.2, 3, default=SETTINGS["sensitivity"], step=0.1, text="Độ nhạy chuột", parent=self.ui,
                      x=-0.25, y=0.02, dynamic=True)

        def changed():
            SETTINGS["volume"] = round(vol.value, 2)
            SETTINGS["sensitivity"] = round(sens.value, 2)
            MUSIC.volume = SETTINGS["volume"] * 0.5
            save_settings()
        vol.on_value_changed = changed
        sens.on_value_changed = changed

        def back_fn():
            self.clear_ui()
            if back == "pause":
                self.pause_panel()
            else:
                self.menu()
        def cb_label():
            return f"Bảng màu dễ phân biệt: {'Bật' if SETTINGS['colorblind'] else 'Tắt'}"
        cb = Button(parent=self.ui, text=cb_label(), scale=(0.5, 0.065), y=-0.09, color=alpha(PAL["wood"], 0.95),
                    highlight_color=PAL["lamp_on"])

        def toggle_cb():
            SETTINGS["colorblind"] = not SETTINGS["colorblind"]
            cb.text = cb_label()
            save_settings()
        cb.on_click = toggle_cb
        Button(parent=self.ui, text="Xong", scale=(0.3, 0.065), y=-0.19, color=alpha(PAL["wood"], 0.95),
               highlight_color=PAL["lamp_on"], on_click=back_fn)

    def result(self):
        g = self.game
        MUSIC.stop()
        won = g.state == "won"
        sfx("win" if won else "lose")
        self.set_mode("result")
        if won:
            self.total += g.score
            if g.night == 3:
                self.ui = panel("Bình Minh", [("Về menu", self.menu)],
                                f"Ba hòn đảo đã sáng lại. Mặt trời lên trên biển mây.\nTổng điểm: {self.total}")
                return
            self.ui = panel(f"Đêm {g.night}: đảo sáng tới bình minh!", [(f"Đêm {g.night + 1}", lambda: self.intro(g.night + 1)),
                                                             ("Về menu", self.menu)],
                            f"Điểm Đêm: {g.score}    Tổng: {self.total}")
        else:
            why = "Hết Ngọn Lửa" if g.result_reason == "no_flames" else "Bình minh tới, đảo chưa đủ sáng"
            self.ui = panel(why, [("Chơi lại Đêm", self.start_night), ("Về menu", self.menu)],
                            f"Điểm Đêm (không cộng): {g.score}    Tổng: {self.total}")

    # -------- per-frame --------
    def human_frame(self):
        f = {"move": [held_keys["d"] - held_keys["a"], held_keys["w"] - held_keys["s"]], "cam_yaw_deg": self.yaw,
             "jump": bool(held_keys["space"]), "interact": bool(held_keys["e"]),
             "pulse": bool(held_keys["f"] or held_keys["left mouse"]),
             "dash": bool(held_keys["shift"] or held_keys["left shift"]), "pause": False}
        f.update(self.pending)
        self.pending = {}
        return f

    def update(self, dt):
        self.anim += dt
        self.mode_time += dt
        if AUTO and self.mode in ("menu", "intro") and self.mode_time > (0.6 if ARGS.bench else 1.2):
            if self.mode == "menu":
                self.new_run(ARGS.night or 1)
            else:
                self.start_night()
            return
        if self.mode != "play" or not self.game:
            return
        g = self.game
        if not AUTO:
            self.yaw += (mouse.velocity[0] * 180 + (held_keys["right arrow"] - held_keys["left arrow"]) * 90 * dt) \
                * SETTINGS["sensitivity"]
        self.acc += dt
        steps = 0
        while self.acc >= DT and not g.over and steps < 8:
            self.acc -= DT
            steps += 1
            if self.bot:
                f = self.bot.frame(g)
                if any(f["move"]):
                    target = math.degrees(math.atan2(*f["move"]))
                    self.yaw += ((target - self.yaw + 180) % 360 - 180) * 0.03
            else:
                f = self.human_frame()
            was_grounded = g.player["grounded"]
            was_warn = g.wind_warning
            for _, name, _d in g.step(f):
                if name == "pulse":
                    self.world.pulse_t = 0.35
                    sfx("pulse")
                elif name in ("mote_picked", "lantern_lit", "dash", "shade_spawned", "charm_picked"):
                    sfx({"mote_picked": "pick", "lantern_lit": "lit", "dash": "dash", "shade_spawned": "shade",
                         "charm_picked": "charm"}[name])
                elif name == "player_hit":
                    sfx("hit")
                elif name == "drifter_steal":
                    sfx("steal")
            if was_grounded and g.player["vel"][1] > 6.9:
                sfx("jump")
            if g.wind_warning and not was_warn:
                sfx("wind")
            sec = int(math.ceil(g.time_left_s))
            if sec <= 10 and sec != self.last_sec and not g.over:
                sfx("tick")
            self.last_sec = sec
        self.world.sync(self.anim)
        self.hud.sync(g, self.total, self.anim, self.yaw)
        th = math.radians(self.yaw)
        p = Vec3(*g.player["pos"])
        camera.position = p + Vec3(-math.sin(th) * 14, 9, -math.cos(th) * 14)
        camera.rotation = Vec3(math.degrees(math.atan2(9 - 1.2, 14)), self.yaw, 0)
        if g.over:
            self.result()


FLOW = Flow()
STATE = {"shots": [], "frames": 0, "t0": None, "end_frames": 0}


def update():
    dt = 4 * DT if ARGS.shots else min(utime.dt, 0.1)
    FLOW.update(dt)
    if ARGS.shots:
        demo_shots()
    if ARGS.bench:
        bench()


def snap(name):
    os.makedirs(ARGS.shots, exist_ok=True)
    if name not in STATE["shots"]:
        STATE["shots"].append(name)
        r = app.screenshot(namePrefix=os.path.join(ARGS.shots, name + ".png"), defaultFilename=False)
        g = FLOW.game
        print(f"[demo] {name} mode={FLOW.mode} tick={g.tick if g else '-'} -> {r}", flush=True)


def demo_shots():
    """Evidence run: bot plays each night ~1 min, screenshots of intro / play / pause / settings / result."""
    g, n = FLOW.game, FLOW.night
    if FLOW.mode == "intro" and FLOW.mode_time > 0.5:
        snap(f"n{n}_0_intro")
    if FLOW.mode == "play" and g:
        for tick, tag in ((240, "1_play"), (1500, "2_mid"), (3000, "3_late")):
            if g.tick >= tick:
                snap(f"n{n}_{tag}")
        if n == 1 and g.tick >= 600 and "pause" not in STATE["shots"]:
            STATE["shots"].append("pause")
            FLOW.toggle_pause()
        if g.tick >= 3100:
            g.over, g.result_reason = "lost", "dawn"  # demo cut: end the night early
            FLOW.result()
    if FLOW.mode == "pause" and FLOW.mode_time > 0.1 and "n1_pause" not in STATE["shots"]:
        snap("n1_pause")
        FLOW.toggle_pause()
    if FLOW.mode == "result" and FLOW.mode_time > 0.5:
        snap(f"n{n}_4_result")
        if n < 3:
            FLOW.intro(n + 1)
        else:
            STATE["end_frames"] += 1
            if STATE["end_frames"] > 5:
                application.quit()


def bench():
    if FLOW.mode != "play":
        return
    STATE["frames"] += 1
    now = utime.perf_counter()
    if STATE["t0"] is None:
        STATE["t0"] = now
        STATE["frames"] = 0
        return
    el = now - STATE["t0"]
    if el >= ARGS.bench:
        fps = STATE["frames"] / el
        g = FLOW.game
        line = (f"night={g.night} window={window.size[0]:.0f}x{window.size[1]:.0f} seconds={el:.1f} "
                f"frames={STATE['frames']} avg_fps={fps:.1f} shades={len(g.shades)} motes={len(g.motes)}")
        print("[bench]", line, flush=True)
        with open(ARGS.out, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        application.quit()


def input(key):  # noqa: A001 (ursina hook name)
    if key in ("escape", "p") and FLOW.mode in ("play", "pause"):
        FLOW.toggle_pause()
    if key == "enter" and FLOW.mode == "intro":
        FLOW.start_night()


if ARGS.night and not AUTO:
    FLOW.new_run(ARGS.night)
else:
    FLOW.menu()
app.run()
