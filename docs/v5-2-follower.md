# V5.2 experimental — city follower timing

The player reports V5.1 is much better, with the remaining visible issue that
their Pokémon falls behind in cities. V5.2 retains the V5.1 player calibration
and gives ordinary active following movement the same city timing.

## Cause and behavior

Live V5.1 instruction traces show player running command 88 using velocity 24576
and three advancing updates, while the follower uses fast-walk command 16 at
16384 and four updates. Walking similarly uses six player updates versus eight
follower updates. Successive steps make the gap grow.

V5.2 scales the registered active follower's ordinary walk commands 12–15 and
fast-walk commands 16–19 by the same 1.5x spatial delta as the player. Final deltas
are clamped so each tile remains exactly 16 world units: six walking advances,
three fast-walking/running advances. Existing player walk/run behavior is retained;
player fast-walk commands 16–19 and follower player-run commands 88–91 are excluded.

The additional follower predicate requires pointer identity with the field's
registered follower, active byte 1, movement type 48, neither movement-paused nor
flag 30 set, player on foot, normal player control enabled, and city map type 1.
NPCs, inactive/unregistered followers, alternate movement modes, scripted control,
bike/surf states, routes and interiors retain their previous tested behavior.
Initialized tile endpoints remain correct if eligibility changes mid-step.

Ordinary follower pose clocks also receive a 1.5x increment. Generic walk/fast-walk
sprite handlers and the follower body-animation path are hooked. Only eligible
moving poses 3/4 are scaled; idle, interaction and other special poses pass through.
The follower body renderer stores its sprite at object+108, unlike the player's
object+10C layout; live tracing uses the actual graphics callback to select it.

The original following logic still chooses directions and paths. No teleport,
position snapping or artificial distance correction is added. Battle overlay 12,
scripts, V5 result text and other NitroFS assets remain byte-identical to V5.1.
Surfing remains unchanged; the earlier location-specific slowdown is unresolved.

## Allocation and reproducibility

The implementation reuses the same guarded 584-byte compact-wrapper slot as V5.1.
Helpers and branches are rebuilt within it; no RAM/BSS or section boundaries move.
Overlay 1 has the existing two player sprite hooks retargeted plus four guarded
follower sprite calls: 0x021F7A10, 0x021F7A4C, 0x021F8E2E and 0x021F8E60.
ARM9 packs to 762848 bytes, followed by its preserved 12-byte Nitro footer, inside
the original 762880-byte slot. Overlay 1 remains 110500 packed bytes. Exact source,
wrapper/instruction guards, slot capacity, decompression, layout and asset checks
are required. The V5.1 default builder still reproduces its delivered SHA256.

Source SHA256:
`c8efa1170ca2969f43899e2373bb78f884414745c26c807e6ec3c32e0ce7b7a4`.
Target `build/v5-2-001/candidate.nds`, SHA256:
`a5ba152ccfa0a794396e8b3d428822d1226b78676873764f312795ded7bd1539`.

```sh
.venv/bin/python scripts/build-v52.py build/v5-1-002/candidate.nds --out build/my-v52
.venv/bin/python scripts/validate-v52-follower.py build/v5-1-002/candidate.nds \
  build/my-v52/candidate.nds --out artifacts/my-v52/follower.json
.venv/bin/python scripts/validate-v5.py build/v4-handoff-001/candidate.nds \
  build/my-v52/candidate.nds --movement-revision v5.1 --out artifacts/my-v52/regression.json
```

The `--movement-revision v5.1` option checks the retained player behavior. New
follower behavior is tested separately against V5.1. Both output paths must be fresh.

## Validation

- 6336 actual-instruction follower movement cases cover selected and excluded
  commands, all directions, city/route/interior maps, player states, control,
  active state, registered identity, movement type and pause flags. Selected
  steps match player timing and preserve selectors, endpoints and final deltas;
  excluded cases match V5.1.
- 1728 generic follower sprite cases and 80 moving/idle/special-pose helper cases
  check the intended clock change and pass-through behavior with backend stubs.
  32 interrupted-step cases retain exact tile endpoints.
- The retained 2016 player movement cases, 864 player sprite cases, 96 player
  interruption cases, 640 state cases, 1400 wait cases, 4800 result selection
  cases, 24 printer cases and 24 script cases pass. All 44 pipeline tests pass.
- Fresh DeSmuME 0.9.12 title capture matches the reviewed V5.1 title exactly.
  Independent BPS decoding/CRC verification reproduces the target ROM.
- Live cave replays simulate the city map type in RAM, restore and verify exact
  target code after loading the disposable checkpoint, then trace both objects.
  V5.1 running gap grew past two tiles (44–46 world units in sampled frames).
  V5.2 straight running stays around 20–22 units after starting, returning to
  16 units when stopped. Walking stays around 17–19 units. Both objects use the
  intended matching velocities/durations and the moving follower clock advances
  at 6144 rather than 4096. Before/after screenshots were reviewed.
- An 84-frame run/stop/reverse/stop replay returns to 16-unit separation after
  both stops, with north and south follower commands observed. Private original
  ROM/save/checkpoint files remain unchanged.

The city condition is synthetic in a cave, not actual city geometry or Delta.
Doors/warps, companion interaction, special following effects, collision/camera,
save/reload, audio and additional species still require gameplay coverage. On
Delta, check walking, running, stopping, turning and entering/leaving a city.
