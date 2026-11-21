"""Dao Den Long - 3D build (Ursina). All gameplay comes from lantern_island.sim (same core as headless).

python3 play.py                 play (seed 1)
python3 play.py --seed 5
python3 play.py --demo --shots docs/proof/phase-1/shots   bot plays, saves screenshots, quits
"""
import argparse
import math
import os
import time as utime

from ursina import (Entity, Text, Ursina, Vec3, application, camera, color, held_keys, mouse, scene,
                    window, destroy)
from ursina.models.procedural.cone import Cone
from ursina.models.procedural.cylinder import Cylinder

from lantern_island.autoplay import Bot
from lantern_island.sim import DT, ISLAND_RADIUS, Game

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--demo", action="store_true", help="bot plays (for screenshots/video)")
ap.add_argument("--shots", help="directory for demo screenshots")
ARGS, _ = ap.parse_known_args()

def mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return color.rgba(*(a[i] + (b[i] - a[i]) * k for i in range(4)))


WARM = color.rgb(1.0, 0.62, 0.2)
GOLD = color.rgb(1.0, 0.85, 0.35)
INK = color.rgb(0.16, 0.05, 0.24)
INK_STUN = color.rgb(0.62, 0.52, 0.85)
NIGHT_GROUND = color.rgb(0.13, 0.12, 0.2)
LIT_GROUND = color.rgb(0.32, 0.4, 0.28)

app = Ursina(title="Dao Den Long", borderless=False, development_mode=False)
window.color = color.rgb(0.05, 0.04, 0.1)
window.fps_counter.enabled = False
window.exit_button.visible = False
scene.fog_color = color.rgb(0.08, 0.05, 0.14)
scene.fog_density = (25, 90)


