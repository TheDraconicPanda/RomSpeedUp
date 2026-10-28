# V4 handoff for another Codex chat

Updated 2026-10-24. This is project context and reproducible guidance; check the
current checkout, inputs and tools before acting on historical observations.

## Corrected V6 requirement — 2026-10-28 (current)

The player clarified that Delta's speed was only a comparison. They want the
**original ROM itself to run gameplay at 2x with ALL sounds at normal speed,
and Delta Fast Forward OFF**. The delivered Delta-3x compensation ROM below
does not satisfy this clarified requirement. Do not deliver it again as the
requested standalone V6. Work is on `feature/v6-rom-only-2x`.

Current experimental build `build/v6-native-001/candidate.nds`, SHA256
`e369d3d641551d4ca75cacc548608f5f6bdd66f45ff7bcaa960c655838cb1033`.
Reproduce with `scripts/build-v6-native.py` from the exact original Europe ROM;
see `docs/v6-rom-only.md`. Earlier prototypes remain private research.
The new build retains original sound assets/ARM7 and normal physical audio
cadence. Its virtual clock targets 60 updates/s, with graphics on alternate ticks.
Equivalent data cipher optimization passes 565 original/reference comparisons.
All 5653 native cases and 49 unit/pipeline tests pass.

Fresh target boot/import/field movement, trainer battle, attacks, enemy fainting,
in-game saving and fresh exported-save import/boot have been exercised. Cave
replay gives 1801 logic / 900 audio updates per 1800 hardware frames, near 2x;
Goldenrod moving replay gives 315 logic / 179 audio updates in 360 frames versus
retail 180 logic: measured **1.75x** in that heavy city. Report this limitation;
no claim that all scenes run at exactly 2x. Delta/full-game validation is pending.
Use battery-save import/fresh boot; old states can resume inside replaced code.
Verified delivery ZIP:
`build/v6-native-delivery/Pokemon_SoulSilver_V6_ROM_ONLY_2X_EXPERIMENTAL.zip`,
60679799 bytes, SHA256
`7bf31d7c26be4793c1125a754d8ab027b973b00f5d94c9ca30b4b93b8a26e8d7`.
It contains the ready ROM, readme, checksum and build report, with no save data.
Drive delivery of this corrected build is **not confirmed**: upload calls from
verified `/tmp` staging paths returned no connector result within 45/120-second
bounded waits. Subsequent exact-name searches returned no file. No permission,
quota or API error was returned, and no file ID exists to cite. The verified
local ZIP is ready for download; do not substitute the old Delta-3x Drive link.
Local implementation commit: `b5bdc48` on `feature/v6-rom-only-2x` (not pushed).

## Earlier V6 Delta compensation build — 2026-10-27 (superseded requirement)

The player requested a new build from the original Europe ROM for 2x gameplay
with normal music. They confirmed Delta's only available Fast Forward is 3x.
Current branch `feature/v6-double-speed`; see `docs/v6-delta-3x.md`.
V6 requires that default **3x Fast Forward enabled**. The original main loop
waits for three physical VBlanks per update (native 2/3 retail), while music
score durations are tripled (native 1/3 tempo). Thus it targets 2x gameplay
and normal score tempo under Delta 3x. Independent hardware timers/heavy scenes
may vary; music envelopes/portamento/fades are not fully time-stretched, and
effects/cries retain their assets and follow Delta's fast-forward audio.
Earlier ROM-only V6 prototypes are superseded and must not be delivered.

Build with `scripts/build-v6.py` from `private/original/user-original.nds`,
SHA256 `94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`.
Candidate `build/v6-3x-001/candidate.nds`, SHA256
`757eccf7f9846e32caeac9166f2353f9077aec85d9fb24eab73819f5bba9f228`.
V5 selective patches are not inherited. All non-sound NitroFS payloads,
ARM7, overlays, music banks/waves and effects are preserved and checked.

48 unit/pipeline tests and 640 movement-state + 48 pacing native cases pass.
Fresh target boot/import reaches the user's save; field movement, trainer
dialogue, battle entry/attacks/text, in-game saving and separate fresh battery
save reload were observed. Reloaded Continue time is 85:29 and resumes Union
Cave. Actual target Goldenrod loads through a disposable standard warp with
temporary code restored. Main updates are 120/360 frames in cave and city,
versus original 180/360. Actual target city movement replay runs 30/90 frames.
Delta hardware/audio listening/full-game validation remains pending.

**Import a battery save and fresh boot. Do not use old quick savestates.**
The sound archive grows and later files shift 67584 bytes; old states retain
obsolete cached NitroFS offsets and reproduced an instruction fault. Fresh
boots and checkpoints created by the actual V6 target do not show that fault.
Original user ROM/save were never overwritten.

