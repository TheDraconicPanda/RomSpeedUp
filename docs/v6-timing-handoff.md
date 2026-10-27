# V6 timing research handoff — 2026-10-27

**V6 is unfinished. No V6 ROM or ZIP has been delivered or uploaded. Do not treat any prototype as a release.**

The user requested a new version, "Pokemon SoulSilver V6", based on the supplied original European ROM, with everything at 2x except music. They find normal speed slow and Delta's presumed default 3x comfortable but too frantic for precise movement.

## Latest steering and blocker

The user confirmed that long-pressing Fast Forward does **not** offer a 2x choice; they only have the default speed. Do not build a solution requiring them to select Delta 2x.

Their exact iPhone/iPad model and Delta version are still unknown. A concise question asking for these is pending, because the presumed default 3x has not been established for their installation. Current Delta source selects 3x for A15+ and 1.5x for A11–A14 DS emulation, unless overridden; source is not evidence of the user's installed version/settings.

The managed workspace became unavailable. The last runtime status reported current observations, desired/observed running, but connectivity **offline**. Shell creation failed with an exec-server transport disconnection/recovery timeout. Available runtime tools expose status/diagnostics, not restart. Do not claim additional tests/builds occurred after that outage.

## Possible better approach with the user's existing default

If the actual default multiplier S is confirmed as 3, a new original-based ROM could target game timing 2/S (two-thirds of retail) and music tempo 1/S (one-third), then use Delta's existing Fast Forward switch. This would target 2x gameplay and 1x music without a selectable Delta 2x option.

This is a new, **unimplemented and untested** approach. Do not claim it works yet. A three-VBlank-per-game-update limiter would target 20 virtual updates/sec; Delta 3x would yield 60 real updates/sec, versus retail 30 at 1x, with every frame rendered. It should avoid the ROM-only prototype's catch-up rendering problems, but must be measured under load. Confirm S first.

DeltaCore's current AudioManager uses AVAudioUnitTimePitch and assigns its rate to the emulator rate. Pitch stays independent of the time stretch; do not assume an octave/pitch correction is necessary. Reference:
https://github.com/rileytestut/DeltaCore/blob/869042a5699b19df3cf9f3369a950737ff818149/DeltaCore/Emulator%20Core/Audio/AudioManager.swift

A separate optional question about whether cries/effects should also remain normal was not answered. The original explicit request only excepted music. Do not silently declare a new audio preference.

## Original input and privacy

Exact user-supplied original:
- Drive ID: 19F-mc9FZqzuYkYoZANYuvnRwvw5vWcYK
- Name: 4840 - Pokemon - SoulSilver Version (v10) (E).nds
- Size: 134217728
- SHA256: 94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17
- SHA1: 27a25c23aa1c0ecabe48a30a004b96c9dbc97730
- Decompressed ARM9 SHA256: 534df6737a9a852bf24c9e63e93453897d9018a17e0685346fd37050123305a5
- Workspace path before outage: /workspace/RomSpeedUp/private/original/user-original.nds

It was downloaded and verified byte-for-byte. The authenticated Drive connector fetched it, but its streamed file was 128 MiB, beyond the local downloader's documented 32 MiB limit. Direct shell network was initially sandbox-blocked. A command with scoped additional network access subsequently downloaded it from the supplied Drive link, followed the download confirmation, and verified the exact hash. No third-party ROM source was used.

The V6 prototypes start from this original, not V5.2. Do not carry over V3 instant text, V4 partial battle timing or V5 city movement changes. Pure, equivalent code compaction was used for helper allocation.

Keep ROMs, BPS files, saves, WAVs, screenshots and checkpoints private and outside Git. No original ROM/save was overwritten. Never publish them as GitHub artifacts.

## Workspace/Git state before outage

- Repository: /workspace/RomSpeedUp, TheDraconicPanda/RomSpeedUp.
- Local branch: feature/v6-double-speed.
- Its parent is local commit f378c5b, completing the previously delivered V5.2 follower work; that commit had not been confirmed pushed.
- V6 prototypes/reports were all under ignored artifacts/v6-prototype/, not committed.
- This remote research branch was created separately from known remote V5.1 commit 230eabe8985fc5d29ed16dda0325abbc77aeafad so these notes survive the outage. Do not overwrite the local feature branch with it; preserve/reconcile local work if the workspace returns.

