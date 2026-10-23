# Add guarded SoulSilver patch tooling and research scaffold

The repository previously had no implementation. This adds a local-only ROM
verification/build pipeline, BPS output, ARM9 disassembly, an isolated DeSmuME boot
oracle, pinned setup and synthetic CI tests. All ten timing decisions, upstream
license/compatibility research and a backup-save validation protocol are recorded.

Validation: 36 synthetic tests pass locally; setup/refresh commands and the local
16 MiB file-splitting helper were exercised. DeSmuME 0.9.13 help and Xvfb 256x384
capture work. No commercial ROM was used in those checks. Remote CI status has
not been observed.

No gameplay enhancements or release patch are included. The clean USA ROM is
absent. The user-provided v3 artifact is now accessible via Drive and structurally
inspected: its USA header conflicts with its European filename, and it does not
match the clean USA reference hash. Emulator startup observations and remaining
blockers are documented in docs/v3-inspection.md. Exact v3 reproduction, selective
timing, music/Delta and save migration checks remain blocked. No ROMs, saves,
BIOS, screenshots or extracted game assets are tracked.

Review this as infrastructure/research work only. Do not merge gameplay changes
without the corresponding emulator/player checks.
