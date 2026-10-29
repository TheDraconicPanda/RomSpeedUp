# V6.2 lower-screen menu correction

The player reported frantic flashing of a lower-screen button in V6.1. The
primary cause was rendering, not merely an accelerated blink timer: every other
field update omitted 2D sprites while OAM publication still ran. That publishes
an empty sprite frame. Consecutive screenshots show the menu's icons and touch
button alternating between visible and absent. V6.1 is superseded for this bug.

V6.2 restores the original 2D sprite draw callback at ARM9 offset 0xF6318 for
every update. It retains V6.1's unskipped resource publication and battle paths.
GPU and field 3D draw pacing remain scoped to the exact field callback. Faster
gameplay and the original physical sound cadence remain in place; Fast Forward
must be OFF. V6.2 is experimental and has not been tested on Delta.

## Separate menu animation timing

The original sprite constructor sets animation speed to `FX32_CONST(2)`
(0x2000), confirmed in both original instructions and the original-ROM replay.
The two field-menu sprite activation loops in overlay 27, at 0x0225B112 and
0x0225B1C0, now call a 16-byte wrapper that retains activation and sets speed to
`FX32_CONST(1)` (0x1000). These loops create the 15 standard field-menu sprites.
Halving this step compensates for the nominally doubled game update rate.
Actual wall-clock pace can vary in overloaded scenes. Touch polling and sprite
drawing continue every update; no input or publication callback is gated.

The wrapper occupies verified unused ARM9 padding at 0x0206278C and ends before
the scheduler's state at 0x020627A4. No executable or overlay RAM layout grows.
The original ARM7 and all sound assets remain byte-identical. Relative to V6.1,
the only NitroFS change is the two activation calls in overlay 27. Existing field
overlay changes remain identical to V6.1. Source identity, edit boundaries,
compression/readback, cartridge size and protected assets are checked by the
builder. The original ROM/save are never written in place.

## Reproduce and validate

```sh
.venv/bin/python scripts/build-v62.py private/original/user-original.nds \
  --out build/my-v62
.venv/bin/python scripts/validate-v61.py private/original/user-original.nds \
  build/my-v62/candidate.nds --out artifacts/my-v62-native.json
.venv/bin/python -m pytest -q
```

Native checks pass: 2160 clock, 56 context, two publication, 640 state, 112
movement and 565 cipher cases, plus 128 executions of the actual patched menu
activation call sites. These check preserved registers/stack, activation,
animation speed and unchanged surrounding sprite data. Pipeline: 51 passed.

`scripts/replay-field-ui.py` records each physical frame, menu entries, actual
sprite draws, per-sprite animation speed and a static menu-icon pixel hash.
Use a checkpoint created by the exact target after fresh boot and battery-save
import. Touch coordinates are relative to the lower screen (256x192).

Private 240-frame idle comparisons in DeSmuME 0.9.12 interpreter:

| Build | Menu updates | Full sprite draw calls | Static icon changes |
| --- | ---: | ---: | ---: |
| Original | 120 | 1788 | 0 |
| V6.1 | 240 | 1800 | 237 |
| V6.2 | 240 | 3600 | 0 |

The original capture window includes a partial sprite pass at its boundary,
hence 1788 rather than 1800. V6.1 renders about half of its updates; V6.2 draws all 15
sprites on all 240 updates. V6.2's 546-frame menu replay additionally opens the
Pokemon party menu by touch and returns to the field. Screenshots were reviewed.
All 15 field-menu sprites retain speed 0x1000, including after menu return.

The final target completed a trainer battle with Geodude/Machop send-outs
(4944 hardware frames, 2073 sprite-buffer and 2073 upload calls), then three
wild battles (6000 frames, 2515 buffer and 2515 upload calls). All returned to
the field with zero lost active-sprite uploads. Initial flags cleared while no
sprites are active are recorded separately (two per battle), as in V6.1.

Goldenrod movement/idle measured 526 game and 300 sound updates per 600 hardware
frames: **1.75x** nominal retail gameplay. Always drawing 2D sprites adds work;
this scene is slower than V6.1's 1.92x. The idle cave menu replay still runs
240 game/menu updates per 240 hardware frames, nominal 2x. These are interpreter
measurements, not Delta performance guarantees. City setup uses a disposable
normal-warp fixture with temporary code restored before capture.

In-game save/export and a separate fresh boot/import of the changed 512-KiB
battery save passed and returned to the saved cave position. Original ROM/save
hashes remain unchanged.

Private final-target evidence is under `artifacts/v61-ui/v62-final-*`. Earlier
research candidate 001 is not the deliverable: it used a quarter-stock animation
step before the original constructor's speed was checked. Only candidate 002,
with the correctly halved step, is packaged.

Original source SHA256:
`94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`.
V6.2 target SHA256:
`b5416f371ae5c8ec53bb5814be59d7e34a186975fdfe7c8d09e377f25e29eba5`.
Both ROMs are 134217728 bytes. Import a battery save and boot fresh; do not load
quick savestates from older builds. Delta, special battle modes and full-game
validation remain pending. Scene speed is approximate, not guaranteed 2x.


## Private delivery

[Download V6.2](https://drive.google.com/file/d/1yhKTLWud3EcjYUES-65WZ7DgsBMmd4yJ/view?usp=drivesdk).
Drive confirmed creation; separate metadata readback verified the V6.2 name,
60826897-byte size and authorized folder. ZIP SHA256:
`2cdb9ac297f0dfab8b8659eb81b129fa1da03af831c223d44f2c8ff41701ecb2`.
[Draft PR #10](https://github.com/TheDraconicPanda/RomSpeedUp/pull/10) is unmerged.
