#!/usr/bin/env python3
"""Build the partial V4 candidate with manual miss/immunity result messages."""
import argparse
import json
from pathlib import Path
import sys

from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from romspeedup.message_wait import HANDLER, patch_manual_wait
from romspeedup.patch import bps

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
if a.out.exists():
    sys.exit('Fresh output directory required')
assembly = Path('features/manual-result-wait.s').read_text()
assembly = '\n'.join(line for line in assembly.splitlines() if not line.startswith('//'))
code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(assembly, addr=HANDLER)
source = a.source.read_bytes()
target, report = patch_manual_wait(source, bytes(code))
report.update(status='experimental-partial-not-v4-release', release_ready=False,
              attacks='unchanged V3 speed', validation='integrity only; see separate test report')
a.out.mkdir(parents=True)
(a.out/'candidate.nds').write_bytes(target)
(a.out/'candidate.bps').write_bytes(bps(source,target))
(a.out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