class View:
    """Builds entities for a Game and syncs them every frame. Rebuilt on restart."""

    def __init__(self, game):
        self.g = game
        self.root = Entity()
        self.ground = Entity(parent=self.root, model=Cylinder(resolution=64, radius=ISLAND_RADIUS, height=1),
                             y=-1, color=NIGHT_GROUND, texture="grass", texture_scale=(8, 8))
        # a few fixed rocks/bushes for depth cues (decor only, not part of the sim)
        for i in range(40):
            a, r = i * 2.39996, 6 + (i * 7.3) % 32
            Entity(parent=self.root, model="sphere", color=color.rgb(0.16, 0.2, 0.22),
                   position=(math.sin(a) * r, 0.2, math.cos(a) * r), scale=(0.9 + i % 3 * 0.4, 0.6, 0.9))
        Entity(parent=self.root, model=Cylinder(resolution=64, radius=ISLAND_RADIUS + 1.5, height=6), y=-7.2,
               color=color.rgb(0.09, 0.08, 0.13))
        # sea of clouds
        for i in range(24):
            a = i / 24 * math.tau
            Entity(parent=self.root, model="sphere", color=color.rgba(0.5, 0.45, 0.7, 0.25),
                   position=(math.sin(a) * 52, -4, math.cos(a) * 52), scale=(16, 4, 12))
        self.lanterns = {}
        for L in game.lanterns:
            base = Entity(parent=self.root, position=Vec3(*L["pos"]))
            Entity(parent=base, model="cube", color=color.rgb(0.25, 0.18, 0.12), scale=(0.25, 3.2, 0.25), y=1.6)
            Entity(parent=base, model="cube", color=color.rgb(0.25, 0.18, 0.12), scale=(1.2, 0.15, 0.15), y=3.2)
            lamp = Entity(parent=base, model="cube", scale=(0.8, 1.0, 0.8), y=2.6, x=0.5, color=color.gray)
            halo = Entity(parent=base, model="sphere", y=2.6, x=0.5, scale=3, color=color.rgba(1, 0.6, 0.2, 0.18),
                          enabled=False)
            safe = Entity(parent=base, model=Cylinder(resolution=48, radius=game.t["safe_radius"], height=0.02),
                          y=0.02, color=color.rgba(1, 0.65, 0.25, 0.18), enabled=False)
            label = Text(parent=base, text=L["id"], billboard=True, scale=8, y=4.2, origin=(0, 0), color=GOLD)
            self.lanterns[L["id"]] = (lamp, halo, safe, label)
        # Moon: boy/girl lantern keeper with a non la (conical hat) and a small lantern
        self.player = Entity(parent=self.root)
        Entity(parent=self.player, model="cube", color=color.rgb(0.25, 0.45, 0.7), scale=(0.7, 0.9, 0.5), y=0.55)
        Entity(parent=self.player, model="sphere", color=color.rgb(0.95, 0.8, 0.65), scale=0.55, y=1.25)
        Entity(parent=self.player, model=Cone(resolution=24, radius=0.75, height=0.45), color=color.rgb(0.9, 0.8, 0.5),
               y=1.42)
        Entity(parent=self.player, model="cube", color=color.rgb(0.3, 0.2, 0.1), scale=(0.03, 0.5, 0.03),
               position=(0.6, 1.2, 0))
        self.p_lamp = Entity(parent=self.player, model="sphere", color=WARM, scale=0.22, position=(0.6, 0.9, 0))
        self.p_glow = Entity(parent=self.player, model="sphere", color=color.rgba(1, 0.7, 0.3, 0.12), scale=2,
                             position=(0.6, 0.9, 0))
        self.motes = {}
        self.shades = {}
        self.pulse_fx = Entity(parent=self.root, model="sphere", color=color.rgba(1, 0.85, 0.4, 0.25), enabled=False)
        self.pulse_t = 0.0

    def sync(self, t_anim):
        g = self.g
        lit = sum(L["lit"] for L in g.lanterns)
        self.ground.color = mix(NIGHT_GROUND, LIT_GROUND, lit / len(g.lanterns))
        scene.fog_density = (25 + lit * 8, 90 + lit * 15)
        for L in g.lanterns:
            lamp, halo, safe, label = self.lanterns[L["id"]]
            lamp.color = WARM if L["lit"] else mix(color.gray, WARM, L["deposited"] / g.t["lantern_cost"] * 0.5)
            halo.enabled = safe.enabled = L["lit"]
            label.text = f"{L['id']} {L['deposited']}/{g.t['lantern_cost']}" if not L["lit"] else L["id"]
        p = g.player["pos"]
        self.player.position = Vec3(*p)
        mx, mz = g.inputs.move
        if mx or mz:
            th = math.radians(g.inputs.cam_yaw_deg)
            wx, wz = mx * math.cos(th) + mz * math.sin(th), -mx * math.sin(th) + mz * math.cos(th)
            self.player.rotation_y = math.degrees(math.atan2(wx, wz))
        self.player.visible = not (g.invuln_ticks > 0 and int(t_anim * 12) % 2 == 0)
        self.p_glow.scale = 1.5 + g.player["carried"] * 0.25
        # motes
        ids = set()
        for m in g.motes:
            ids.add(m["id"])
            e = self.motes.get(m["id"])
            if e is None:
                e = self.motes[m["id"]] = Entity(parent=self.root, model="sphere", color=GOLD, scale=0.3)
                Entity(parent=e, model="sphere", color=color.rgba(1, 0.9, 0.4, 0.2), scale=3)
            ph = hash(m["id"]) % 100 / 10
            e.position = Vec3(m["pos"][0], 0.9 + 0.25 * math.sin(t_anim * 2.5 + ph), m["pos"][2])
        for k in [k for k in self.motes if k not in ids]:
            destroy(self.motes.pop(k))
        # shades
        for s in g.shades:
            e = self.shades.get(s["id"])
            if e is None:
                e = self.shades[s["id"]] = Entity(parent=self.root, model="sphere", scale=(1.6, 1.9, 1.6))
                Entity(parent=e, model="sphere", color=color.rgb(0.8, 0.3, 1.0), scale=0.12, position=(-0.15, 0.15, 0.45))
                Entity(parent=e, model="sphere", color=color.rgb(0.8, 0.3, 1.0), scale=0.12, position=(0.15, 0.15, 0.45))
            e.position = Vec3(*s["pos"]) + Vec3(0, 0.15 * math.sin(t_anim * 3 + len(s["id"])), 0)
            e.color = INK_STUN if s["state"] == "stunned" else INK
            e.look_at_2d(Vec3(p[0], 0, p[2]), "y")
        # pulse fx
        if self.pulse_t > 0:
            self.pulse_t -= 1 / 60
            k = 1 - self.pulse_t / 0.35
            self.pulse_fx.enabled = True
            self.pulse_fx.position = Vec3(p[0], 0.8, p[2])
            self.pulse_fx.scale = 2 * g.t["pulse_radius"] * k
        else:
            self.pulse_fx.enabled = False

    def destroy(self):
        destroy(self.root)


hud = Text(position=window.top_left + Vec3(0.02, -0.02, 0), scale=1.1, color=color.rgb(1, 0.9, 0.75))
banner = Text(origin=(0, 0), scale=2.4, y=0.12, color=GOLD)
helptext = Text(text="WASD di chuyển · Chuột/mũi tên trái-phải xoay camera · Space nhảy · E nạp đèn · F/Click tỏa sáng · R chơi lại",
                position=window.bottom_left + Vec3(0.02, 0.04, 0), scale=0.8, color=color.rgb(0.8, 0.75, 0.9))

