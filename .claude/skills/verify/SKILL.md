---
name: verify
description: Run all checks for the current phase and regenerate evidence in docs/proof/<phase>/ (tests, headless scenarios, bot playthroughs, determinism, exit codes, timing). Use before tagging a phase or after changing sim/headless code.
---

1. Run `bash scripts/verify.sh phase-N` (N = current phase). It exits non-zero if any check fails.
2. If it fails: read `docs/proof/phase-N/REPORT.md` and `unittest.log`, fix the **code** (not the expected values), rerun.
3. For visual requirements (HUD, lighting), regenerate screenshots: `python3 play.py --demo --shots docs/proof/phase-N/shots` (needs a display; quits by itself).
4. Never edit files under `docs/proof/` by hand. Commit the regenerated folder together with the code it verifies, then tag.
5. Update the requirement → evidence table in `docs/proof/phase-N/TRACE.md` if requirements changed.
