# V4 handoff for another Codex chat

Updated 2026-10-24. This is project context and reproducible guidance; check the
current checkout, inputs and tools before acting on historical observations.

## v5 follow-up — 2026-10-25

The player authorized implementation, named v5: estimated 2x city movement and
fast visible (not instant) miss/immunity results with automatic advancement.
Branch `feature/v5-city-and-text`; see `docs/v5-experimental.md`, `scripts/build-v5.py`
and `scripts/validate-v5.py`. Corrected private candidate is `build/v5-002`, SHA256
`4872087cab43c11df33507aaef88186208a4a2c1ac9bab9abfe66835fbe16e7b`.
The early `v5-001` candidate failed instruction checks and must not be delivered.
Normal movement state code is compacted within its original slot; no field overlay
expansion. Selected results print one glyph/task invocation plus WaitTime 24;
manual-only result behavior is superseded. Delta/city/follower/camera gameplay
testing remains pending; attack acceleration remains unimplemented.

## Follow-up: city movement mapping only — 2026-10-25

Player reports slower city movement in Delta (Goldenrod/Ecruteak), also present
in V3; audio comparison unavailable. They authorized mapping first and deferred
implementation. `research/city-movement-map` adds read-only instruction research;
see `docs/city-movement-map.md` and `scripts/map-city-movement.py`. Actual European
code uses the same ordinary per-update walk/run speeds in cities and routes
(8/4 advancing callbacks per tile). City detection and a player decision boundary
are mapped, so a scoped compensating change has research targets. Real-time parity,
the Delta cadence ratio and safe helper-code allocation are not established.
No movement patch or new ROM was built; await the user's implementation decision.

## Follow-up: manual miss/immunity results

The player reports the delivered partial build works and other attempted
checklist items were good; fainting remains untested. Miss and immunity result
messages disappeared too quickly. They chose a fresh A/B press with unlimited
reading time. `feature/manual-result-text` implements this incremental change on
the exact partial candidate; see `docs/manual-result-text.md` for build commands,
guards, scope and actual-instruction/script/boot evidence. It remains partial V4;
attack acceleration is still unimplemented. Do not confuse a result-message fix
with full manual advancement for every battle message or finished V4.

## Start here

Repository: `TheDraconicPanda/RomSpeedUp`.
The working implementation is on **`feature/v4-selective`**, not `main`.
Implementation commit: `cc46daa` (this handoff is a later documentation commit).
Fetch/check out that branch before trying the commands below. Preserve existing
work if the receiving chat already has a dirty checkout.

The user wants the supplied **European V3 updated to V4**. The earlier USA-first
plan was superseded. Every "unchanged" requirement means unchanged relative to
V3, not the retail game. Do not require a USA ROM or reapply V3's frame/text edits.

**A reproducible partial candidate already exists. It is not finished V4.**
If the immediate task is delivery, rebuild this candidate without inventing new
timing changes and label it `PARTIAL_EXPERIMENTAL`. If the task is finishing V4,
continue the selective attack research and remaining validation below.

Read these tracked files next:

- [Detailed implementation and evidence](docs/v4-experimental.md)
- [Guarded overlay edits](features/v4-experimental.json)
- [Requirement status](features/status.json)
- [V3 inspection](docs/v3-inspection.md) and [baseline](docs/v3-baseline.md)
- [Research and licenses](docs/research.md)
- [Test checklist](docs/test-checklist.md) and [changelog](CHANGELOG.md)

## User decisions and current implementation

| Action | Requested behavior relative to V3 | Partial candidate |
| --- | --- | --- |
| Wild encounters | Faster, but visible | Ordinary effect IDs 0–5 shortened; special paths unchanged/unverified |
| Trainer introductions | Unchanged | No selected edits; trainer replay still needed |
| Pokémon entrances | Unchanged | No selected edits; detailed timing still needed |
| Battle text | Instant, manual advancement | V3 ARM9 retained exactly |
| HP bars | Unchanged | Controlled replay timing matches V3 |
| EXP bars | Unchanged | Controlled replay timing matches V3 |
| Attack animations | Approximately 1.5× V3 | **Not implemented: still V3 speed** |
| Fainting animations | Approximately 1.5× V3 | Visual steps 8 → 12 pixels; cry wait retained, so total sequence is not 1.5× |
| Switching | Unchanged | No selected edits; voluntary/forced switch replay still needed |
| End of battle | Faster, but visible | Shorter battle-exit palette wait |

Preserve music tempo/pitch, save compatibility, calculations, encounters,
Pokémon data and progression. Do not add global acceleration to implement attack
speed. Do not shorten unrelated waits as a substitute for attack animation work.

## Private inputs and destinations

The user supplied and authorized using these files and adding the build to this
Drive folder:

<https://drive.google.com/drive/folders/1J7caSyzIpCCnbDhVRo7x4OX5CEijfpIV>

Only retrieve user-supplied files; never obtain ROMs from other download sites.
Do not publish ROMs, saves or private screenshots/checkpoints to GitHub. Existing
Git exclusions cover private/build/artifact outputs, but inspect staged files.

