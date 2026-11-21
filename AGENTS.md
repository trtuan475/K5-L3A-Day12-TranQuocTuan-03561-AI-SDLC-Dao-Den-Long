# AGENTS.md: Đảo Đèn Lồng

Game 3D (Python + Ursina) for the AI-SDLC lab. Graded mostly by hidden headless tests (Test Contract), so **contract correctness beats features**.

## Commands
- Install: `python3 -m pip install -r requirements.txt` (Ursina is only needed for `play.py`)
- Tests: `python3 -m unittest discover -s tests` (must be green before you finish; a Stop hook enforces this)
- Evidence: `bash scripts/verify.sh phase-N` → regenerates `docs/proof/phase-N/` (see skill `verify`)
- Headless: `python3 headless.py --seed 1 --night 1 --ticks 600 --out /tmp/o.jsonl [--scenario f] [--inputs f]`
- Play: `python3 play.py` · Demo/screenshots: `python3 play.py --demo --shots <dir>`

## Layout
- `lantern_island/sim.py`: the ONLY gameplay logic. Stdlib only, deterministic, integer tick timers. Never import ursina here.
- `headless.py`: contract CLI (I/O only). `play.py`: rendering + input mapping only, it calls `Game.step()`.
- `game.contract.json`: tuning is loaded from here at runtime, so declared numbers == game numbers. Change numbers only here.
- `docs/notes/`: spec, assumptions (A1..), AC table, AI log, retro. `docs/lab/`: original lab handouts (read-only).

## Rules
- Requirements come from the PRD/ticket text the user pastes. Do not invent requirements; if ambiguous, add an assumption to `docs/notes/phase-N-spec.md`.
- Tick model: step k reads input of tick k, produces state k+1; events carry tick k+1. Snapshot 0 = after scenario, before input.
- Every new behaviour gets a test named after its AC. Fix the code, not the test, unless the test contradicts the spec (say why in the commit).
- Extra creative entities must be disabled in headless (must not change contract output).
- Never hand-edit files in `docs/proof/`; regenerate with `scripts/verify.sh`.
- Small commits, clear messages. No secrets/.env.
