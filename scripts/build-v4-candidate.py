#!/usr/bin/env python3
"""Build explicitly partial research candidates, never a completed v4 release."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from romspeedup.overlay_patch import patch_overlays, digest
from romspeedup.patch import bps

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('rom', type=Path)
p.add_argument('--feature', action='append', required=True,
               choices=['faint-motion', 'battle-exit-palette', 'ordinary-wild-transition'])
p.add_argument('--out', required=True, type=Path)
p.add_argument('--bps', action='store_true')
a = p.parse_args()
try:
    spec_bytes = Path('features/v4-experimental.json').read_bytes()
    spec = json.loads(spec_bytes)
    if a.out.exists():
        raise ValueError('Output directory already exists')
    source = a.rom.read_bytes()
    target, changes = patch_overlays(source, spec, a.feature)
    a.out.mkdir(parents=True)
    (a.out / 'candidate.nds').write_bytes(target)
    if a.bps:
        (a.out / 'candidate.bps').write_bytes(bps(source, target))
    report = dict(status=spec['status'], release_ready=False, selected=a.feature,
                  pending=spec['pending'], source_sha256=digest(source),
                  target_sha256=digest(target), spec_sha256=digest(spec_bytes), overlays=changes,
                  validation='Integrity only; consult separate instruction/emulator reports')
    (a.out / 'build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
except (OSError, ValueError, KeyError) as e:
    sys.exit(str(e))
