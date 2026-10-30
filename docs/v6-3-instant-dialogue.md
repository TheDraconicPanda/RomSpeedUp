# V6.3 instant dialogue

The player confirmed V6.2 works correctly on Delta; the continued flashing report
came from an older build. V6.3 adds immediate ordinary dialogue pages outside
battle while retaining the working V6.2 graphics, gameplay and sound behavior.
Pages still wait for input, and explicit scripted pauses and scrolling remain.
Use normal emulator speed / Fast Forward OFF and a fresh battery-save boot.

## Implementation

Only the asynchronous printer's call at 0x02020312 and a 40-byte helper at
0x020626F4 change relative to V6.2, apart from the compressed-end pointer. The
helper reuses the unreferenced former V6.1 sprite gate; no code/RAM layout grows.
All NitroFS files, battle/field/menu overlays, sound assets and ARM7 are
byte-identical to V6.2. The builder checks the exact V6.2 hash, edit boundaries,
compression/readback, protected assets and executable layout.

For a callback-free task printer, the helper clears the ordinary glyph delay and
drains PRINT results until the renderer reaches an input/control event or EOS.
It copies the completed page before returning the original renderer status.
It preserves the asynchronous printer, explicit delayCounter waits, page/scroll
states, manual advancement and task destruction. It does not change the saved
text-speed option. Synchronous instant/no-transfer printers keep their original
path. Text with custom callbacks keeps its original pacing and callback visits.

All ordinary asynchronous battle-message entry points supply ov12_0223CF14
(Thumb callback 0x0223CF15), so the helper sends them through the stock path.
Battle menu labels and HP/name text use the unchanged synchronous path. Reference:
the pinned pret/pokeheartgold battle_system.c print helpers and text.c renderer.

## Actual verification

DeSmuME 0.9.12 interpreter, fresh target boot with a disposable battery-save copy
and checkpoints created by that target:

- The first trainer dialogue printed 27 characters across a 53-hardware-frame
  span in V6.2 (frames 118 to 171). V6.3 prints all 27 in one task invocation at
  frame 118; the full page is visible at the next captured frame 120. With no
  input it remains on that page through frame 300. A then advances normally.
- The comparison includes 24 battle-printer invocations in each build. Per-call
  state, speed, glyph counts, copies and destruction agree; hardware-frame
  placement can differ slightly with changed field workload.
- A complete trainer battle with Geodude/Machop send-outs and return to field
  passed with zero lost active-sprite uploads.
- In-game saving changed the disposable 512-KiB battery save; a separate fresh
  boot/import restored the saved cave position. The original ROM/save hashes
  remain unchanged.
- A 546-frame field-menu replay opens the party by touch and returns. Its initial
  240 updates draw all 15 sprites every time (3600 draws), with zero static-icon
  changes. Field-menu speed remains 4096, as in V6.2.

Native printer checks: 21 instant-page cases (through 1024 glyphs), 24 callback
regressions, three paused cases, eight explicit renderer control-boundary cases,
six real RenderText timed-delay/EOS comparisons, 24 real battle-entry callback
checks and 12 preserved-register cases. Palette/graphics APIs are stubbed where
needed. Native scheduler/context/movement/cipher/menu checks also pass. Pipeline:
52 passed. Private evidence is under `artifacts/v63/` and is not tracked.

```sh
.venv/bin/python scripts/build-v63.py private/original/user-original.nds \
  --out build/my-v63
.venv/bin/python scripts/validate-v63-text.py \
  build/v62-candidate-002/candidate.nds build/my-v63/candidate.nds \
  --out artifacts/my-v63-text.json
.venv/bin/python scripts/validate-v61.py private/original/user-original.nds \
  build/my-v63/candidate.nds --out artifacts/my-v63-regression.json
.venv/bin/python -m pytest -q
```

Source SHA256:
`94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`.
V6.3 target SHA256:
`5b4a5e458ff82e8a5af3e3dcffc72ee36e24a1313c297e1e12207761cb2a05e4`.
Both ROMs are 134217728 bytes. V6.2's approximate scene speeds remain the target;
city performance was not remeasured for this dialogue-only change. V6.3 Delta,
specialty callback-driven screens and full-game checks remain pending. Avoid old
quick savestates; import the battery save and boot fresh.
