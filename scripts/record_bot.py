"""Record the bot playing the default Night 1 into a contract inputs.json (only changed fields per frame).

python3 scripts/record_bot.py --seed 1 --out docs/proof/phase-1/bot_inputs_seed1.json
The file is then replayed by headless.py; the bot itself never writes results.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lantern_island.autoplay import Bot  # noqa: E402
from lantern_island.sim import Game  # noqa: E402


def record(seed, max_ticks=18000):
    g, bot, frames, last = Game(seed=seed), Bot(), [], {}
    while g.state == "playing" and g.tick < max_ticks:
        f = bot.frame(g)
        diff = {k: v for k, v in f.items() if last.get(k) != v}
        if diff:
            frames.append({"tick": g.tick, **diff})
            last.update(diff)
        g.step(f)
    return {"frames": frames}, g


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data, g = record(a.seed)
    with open(a.out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"seed={a.seed} bot finished: state={g.state} tick={g.tick} score={g.score} frames={len(data['frames'])}")
