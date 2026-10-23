# Local input files and transfer limits

The cloud cannot open a Windows `C:\...` path. The supplied v3 `.nds` upload
was rejected by the executor transfer tool because it exceeds 32 MiB. That attachment route could not be inspected. The Google Drive URL initially
returned HTTP 403; after the user published the network settings, the full file
was downloaded privately and structurally inspected. See [v3 inspection](v3-inspection.md).
The helper below remains a fallback when Drive access is unavailable.

Run this standard-library helper on your own computer after cloning the project:

```powershell
py scripts/local-rom.py "C:\path\SoulSilver_Europe_60FPS_InstantText_v3_EXPERIMENTAL.nds" --out private/v3-report
```

Upload only `private/v3-report/rom-report.json` first for header/hash analysis.
It contains no ROM bytes. This does not reveal which instructions were patched.
For full local research input through the 32 MiB transfer limit, create parts:

```powershell
py scripts/local-rom.py "C:\path\SoulSilver_Europe_60FPS_InstantText_v3_EXPERIMENTAL.nds" --out private/v3-parts --split
```

Each `rom.partNNN` is at most 16 MiB. If supplying the ROM itself, attach **all**
parts plus `rom-report.json` through the private upload flow. Parts are still ROM
data: never push them, post them publicly or add them to a release. Reassembly
must preserve part order and verify each part digest plus the full ROM SHA256
before inspection. Do not use these parts as a clean source build.

The v3 artifact is already patched; comparison to the subsequently supplied
original establishes its European English baseline. The shared `IPGE` code alone
does not distinguish Europe from USA. Its byte delta can now be inspected using the supplied matching European
original; validated recompression remains separate from identifying the edits. A US port requires the user's clean USA dump matching the bundled profile.
Only use files the user supplies; no commercial ROM acquisition links are included.
