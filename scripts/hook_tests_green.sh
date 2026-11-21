#!/usr/bin/env bash
# Claude Code Stop hook: refuse to finish while tests are red (exit 2 sends stderr back to the agent).
cd "$(dirname "$0")/.."
if ! OUT=$(python3 -m unittest discover -s tests 2>&1); then
  echo "Tests are RED - fix them before finishing:" >&2
  echo "$OUT" | tail -25 >&2
  exit 2
fi
exit 0
