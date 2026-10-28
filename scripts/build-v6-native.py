#!/usr/bin/env python3
"""Build the conservative V6 graphics control (use build-v61.py for V6.1)."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.v6_native import build

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
p.add_argument('--legacy-rejected',action='store_true',help='Reproduce the rejected V6 battle-graphics build; research only')
a=p.parse_args()
if a.out.exists():p.error('Fresh output directory required')
target,report=build(a.source.read_bytes(),graphics_safe=not a.legacy_rejected)
a.out.mkdir(parents=True)
(a.out/'candidate.nds').write_bytes(target)
(a.out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
