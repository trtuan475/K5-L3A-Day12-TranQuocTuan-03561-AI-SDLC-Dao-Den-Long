"""Local leaderboard (Ticket-04 part 3). Stdlib only so it is testable headless.

Entry: name, score (total of won nights), nights_won (0-3), achieved_at (ISO 8601 with timezone), seed.
Top 10, score desc; ties: earlier achieved_at first (then insertion order).
"""
import datetime
import json
import os
import re

DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".dao_den_long_leaderboard.json")
NAME_RE = re.compile(r"^\w{3,12}$")  # [A-Za-z0-9_] + Vietnamese letters with diacritics (bonus)
TOP = 10


def path():
    return os.environ.get("DDL_LEADERBOARD", DEFAULT_PATH)


def valid_name(name):
    return isinstance(name, str) and bool(NAME_RE.match(name)) and "\n" not in name


def load(p=None):
    try:
        with open(p or path(), encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", []) if isinstance(data, dict) else []
        return [e for e in entries if isinstance(e, dict) and "score" in e]
    except (OSError, ValueError):
        return []


def _sorted(entries):
    return sorted(entries, key=lambda e: (-int(e["score"]), e.get("achieved_at", "")))[:TOP]


def add(name, score, nights_won, seed, p=None, now=None):
    if not valid_name(name):
        raise ValueError("Tên phải dài 3-12 ký tự: chữ, số hoặc _")
    if not 0 <= int(nights_won) <= 3:
        raise ValueError("nights_won must be 0..3")
    now = now or datetime.datetime.now().astimezone()
    entry = {"name": name, "score": int(score), "nights_won": int(nights_won),
             "achieved_at": now.isoformat(timespec="seconds"), "seed": int(seed)}
    entries = _sorted(load(p) + [entry])
    target = p or path()
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, target)  # atomic: survives crashes mid-write
    return entry, entries


def export(out, p=None):
    entries = _sorted(load(p))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, ensure_ascii=False, indent=1)
    return entries
