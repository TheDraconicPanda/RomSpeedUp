#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.v61 import build
p=argparse.ArgumentParser(description='Build the V6.1 field-scoped graphics candidate')
p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists():p.error('Fresh output directory required')
target,report=build(a.source.read_bytes());a.out.mkdir(parents=True)
(a.out/'candidate.nds').write_bytes(target)
(a.out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
