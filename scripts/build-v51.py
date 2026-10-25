#!/usr/bin/env python3
"""Build V5.1 from the exact delivered V5; requires a fresh output path."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.v51 import build
from romspeedup.patch import bps

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
if a.out.exists():p.error('Fresh output directory required')
source=a.source.read_bytes()
target,report=build(source)
a.out.mkdir(parents=True)
(a.out/'candidate.nds').write_bytes(target)
(a.out/'candidate.bps').write_bytes(bps(source,target))
(a.out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
