# AGENTS.md: Đảo Đèn Lồng

Game 3D (Python + Ursina) for the AI-SDLC lab. Graded mostly by hidden headless tests (Test Contract **v1.1**), so **contract correctness beats features**.

## Commands
- Install: `python3 -m pip install -r requirements.txt` (Ursina is only needed for `play.py`)
- Tests: `python3 -m unittest discover -s tests` (must be green before you finish; a Stop hook enforces this)
- Evidence: `bash scripts/verify.sh phase-N` → regenerates `docs/proof/phase-N/` (see skill `verify`)
- Headless: `python3 headless.py --seed 1 --night 1|2|3 --ticks 600 --out /tmp/o.jsonl [--scenario f] [--inputs f]`
- Play: `python3 play.py [--night N]` · Screenshots: `python3 play.py --demo --shots <dir>` · FPS: `python3 play.py --bench 30 --night 3 --out <file>`
- Sounds are generated: `python3 scripts/gen_sfx.py` (assets/sfx, self-made)

## Layout
- `lantern_island/sim.py`: the ONLY gameplay logic. Stdlib only, deterministic, integer tick timers. Never import ursina here.
  `Game.step()` follows the Ticket-02 order (pause → counters → move/fall → pickups → interact → safe zones → pulse →
  shades/drifters → collisions → spawns → win/lose). Keep that order; tests depend on it.
- `lantern_island/maps.py`: standard maps of the 3 nights (angles: z = r·sin a). `autoplay.py`: evidence bot only.
- `headless.py`: contract CLI (I/O only). `play.py`: rendering, menus, HUD, audio. It calls `Game.step()` only.
- `game.contract.json`: standard tuning (Ticket-02 part 1), loaded at runtime. Do not change these numbers.
- `docs/notes/phase-N-spec.md`: assumptions (A1.., B1..) + AC table. `docs/lab/`: original lab handouts (read-only).

## Rules
- Requirements come from the PRD/ticket text the user pastes. Do not invent requirements; if ambiguous, add an assumption to the current phase spec.
- Tick model: step k reads input of tick k, produces state k+1; events carry tick k+1. A timer of N ticks set at tick p
  is active on ticks p..p+N-1 (cooldown ready again at p+N). Check this before "fixing" off-by-one test failures.
- Every new behaviour gets a test named after its AC (`P2-x`). Fix the code, not the test, unless the test contradicts the spec (say why).
- Scenario helpers must clear ALL default entities (motes, shades, drifters, charms, wind) or tests pick up map defaults.
- Extra creative/visual entities live in `play.py` only (must not change headless output).
- Never hand-edit files in `docs/proof/`; regenerate with `scripts/verify.sh`.
- Small commits, clear messages. No secrets/.env.
