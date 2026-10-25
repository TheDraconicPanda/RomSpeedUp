# City versus route movement mapping — 2026-10-25

## Finding and decision boundary

**A city-scoped player movement adjustment has identifiable control points in the
supplied European ROM. Exact real-time parity with routes is not yet confirmed.**
This is mapping/research only. No ROM edits, speed patch, new game build or Drive
upload were made. The player asked to decide implementation after this mapping.

Ordinary unobstructed walking and running already use the **same parameters per
movement update** in cities and routes. There is no separate slower city duration
in this selector/step path to replace with a route constant. The reported apparent
difference must be investigated at the update-cadence, terrain/path or presentation
level; this experiment does not identify its cause. Variable workload under V3's
existing uncapped-frame change is a hypothesis, not a measured diagnosis of Delta.

Player observations: Delta; Goldenrod and Ecruteak (and reportedly all cities)
feel slower; V3 behaves the same; audio comparison unavailable. This establishes
that the symptom predates the partial V4 and manual-result-message changes.

## Verified European ARM9 map

Source and current build share decompressed ARM9 SHA256
`fe4737fabcc20b149250e6ec10b3e18bf862077788d223fdd67c6283bef8e3a9`.
Addresses below were checked against actual ROM instructions/data, then exercised
with Unicorn 2.1.4; they are not unverified USA-to-Europe address assumptions.

| RAM address | Role | Verified behavior |
| --- | --- | --- |
| `0x020F6BE0` | Map-header table | 24-byte records; map type is bits 8–11 of the word at record offset 20 |
| `0x0203B4DC` | `MapHeader_GetMapType` | Returns 1 for Goldenrod/Ecruteak, 2 for Routes 35/36, 4 for Ecruteak's Pokemart |
| `0x0205F52C` | `MapObject_GetFieldSystem` | Real accessor chain resolves the object's manager and field system |
| `0x0205D4B4` | Ordinary player movement selector | Clear ground chooses walking family `0x0C` or running family `0x58`, then direction |
| `0x0205D44C` | Player command decision boundary | Currently returns command argument `r2`; walking call is at `0x0205D574`; also used by surfing, which a future change must exclude |
| `0x0206234C` | Direction/command-family mapper | Converts family and direction into the selected movement command |
| `0x0206245C` | Shared movement-command dispatcher | Reads callback table at `0x020FD2D8`; shared with other objects, so not a global speed-edit target |
| `0x020624CC` | Step initialization | Stores animation, facing, fixed-point delta and remaining update count |
| `0x02062514` | Advancing callback | Applies delta, decrements the remaining count, completes the tile once |

Current-map access from the player object is available through
`MapObject_GetFieldSystem(object) -> fieldSystem->location (+0x20) -> mapId (+0)`.
The field system also holds the player avatar at `+0x40`, whose map object is at
`+0x30`, providing an identity check to distinguish the player from NPCs/followers.
Synthetic structures following these layouts were exercised through the real
object/field accessor; this is not a captured live Delta pointer chain.

Map IDs tested: Route 35 = 39; Route 36 = 40; Goldenrod = 76; Ecruteak = 78;
Ecruteak Pokemart = 79. **Map type 1 also includes Bellchime Trail (ID 6)**.
A future "cities only" implementation needs a reviewed map scope rather than
assuming every city/town-type map is an ordinary city street. Buildings are
separate maps and must not inherit a speed change merely from their city name.

## Measured instruction behavior

| Ordinary gait | Commands, by direction | City advancing updates/tile | Route advancing updates/tile | Delta/update |
| --- | --- | ---: | ---: | --- |
| Walk | 12–15 (`0x0C`–`0x0F`) | 8 | 8 | 8192 fixed-point = 2 world units |
| Run | 88–91 (`0x58`–`0x5B`) | 4 | 4 | 16384 fixed-point = 4 world units |

