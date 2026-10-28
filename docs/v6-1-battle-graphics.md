# V6.1 battle graphics correction

V6.1 replaces the rejected ROM-only V6. It starts from the exact original Europe
ROM and targets approximately 2x gameplay with original sound at normal speed.
**Delta Fast Forward must be OFF.** This is still an experimental build.

The player reported white sprite boxes in the first battle and a trainer where
a Pokemon should be in the second. V6's skipped graphics publication was unsafe.
The old smoke checks were insufficient and must not be cited as battle coverage.

## Cause and correction

`PokepicManager_DrawAll` (0x02008120) buffers image and palette changes. The two
buffer routines replace `needLoadImage` / `needLoadPltt` at manager offsets 0x331
and 0x332; they do not accumulate pending work. Skipping the subsequent graphics
callback lets another buffer update clear these flags before the data reaches
VRAM. A later draw then uses a stale trainer texture or incomplete sprite data.

The rejected V6 trainer replay recorded 2205 buffer calls but 1102 upload
callbacks and **22 lost image/palette updates for active sprites**. V6.1's
trainer replay records 2072 buffer and 2072 upload callbacks, with **zero lost
active-sprite updates**. Counts refer to operations, not distinct Pokemon.
Initialization also clears flags with no active sprites: two such cases occur
in both paths and are recorded separately, not counted as an active-sprite loss.

V6.1 leaves swap handling, main graphics publication and the VWait task queue
byte-identical to retail and runs them every update. The low-level GPU and sprite
draw gates and conditional VBlank wait apply only while `gSystem`'s callback is
exactly the verified field callback, 0x021E5901. Battle, battle exit, NULL/loading
and other callbacks always take their complete graphics and wait paths. The
field draw root retains alternate virtual-tick pacing to reduce city overhead.

Sound updates use the physical frame counter at the original one-per-two-VBlank
cadence, with bounded catch-up. ARM7, all sound assets and every NitroFS file
except the field overlay are byte-identical to the original. Equivalent cipher
optimization, ordinary movement parameters, tile endpoints and follower logic
are preserved. No user save is included or modified in place.

## Actual validation

DeSmuME 0.9.12 interpreter, target-created checkpoints after fresh target boot
and import of a disposable copy of the user's battery save:

| Scenario | Hardware frames | Observation |
| --- | ---: | --- |
| Trainer battle, Geodude then Machop | 4944 | 4757 game / 2416 sound updates; correct send-outs and return to field; zero active upload losses |
| Two following wild battles | 3000 | Both complete and return to field; zero active upload losses |
| Manual switch to Mordecai/Dragonite | 1362 | Correct player/opponent sprites after switch and attack; zero active upload losses |
| Goldenrod movement and idle | 600 | 575 game / 300 sound updates, versus nominal retail 300 game updates: 1.92x |
| In-game save, export, fresh boot/import | 1800 reload | Reloaded changed 512-KiB battery save and reached the cave successfully |

The controlled trainer replay used a temporary RAM repel fixture to avoid wild
encounters en route; it was cleared before the consecutive wild test. City setup
used a disposable normal-warp fixture whose temporary code was restored before
capture. Fixtures affect only temporary emulator copies, not the delivered ROM
or original save. Screenshots were reviewed, including the switched Dragonite.

Native instruction checks pass: 2160 clock cases, 56 callback-context cases,
two actual publication dispatches, 640 state comparisons, 112 movement cases,
565 cipher comparisons. Pipeline tests: 50 passed. The builder checks exact
source identity, compression roundtrip, executable edit boundaries, protected
files/metadata, memory layout and field-overlay readback.

Private evidence: `artifacts/v61/{old-trainer-complete,scoped-trainer,
scoped-consecutive-wild,scoped-switch,scoped-city,scoped-save,reload-scoped-final}`
and `artifacts/v61/native-scoped.json`. Generated evidence is not tracked.

## Reproduce

```sh
.venv/bin/python scripts/build-v61.py private/original/user-original.nds \
  --out build/my-v61
.venv/bin/python scripts/validate-v61.py private/original/user-original.nds \
  build/my-v61/candidate.nds --out artifacts/my-v61-native.json
.venv/bin/python -m pytest -q
```

For replay, use `scripts/replay-sprite-uploads.py --help`, target-created
checkpoints, the private action sequences and `--require-no-active-losses`.
`--min-battles` and `--end-in-field` can assert scenario completion. Do not reuse
old executable savestates to validate a new ROM.

Source SHA256:
`94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`.
V6.1 SHA256:
`81d63f41e1c5f29a03a30fa1417222ffdb956bf4a201c846df4a26197ae855f1`.
Both are 134217728 bytes. The user's original ROM and save hashes are unchanged.

Delta, double battles, unusual forms, link battles and full-game progression
remain untested. Timing varies with scene load; 2x is a target, not a guarantee.
Normal audio assets/cadence are verified; Delta listening is still required.
Import a battery save and boot fresh. Avoid quick savestates from V6 or earlier.


## Private delivery

Drive confirmed the new ZIP and separate readback verified its name, 60826591
bytes and authorized folder. [V6.1 download](https://drive.google.com/file/d/1e4baq4XPcpjy360KmBkaDPusq3iuPJ-5/view?usp=drivesdk).
ZIP SHA256: `a182c3fe7c4fffbdcb3edf90271c217819251cda5b5044e550d75f4ebf437e28`.
The previous V6 file is marked WITHDRAWN_BROKEN_BATTLE_GRAPHICS; do not use it.