| Input | Drive file ID | Historical local path |
| --- | --- | --- |
| European V3 | `1ruZgJFdTt3uFas2So3vLLcf9W9wQykRy` | `private/v3/europe-v3.nds` |
| Original Europe, research only | `19F-mc9FZqzuYkYoZANYuvnRwvw5vWcYK` | `private/original/user-original.nds` |
| Original USA, optional, not used in this build | `1Bg3CcE2UvLN5-fPjLnJxjIXgn5k7JAnN` | Not downloaded in this session |
| Disposable battery save backup | `12UR9flMXkgop4ZGcKnInBafutsypm1uK` | `private/save/user-backup.dsv` |

Files might have moved or access might have changed. Private local files do not
travel with the Git repository. Preserve original inputs and work on copies.

Required V3 identity (also enforced by `profiles/europe-v3.json`):

```text
size:   134217728 bytes
SHA1:   a6a16924b84ea7b3b262297663b5891bbb55efdd
SHA256: ee605e633c6fda51b36fdd396a1c4573dbab40dd020ede1d06a4afea2efc30cb
header: IPGE, revision 10
```

**IPGE alone does not identify USA.** European English and USA/Australia can
share that code. The original supplied Europe SHA1 was
`27a25c23aa1c0ecabe48a30a004b96c9dbc97730`; do not mislabel it as USA.

The backup save is **524288 raw battery bytes despite its `.dsv` suffix**.
SHA256: `10a9cb080b6713c85700750e12a00ddc15e014f679d9c247939387a7848c1733`.
Do not truncate it or assume it needs a DeSmuME footer stripped. The replay
script imports a temporary copy through the emulator's raw-save API. Cross-region
save migration and save/write/reload have not been established by this replay.

### Drive access lessons

This chat could download the shared files but exposed **no authenticated Drive
upload tool**, even after the user connected/tagged Drive. That observation is
specific to this chat; the receiving chat must inspect its own available tools
and configured authentication. The user reports another chat can upload.

A public folder editor link is not itself an authenticated API upload session.
Do not repeatedly ask the user to reconnect without checking actual tool support.
Do not request passwords/tokens in chat. If supported upload tools/authentication
are already available, the user has authorized upload to the folder above.
Preserve existing files, upload an explicitly named candidate, verify the returned
file ID/link and size (and downloaded hash if available), and report the actual
result. Do not claim success merely because a local file exists.

Historical download method: `https://drive.google.com/uc?export=download&id=ID`.
Large files can return a normal download-confirmation HTML form instead of ROM
bytes; follow its `download-form` action/hidden parameters to
`drive.usercontent.google.com/download`, retaining TLS/proxy verification.
Verify size/hash afterward. Receiving HTML is not a valid ROM download.

## Rebuild the exact partial candidate

Run from the repository root with Python 3.12 (the tested environment). Setup
installs hash-locked dependencies and runs the synthetic tests:

```sh
bash scripts/setup.sh
source .venv/bin/activate
romspeedup verify private/v3/europe-v3.nds --profile profiles/europe-v3.json
python scripts/build-v4-candidate.py private/v3/europe-v3.nds \
  --feature faint-motion --feature battle-exit-palette \
  --feature ordinary-wild-transition --out build/v4-handoff-001 --bps
sha256sum build/v4-handoff-001/candidate.nds
```

The output directory must be fresh. Expected target SHA256:

```text
cdf7059ea67936816d724df8d5336e1b5c364a5d41acef7e4e5f8280db6e9e92
```

Outputs: `candidate.nds`, `candidate.bps`, `build.json`. The BPS applies to the
exact **V3**, not the unedited European ROM. Expected BPS size: 122607 bytes.
The builder enforces exact source/overlay hashes, guarded instructions,
same-size edits, compression/container integrity and unchanged unrelated assets.
Never bypass source/guard checks to make an unexpected ROM pass.

The nine changed bytes are in compressed ARM9 overlays 12 and 120. They preserve
V3 ARM9, ARM7, data/assets and other NitroFS files byte for byte. Recompressed
overlay sizes remain 162460 and 3740 bytes. Use one `--feature` at a time for
isolated builds. See the manifest for exact addresses and instruction guards.

Historical delivery folder in this workspace:

```text
build/user-delivery/SoulSilver_Europe_V4_PARTIAL_EXPERIMENTAL.nds
build/user-delivery/SoulSilver_Europe_V4_PARTIAL_EXPERIMENTAL.bps
build/user-delivery/SoulSilver_Europe_V4_PARTIAL_EXPERIMENTAL.zip
build/user-delivery/READ-ME-FIRST.txt
build/user-delivery/build.json
```

These ignored files will not exist in a fresh checkout. The ZIP contains the
ROM, BPS and warning readme; package equivalent private outputs if needed, with
the same explicit partial label and limitations. Do not overwrite the user's
only ROM or save. Do not call the candidate completed V4.

## Emulator setup and validation

