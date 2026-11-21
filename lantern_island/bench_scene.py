"""Ticket-04 standard benchmark scene (same for everyone): Night 1, 200 wandering shades spread over the island,
100 motes, L1-L3 lit with fuel 100, Mây idle at (0,0,0). Spawning/damage/pickups/fuel decay/end are off (Game(bench=True)).
"""
import math
import random

from .sim import Game

ISLAND_R = 40.0


def _spread(rng, n, rmin, rmax):
    pts = []
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(rmin * rmin, rmax * rmax))  # uniform over the area
        pts.append([round(r * math.cos(a), 3), 0.0, round(r * math.sin(a), 3)])
    return pts


def bench_scenario(seed=42):
    rng = random.Random(seed)
    return {
        "player": {"pos": [0, 0, 0]},
        "random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
        "motes": _spread(rng, 100, 2.0, ISLAND_R - 2.0),
        "shades": [{"id": f"S{i + 1}", "pos": p, "state": "wander"} for i, p in enumerate(_spread(rng, 200, 3.0, ISLAND_R - 1.0))],
        "drifters": [], "charms": [],
        "lanterns": [{"id": f"L{i}", "lit": True, "fuel": 100} for i in (1, 2, 3)],
    }


def bench_game(seed=42):
    return Game(seed=seed, night=1, scenario=bench_scenario(seed), bench=True)
