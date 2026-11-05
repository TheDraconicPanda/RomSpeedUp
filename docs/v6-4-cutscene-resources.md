# V6.4 cutscene resource lifetime

V6.3 can freeze when an overworld event starts, including the Vermilion Suicune
scene. The supplied current battery save reproduces it before dialogue begins.
The earlier pocket-submitted timing/V6.2 answers were withdrawn and are not
evidence. Local testing also finds the race in V6.2 under a different schedule.

## Cause and correction

Field overlay 1's `ov01_021F197C` queues a texture upload on VBlank and cleanup
on VWait. Its environment is incorrectly initialized as already ready. Retail
normally uploads before cleanup, but the accelerated field loop can run VWait
before the next physical VBlank. Cleanup then frees the texture source before
upload. The actual save trace reaches `GF3dGfxRawResObj_LoadTex`'s assertion at
0x020259C0 after cleanup; game updates stop while interrupts continue.

V6.4 changes the Thumb instruction at 0x021F198C from `movs r0,#1` to
`movs r0,#0`. The existing upload callback marks it ready after loading. Cleanup
waits for that completion. Assertions remain enabled and scripts are unchanged.
The builder pins the exact V6.3 baseline, checks that only this instruction
changes in decompressed overlay 1, recompresses within its existing slot and
verifies container readback. ARM9, ARM7, sound, other overlays and all other
NitroFS payloads remain byte-identical to V6.3. Instant dialogue and battle text
behavior are retained; no RAM layout or movement calibration changes.

## Verification

DeSmuME 0.9.12 interpreter, actual candidate, fresh battery-save boot:

- The supplied save starts outside the ship in Vermilion. Normal movement
  triggers Suicune, Eusine dialogue completes, both depart and control returns.
  Readback confirms variables 0x4070/0x4071=0, 0x4086=1, hide-Suicune flag
  0x29F set and no active field task. A repeat records upload before cleanup,
  zero GF_AssertFail calls and continuing gameplay/audio updates. Walking after
  the scene succeeds.
- An older save, moved using the normal warp task to Victory Road 3F, exercises
  the rival event's start. Both old V6.2/V6.3 fixtures froze before dialogue.
  V6.4 progresses through the introduction into battle, with correct Sneasel and
  player Pokemon sprites and zero lost uploads for active battle sprites.
  Two discarded uploads belong to an inactive manager during transition.
  This fixture checks scene/battle entry, not a completed rival battle.
- In-game saving after Suicune changes the disposable battery save; a separate
  fresh boot/import restores Vermilion and all completed event flags. The source
  save is unchanged.
- Actual native initializer/upload/cleanup instructions pass 57 task-order
  cases: baseline unsafe in 26, candidate unsafe in zero. Only allocator,
  task-queue and texture APIs are mocked.
- All 98 printer cases and 3663 scheduler/context/publication/state/movement/
  cipher/menu cases pass. Pipeline: 53 tests pass.

Private traces, screenshots and saves are under `artifacts/v64/`; source inputs
are unchanged. Full-game and Delta testing remain pending. Keep Fast Forward
OFF and boot with a battery save; avoid quick savestates from earlier builds.
Heavy cities can still run below the nominal 2x target.

```sh
.venv/bin/python scripts/build-v64.py private/original/user-original.nds \
  --out build/my-v64
.venv/bin/python scripts/validate-v64-resources.py \
  build/v63-candidate-002/candidate.nds build/my-v64/candidate.nds \
  --out artifacts/my-v64-resources.json
.venv/bin/python scripts/validate-v63-text.py \
  build/v62-candidate-002/candidate.nds build/my-v64/candidate.nds \
  --out artifacts/my-v64-text.json
.venv/bin/python scripts/validate-v61.py private/original/user-original.nds \
  build/my-v64/candidate.nds --out artifacts/my-v64-regression.json
.venv/bin/python -m pytest -q
```

Source SHA256:
`94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`.
V6.4 SHA256:
`b12b08cb3529381dfc29299cb06ee78f15bdd495a8740fc38c342185a85ebecc`.
Both ROMs are 134217728 bytes. No user save is included in delivery.

## Confirmed Drive delivery

[Download V6.4](https://drive.google.com/file/d/1sKDsOvTrw43Yjs1R7yfvEIsN-qCeTErL/view?usp=drivesdk).
Drive confirms creation and separate metadata readback verifies exact name,
60679586-byte size and authorized parent folder. ZIP SHA256:
`56857e32733b962f48005111aadbf63378a11f7a8ac69adfabed671d6add60e5`.
Private package: `build/v64-delivery/`, ROM/readme/checksum/report only.
