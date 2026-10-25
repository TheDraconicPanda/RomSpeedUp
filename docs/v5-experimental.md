# v5 experimental — city movement and automatic visible result text

The player requested the name **v5**, an estimated 2x city walking/running boost,
and fast but noninstant miss/immunity text that advances without user input.
The multiplier is the player's approximation to the walk/run difference, not a
measured Delta correction. The earlier partial V4 wild/faint/exit edits remain.
Selective attack acceleration remains unimplemented. This is not a fully tested
release and has not been played on Delta in this environment.

## Behavior and scope

- Ordinary player walk/run: double spatial delta and halve advancing duration in
  map type 1 (city/town outdoor maps), with original gait animation, tile endpoint
  and completion behavior retained. Walk 8 -> 4 advancing callbacks; run 4 -> 2.
- Routes, interiors, other movement families, NPCs, surf/bike states and movement
  while normal player control is disabled retain their tested baseline behavior.
  Map type 1 includes Bellchime Trail as documented in the mapping report.
- Result messages 12, 18, 21, 24, 27, 342 and 1036 in the standard battle message
  bank print one glyph per printer-task invocation, then use a 24-update automatic
  pause. These include miss/avoided and type/ability immunity results. A/B/touch
  is not required and does not skip that pause. Printer tasks can run more than
  once per game update; the setting is not a fixed wall-clock reading time.
- Other text retains V3's printing behavior. Protect, generic failure and Sturdy
  protection do not get this selected-message override. Link battles retain their
  old print-delay and timed-wait paths; live multiplayer is not validated.

## Implementation

The mapped `PlayerAvatar_UpdateMovement` slot at `0x0205CE68` is 220 bytes.
A compact equivalent of its original state machine occupies 108 bytes, freeing
space for an 80-byte city initializer and a 32-byte text-yield continuation in
that exact slot. No ARM9 section or BSS address moves; overlay 1 is not extended
into overlay 2. Calls from the eight walk/run initialization wrappers target the
city helper. It verifies object identity, on-foot state, normal movement allowed,
and map type before scaling delta/duration, then calls the original initializer.
It passes through the original animation value and uses the normal completion path.

Selected battle-message printing uses constructor speed `0x41`, resulting in the
printer's encoded speed byte `0xC0`. Two guarded continuations in V3's printer loop
yield after each printed glyph only for that marker. Ordinary printers keep the
existing V3 loop behavior, including callbacks. A normal battle message-bank check
and link-type check prevent marking unrelated text contexts.

The original 156-byte battle wait-handler slot holds a compact equivalent wait
prefix and the result marker selection helper. The prefix tail-shares the original
unchanged `WaitTime` calculation body with its exact stack layout. Ordinary timed
wait semantics are checked against the original code. Selected script paths in
subscripts 7 and 176 use the existing `WaitTime 24` opcode instead of manual waiting;
their link fallback remains the original timed button wait.

The builder starts from the exact reproduced partial V4 (`cdf7059e...`), not the
manual-text variant, so the superseded manual-only result behavior is absent.
Only guarded ARM9 ranges, overlay 12 ranges, scripts 7/176 and required container
size/checksum fields change. ARM7, other assets/files, original global frame-rate
instruction and unrelated V3 text behavior remain preserved.

ARM9 recompresses to 762724 bytes. The original 12-byte Nitro footer is moved to
follow its new packed end, inside existing padding. Its contents, autoload table,
section addresses/sizes/BSS and module settings remain preserved except for the
required packed-end pointer. The header ARM9 size and header CRC are updated.
Overlay 12 recompresses to 162500 bytes with its RAM/BSS/static-init layout retained.
Every modified compressed image passes decompression readback and guarded-range
comparison. No neighboring file is relocated or overwritten.

Assembler literal-pool alignment is mandatory. An early unreleased candidate
failed differential tests after misaligned literals caused Thumb-2 relaxation and
a shifted call encoding. The corrected assembler preserves alignment and rejects
any four-byte instruction other than ARM9-supported BL/BLX in generated code.
Only corrected candidate `v5-002` is eligible for delivery.

## Reproduce

Use the locked project, assembler and emulator dependencies, then:

```sh
.venv/bin/python scripts/build-v5.py build/v4-handoff-001/candidate.nds \
  --out build/my-v5
.venv/bin/python scripts/validate-v5.py build/v4-handoff-001/candidate.nds \
  build/my-v5/candidate.nds --out artifacts/my-v5/instructions.json
```

Fresh output paths are required. The builder's BPS targets the exact previous
partial V4; delivery packaging additionally generates a clearly labeled FROM_V3
patch against the exact supplied European V3. Keep ROMs/patches/saves/screenshots
private and outside Git.

Source SHA256: `cdf7059ea67936816d724df8d5336e1b5c364a5d41acef7e4e5f8280db6e9e92`.
v5 SHA256: `4872087cab43c11df33507aaef88186208a4a2c1ac9bab9abfe66835fbe16e7b`.

## Actual validation and limits

- 640 original-versus-compact player state-machine cases matched object/avatar
  memory and environmental call traces.
- 864 movement cases exercised the actual initializer and advancing callbacks:
  ordinary and excluded command families; city/route/interior maps; player/NPC
  identity; foot/bike/surf states; normal control enabled/disabled. Endpoint and
  animation matched; selected cases took exactly half the advancing callbacks.
- 1400 ordinary timed-wait differential cases matched, including link/recording
  flags, timeout/counter boundaries, keys and touch. Automatic result waits ended
  after 24 increments plus completion with no input, held keys or touch.
- 4800 message selection cases checked IDs 0–1199, link versus local and standard
  versus unrelated message bank. Only the seven intended local results were marked.
- 24 printer cases checked short/long strings, marker/ordinary printers,
  callback/null callback and global pause. Selected text advanced one glyph per
  task invocation; ordinary text matched the source printer behavior.
- 24 script-path cases checked local automatic waits and unchanged link/other
  result paths. All 44 pipeline tests passed. Private artifact/whitespace checks pass.
- Fresh DeSmuME 0.9.12 interpreter boots under SDL dummy reached visually reviewed
  SoulSilver title screens; corrected v5 and baseline captures matched exactly.

Instruction experiments stub environment, font and audio services. They do not
verify live glyph rendering, full city scene collisions, companion following,
camera motion, map transitions, save/reload, music or Delta gameplay. A successful
title boot does not clear those checks. Initial user testing should cover walking
and running in Ecruteak/Goldenrod, adjacent routes, doors, companion following, an
attack miss and a type immunity. Keep the previous ROM and in-game save backups.
