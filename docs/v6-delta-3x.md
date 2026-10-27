# V6 — original Europe ROM calibrated for Delta 3x (experimental)

The player requested a new version based on the original ROM, with roughly 2x
gameplay and normal music. Delta exposes only its default Fast Forward setting;
the player confirmed that setting is 3x. V6 therefore requires **Fast Forward
enabled**. At normal emulator speed the ROM intentionally plays slowly.

This supersedes the earlier private ROM-only acceleration prototypes. None of
those prototypes is the delivered V6. V6 starts with the exact original Europe
ROM, not V3/V4/V5, so their selected text, transition and city/follower edits are
not inherited. The original scripts, battle data and movement parameters remain.

## Build and allocation

Source SHA256:
`94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`.
Target SHA256:
`757eccf7f9846e32caeac9166f2353f9077aec85d9fb24eab73819f5bba9f228`.
Both files are 134217728 bytes. Private candidate: `build/v6-3x-001/candidate.nds`.

```sh
.venv/bin/python scripts/build-v6.py private/original/user-original.nds --out build/my-v6
.venv/bin/python scripts/validate-v6.py private/original/user-original.nds \
  build/my-v6/candidate.nds --out artifacts/my-v6/native.json
.venv/bin/python -m pytest -q
```

The original main loop normally consumes two physical VBlanks per update. Its
second wait call at 0x02000E1E now calls a helper that waits until three VBlanks
have elapsed. It preserves the original first wait and frame-counter reset,
counts time already spent working, and does not add needless waits to overloaded
updates. The original 220-byte player-state slot at 0x0205CE68 contains an
equivalent 108-byte movement-state routine and the 32-byte wait helper at
0x0205CED4. RAM/BSS and executable section boundaries remain unchanged. The
compressed ARM9 footer is retained and compression is verified by decompression.

The resulting native update rate is nominally 2/3 retail; Delta 3x gives 2x
retail. This is a main-loop calibration, not a promise that every independent
hardware timer, VBlank task, heavy scene or emulator bottleneck scales identically.

## Music

Music and musical fanfares (SDAT players 1, 2 and 7) receive tripled note/rest
tick durations. Tempo changes, note pitches, instruments, branch/call/track
targets, control flow and raw unreachable data are preserved. Modulation delays
are tripled; byte-sized vibrato rates are rounded to one third. No bank or wave
payload is changed. DeltaCore uses `AVAudioUnitTimePitch` for fast-forward audio,
so score timing rather than note pitch is compensated. See
[DeltaCore AudioManager](https://github.com/rileytestut/DeltaCore/blob/869042a5699b19df3cf9f3369a950737ff818149/DeltaCore/Emulator%20Core/Audio/AudioManager.swift).

296 unique music files are retimed. One file shared with menu/dummy effects is
cloned for its two music aliases; the effects keep their exact original payload.
2058 original internal sound files are protected byte-for-byte. All sequence
names and INFO metadata are retained except those two music-only file IDs.
The rebuilt SDAT is 8727648 bytes. Subsequent NitroFS payloads shift by 67584
bytes, using unused cartridge tail capacity, and their FAT entries are updated.
Every non-sound NitroFS file, ARM7, overlay tables and banner is checked against
the original. Cartridge size remains 128 MiB.

The custom sequence reader handles actual consumed VLQ lengths, A1 instrument
variables and the 16-bit E0 modulation delay. ndspy 4.2.0's generic reader/writer
has length issues for these cases. Each original event graph is serialized and
read back before retiming; each retimed graph is then compared with the expected
graph, including relocated targets. Unit regressions cover these encodings.

This preserves score tempo, not a bit-identical recording. Instrument envelopes,
portamento and runtime fades are not globally time-stretched by this patch;
vibrato quantization can also change timbre slightly. Cries and sound effects
retain their original assets and follow Delta's audio acceleration behavior.
Music and fanfare timing should be checked on the player's Delta device.

## Validation and save handling

- 640 native instruction comparisons preserve the compacted movement state's
  outputs and stub-call traces. 48 IRQ pacing cases verify waits, elapsed-frame
  accounting, stack balance and callee-saved registers.
- 48 pipeline/unit tests pass. Full original identity, executable layout,
  compression roundtrip, sound graph and payload preservation checks pass.
- Fresh DeSmuME 0.9.12 boot reaches the title and the user's Continue menu.
  Fresh battery-save import reaches Union Cave; player/follower movement,
  trainer dialogue, battle entry, attacks and battle text were observed.
  A 360-frame field interval executes 120 updates; the retail checkpoint
  executes 180. Music output is non-silent in fresh title and field recordings.
- The in-game save screen reports completion. Exported battery bytes change
  from the disposable original (1663 changed bytes); a separate fresh boot
  shows the updated 85:29 Continue entry and successfully resumes Union Cave.
- Goldenrod is loaded through a disposable standard warp task, with temporary
  code restored before capturing the checkpoint. The actual target runs 120
  updates in 360 city frames, and a separate movement replay runs 30 in 90.
  Player/follower movement and the city screenshot were reviewed.
- Delivery ZIP is 60695388 bytes, SHA256
  `844fb12257614835deda54b92569768ba2b08a6f9b7b1fd95aceaa0871e06ac0`.
  Its ROM checksum and ZIP integrity were verified. Two Drive upload calls
  stalled and were interrupted, with no file ID returned. Subsequent exact
  folder searches returned no V6 result. **No Drive delivery is confirmed.**

Do not load a V3/V4/V5/original quick savestate into V6. NitroFS metadata cached
in an old state references original physical file positions, which can cause
bad reads after the sound archive relocation. An old Goldenrod state reproduced
this fault. The same pacing code with the original file layout runs 120/360
updates without the fault, and clean boots of the actual target load correctly.
Use Delta's battery-save import and start V6 from a fresh boot. Keep the user's
original save and ROM intact. Delta hardware validation and full-game coverage
remain pending; do not merge as a verified release.