Both cover exactly 16 world units (65536 in 20.12 fixed point) per tile and
complete the step once. These are **advancing callback counts**, not milliseconds,
displayed frames, total start-to-start tile intervals or Delta performance numbers.
The initializer and movement completion scheduler have their own dispatch work.

For each ROM, 64 selector cases covered the four outdoor maps, four directions,
running input on/off and running shoes owned/not owned. Another 32 cases ran each
walking/running command through its actual initializer and advancing callback in
each outdoor map. The map getter and existing command pass-through were also run.
All source/current code guards, map data, selections and measured steps matched.

Environmental stubs: `0x0205DA34` supplies clear collision/terrain flags;
`0x0205E048` suppresses per-step gameplay notifications; `0x02061070` suppresses
terrain-height queries; `0x0205F484` suppresses a graphics callback. Selection is
captured at command issue before full field-object scheduling. Other movement
instructions run from the supplied ROM. These experiments do not test live scenes,
slopes, collision safety, follower behavior, camera tracking, doors, scripted
movement, bicycles, surfing, audible music, encounters or Delta frame cadence.

## Feasible approach if implementation is approved

Scope the player movement choice to explicitly selected city maps and ordinary
walk/run commands, preserving route/building/bike/surf/scripted behavior. A local
movement transform can shorten the tile duration while increasing its spatial
delta proportionally, leaving the tile endpoint, collision checks and completion
notification count intact. It must preserve the gait animation and follower/camera
coordination; simply substituting a different fast command can change animation.
Avoid shared queue/main-loop acceleration, map-header type rewrites and global
movement-table edits, which have much broader effects.

There is **no justified fixed multiplier yet**. If city and route movement update
rates are `C` and `R`, equal wall-time traversal with route duration `N` requires
approximately `N * C/R` city advancing updates, with appropriate rounding or a
fractional schedule. For example, a *measured* 30-versus-60 update rate would suggest
halving duration; this investigation did not measure such rates. A fixed multiplier
would not ensure exact parity if scene load changes that ratio.

Before implementing: capture ordinary walking/running tile traversal and update
cadence in Goldenrod, Ecruteak and adjacent routes under identical Delta/device
settings. Select the intended map scope and desired tolerance. A software-side
cadence trace on the same ROM can support diagnosis but cannot replace Delta data.

This map identifies the decision boundary and timing state, **not a ready code
injection site**. The original decision function has only four bytes. Overlay 1's
RAM+BSS ends at `0x02245B80`, exactly where overlay 2 begins: appending arbitrary
helper code there is unsafe. A future implementation needs an independently
audited allocation/relocation strategy and guarded recompression, followed by
collision, follower, camera, warp and save regression checks. No strategy has
been chosen or installed during this mapping-only task.

## Reproduce the read-only checks

Install normal project dependencies and locked optional emulator dependencies,
then run from the repository root:

```sh
.venv/bin/python scripts/map-city-movement.py private/v3/europe-v3.nds \
  --out artifacts/city-movement/v3-map.json
.venv/bin/python scripts/map-city-movement.py build/manual-result-text-001/candidate.nds \
  --out artifacts/city-movement/current-map.json
```

Output files must be fresh. The script requires the exact verified ARM9 digest,
writes JSON only and rechecks that input ROM bytes are unchanged. Reports contain
function-range SHA256 guards and numerical results; private ROMs/data remain
outside Git. No game binary instructions are embedded in this research script.

Research reference: [pret/pokeheartgold at the existing pinned revision](https://github.com/pret/pokeheartgold/tree/6988158691eb6178cff697cda0428045ddcba5fb),
specifically `asm/unk_0205CB48.s`, `asm/unk_02062108.s`, `asm/unk_0205FD20.s`,
`src/map_header.c`, `src/data/map_headers.h`, `src/map_object.c` and their structure
headers. Source remains an external research checkout at
`/tmp/hgss-movement-source`. No upstream implementation was copied into this repo;
the license limitations in `docs/research.md` still apply.
