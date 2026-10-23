# V3 → v4: partial experimental candidate

**This is not completed v4.** The user clarified that all unchanged behavior means
unchanged from the supplied European v3, including its existing frame-rate/text
patches. No clean USA ROM is needed to build against that baseline. The originals
are research inputs only. No original ROM or save has been modified.

## Current behavior

| Requirement | Candidate implementation | Evidence / remaining limitation |
| --- | --- | --- |
| Wild transition faster, visible | Ordinary effect IDs 0–5: interpolation durations reduced in overlay 120 | Tested effect retained every group and took 77 emulated frames vs 80 in v3; modest improvement, not 1.5x overall. Other ordinary effects and special/legendary paths are not covered by the replay. Special effects remain v3. |
| Trainer introduction unchanged | No trainer transition handlers changed | Static dispatch/code/asset preservation; trainer battle not replayed |
| Entrance unchanged | No entrance handler edits | Same Pokémon reached command menu; detailed entrance timing unmeasured |
| Instant text/manual advance | Existing v3 ARM9 retained exactly | Encounter/EXP messages waited for input in the scenario; full text/prompt matrix unrun |
| HP unchanged | No HP handler edits | Same 51 callbacks and 50-frame span, same state counts |
| EXP unchanged | No EXP handler edits | Same 9 callbacks and 8-frame span; 27 EXP observed in both |
| Attack approximately 1.5x v3 | **NOT IMPLEMENTED** | Ember remains 35 callbacks over a 36-frame span, exactly v3 |
| Faint approximately 1.5x | Visual shadow/sprite/crop steps 8 → 12 pixels | Quantized by sprite size. Tested Zubat: shadow callbacks 3 → 2, sprite callbacks 8 → 6. Cry wait remains 70 callbacks. Entire faint sequence is consequently not 1.5x end-to-end. |
| Switching unchanged | No switch handler edits | Voluntary/forced switching not replayed |
| Battle exit faster, visible | Battle-end palette wait 1 → 0 | Palette-wait state visits 16 → 9; callback span 16 → 9 emulated frames. Music fade call/parameters and overworld restoration fade remain v3. Special exit/blackout paths unrun. |

No new global frame/scheduler/audio acceleration was introduced. Music assets,
ARM7, v3's ARM9, Pokémon data and all unselected NitroFS files remain byte-identical.
This is structural evidence, not a substitute for audible music/cry regression
or all possible battle/progression/save scenarios.

## Why attack timing is still blocked

The actual attack dispatcher is overlay 12's `ov12_0225FD14`. Its animation wait
states call overlay 7's `ov07_0221C394`, which updates an animation-script function.
Visual effects also create independent tasks through `ov07_0221BE68` onto the
shared main SysTask queue. Updating the interpreter more often or reducing its
waits alone does not accelerate all sprites, particles and callbacks consistently.
Accelerating the shared queue or main loop would violate the selective requirement.

A correct 3/2 implementation needs scoped ownership/timing of the move's visual
tasks, safe handling of completion/destruction and a distinction between attacks
and secondary effects used by entrances/switches. That hook is not implemented or
validated here. No global toggle, shortened unrelated delay, skipped keyframe or
script-only speed change has been substituted. This is unresolved engineering,
not a claim the feature is impossible or that the project is complete.

## Reproducible build

Input: exact user-supplied v3, SHA256
`ee605e633c6fda51b36fdd396a1c4573dbab40dd020ede1d06a4afea2efc30cb`.

The guarded spec is `features/v4-experimental.json`. It edits only nine bytes
across overlays 12 and 120 after decompression. RAM size/addresses, BSS and static
initializer positions are preserved. Both recompressed streams fit their original
slots at exactly the original sizes (162460 and 3740 bytes). The general builder
refuses overflow/nonpadding overwrite and checks its container/decompression
roundtrip and all unselected assets before producing a candidate.

```sh
source .venv/bin/activate
romspeedup verify private/v3/europe-v3.nds --profile profiles/europe-v3.json
python scripts/build-v4-candidate.py private/v3/europe-v3.nds \
  --feature faint-motion --feature battle-exit-palette \
  --feature ordinary-wild-transition --out build/my-new-candidate --bps
```

Use a fresh output folder. For isolated candidates, pass one `--feature` only.
The output is explicitly labeled partial/experimental; no release is approved.
Combined ROM SHA256:
`cdf7059ea67936816d724df8d5336e1b5c364a5d41acef7e4e5f8280db6e9e92`.
The 122607-byte BPS independently decoded back to that exact target, with all
source/target/patch CRC32s checked. All ROM/BPS/save/screenshots stay outside Git.

