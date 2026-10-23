# Research ledger — 2026-10-23

Initial research retrieved documentation and source repositories only. After
the user supplied a Drive link and published its network access, the user-provided
v3 ROM was downloaded privately for inspection. No third-party commercial ROMs,
BIOS dumps, Nintendo SDKs or save files were acquired. External source trees live outside
this checkout and are not dependencies or distributable project content.

## Sources inspected

| Source | Revision / evidence | License / permission observed | Compatibility and limits |
| --- | --- | --- | --- |
| [pret/pokeheartgold](https://github.com/pret/pokeheartgold/tree/6988158691eb6178cff697cda0428045ddcba5fb) | README lists US SoulSilver SHA1 `f8dc38ea20c17541a43b58c5e6d18c1732c7e582`; `src/battle/battle_system.c`, `src/battle/battle_command.c`, `src/text.c` inspected | No repository-wide LICENSE found; tool subdirectories have their own licenses. Public visibility does not establish reuse permission. No upstream code copied. | WIP matching US HG/SS disassembly; README warns layout/size edits can crash partially decompiled code. Not itself a speed patch. Symbols are research leads, not verified byte offsets in our ROM. |
| [BluRosie/hg-engine](https://github.com/BluRosie/hg-engine/tree/f4fca05a63dc7c694b72c89f178fb3030ba6f5ad) | `CONFIG.md` documents `FAST_TEXT_PRINTING`; `armips/asm/user_config.s` has conditional ARM9 edits | README grants hobby/noncommercial reuse, requires freely accessible derivatives and replicated credits; not a permissive general-purpose license. No root LICENSE found. No code incorporated. | Targets English **HeartGold**, is a mechanics overhaul, and calls text “borderline instant.” Direct application violates the no-mechanics-change requirement. Its text edits are global and not proof of manual battle-message advancement or SS compatibility. |
| [DS-Homebrew/nds-bootstrap](https://github.com/DS-Homebrew/nds-bootstrap/tree/ce62a1c1b2a35ad01834419de0ae655a7f01e6a7) | Retail card header comments identify `IPGE` as SoulSilver with infrared | Root GPL-3.0 text; per-file notices still apply. No implementation copied. | Loader/compatibility reference, not an audited selective speed patch. Runtime cheat writes and ROM file edits are different operations. |
| [DeSmuME](https://desmume.org/) / Debian trixie package | Installed CLI version 0.9.13-4; CLI `--help` and Xvfb capture verified | Debian package copyright includes GPL-2+ for emulator and component notices; installed outside repo, not vendored | Desktop test backend; not equivalent to Delta. Uses HLE defaults. Actual commercial-game boot and anti-piracy behavior remain untested. |
| Player's European v1/v2/v3 history | v1 60 FPS worked; v2 instant text white-screened; v3 instant text worked (player report) | Author/source and patch redistribution rights not yet established | The user-provided patched binary is now available privately; the subsequently supplied original matches the European English reference. `IPGE` is shared by Europe and USA. A private original-to-v3 byte diff is now available; source scripts remain unavailable. It is not a clean USA baseline; see v3-inspection.md. |

## Concrete findings

`BattleSystem_GetTextFrameDelay` in the US disassembly consults options and has a
link-battle special case. `BattleSystem_PrintBattleMessage` passes a delay to the
printer and a battle callback. `BtlCmd_WaitButtonABTime` is a separate battle script
command. `src/text.c` distinguishes instant and no-transfer modes and manages
printer tasks. Consequently a delay edit alone does not prove manual advancement
or callback correctness; the v2 white screen demands testing task lifecycle and
window transfers. Do not transplant hg-engine HeartGold RAM addresses into SS.

hg-engine's fast text option modifies several ARM9 sites, not a single isolated
battle delay. It is a useful lead but is not a licensed, validated SS solution.
A researched 60 FPS cheat or emulator speed toggle would alter broad scheduling;
it is excluded as the v4 implementation. No independently verified, suitably
licensed off-the-shelf selective HGSS 1.5x patch was located in this investigation.
This is a bounded finding, not proof none exists.

## Required next evidence

1. Dump a legally owned USA cartridge and run the profile verifier. The project's
   reference hash identifies one original revision, not all US releases or hacks.
2. Bring v3 source or a patch plus the matching original ROM identity into the cloud.
   Prefer a minimal patch/source over uploading a full patched ROM. A Windows
   `C:\...` path is not mounted in this Linux environment.
3. Use original/v3 comparison to classify changed header, ARM9, overlays and NARC
   files. Map semantics using the US symbols, never a constant region offset.
4. Review reuse terms before incorporating upstream code; record attribution and
   compatibility for any specific patch adopted later.

## Matching European baseline identified

[libretro's No-Intro metadata](https://github.com/libretro/libretro-database/blob/12c21cf79f1e20eff6ac68b80875816c717d0a7a/metadat/no-intro/Nintendo%20-%20Nintendo%20DS.dat)
records the supplied original SHA1 `27a25c23aa1c0ecabe48a30a004b96c9dbc97730`
as Europe and `f8dc38ea20c17541a43b58c5e6d18c1732c7e582` as USA/Australia.
Both have serial IPGE. Only metadata was fetched from this repository; no ROM
was downloaded from it. [The baseline report](v3-baseline.md) maps the observed
v3 differences against that supplied original.
