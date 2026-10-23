# Changelog

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
