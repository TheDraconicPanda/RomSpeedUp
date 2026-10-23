# Patch architecture and v4 investigation

Current user clarification: the **supplied European v3 is the baseline** for all
unchanged behavior. Its existing frame-rate and text edits are retained. US and
clean European originals are optional research inputs, not required v4 bases.
See [current experimental implementation](v4-experimental.md).

## Ten fixed decisions

| Component | Required behavior | Validation |
| --- | --- | --- |
| Wild encounter transition | Faster, still visible | Count first transition frame through battle scene; approve visible duration |
| Trainer introduction | Unchanged | Compare intro duration, poses, dialogue and order |
| Pokémon entrance | Unchanged | Compare send-out effect, cry and sprite frames |
| Battle text | Instant, manually advanced | Full message by next presentation; wait with no input; one press advances once |
| HP | Unchanged | Compare per-frame bar progression |
| EXP | Unchanged | Compare progression, level-up and overflow |
| Attack animation | Approximately 1.5x current speed | Visual duration near baseline / 1.5; no skipped effects or logic callbacks |
| Faint animation | Approximately 1.5x current speed | Visual duration near baseline / 1.5; preserve faint handling and awards |
| Switching | Unchanged | Recall, selection, send-out timings and sequence |
| End-of-battle transition | Faster, still visible | Compare victory, flee, capture and blackout transitions separately |

“Current speed” and “unchanged” are measured against the actual supplied v3.
The historical 60 FPS edit is retained byte-for-byte; no additional global
acceleration is allowed. Original-game timings are not the unchanged baseline.
No music, save layout, calculations, encounters, Pokémon data or progression
changes are permitted. Do not run global frame, VBlank, audio, RNG or script
scheduler acceleration to implement a visual effect.

## Guarded pipeline

`verify` requires the bundled profile's game code, revision, exact size and known
SHA1, plus NDS header and logo CRC16s, executable bounds/entries, section overlap,
FAT ranges and overlay table file IDs. It records SHA256 for the actual dump.
SHA1 identifies the historical dump; manifests use SHA256. CRCs alone never
establish authenticity. A different revision is refused until researched.

`inspect` is informational and accepts structurally valid non-USA images; it is
not a substitute for `verify`. Structural checks are useful sanity checks, not a
complete NDS filesystem or compressed-stream verifier. Only a matching reference
hash permits a production source build.

`disasm` decompresses ARM9 using ndspy and decodes ARM or Thumb via Capstone.
Offsets are relative to the **decompressed** image and addresses are RAM addresses.
Compressed data cannot be patched by copying these offsets into the file. Overlays
must be mapped through their table and FAT; they are not included in the current
ARM9-only disassembler. Add overlay tooling only after actual-ROM investigation.
Do not assume disassembly output distinguishes code from literal pools.

A schema-1 manifest has `status: verified`, `source_sha256`, `target_sha256`,
`features` and nonempty `edits` (`offset`, hex `before`, hex `after`, `rationale`).
Offsets are ROM file offsets. Edits must preserve length, avoid the header,
not overlap, and match original bytes. The output digest must match an independently
reviewed intended target. This tooling does not infer semantic safety from hashes.
No example is labeled a real game patch and no placeholder address can build.
Tests construct synthetic manifests only. Use one independently validated feature
per manifest, then a separately tested combined manifest against the clean source.

BPS v1 output uses SourceRead and TargetRead commands, standard variable integers
and source/target/patch CRC32s. Generated ROM, BPS and reports stay in ignored local
build folders. Release only reviewed BPS files and documentation, never ROMs.
The current fixed-size engine intentionally rejects relocation/repacking needs;
add a reviewed transform with recompression/layout validation if required. Do not
fake an offset patch to work around compressed ARM9 or overlays.

## Selective timing approach (research, not implemented ROM changes)

First trace ownership of attack visual tasks, faint callbacks, transition timers
and their completion signals with a verified ROM. Isolate visual updates from
battle scripts and audio tasks. A possible 3/2 accumulator advances a *pure visual*
track in a 1,2,1,2 sequence per display tick, preserving every logical keyframe and
completion event once. This is unsuitable if callbacks consume RNG, drive battle
logic, wait on audio or share state with HP/EXP/entrances. In those cases use local
duration/interpolation changes, or report that the exact modification is blocked.
Do not double-run shared callbacks or blindly halve waits. Short animations may
need rounding; measure durations before choosing an acceptable tolerance (proposed
±1 display frame for deterministic effects; inspect long effects individually).

Begin with separate branches: `feature/us-v3-text`, `feature/wild-transition`,
`feature/battle-exit`, `feature/attack-timing`, `feature/faint-timing`. Each needs a
byte map, call path, baseline capture, isolated regression results and a PR.
Only then test a combined v4 profile. Infrastructure work does not count as any
of these modifications being complete.
