"""Standard maps (Ticket-02 part 2). Angles: CCW from +X, point = (r cos a, y, r sin a) (assumption B2)."""
import math


def polar(r, deg, y=0.0, cx=0.0):
    a = math.radians(deg)
    return [round(cx + r * math.cos(a), 6), float(y), round(r * math.sin(a), 6)]


def _ground_n1(x, z):
    return 0.0 if math.hypot(x, z) <= 40.0 else None


def _ground_n2(x, z):
    if math.hypot(x, z) <= 28.0 or math.hypot(x - 70.0, z) <= 28.0:
        return 0.0
    if 26.0 <= x <= 44.0 and -2.0 <= z <= 2.0:
        return 0.0
    return None


RAMPS_N3 = (30.0, 150.0)


def _ground_n3(x, z):
    r = math.hypot(x, z)
    if r > 45.0:
        return None
    if r < 2.0:
        return 14.0  # bell tower (6 m tier + 8 m tall): acts as a wall, not climbable
    if r < 8.0:
        return 6.0
    if z > 0 and 12.0 <= r <= 24.0:
        return 3.0
    for deg in RAMPS_N3:
        ux, uz = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        along = x * ux + z * uz
        perp = abs(-x * uz + z * ux)
        if perp <= 1.5 and 24.0 <= along <= 30.0:
            return 3.0 * (30.0 - along) / 6.0
    return 0.0


def _unit(dx, dz):
    d = math.hypot(dx, dz)
    return (dx / d, dz / d)


NIGHTS = {
    1: dict(
        name="Đảo Bến", ground=_ground_n1, duration_s=300, start=[0.0, 0.0, 0.0],
        lanterns=[[0, 0, 25], [23.8, 0, 7.7], [14.7, 0, -20.2], [-14.7, 0, -20.2], [-23.8, 0, 7.7]],
        mote_points=[polar(12, 45 * i) for i in range(8)] + [polar(33, 22.5 * i) for i in range(16)],
        shade_points=[polar(37, 15 + 30 * i) for i in range(12)],
        shade_every=480, shade_max=6, shade_speed=4.0,
        pads=[], charms=[], drifters=False, wind=False,
    ),
    2: dict(
        name="Đảo Cau", ground=_ground_n2, duration_s=330, start=[0.0, 0.0, 0.0],
        lanterns=[[0, 0, 20], [17, 0, -10], [-17, 0, -10], [70, 0, 20], [87, 0, -10], [53, 0, -10]],
        mote_points=[p for cx in (0.0, 70.0) for p in
                     [polar(10, 90 * i, cx=cx) for i in range(4)] + [polar(22, 45 * i, cx=cx) for i in range(8)]],
        shade_points=[polar(26, 22.5 + 45 * i, cx=cx) for cx in (0.0, 70.0) for i in range(8)],
        shade_every=420, shade_max=8, shade_speed=4.0,
        pads=[dict(pos=[20, 0, 18], vy=14.0, h=[24 * c for c in _unit(70 - 20, 0 - 18)]),
              dict(pos=[50, 0, -18], vy=14.0, h=[24 * c for c in _unit(0 - 50, 0 + 18)])],
        charms=[[35, 0, 0]], drifters=True, wind=False,
    ),
    3: dict(
        name="Đảo Chuông", ground=_ground_n3, duration_s=360, start=[0.0, 0.0, -30.0],
        lanterns=[[0, 6, 6], [18, 3, 10], [-18, 3, 10], [35, 0, -10], [-35, 0, -10], [20, 0, -35], [-20, 0, -35]],
        mote_points=[polar(34, 20 * i, 0) for i in range(18)] + [polar(18, 20 * i, 3) for i in range(1, 9)]
                    + [polar(5, a, 6) for a in (45, 135, 225, 315)],
        shade_points=[polar(43, 22.5 * i) for i in range(16)],
        shade_every=360, shade_max=10, shade_speed=4.5,
        pads=[dict(pos=[0, 3, 13], vy=12.0, h=[0.0, -8.0])],
        charms=[[30, 0, 25], [-30, 0, 25]], drifters=True, wind=True,
    ),
}
