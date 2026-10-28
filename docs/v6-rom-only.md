# Corrected V6 — standalone gameplay acceleration, normal sound

The player clarified that Delta 3x was a comparison, not an intended emulator
setting. This build starts from the original European ROM and targets 2x game
updates with normal audio at **normal emulator speed / Fast Forward OFF**.
The previously delivered `FOR_DELTA_3X` ROM does not satisfy this requirement.

This is an experimental nominal-2x build, not a guarantee of twice the speed in
every scene. A fresh cave replay reaches 1801 game updates and 900 sound updates
in 1800 hardware frames (retail game updates are nominally 900). A separate
lighter-scene replay reaches 358/360 updates. Goldenrod's moving replay reaches
315/360 updates versus retail 180/360: **1.75x**, with 160 rendered frames.
The original emulated CPU/GPU remains a bottleneck there. Delta device testing
and additional special graphics paths remain unverified. These limits must be
reported with the download; do not describe every city as an exact 2x.

## Reproduce

```sh
.venv/bin/python scripts/build-v6-native.py private/original/user-original.nds \
  --out build/my-native-v6
.venv/bin/python scripts/validate-v6-native.py private/original/user-original.nds \
  build/my-native-v6/candidate.nds --out artifacts/my-native-v6/native.json
.venv/bin/python -m pytest -q
```

Source SHA256:
`94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`.
Candidate SHA256:
`e369d3d641551d4ca75cacc548608f5f6bdd66f45ff7bcaa960c655838cb1033`.
Both ROMs are 134217728 bytes. The tracked builder reproduces the private tested
prototype exactly. No ROM bytes, user saves or screenshots are tracked.

## Separate update, graphics and sound clocks

The retail loop normally advances once per two physical VBlanks. The new clock
tracks a virtual game tick against the monotonic physical frame counter and
targets one update per VBlank. It waits only when caught up, resets unreasonable
debt after stalls/wrap and never spins an unbounded sound catch-up loop.

Rendering and graphics publication use alternating virtual ticks, independently
of the wait/debt flag. Earlier private prototypes coupled rendering to that flag
and produced uneven presentation. The current implementation gates the field
draw root, GPU scale/draw entrypoints, sprite draw callback, swap handling and
main-loop graphics publication. Brightness/fade logic keeps the accelerated game
clock. All ordinary movement parameters, tile endpoints and follower path logic
retain their original values; game updates accelerate them together.

Audio uses one `DoSoundUpdateFrame` per two physical VBlanks, with at most four
catch-up calls and resynchronization after excessive debt. ARM7 and the entire
original SDAT, including scores, banks, waves, cries and effects, are byte-identical
to the original. No audio tempo/pitch compensation or emulator acceleration is
used. Recorded fresh boot/field audio is non-silent, and replay counts verify
the original 30-Hz audio update cadence. Listening on Delta remains necessary;
this is not a bit-identical waveform claim for every sound combination.

## Equivalent data cipher optimization

Profiling found frequent calls to the original Pokemon/data XOR cipher. Its
byte-for-byte equivalent replacement keeps the exact size/2 truncation and
LCRNG recurrence `seed = seed * 0x41c64e6d + 0x6073`, XORing each halfword with
the upper seed half. It uses ARM multiply-accumulate and unrolls groups of four;
other lengths use a scalar fallback. It preserves callee-saved registers and
does not alter Pokemon calculations, checksums, data format or the global RNG.

The existing 220-byte player-state slot contains the previously verified
108-byte equivalent movement-state routine plus the 112-byte ARM cipher. The
original cipher's 44-byte slot contains the interworking entry and scalar
fallback. The 584-byte movement-wrapper slot contains equivalent compact
direction wrappers, clocks/gates and a 20-byte runtime state. Main RAM, BSS and
autoload section boundaries remain unchanged. Packed ARM9 is 762760 bytes with
its original 12-byte Nitro footer preserved. The field overlay has one selected
draw-call change. The builder checks executable edit ranges, memory layouts,
compression roundtrip, every protected NitroFS payload, ARM7 and cartridge size.

## Validation

- 4320 native clock cases cover initialization, phase, debt, wrap, audio cost,
  bounded catch-up and resynchronization. Twelve Thumb gate cases and four ARM
  gate cases check pass-through arguments, publication phase and stack behavior.
- 112 ordinary movement cases retain original results across four maps and
  direction families; 640 movement-state comparisons retain original memory
  outputs and environmental call traces.
- 565 original/optimized/reference cipher cases cover zero/odd/boundary lengths,
  random data and seeds, untouched buffer tails, callee-saved registers and stack.
- All 49 unit/pipeline tests pass. The original source identity is mandatory.
- Fresh target boot imports a disposable copy of the original battery save,
  reaches Union Cave and shows player/follower movement and trainer dialogue.
  The trainer battle renders, attacks resolve, Geodude faints and the next-enemy
  switch prompt appears. Target Goldenrod movement screenshots were reviewed.
- In-game saving changes 1665 battery bytes on the disposable copy. A separate
  clean import/boot of that exported save resumes the game. Original ROM/save
  files remain intact. Delta hardware and full-game coverage are pending.

Old savestates must not be used to validate this build: they can resume inside
the old cipher with an incompatible instruction/stack context. Private original
checkpoint replays migrate code only at a safe main-loop boundary; final smoke
checks boot the target itself and use checkpoints created by that target.
For the player, import a **battery save and boot fresh**. Keep Fast Forward OFF.

Verified delivery archive:
`Pokemon_SoulSilver_V6_ROM_ONLY_2X_EXPERIMENTAL.zip`, 60679799 bytes, SHA256
`7bf31d7c26be4793c1125a754d8ab027b973b00f5d94c9ca30b4b93b8a26e8d7`.
The ZIP CRC check passes, and extracting its ROM reproduces the candidate SHA256.
