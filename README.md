# SoulSilver v3 → v4 selective speed patch

Development now targets the **user-supplied European v3**. Everything marked
unchanged is relative to v3, including its existing frame-rate and text edits.
USA and clean European originals are optional research inputs.

**Status: partial experimental candidate, not completed v4.**

| Feature | Current implementation |
| --- | --- |
| Fainting | Visual steps 8 → 12 pixels; cry wait unchanged |
| Battle exit | Shorter battle palette fade; audio fade parameters unchanged |
| Ordinary wild transitions | Reduced interpolation durations, modest speedup in tested case |
| Attack effects at 1.5x | **Not implemented**; scoped visual-task timing remains unresolved |
| Other behavior | v3 code/assets retained; full regression/Delta testing incomplete |

See [implementation, measured results and limitations](docs/v4-experimental.md).
No ROMs, saves, BIOS, screenshots or generated game assets are committed here.

## Setup and tests

Python 3.11+; cloud validation uses Python 3.12 on Debian 13.

```sh
bash scripts/setup.sh
source .venv/bin/activate
python -m pytest -q
python scripts/check_assets.py
```

Core dependencies are pinned with hashes in `requirements-dev.lock`. For optional
instruction-level and frame-stepped game tests:

```sh
bash scripts/setup-emulator.sh
python -m pip install --require-hashes -r requirements-emulator.lock
source scripts/emulator-env.sh
```

Both the 0.9.13 CLI and the optional binding's 0.9.12 core are available. Compare
baseline/candidate with the same backend and settings; do not mix their timings.

## Build a partial candidate locally

Use only the exact supplied v3 matching [its profile](profiles/europe-v3.json).
Keep all inputs in ignored `private/` paths. The builder preserves v3 ARM9 and ARM7
and modifies selected compressed overlays within their existing file slots.

```sh
romspeedup verify private/v3/europe-v3.nds --profile profiles/europe-v3.json
python scripts/build-v4-candidate.py private/v3/europe-v3.nds \
  --feature faint-motion --feature battle-exit-palette \
  --feature ordinary-wild-transition --out build/my-new-candidate --bps
```

Outputs: local `candidate.nds`, `candidate.bps`, `build.json`. A new output folder
is mandatory. Select one feature to test it independently. The BPS applies to v3,
not to either unmodified original. No release-ready v4 is currently available.

The earlier generic USA verifier/file-edit pipeline remains available for
research. Its clean-USA default profile is **not** the v4 baseline. Informational
`romspeedup inspect` accepts other structurally valid inputs. ARM9 decompression
and ARM/Thumb inspection use ndspy/Capstone; see `romspeedup disasm --help`.

## Evidence and workflow

44 synthetic tests, 24 actual-instruction faint cases, fresh title-screen
comparison and one controlled wild battle on v3/three isolated candidates/their
combination passed their stated checks. These do not prove all gameplay behavior.
See the report for unchanged phases, measured speedups and outstanding checks.

Use feature branches and reviewable PRs. Do not merge unverified gameplay changes.
Cloud tasks already provide isolation: use the existing checkout rather than a
worktree unless explicitly requested. Generated ROMs, saves and private evidence
stay out of Git and public releases.

- [Current v4 report and build/test commands](docs/v4-experimental.md)
- [Ten decisions and architecture](docs/design.md)
- [Feature status](features/status.json)
- [Required test matrix](docs/test-checklist.md)
- [Matched original and v3 edits](docs/v3-baseline.md)
- [Research and license observations](docs/research.md)
- [Backup-save protocol](docs/save-compatibility.md)
- [Changelog](CHANGELOG.md)
