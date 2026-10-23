# User-supplied v3 artifact inspection — 2026-10-23

The user supplied a private Google Drive link and published access for its
view/download hosts. The full file was downloaded from that link, not obtained
from a ROM distribution site. The separate attachment route failed the executor's
32 MiB transfer limit; that obstacle no longer prevents access to the Drive copy.

## Identity and structure

| Observation | Value |
| --- | --- |
| Supplied filename | SoulSilver_Europe_60FPS_InstantText_v3_EXPERIMENTAL.nds |
| Bytes | 134217728 (128 MiB) |
| Internal title | POKEMON SS |
| Header game code | IPGE |
| Header revision byte | 10 |
| Emulator serial | NTR-IPGE-USA |
| SHA1 | a6a16924b84ea7b3b262297663b5891bbb55efdd |
| SHA256 | ee605e633c6fda51b36fdd396a1c4573dbab40dd020ede1d06a4afea2efc30cb |
| ARM9 ROM offset / stored size | 16384 / 762648 bytes |
| Decompressed ARM9 size | 1122040 bytes |
| Decompressed ARM9 SHA256 | fe4737fabcc20b149250e6ec10b3e18bf862077788d223fdd67c6283bef8e3a9 |
| ARM9 overlay table | 129 records |
| FAT | 513 file entries |

`romspeedup inspect` passed its header/logo CRC16, executable/section range,
section overlap, FAT and overlay-table checks. ndspy parsed the ROM and
successfully decompressed ARM9. These checks establish structural consistency,
not that any specific patch or region attribution is correct.

The initial interpretation of `IPGE` and the emulator's USA serial as conclusive
region evidence was incorrect: `IPGE` is shared by the European English and
USA/Australia releases. The later supplied original matches the European metadata
hash exactly. See [the baseline comparison](v3-baseline.md). The patched file
is still ineligible as a clean source for US builds.

## Exploratory emulator startup

Used Debian DeSmuME CLI 0.9.13-4, no save, HLE defaults, and a disposable ROM copy
with isolated HOME/config/data directories. Original bytes and saves were not
modified. All screenshots/logs are private ignored outputs, not committed assets.

- Interpreter/default renderer: at 5 seconds both screens were black; at 20
  seconds upper screen was white and lower black. This did not establish a boot
  pass or a permanent hang; it was not sufficient evidence of a ROM defect.
- JIT plus SDL software renderer: at 10 seconds the lower screen displayed the
  moon/ocean intro; at 30 seconds it displayed Suicune. These are recognizable
  SoulSilver intro frames and demonstrate startup progress under those settings.
- No reviewed screenshot oracle was used, so **no automated boot pass** is claimed.
  No title-screen input, battle, text interaction, music, save or Delta test ran.

Reproduction settings, after sourcing `scripts/emulator-env.sh`:

```sh
# Run on a disposable copy with temporary HOME/XDG_CONFIG_HOME/XDG_DATA_HOME.
# xvfb-run -a -s '-screen 0 256x384x24 -nolisten tcp' wraps the capture process.
SDL_RENDER_DRIVER=software desmume-cli --disable-sound --jit-enable --num-cores 2 game.nds
```

The emulator's normal frame limiter was retained. JIT selects CPU emulation, not
a game-speed cheat. Interpreter and JIT captures are different test configurations;
do not mix their wall-clock timings as animation performance evidence.

## Remaining blockers

The binary alone does not reveal its exact edits relative to the clean source.
The matching European original is now available, and the six changed
decompressed ARM9 ranges are documented in v3-baseline.md. Exact ROM regeneration
from those edits still needs validated recompression; the initial recompressor
output differed from the supplied compressed stream. A separate clean user-supplied USA dump matching the known
profile remains required for the intended US build workflow. No 60 FPS or
instant-text behavior has been independently validated from this artifact yet.
