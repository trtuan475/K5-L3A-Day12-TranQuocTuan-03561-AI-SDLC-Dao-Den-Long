---
name: verify
description: Run all checks for the current phase and regenerate evidence in docs/proof/<phase>/ (tests, headless scenarios, bot playthroughs of nights 1-3, determinism per night, exit codes, 30 s timing, FPS, screenshots). Use before tagging a phase or after changing sim/headless/play code.
---

1. Commit the code first (the report records the commit hash), then run `bash scripts/verify.sh phase-N`. It exits non-zero if any check fails.
2. If it fails: read `docs/proof/phase-N/REPORT.md` and `unittest.log`, fix the **code** (not the expected values), rerun.
   Off-by-one failures: re-check the tick model in AGENTS.md before changing anything.
3. Visual/UI requirements (HUD, palette, menus, pause): `python3 play.py --demo --shots docs/proof/phase-N/shots` (needs a display; quits by itself). Open 2-3 images and actually look at them.
4. Performance: `python3 play.py --bench 30 --night 3 --out docs/proof/phase-N/fps.txt` (1280x720, must be >= 30 FPS).
5. Never edit files under `docs/proof/` by hand. Commit the regenerated folder, then tag.
6. Update the requirement → evidence table in `docs/proof/phase-N/TRACE.md`; mark anything unverified as such.
