# Validation and release checklist

## Current evidence

- Pipeline unit/integration tests: synthetic fixtures only; see actual pytest output.
- ARM/Thumb tools installed; ARM decoder synthetic instruction test passed.
- DeSmuME CLI 0.9.13 and Xvfb screenshot capture available on this machine.
- Real US ROM structure/hash verification: BLOCKED, no input ROM.
- Real ROM boot, v3 reproduction, timing/audio/Delta/save tests: NOT RUN.
- No gameplay patch is implemented or released. See `features/status.json`.

## Pipeline checks required for every PR

- Run `python -m pytest -q` and `python scripts/check_assets.py`.
- Wrong revision/hash, malformed headers, out-of-bounds and overlapping edits fail.
- Source ROM is unchanged and output overwrite is refused.
- BPS independently decodes to the exact target; CRC32s match.
- Review exact changed ranges against manifest rationale and protected assets.
- Do not count synthetic tests as real ROM or gameplay validation.

## Private emulator boot gate

After obtaining a verified US ROM, manually establish a stable, recognizable
SoulSilver screen in the pinned emulator. Capture a reference image on the same
256x384 virtual display, renderer, RTC and firmware settings. Inspect that it is
the game, not an emulator menu/error screen. Keep it in `private/`; do not commit
copyrighted screenshots. Record input ROM hash and reviewer in a private log.

`boot` requires this reviewed nonblank reference, runs a ROM copy in a fresh
sandbox, captures the full X display, compares dimensions and pixel error, and
writes `boot.json` only on success. A new output folder and emulator logs belong
to each run. Crashes, mismatches and blank references fail. No reference or ROM
means the check is blocked, never passed. The screenshot threshold is a smoke
oracle, not proof against all white screens, hangs or later gameplay defects.
Animated scenes may require a more deterministic movie/frame harness; do not
relax the threshold to hide failures. Desktop decorations/scaling must match.

Run stock and patched variants. Withhold manual inputs to detect auto-advance;
then test individual button presses. A boot test cannot verify this. Audio is
muted only in the automated boot harness, so music is explicitly **not validated**
by that check. Use normal audio for the gameplay and music checks below.

## Required manual/instrumented matrix, per feature and combined

Record emulator/version, ROM and patch hashes, save-copy hash, event boundaries,
frame counts, measured ratio, observations and pass/fail. Keep baseline and
candidate traces. Disable emulator speed cheats/frameskip. Repeat on Delta.

- [ ] New game, continue, save, reload; long play session without white screens.
- [ ] Wild encounter including special transitions; trainer intro and battle.
- [ ] Send-out/cry, voluntary switch, forced switch, double battle entrances.
- [ ] Instant text long/multiline messages, manual hold, single press, prompts,
      choices, status/damage/EXP/level-up dialogue; no callback deadlocks.
- [ ] HP/EXP progress unchanged at low/high values and level boundaries.
- [ ] Physical/special/status/multi-hit/charge/weather/recoil/failed attacks;
      animation setting on/off; keyframes and callbacks complete once.
- [ ] Faint on each side, recoil/double faint, Destiny Bond and victory/blackout.
- [ ] Exit after victory, escape, capture, trainer defeat and blackout.
- [ ] Music tempo/pitch and loop duration match baseline; cries/effects unaffected.
- [ ] Damage, RNG calls and outcomes match at controlled battle entry state.
      Equal wall-clock input is insufficient when event timing changes RNG frames.
- [ ] Encounters, party/PC data, inventory, progression flags and save integrity
      match; compare parsed fields, not only a whole-save hash (RTC changes it).
- [ ] Backup-copy EU→US migration and US→EU round trip, per save protocol.

Merge only after required checks for that feature pass. Infrastructure PRs can
be reviewed based on their own tests, but do not clear these gameplay gates.