## Validation performed

- **44 synthetic tests passed**: original pipeline plus compressed-overlay
  roundtrip, unchanged assets, deterministic output and rejection guards.
- **24 actual-instruction cases passed** using Unicorn 2.1.4 and instructions
  loaded from the actual source/candidate, with graphics/environment calls
  stubbed. Positive shadow/crop sizes 1–128 include rounding and zero clamps;
  deletion occurred exactly once in each crop case. This is not a gameplay test.
- **Fresh boot passed a reviewed smoke oracle**: v3 and the combined candidate
  reached the recognizable title screen using identical frame-stepped input;
  both captures were visually reviewed, normalized pixel error 0.0.
- **Five battle replays completed**: v3, faint-only, exit-only, wild-only, combined.
  Each loaded the same copied battery save/checkpoint and used the same scripted
  inputs. All exercised wild transition, Ember, HP loss, faint, EXP and exit.
  Edited RAM instructions were checked against the selected ROM during replay;
  zero code mismatches. Original input hashes were unchanged afterward.
- Isolated changes affected only their measured phase. Move, HP and EXP callback
  state counts/spans were identical in every replay. The faint cry-wait state
  count was also identical. The combined run returned normally to the cave.

| Phase | v3 | Faint only | Exit only | Wild only | Combined |
| --- | ---: | ---: | ---: | ---: | ---: |
| Wild callback visits | 55 | 55 | 55 | 53 | 53 |
| Move callback visits | 35 | 35 | 35 | 35 | 35 |
| HP-motion callback visits | 51 | 51 | 51 | 51 | 51 |
| Faint callback visits | 85 | 82 | 85 | 85 | 82 |
| EXP-motion callback visits | 9 | 9 | 9 | 9 | 9 |
| Exit callback visits | 18 | 18 | 11 | 18 | 11 |

Callback visits, emulated frame spans and wall-clock speed are distinct. In
particular, the large unchanged cry wait dominates the total faint duration.
No claim of a 1.5x whole encounter/faint/battle is made from these measurements.

## Reproduce private emulator tests

Install optional pinned/hash-checked dependencies:

```sh
.venv/bin/python -m pip install --require-hashes -r requirements-emulator.lock
source scripts/emulator-env.sh
python scripts/validate-faint-instructions.py private/v3/europe-v3.nds \
  build/my-new-candidate/candidate.nds --out artifacts/faint-instructions.json
xvfb-run -a .venv/bin/python scripts/replay-battle.py build/my-new-candidate/candidate.nds \
  --save private/save/user-backup.dsv --checkpoint artifacts/v4-research/pre-walk.dst \
  --out artifacts/my-new-replay
python scripts/compare-replays.py artifacts/v4-research/baseline-replay/replay.json \
  artifacts/my-new-replay/replay.json --feature faint-motion \
  --feature battle-exit-palette --feature ordinary-wild-transition
```

The private checkpoint is an overworld savestate generated from a disposable
copy of the supplied battery save, before the encounter. It is not a distributed
fixture. The 524288-byte input was imported through DeSmuME's raw-save API without
truncating it or modifying the original. A future user needs an equivalent private
checkpoint; the exact repeatability claims here refer to the retained checkpoint.
The scenario is `tests/scenarios/cave-battle.json`; a different save/location/move
may require a different script and new baseline measurements.

`py-desmume` 0.0.9 bundles a **DeSmuME 0.9.12** core. It is separate from the
prepared **0.9.13** CLI. Frame-stepped comparisons used the same 0.9.12 core for
both sides, interpreter mode and Xvfb. Sound was muted; audio remains unverified.
For fresh title captures use `scripts/compare-boot.py --capture ROM --out IMAGE`
in separate Xvfb processes, manually review the v3 reference, then use
`--compare BASELINE CANDIDATE`. Do not treat blank captures as success.

## Delivery and outstanding work

Local private delivery files are in `build/user-delivery/`, explicitly named
`SoulSilver_Europe_V4_PARTIAL_EXPERIMENTAL.*`, with a warning/readme. Do not
replace the user's only ROM/save or label this as the requested finished v4.
The Drive folder is readable through shared download URLs; this session has no
connected authenticated Drive upload tool. Editor-link access does not provide
an upload session, so **no file was added to Drive**.

Still required: selective attack implementation, special wild transitions,
broader attacks/double battles, trainer/entrance/switch checks, audible music and
cries, save/write/reload and Delta testing. All feature PRs remain unmerged.
