"""Headless runner (Test Contract v1.1).

python3 headless.py --seed 1 --night 1 [--scenario s.json] [--inputs i.json] --ticks N --out o.jsonl [--snapshot-every 10]
Exit 0 on success, 2 on bad arguments / malformed inputs or scenario, 1 on other errors.
"""
import argparse
import json
import sys

from lantern_island.sim import Game, ScenarioError, validate_inputs


def _load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ScenarioError(f"{what}: cannot read {path}: {e}")


def _dump(f, obj):
    f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def run(args):
    scenario = _load_json(args.scenario, "scenario") if args.scenario else None
    frames = validate_inputs(_load_json(args.inputs, "inputs")) if args.inputs else {}
    if args.ticks < 0 or args.snapshot_every < 1:
        raise ScenarioError("--ticks must be >= 0 and --snapshot-every >= 1")
    game = Game(seed=args.seed, night=args.night, scenario=scenario)
    with open(args.out, "w", encoding="utf-8") as f:
        _dump(f, {"type": "event", "tick": 0, "name": "night_start", "data": {"night": game.night}})
        _dump(f, game.snapshot())
        last_snap = 0
        for k in range(args.ticks):
            for (tick, name, data) in game.step(frames.get(k)):
                _dump(f, {"type": "event", "tick": tick, "name": name, "data": data})
            if game.tick % args.snapshot_every == 0:
                _dump(f, game.snapshot())
                last_snap = game.tick
            if game.over:
                break
        if last_snap != game.tick:
            _dump(f, game.snapshot())
        _dump(f, {"type": "end", "ticks": game.tick, "state": game.state, "score": game.score})


def main(argv=None):
    p = argparse.ArgumentParser(description="Dao Den Long headless runner")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--night", type=int, required=True)
    p.add_argument("--scenario")
    p.add_argument("--inputs")
    p.add_argument("--ticks", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--snapshot-every", type=int, default=10)
    args = p.parse_args(argv)  # argparse exits with code 2 on bad args
    try:
        run(args)
    except ScenarioError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
