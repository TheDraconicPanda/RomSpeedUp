# SoulSilver selective battle speed patch

Standalone research and development tools for **Pokémon SoulSilver USA**.
ROM changes are **blocked**, not implemented: no verified clean USA input is available.
The original supplied through Drive matches the European English reference, not
the USA reference. It matches v3's underlying build; `IPGE` is shared by both regions.
See [baseline comparison](docs/v3-baseline.md).
The pipeline can be developed and tested without any game files.

No ROM, save, BIOS or game asset is distributed or downloaded by these tools.
Use your own verified cartridge dump. Keep private inputs under `private/`.

## Prepared tooling

- Known-USA profile and structural/hash verifier.
- Guarded fixed-size edits with original bytes and source/target SHA256 checks.
- BPS patch generation and reproducible local build reports.
- ARM9 decompression and ARM/Thumb disassembly via ndspy and Capstone.
- DeSmuME/Xvfb boot screenshot harness, isolated from original saves and ROMs.
- Synthetic automated tests, CI and tracked-private-artifact checks.

## Setup

Python 3.11+ is required (cloud validation uses 3.12 on Debian 13).

```sh
bash scripts/setup.sh
source .venv/bin/activate
python -m pytest -q
python scripts/check_assets.py
```

Dependencies and transitive versions/hashes are in `requirements-dev.lock`.
`requirements-dev.txt` is the resolver input. To refresh deliberately:
`uv pip compile --generate-hashes -o requirements-dev.lock requirements-dev.txt`.
Do not refresh merely to silence installation errors.

For the cloud's Debian 13 emulator setup (unprivileged, signed Debian packages):

```sh
bash scripts/setup-emulator.sh
source scripts/emulator-env.sh
```

The emulator packages live in `/workspace/emulator`, outside the project. This
helper depends on the managed Debian base's existing SDL/X11/system libraries.
Other Linux machines should install DeSmuME 0.9.13, Xvfb and xauth through their
trusted package manager. Desktop emulator help and Xvfb capture were checked;
actual SoulSilver boot, music and Delta behavior remain untested.

## Verify, inspect and build locally

Run from the repository root; the default USA profile path is relative to it.

```sh
romspeedup verify private/soulsilver-usa.nds
romspeedup inspect private/soulsilver-usa.nds
romspeedup disasm private/soulsilver-usa.nds --offset 0x0 --length 0x100
# Use --thumb only for a known Thumb code region.
```

Verification accepts the original US revision with game code `IPGE`, size
134217728, SHA1 `f8dc38ea20c17541a43b58c5e6d18c1732c7e582`.
This reference is sourced from [pret's US disassembly](docs/research.md).
No user ROM has yet passed it here. `inspect` is informational, not verification.

After a feature is implemented, reviewed and has a verified manifest:

```sh
romspeedup build private/soulsilver-usa.nds path/to/verified-manifest.json --out build/feature-run-001
```

There is deliberately no runnable game manifest yet. The builder refuses empty,
draft, wrong-hash, overlapping or unguarded edits. Each output directory must be
new. It produces `patched.nds`, `patch.bps` and `build.json`. Keep the ROM local;
only reviewed patches and instructions belong in a release. See the manifest
contract in [design.md](docs/design.md).

After manually reviewing a deterministic boot reference screenshot:

```sh
source scripts/emulator-env.sh
xvfb-run -a -s '-screen 0 256x384x24 -nolisten tcp' \
  .venv/bin/romspeedup boot private/soulsilver-usa.nds \
  --reference private/stock-boot.png --out artifacts/stock-boot-001
# For a patched ROM add --manifest path/to/verified-manifest.json
```

A process or open display alone is not success. This command requires a
recognizable, manually reviewed reference and fails on blank/mismatched screens.
The boot check mutes sound; music needs the separate audio regression test.

## Scope and workflow

All ten decisions, the proposed timing approach and protected behavior are in
[the design](docs/design.md). **No global speed toggle implements v4.** The earlier
60 FPS patch must be audited against the unchanged-animation decisions before it
can be considered a baseline. The exact v3 changes cannot be inferred from its
filename, patched binary alone or the player's report.

Use feature branches, test each change in isolation, and create a PR with the
changed byte map and evidence. Do not merge unverified gameplay modifications.
The initial `main` contains only a project introduction; scaffold work is on
`feature/patch-pipeline`. Cloud tasks already provide isolation: use the existing
checkout; do not create a worktree unless explicitly requested.

- [Research, licenses and compatibility](docs/research.md)
- [Required testing and current limitations](docs/test-checklist.md)
- [Safe EU→US save investigation](docs/save-compatibility.md)
- [Input transfer/report helper](docs/input-files.md)
- [Per-feature blockers](features/status.json)
- [Changelog](CHANGELOG.md)

The next inputs are a verified US dump, an inspectable v3 patch/source or split
artifact, and a backup European battery save. No release or preservation claim
is made before the corresponding checks pass.