state = {"game": None, "view": None, "acc": 0.0, "yaw": 0.0, "anim": 0.0, "bot": None, "shots": [], "pulse_btn": False}


def new_game():
    if state["view"]:
        state["view"].destroy()
    g = Game(seed=ARGS.seed)
    state.update(game=g, view=View(g), acc=0.0, bot=Bot() if ARGS.demo else None)
    banner.text = ""


def human_frame():
    mx = held_keys["d"] - held_keys["a"]
    mz = held_keys["w"] - held_keys["s"]
    return {"move": [mx, mz], "cam_yaw_deg": state["yaw"], "jump": bool(held_keys["space"]),
            "interact": bool(held_keys["e"]), "pulse": bool(held_keys["f"] or held_keys["left mouse"])}


def update():
    g, v = state["game"], state["view"]
    dt = 4 * DT if ARGS.shots else min(utime.dt, 0.1)  # evidence mode: fixed 4 ticks per frame
    state["anim"] += dt
    if not ARGS.demo:
        state["yaw"] += mouse.velocity[0] * 180 + (held_keys["right arrow"] - held_keys["left arrow"]) * 90 * dt
    state["acc"] += dt
    while state["acc"] >= DT and g.state == "playing":
        state["acc"] -= DT
        f = state["bot"].frame(g) if state["bot"] else human_frame()
        if state["bot"]:
            if any(f["move"]):  # camera slowly follows the bot's heading
                state["yaw"] += ((math.degrees(math.atan2(*f["move"])) - state["yaw"] + 180) % 360 - 180) * 0.02
        for _, name, _d in g.step(f):
            if name == "pulse":
                v.pulse_t = 0.35
    v.sync(state["anim"])
    # camera behind the player along cam yaw
    th = math.radians(state["yaw"])
    p = Vec3(*g.player["pos"])
    camera.position = p + Vec3(-math.sin(th) * 15, 10, -math.cos(th) * 15)
    camera.rotation = Vec3(math.degrees(math.atan2(10 - 1.2, 15)), state["yaw"], 0)  # pitch down, no roll
    lit = sum(L["lit"] for L in g.lanterns)
    t = g.t
    hud.text = (f"Đêm 1 – Đảo Bến\n"
                f"Đèn Lồng Lớn: {lit}/{len(g.lanterns)}\n"
                f"Đom đóm đang mang: {g.player['carried']}/{t['carry_capacity']}\n"
                f"Ngọn lửa: {'* ' * g.player['flames']}({g.player['flames']}/{t['flames']})\n"
                f"Bình minh sau: {int(g.time_left_s) // 60}:{int(g.time_left_s) % 60:02d}\n"
                f"Hồi tỏa sáng: {'sẵn sàng' if g.pulse_cd_ticks == 0 else f'{g.pulse_cd_ticks / 60:.1f}s'}\n"
                f"Điểm: {g.score}")
    if g.state == "won":
        banner.text = f"Đảo đã sáng lại!  THẮNG\nĐiểm: {g.score}\nNhấn R để chơi lại"
    elif g.state == "lost":
        why = "Hết ngọn lửa" if g.result_reason == "no_flames" else "Bình minh đã tới"
        banner.text = f"{why}  THUA\nĐiểm: {g.score}\nNhấn R để chơi lại"
    if ARGS.demo and ARGS.shots:
        demo_shots(g)


def demo_shots(g):
    os.makedirs(ARGS.shots, exist_ok=True)
    plan = [(5, "01_start"), (900, "02_playing"), (1800, "03_lanterns_lit")]
    for tick, name in plan:
        if g.tick >= tick and name not in state["shots"]:
            state["shots"].append(name)
            r = app.screenshot(namePrefix=os.path.join(ARGS.shots, name + ".png"), defaultFilename=False)
            print(f"[demo] tick={g.tick} state={g.state} shot={name} -> {r}", flush=True)
    if g.state != "playing":
        state["acc"] = 0
        state.setdefault("end_frames", 0)
        state["end_frames"] += 1
        if state["end_frames"] == 30:
            r = app.screenshot(namePrefix=os.path.join(ARGS.shots, f"04_{g.state}.png"), defaultFilename=False)
            print(f"[demo] end tick={g.tick} state={g.state} score={g.score} shot -> {r}", flush=True)
        if state["end_frames"] > 40:
            application.quit()


def input(key):  # noqa: A001 (ursina hook name)
    if key == "r":
        new_game()
    if key == "escape":
        mouse.locked = not mouse.locked


new_game()
if not ARGS.demo:
    mouse.locked = True
app.run()
