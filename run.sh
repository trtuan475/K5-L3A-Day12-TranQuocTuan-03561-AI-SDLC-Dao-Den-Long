#!/usr/bin/env bash
# Release launcher (macOS/Linux): creates a local venv on first run, installs Ursina, starts the game.
# Usage: ./run.sh [play.py args]   e.g. ./run.sh --night 2   or   ./run.sh --bench-mode --duration 30 --out bench.json
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -q -r requirements.txt
fi
exec .venv/bin/python play.py "$@"
