# V5.1 experimental — slower city motion and sprite clock correction

The player found V5 city motion too fast and reported a frozen/sliding player
sprite. They requested a reduction of 0.5 from the nominal 2x setting. They also
reported slowness in some surfing areas; a specific location is still unknown.

## Behavior

City walk/run spatial deltas now use **1.5x** their V3 values, down from 2x.
Movement is quantized to whole advancing callbacks and complete tiles: walking
takes six callbacks (five 3-unit deltas and a final 1-unit delta), running takes
three (two 6-unit deltas and a final 4-unit delta). Both end at exactly 16 units.
The average across these advancing callbacks is therefore **4/3x**, not exactly
1.5x. Initialization, idle updates and Delta's scene cadence further affect real
time. This is a conservative speed calibration, not measured route/city parity.

The ordinary walk/run sprite animation clock receives a matching 1.5x increment
for the same eligible city player. V5 shortened movement while retaining the old
animation clock, so running could end a tile before reaching its next pose. Live
replay reproduced repeated early poses in V5; V5.1 reaches subsequent poses.
The earlier instruction checks only preserved the animation selector; that was
insufficient to establish correct visible animation.

Eligibility remains player identity, on-foot state, normal movement enabled and
outdoor city/town map type 1 (including Bellchime Trail). Routes, interiors, NPCs,
bike/surf states and scripted control keep their baseline behavior in instruction
checks. Final tile clamping follows the initialized movement even if eligibility
changes mid-tile, avoiding overshoot after a control, state or map change.

V5 result text and all battle changes are retained byte for byte. Surfing is
unchanged. Its ordinary selection uses commands 16–19 and four 4-unit advancing
callbacks on the sampled maps; the location-dependent slowdown remains unresolved.
There is no new global acceleration. Attack acceleration remains unimplemented.

## Allocation and guards

Seven existing direction-wrapper families in ARM9 `0x02062568..0x020627B0` are
compacted from 584 bytes to 252. Each four-direction group shares its original
animation, velocity, duration, stack argument and return path. The 28 initialization
table pointers are redirected; original references and direct branches are checked.
The remaining original slot holds the city predicate, initializer, final-delta
clamp and sprite-speed helper. No ARM9/overlay RAM or BSS boundaries move.

The normal advance's call at `0x02062524` clamps only the selected walk/run commands
with the new velocities on their last callback. Field overlay 1 changes only the
two guarded sprite-advance calls at `0x021F8014` and `0x021F82EA`. These ordinary
walk/run render handlers retain the object in r5, used by the shared predicate.
The old V5 city helper is unreachable from the replaced wrappers; its slot and the
adjacent text-yield helper remain intact.

ARM9 packs to 762760 bytes; the original 12-byte Nitro footer follows it inside
existing ROM padding. Overlay 1 packs to 110500 bytes. Builders verify exact source
identity, slot boundaries, compressed readback, section/RAM/BSS layouts, checksums,
unselected files and preserved ARM7. Overlay 12 and battle scripts do not change.

Source: delivered V5 SHA256
`4872087cab43c11df33507aaef88186208a4a2c1ac9bab9abfe66835fbe16e7b`.
Deliverable: `build/v5-1-002/candidate.nds`, SHA256
`c8efa1170ca2969f43899e2373bb78f884414745c26c807e6ec3c32e0ce7b7a4`.
An earlier private `v5-1-001` was superseded by the mid-tile clamping correction.

```sh
.venv/bin/python scripts/build-v51.py build/v5-002/candidate.nds --out build/my-v51
.venv/bin/python scripts/validate-v5.py build/v4-handoff-001/candidate.nds \
  build/my-v51/candidate.nds --movement-revision v5.1 --out artifacts/my-v51/instructions.json
.venv/bin/python scripts/validate-v51-sprites.py build/v4-handoff-001/candidate.nds \
  build/my-v51/candidate.nds --out artifacts/my-v51/sprites.json
```

## Evidence and limits

- 2016 movement cases cover all 28 compacted commands, six map IDs, three avatar
  states, player/NPC identity and movement-enabled/disabled cases. Unselected
  positions, durations, velocities, animations and completion match the baseline;
  selected city steps retain endpoints and the intended final shorter delta.
- 864 real sprite-dispatcher cases compare the unchanged backend call sequence,
  selectors and object memory, with only eligible animation increments changed.
  Graphics backend calls are stubbed for these instruction experiments.
- 96 initialized movements retain exact endpoints after mid-tile control, state
  and map eligibility changes. The previous 640 state, 1400 wait, 4800 message,
  24 printer and 24 script cases pass, as do 44 pipeline tests.
- Fresh DeSmuME 0.9.12 interpreter boot matches the reviewed V5 title exactly.
  Independent BPS decode/CRC checks reproduce the candidate.
- Live DeSmuME replays use a disposable checkpoint from a copy of the user's
  backup save. `scripts/replay-city-motion.py` checks loaded V5 code, restores and
  reads back only known target code ranges, then simulates city eligibility by
  changing the cave map's type **in RAM**. Both walking and running execute their
  expected commands. Walking explicitly disables locked running shoes in RAM;
  an earlier nominal walk replay actually ran and is excluded from walk evidence.
  The corrected replays show 6144 animation increments versus 4096 in V5, and
  advancing later poses instead of V5's repeated early running phase. Screenshots
  were inspected. ROM, checkpoint and original battery-save files remain unchanged.
- 64 additional stubbed surfing selector/step cases across Cianwood, Olivine,
  Ecruteak, sea routes 40/41, routes 42/43 and Union Cave use the same ordinary
  surf command and per-update speed. This does not measure Delta performance.

The live city condition is synthetic inside the cave scene; it does not verify
Goldenrod geometry, Delta cadence, follower/camera interactions, collisions,
doors/warps, save/reload or audio. Keep previous ROM/save backups and test walking,
running, stopping, turning, doors and following in an actual city on Delta.
