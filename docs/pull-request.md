# Add guarded SoulSilver patch tooling and research scaffold

The repository previously had no implementation. This adds a local-only ROM
verification/build pipeline, BPS output, ARM9 disassembly, an isolated DeSmuME boot
oracle, pinned setup and synthetic CI tests. All ten timing decisions, upstream
license/compatibility research and a backup-save validation protocol are recorded.

Validation: 36 synthetic tests pass locally; setup/refresh commands and the local
16 MiB file-splitting helper were exercised. DeSmuME 0.9.13 help and Xvfb 256x384
capture work. No commercial ROM was used in those checks. Remote CI status has
not been observed.

No gameplay enhancements or release patch are included. The USA ROM is absent;
the uploaded EU v3 image exceeds the transfer tool's 32 MiB limit. Its contents
are uninspected. V3 reproduction, selective timing, music/Delta and save migration
checks remain blocked. The required evidence and next steps are documented rather
than represented as passing tests. No ROMs, saves, BIOS or extracted game assets
are tracked.

PR creation through GitHub API is currently blocked by network policy. This text
is ready for `gh pr create --base main --head feature/patch-pipeline --title
"Add guarded SoulSilver patch tooling and research scaffold" --body-file
docs/pull-request.md` once API access works. Do not merge gameplay changes without
the corresponding emulator/player checks.
