"""Soak test (Ticket-04 part 2): python3 soak.py --seed 7 --nights 10 --out soak.json

Runs N nights headless in one process (Night 1 -> 2 -> 3 rotating), night i uses seed+i, random inputs from the seed:
new move direction every 30 ticks; per tick 5% jump, 3% dash, 2% pulse, 10% interact.
"""
import argparse
import gc
import json
import math
import os
import random
import subprocess
import sys
import time

from lantern_island.sim import Game


def rss_mb():
    """Current resident set size of this process in MB (Linux /proc, otherwise `ps`)."""
    try:
        with open("/proc/self/statm") as f:
            return round(int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 2 ** 20, 1)
    except OSError:
        out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True).stdout
        return round(int(out.strip()) / 1024, 1)


def play_night(game, rng, max_ticks):
    move = [0.0, 0.0]
    while not game.over and game.tick < max_ticks:
        if game.tick % 30 == 0:
            a = rng.uniform(0, 2 * math.pi)
            move = [round(math.cos(a), 4), round(math.sin(a), 4)]
        game.step({"move": move, "jump": rng.random() < 0.05, "dash": rng.random() < 0.03,
                   "pulse": rng.random() < 0.02, "interact": rng.random() < 0.10})
    return game.state if game.over else "timeout"


def soak(seed=7, nights=10, max_ticks=None):
    t0 = time.perf_counter()
    results, crashes, mem_start = [], 0, None
    for i in range(nights):
        night = 1 + i % 3
        try:
            game = Game(seed=seed + i, night=night)
            if mem_start is None:
                mem_start = rss_mb()  # after the first night is loaded
            limit = max_ticks or (int(game.t[f"night{night}_duration_s"]) * 60 + 10)
            results.append(play_night(game, random.Random(seed + i), limit))
        except Exception as e:  # noqa: BLE001 - a crash is a result, keep soaking
            crashes += 1
            results.append("crash")
            print(f"night {i + 1} crashed: {type(e).__name__}: {e}", file=sys.stderr)
        game = None  # reset before the next night
        gc.collect()
    return {"nights": nights, "crashes": crashes, "results": results, "mem_start_mb": mem_start,
            "mem_end_mb": rss_mb(), "duration_s": round(time.perf_counter() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nights", type=int, default=10)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rep = soak(a.seed, a.nights)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep))
    return 0 if rep["crashes"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
