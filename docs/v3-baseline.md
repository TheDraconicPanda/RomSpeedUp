# Matched European baseline and v3 delta

The folder supplied by the user contains v3 and an original named
`4840 - Pokemon - SoulSilver Version (v10) (E).nds`. Although supplied as a US
original, its SHA1 exactly matches the **European English** metadata entry:

- Source SHA1: `27a25c23aa1c0ecabe48a30a004b96c9dbc97730`
- Source SHA256: `94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17`
- Source size: 134217728; header revision 10; serial IPGE.
- Target v3 SHA256: `ee605e633c6fda51b36fdd396a1c4573dbab40dd020ede1d06a4afea2efc30cb`

Reference: [No-Intro metadata mirrored by libretro](https://github.com/libretro/libretro-database/blob/12c21cf79f1e20eff6ac68b80875816c717d0a7a/metadat/no-intro/Nintendo%20-%20Nintendo%20DS.dat).
The USA/Australia original is a different entry with SHA1
`f8dc38ea20c17541a43b58c5e6d18c1732c7e582`. **Both entries use IPGE**. Header game
code and an emulator-generated region label are insufficient to distinguish them.
The earlier apparent filename/header conflict is therefore resolved; the earlier
USA inference was wrong. No identity requirements have been weakened.

## Observed differences, not a US patch manifest

All ROM bytes outside the stored ARM9 image match exactly. ARM9 is 762648 bytes
at ROM offset 0x4000 in both files. Compressed-stream differences span 22336 runs
and 710446 changed bytes; this is not evidence of that many semantic code edits.

After ndspy 4.2.0 decompression, both ARM9 images are 1122040 bytes and differ in
only **17 bytes in six contiguous runs**. Source decompressed SHA256:
`534df6737a9a852bf24c9e63e93453897d9018a17e0685346fd37050123305a5`.
The following tiny instruction differences are recorded for research, not as a
verified build recipe or a claim of permission to reuse a third-party patch.

| Decompressed offset | RAM address | Before → after (hex bytes) | Observed effect / research lead |
| --- | --- | --- | --- |
| 0xE28 | 0x02000E28 | `2563` → `0000` | Replaces store to main-system counter with Thumb NOP; matches global uncapped-frame-rate option |
| 0x2346 | 0x02002346 | `410e` → `0021` | Replaces bit extraction with `movs r1, #0`; text-printer speed lead |
| 0x202EE | 0x020202EE | `19480c1c` → `0c1c1848` | Reorders register setup/literal load in text printer task |
| 0x2031E | 0x0202031E | `032803d010bd` → `10bd2d3ce5e7` | Changes task-return and printer-state loop control |
| 0x2032E | 0x0202032E | `10` → `df` | Retargets conditional branch to text loop |
| 0x2033A | 0x0202033A | `10bd` → `f1e7` | Changes return to loop-back branch |

These addresses and semantics align with hg-engine's `ALWAYS_UNCAPPED_FRAME_RATE`
and `FAST_TEXT_PRINTING` settings in the pinned source already recorded in the
research ledger. This is strong implementation-pattern evidence, not proof of
authorship, licensing provenance or behavior in every context. Those upstream
settings are not battle-only and do not implement selective 1.5x visuals.
Do not carry the uncapped main loop into v4 as a substitute for the requested
selective attack/faint modifications. Manual advancement still needs interaction
tests; printer-loop changes alone do not prove it.

## Reproduction limits

Applying these six edits to the decompressed original reproduces the supplied
v3's decompressed ARM9 exactly. Recompression using ndspy 4.2.0 with
`isArm9=True` produced 762632 bytes, whereas the stored v3 stream has 762648.
The compressed prefix also differed; simply retaining a 16-byte source tail did
not match v3. No such output was installed, executed or released. A proper build
transform must handle the compression end pointer, container bounds and any
padding conventions, then validate decompressed equality and emulator startup.
Do not pad an arbitrary shortened compressed stream and assume it is loadable.

The existing fixed-file-offset builder remains unchanged and correctly refuses
this European source under its USA profile. Its raw file offsets must not be
used for decompressed edits. No v4 patch has been generated.

## Next work

Keep USA as the selected target, per the user's reply. Obtain the correct
user-supplied US dump and verify it before porting. Online source documentation
can explain routines and suggest mappings; it cannot replace target-ROM byte
checks or emulator/player tests. The verified European pair can now serve as
research evidence for v3 rather than guessing from its filename.

No save backup has been supplied. No battle/text/audio/save or 1.5x timing test
has passed. Intro progress observed in v3 does not clear those checks.