Latest delivered version is still V5.2:
https://drive.google.com/file/d/1xttJGeUfld7ppcbPYlZnr6vkwubBMaHR/view
Drive metadata confirmed 61744321 bytes in folder 1J7caSyzIpCCnbDhVRo7x4OX5CEijfpIV.
V5.2 ROM SHA256: a5ba152ccfa0a794396e8b3d428822d1226b78676873764f312795ded7bd1539.

## Timing findings

Original NitroMain uses two VBlank waits per logical update and normally updates gameplay at 30/sec. Existing V3 removes the main frame-counter reset, allowing varying update rates depending on scene cost. This explains the earlier route/city mismatch; an uncapped patch is not a uniform 2x implementation.

European ARM9 research addresses:
- Main loop start: 0x02000DAC.
- Main_RunOverlayManager: 0x02000E84.
- First wait conditional branch: 0x02000DF8.
- First OS_WaitIrq call: 0x02000DFE.
- Handle3DBufferSwapRequest call: 0x02000E10, original target 0x02026E60.
- Second wait call: 0x02000E1E.
- Main frameCounter reset: 0x02000E28.
- Callback argument load and indirect call: 0x02000E38..0x02000E3C.
- Main DoSoundUpdateFrame call: 0x02000E3C, target 0x02004208.
- VWait task queue call: 0x02000E42, target 0x0201F880.
- OS_WaitIrq ARM entry: 0x020D0E6C.
- gSystem: 0x021D110C. Physical frameCounter is +0x30; software vblankCounter is +0x2C.
- Field draw call in overlay 1: 0x021E6022 -> 0x021E6220.
- Original SpriteList render-function table: 0x020F6314; active render pointer at +4 is 0x02024EB5. Animation is called separately, so a render-only gate preserves animation advancement.
- NNS_G2dDrawSpriteFast ARM entry: 0x020B7418.
- NNS_G3dDraw ARM entry: 0x020BFCC8.
- Both NNS entries start with push {r4,lr}, suitable for a guarded ARM B trampoline that replays the prologue before returning to entry+4.
- Music tempo wrapper GF_SndHandleSetTempoRatio: 0x0200596C. It calls GF_GetSoundHandle, then NNS_SndPlayerSetTempoRatio. This is a research lead for compensation, not implemented.
- Source sound handles: FIELD=0, PV=1, ME=2, SE=3..6, BGM=7, CHORUS=8. Radio player is 9. Classify actual music/ambient/fanfare/radio usage before modifying ratios; do not assume all handles are BGM.
- Only two known source callers of GF_SndHandleSetTempoRatio were found, in overlay 91. Preserve intentional dynamic tempo changes rather than blindly overwriting them every update.

Source research checkout before outage:
 /workspace/research/hgss-v5
Pinned pret/pokeheartgold commit:
 6988158691eb6178cff697cda0428045ddcba5fb

## ROM-only prototype progression (none eligible for delivery)

Artifacts in /workspace/RomSpeedUp/artifacts/v6-prototype/:
- build.py / prototype.nds: alternating wait/audio gates; only 240 gameplay updates over 360 hardware frames, versus original 180 (1.33x).
- build2.py / prototype2.nds: retained physical counter across fast ticks; still 240.
- build3.py / prototype3.nds: added field draw gating; still 240.
- build4.py / prototype4.nds: paced using physical counter; cave 296, actual Goldenrod 251 updates over 360 (not uniform 2x).
- build5.py / prototype5.nds: adaptive game clock; crashed DeSmuME's DMA assertion. Cause: replacement callback gate omitted the original load of the callback argument from gSystem+4. Do not use it.
- build6.py / prototype6.nds: fixed callback argument and bounded audio catch-up. Measured 358 gameplay updates/360 hardware frames in cave and Goldenrod, versus original 180. Audio callbacks remained 180. However rendered-frame frequency was very low.
- build7.py / prototype7.nds: added pure render gates for both NNS ARM entries, the active SpriteList render function, and the main swap handler. Gameplay measured 357 updates/360 frames in cave and Goldenrod, audio 180/179 versus original 180. Render frequency improved but remained insufficient for a comfortable release (estimated around 9–10/sec from queue counts; moving visual verification still needed). Do not present this as a finished playable V6.

Prototype 6 SHA256:
07e937f58d63205d1ae5d6d72ababc44683518e204ec9110d420d7985a1ecefb
Prototype 7's ROM hash was not separately recorded in this handoff; recover it from its trace.json and recheck the actual file.