Verified private delivery ZIP:
`build/v6-delivery/Pokemon_SoulSilver_V6_FOR_DELTA_3X_EXPERIMENTAL.zip`,
60695388 bytes, SHA256
`844fb12257614835deda54b92569768ba2b08a6f9b7b1fd95aceaa0871e06ac0`.
Contains ready ROM, readme, checksums and build report; no user save.
**Drive upload confirmed on 2026-10-28:**
<https://drive.google.com/file/d/1vXN7j74XGBHCOnKRh9TazrotbwR1J2ZF/view?usp=drivesdk>.
Metadata readback confirms the exact filename, 60695388 bytes and authorized
parent folder `1J7caSyzIpCCnbDhVRo7x4OX5CEijfpIV`. Earlier workspace-path upload
calls stalled without an API result. A retry using an identical, checksum-verified
copy staged at `/tmp/Pokemon_SoulSilver_V6_FOR_DELTA_3X_EXPERIMENTAL.zip` succeeded.
The underlying cause of earlier stalls is unconfirmed; no permission/quota/API
error was returned. The Drive folder is now under `05 - Projects & Development`
but retains the same ID. The local verified ZIP remains available.

## v5 follow-up — 2026-10-25

### V5.2 follower correction — 2026-10-27

Player reports V5.1 much better, but Pokémon lags behind in cities. Branch
`feature/v5-2-follower`; `docs/v5-2-follower.md` describes the scoped correction.
Build exact V5.1 with `scripts/build-v52.py`, which reuses the guarded V5.1 builder
with the follower option. Private `build/v5-2-001/candidate.nds` SHA256
`a5ba152ccfa0a794396e8b3d428822d1226b78676873764f312795ded7bd1539`.
Follower ordinary walk/fast-walk uses six/three advances, matching the unchanged
V5.1 player. Identity/active/type/pause/control/map guards and moving-pose clock
hooks retain other contexts. Native follower and retained regressions pass; live
synthetic-city cave replays keep a close gap and return to one tile at stops,
including a turn. Delta and actual city geometry validation remain pending.

Drive confirmed V5.2 ZIP upload on 2026-10-27, file ID
`1xttJGeUfld7ppcbPYlZnr6vkwubBMaHR`, 61744321 bytes, in the authorized folder.
<https://drive.google.com/file/d/1xttJGeUfld7ppcbPYlZnr6vkwubBMaHR/view>
ZIP SHA256 `403fcc30599adf654deac0ba7c82677448fec51e3d15ba4e3d83f055f1fb5d2d`.

### V5.1 correction — 2026-10-25

User reports V5 cities too fast and a frozen/sliding player, requests lowering
the 2x boost by 0.5. Branch `feature/v5-1-movement`; see
`docs/v5-1-movement.md`. New private candidate `build/v5-1-002`, SHA256
`c8efa1170ca2969f43899e2373bb78f884414745c26c807e6ec3c32e0ce7b7a4`.
Build from exact delivered V5 with `scripts/build-v51.py`. Spatial delta and
eligible walk/run animation clock use 1.5x; whole tile/frame rounding yields
six/three advances and a 4/3x average across advancing callbacks. Do not claim
exact 1.5x real-time speed. Sprite dispatcher, movement, mid-tile changes and
retained text checks pass. Live cave replay with a synthetic city type reproduces
the V5 pose problem and shows later poses in V5.1. This is not actual Delta/city
geometry validation. Surf stays unchanged: user reports some slow areas but has
not identified one yet. Ask for one example before choosing surfing scope.
V5 battle text is preserved exactly. Prior V5.1-001 is superseded.

Delivery attempt: `build/v5-1-delivery/SoulSilver_Europe_v5_1_EXPERIMENTAL.zip`,
61744989 bytes, SHA256
`1d0d1acb6409bfd40735502ca9b737c8c4a9cda7c01cbc170f58224d2a6c5f90`.
Drive upload to the authorized folder **failed**, HTTP 403
`storageQuotaExceeded`: "The user's Drive storage quota has been exceeded."
No new Drive file ID was returned; do not claim V5.1 is saved there. Retain old
files and retry only after capacity is available. Code is pushed; draft PR #7:
<https://github.com/TheDraconicPanda/RomSpeedUp/pull/7> against V5.

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

### V5.1 Drive retry succeeded — 2026-10-26

After the player freed storage, Drive confirmed upload and separate metadata
readback of `SoulSilver_Europe_v5_1_EXPERIMENTAL.zip`, 61744989 bytes, in the
authorized RomSpeedUp folder. File ID `1vHr8gUtOxbFt0rx5Cl_P1EdQekHnh0s1`.
<https://drive.google.com/file/d/1vHr8gUtOxbFt0rx5Cl_P1EdQekHnh0s1/view>
The local ZIP hash still matches the packaged V5.1 build. This supersedes the
earlier storage-quota delivery failure; no build changes were made for the retry.
