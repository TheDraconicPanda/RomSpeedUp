# Manual miss and immunity results — experimental partial V4

The player requested unlimited reading time with a fresh A/B press. This update
keeps instant printing and targets ordinary misses/avoided attacks, type immunity,
Levitate, Magnet Rise, Wonder Guard, and the one-hit-KO unaffected result. Protect,
generic failure, Sturdy protection, and other battle messages keep their waits.
The first invocation ignores input already present; subsequent invocations use
`gSystem.newKeys & 3`, never repeated/held keys or touch. There is no countdown.

The selected paths in battle subscripts 7 and 176 use a new `-1` wait argument.
They check `BATTLE_TYPE_LINK` first and preserve the original 30-update timed wait
in link battles, including recordings. Actual multiplayer synchronization has
not been tested. No other archive members change.

The existing European `WaitButtonABTime` command table entry points to
`0x0223E2F0` in overlay 12. The replacement fits its exact 156-byte function and
literal-pool slot. Its original source-function SHA256 is
`233a3d7c1e202aecede2cd48d5e6d75518ee420edc223367f917aed284c3bf84`.
It retains normal timed-wait semantics and the battle continuation bit, preserves
callee-saved registers and stack alignment, and does not change memory layout.
Recompressed overlay size is 162492 bytes; battle archive size is 54024 bytes.
Expansion uses verified existing padding without moving neighboring files.
ARM9/ARM7, other scripts/files, assets and prior partial-V4 changes are preserved.

## Reproduce

First build the exact previous partial candidate per `memory.md`. Then:

```sh
.venv/bin/python -m pip install --require-hashes -r requirements-assembler.lock
.venv/bin/python scripts/build-manual-result-text.py \
  build/v4-handoff-001/candidate.nds --out build/manual-result-text-001
.venv/bin/python scripts/validate-manual-result-text.py \
  build/v4-handoff-001/candidate.nds build/manual-result-text-001/candidate.nds \
  --out artifacts/manual-result-text/instructions.json
```

Assembler lock contains the tested Linux x86-64 Keystone 0.9.2 wheel. Instruction
validation requires the optional locked emulator dependencies (Unicorn 2.1.4).
The validator reads instructions/scripts from private ROMs; none are embedded in
the repository. Assembly is our own implementation. The pinned upstream source
in `docs/research.md` informed opcode/input semantics; upstream code was not copied.

Source SHA256: `cdf7059ea67936816d724df8d5336e1b5c364a5d41acef7e4e5f8280db6e9e92`.
Target SHA256: `8ee76fdb70c2c34ee4be096225764bf385ce76271dbc023ec6d06c62dd6c6afc`.
The delta BPS produced by this builder applies to the previous partial candidate,
not V3 or retail. Delivery packaging must identify the patch baseline explicitly.

## Evidence and limitations

- 1400 actual-instruction differential cases matched original timed waits:
  normal/link types, recording flags, timeout/counter boundaries, keys and touch.
- Manual wait remained pending for 1200 updates without A/B, including touch.
  First-invocation A/B and unrelated keys were ignored; fresh A and B each ended
  the wait and reset its state. Callee-saved registers and stack were checked.
- 28 script-path simulations checked selected and unselected results plus link
  fallbacks. Messages were unchanged and every simulated path terminated.
- 44 existing synthetic pipeline tests passed; tracked-asset check passed.
- Separate fresh DeSmuME 0.9.12 interpreter boots reached a visually reviewed
  recognizable title screen in both builds; normalized pixel difference was 0.
  Initial sandbox display-access failures were resolved by enabling local network
  access for Xvfb. No ROM modification was needed to resolve those failures.

These checks stub the touch API and simulate script control flow. They are not
a full miss/immunity gameplay replay or Delta test. Player should reproduce a
miss and a type immunity, wait without input, hold A/B before the message, then
release and press again. Check that Protect/failure and ordinary battle messages
still behave as before. Attack acceleration remains unimplemented; fainting is
still untested by the player. Previous feedback: all other attempted checklist
items were reported good, without individual scenario coverage or emulator/version.
