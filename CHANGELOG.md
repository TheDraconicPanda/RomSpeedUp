# Changelog

## V5.1 — experimental city calibration and animation correction (2026-10-25)

- Reduced city spatial deltas from 2x to 1.5x, with shorter final deltas to retain
  tile endpoints. Frame/tile rounding gives a 4/3x average advancing speed.
- Matched eligible walk/run animation increments to the boost, correcting the
  repeated early running pose reproduced in live emulator replay.
- Added compact shared movement wrappers and guarded sprite hooks without
  expanding runtime sections. V5 battle results remain byte-identical.
- Passed movement/sprite/interruption instruction checks, retained battle checks,
  44 pipeline tests, BPS integrity and fresh title comparison. Actual city/Delta
  regression remains pending. Location-specific surfing slowness remains unresolved.

## v5 — experimental city movement and result text (2026-10-25)

- Added the player's estimated 2x city/town outdoor walking/running target with
  original gait animations and tile endpoints; tested route/interior/NPC/script
  exclusions. No new global acceleration or field-overlay memory expansion.
- Replaced manual miss/immunity waits with fast visible printing and a short
  automatic pause. Other text and link fallback paths retain prior behavior.
- Added guarded ARM9 recompression/Nitro-footer preservation and actual-instruction
  comparisons. Corrected candidate passed instruction checks, 44 pipeline tests
  and fresh title-screen comparison. Delta/follower/camera/gameplay checks pending.
- Selective attack acceleration remains unimplemented.

## Experimental manual result messages — 2026-10-24

- Added fresh-A/B manual waits for selected miss and immunity messages while
  retaining instant printing, ordinary timed waits and link-battle fallback.
- Guarded exact European partial-candidate identity, handler slot, command table,
  scripts, compression and protected files. No code/data relocation.
- 1400 actual-instruction timed-wait comparisons, 1200 manual-wait updates,
  28 script paths and fresh title-screen comparisons passed. Full gameplay/Delta
  checks remain for the player; attack acceleration remains unimplemented.

## 0.1.0 — development scaffold (2026-10-23)

- Added strict USA source identification and NDS structural checks.
- Added guarded fixed-size patch manifests, BPS output and ARM9 disassembly.
- Added pinned/hash-checked Python setup, signed Debian emulator setup and an
  isolated screenshot-based boot harness.
- Added synthetic tests and CI, private-artifact checks, research/license notes,
  ten-decision specification, feature blockers and save test protocol.
- Added local header/hash reporting and 16 MiB transfer splitting helper.
- No v3/v4 ROM enhancements implemented. Real-ROM, save, music, timing and Delta
  checks remain blocked; a passing tools suite is not a game release.

## Research update — user-provided v3 access

- Downloaded and structurally inspected the user's private Drive artifact after
  network publication; ARM9 decompression succeeded.
- Recorded its IPGE/revision-10 header conflict with the European filename.
- Observed recognizable intro progression in DeSmuME JIT/software-renderer mode.
  Battle/text/music/save behavior and automated boot validation remain unverified.

## Research update — matched original

- Identified the supplied original as the European English reference by SHA1;
  corrected the earlier assumption that IPGE uniquely identified the USA release.
- Compared the matching pair: only stored ARM9 differs; after decompression the
  differences reduce to 17 bytes across six ranges matching global uncapped-rate
  and fast-text implementation patterns.
- Recorded exact-recompression limitations. Kept the USA target and its input
  verifier unchanged; no v4 patch or gameplay validation was claimed.

## Partial v4 experiment — European v3 baseline

- Applied the user's clarification: unchanged means v3, not the original game.
  Retained the exact existing v3 frame-rate/text edits; USA is not a prerequisite.
- Added guarded compressed-overlay edits for faint visual motion (8 → 12 pixels),
  ordinary transition interpolation and battle-end palette wait. Preserved RAM,
  BSS, file layout, ARM9/ARM7 and every unselected asset.
- Validated three isolated candidates and their combination in one repeatable
  Zubat battle using a disposable user-save copy; attack, HP/EXP and cry-wait
  traces stayed at their stated v3 baselines. Fresh title captures matched.
- Added actual-instruction checks, optional hash-locked emulator tools and private
  replay/boot comparison scripts. 44 synthetic tests and 24 instruction cases pass.
- Attack 1.5x, special wild transitions and broad/audio/save-write/Delta regression
  remain outstanding. Outputs are partial experiments, not a completed release.
- No ROM/save/screenshots committed; no Drive upload performed.