```sh
bash scripts/setup-emulator.sh
.venv/bin/python -m pip install --require-hashes -r requirements-emulator.lock
source scripts/emulator-env.sh
.venv/bin/python scripts/validate-faint-instructions.py \
  private/v3/europe-v3.nds build/v4-handoff-001/candidate.nds \
  --out artifacts/handoff-faint-instructions.json
```

The prepared standalone DeSmuME CLI is 0.9.13, but `py-desmume` 0.0.9 bundles
**0.9.12**. Controlled frame comparisons used the same 0.9.12 core, interpreter
mode, under Xvfb. Do not compare frame timing across these different backends.

Fresh-boot captures must use separate processes and a reviewed, recognizable
baseline title screen (matching blank screens do not count):

```sh
xvfb-run -a .venv/bin/python scripts/compare-boot.py \
  --capture private/v3/europe-v3.nds --out artifacts/handoff-boot-v3.png
xvfb-run -a .venv/bin/python scripts/compare-boot.py \
  --capture build/v4-handoff-001/candidate.nds --out artifacts/handoff-boot-v4.png
.venv/bin/python scripts/compare-boot.py --compare \
  artifacts/handoff-boot-v3.png artifacts/handoff-boot-v4.png
```

For private battle replay commands, see `docs/v4-experimental.md`. Both baseline
and candidate need the **same copied battery save and an overworld checkpoint
before the battle overlays load**. Historical checkpoint:
`artifacts/v4-research/pre-walk.dst`; scenario:
`tests/scenarios/cave-battle.json`. Neither the checkpoint nor evidence is in Git.
If unavailable, create a new disposable overworld checkpoint and suitable inputs,
then capture a new baseline. Do not claim the historical replay was reproduced.
Replay hooks verify that edited overlay instructions actually loaded from the
selected ROM, so a source savestate cannot silently supply original battle code.

Historical evidence, not a claim of fresh verification in the receiving chat:

- 44 synthetic tests; 24 actual-Thumb faint instruction cases with graphics/API
  stubs; deterministic ROM/BPS rebuild and independent BPS CRC/target validation.
- Fresh-boot title images reviewed, baseline/candidate pixel difference 0.0.
- Five controlled Union Cave wild-battle replays: V3, each feature separately,
  and combined. All returned to the cave with zero loaded-code mismatches.
- Ember remained 35 callback visits over a 36-frame span. HP and EXP ordered
  state/relative-frame traces matched V3. 27 EXP was observed in both builds.
- Wild callback span 80 → 77 frames; faint shadow visits 3 → 2 and sprite visits
  8 → 6; cry wait retained at 70 visits; exit span 16 → 9 frames.
- Original ROM/save hashes were unchanged. Sound was muted: this does not verify
  audible music/cry behavior. Callback visits, frame spans and wall time differ.

Still needed: attack implementation; more ordinary/special encounters, trainer
introductions, entrance/switch timing, multiple attacks and double battles,
audible music/cries, save/write/reload, progression checks and Delta testing.

## Remaining engineering: selective attack speed

Overlay 12 dispatcher `ov12_0225FD14` invokes overlay 7's `ov07_0221C394` in its
animation wait states. The latter updates the animation-script function.
Independent visual tasks are also created through `ov07_0221BE68` on the shared
main SysTask queue. Increasing only interpreter updates or reducing script waits
does not consistently accelerate all visual effects.

A safe 3/2 hook still needs scoped ownership/timing for a move's visual tasks,
correct completion/destruction, and separation from secondary effects reused by
entrances/switches. Do not accelerate the whole queue/main loop. This is an
unresolved implementation task, not evidence that selective speed is impossible.
Preserve all unaffected behavior and test each new modification independently
before combined regression tests. Update traces/tests intentionally if attacks
are implemented: the current replay comparator requires attacks to match V3.

Research used `pret/pokeheartgold` commit
`6988158691eb6178cff697cda0428045ddcba5fb`; historical checkout was
`/tmp/romspeedup-hgss-source`. It may not persist. Consult tracked research/license
notes; do not assume USA decompilation addresses apply to European overlays.

## Git workflow and reporting

The user authorized feature branches, commits, pushes and reviewable PRs without
asking at every step. Do not merge unverified/broken changes. Historical PR stack:

- PR #1: `feature/patch-pipeline` → `main`
- PR #2: `feature/v3-baseline` → `feature/patch-pipeline`
- PR #3: `feature/v4-selective` → `feature/v3-baseline`

All were drafts/unmerged at handoff; check live state before acting. A checkout
of `main` alone lacks the implementation. Continue on an appropriate feature
branch, run necessary checks, update documentation/status and create/update a PR.
Keep ROMs/saves/patch binaries out of Git; `scripts/check_assets.py` checks tracked
files. A docs-only handoff does not require rerunning emulator scenarios.

Report what was implemented, what was actually tested, what remains blocked and
where the user can obtain the private build. Do not equate a successful upload,
boot smoke test or automated tests with completing every V4 requirement.