Prototype 7 allocation:
- Compacted 28 original movement-init wrappers in the original 584-byte slot 0x02062568..0x020627B0 into seven 36-byte direction groups (252 bytes), preserving original velocities, durations, selectors and endpoints.
- Helper allocation follows those groups.
- Twenty mutable RAM bytes at END-20: render flag, virtual ticks, last audio hardware tick, initialized flag, present flag.
- Adaptive clock targets one game update per physical VBlank (60/sec versus original 30), drops catch-up debt after discontinuities >8 frames, bounds sound catch-up to four calls, and runs sound at one update per two physical VBlanks.
- Render-only catch-up gates suppress geometry; genuine animation update paths continue.
- VRAM callback and VWait transfers are gated to presentation ticks. The callback gate must replay ldr r0,[r4,#4] before tail-calling r1.
- Physical frameCounter is kept monotonic by replacing its main reset; first wait is removed, final wait is gated. Original logical counter paths are adjusted.
- No ARM9 section/RAM/BSS expansion. Original 12-byte Nitro footer is relocated with the packed ARM9; header size and CRC are updated. Overlay 1 only changes the field-render call. Other files/ARM7 remain original.
- Prototype 7 packed ARM9: 762700 bytes (original slot capacity 762880 before next table; include the footer when checking capacity).

The important outstanding problem is render smoothness/performance, not proving that the software clock can tick approximately twice as fast.

## Native and live evidence

Private validators validate6.py and validate7.py:
- 4320 actual-instruction clock state/wrap/stall cases.
- 112 original-versus-compacted movement cases.
- Conditional wait, field render, callback, VWait, sprite and swap gate checks.
- Both ARM trampolines tested for arguments, stack/prologue and interworking.
- The final print still says "8 gate cases"; prototype 7 actually exercised six gates x two states, plus four ARM-entry cases. Correct reporting before formalizing.

Live replays use DeSmuME 0.9.12 interpreter with SDL_VIDEODRIVER=dummy, controlled hardware frame counts and restored/verified target code after loading checkpoints. WAV core recording was enabled through exported C++ symbols:
- _Z9WAV_BeginPKc7WAVMode (mode 0 = core)
- _Z7WAV_Endv
Captures were 44.1 kHz stereo 16-bit PCM.

Original versus first prototype cave music stayed aligned at the same elapsed hardware time: short-window correlations approximately 0.9999996 at 2 seconds and 0.9999978 at 4 seconds, near-zero lag. Later prototype WAVs were captured but had not yet been compared numerically. Do not generalize the first prototype's audio result to all later revisions or all songs.

Original baseline idle: 180 main/gameplay and sound callbacks over 360 hardware frames in both Union Cave and actual Goldenrod. Later prototype counts are above. Shader/render cadence and animation appearance must be checked separately from update counters.

A real original-ROM Goldenrod checkpoint was created using a disposable copy of the user's save and a temporary debug warp thunk:
- /workspace/RomSpeedUp/artifacts/v6-prototype/goldenrod-state/goldenrod-original.dst
- Map 76, position approximately x358,z370, night; screenshot manually confirmed Goldenrod.
- Used ordinary sub_020538C0 warp task, then restored injected NitroMain-init code/main call before saving the checkpoint.
- This is actual city geometry, unlike V5.1's synthetic cave map-type test.
- Original source ROM/save/checkpoints were not overwritten.

Replay helper: artifacts/v6-prototype/replay.py
Arguments: ROM output-name kind [checkpoint checkpoint-ROM].
kind idle records 360 frames; move records 90. Defaults use the earlier V5 Union Cave checkpoint and its exact V5 source ROM, then restore differing target ARM9/overlay-1 code with checks.
For actual city use the Goldenrod checkpoint and original ROM as checkpoint-ROM.
The script records trace.json, music.wav and private screenshots.

Pending verification before any V6 delivery: smooth movement/follower/turn/stop behavior, menus and tap handling, a battle/attack and result text path, audio comparison for the final design, fresh boot, independent BPS/container checks, and save/write/reload. No V6 save/reload test or full battle regression was completed.

## Recovery priorities

1. Confirm the user's device and installed Delta version/default multiplier; do not re-ask about selecting 2x.
2. Recover the workspace if available and preserve the local V5.2 commit and ignored V6 research. Never overwrite the user's original/save.
3. Decide implementation based on the confirmed multiplier and the user's existing Fast Forward workflow. The default-3x compensation approach is promising but untested.
4. Produce a concrete, measured build; no prototype can be labelled finished V6 yet.
5. Upload only an eligible tested private ZIP to the authorized Drive folder; read back the returned ID, parent and size before claiming success.
