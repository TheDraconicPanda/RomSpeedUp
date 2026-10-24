#!/usr/bin/env python3
"""Compare observed battle traces, without claiming broad gameplay coverage."""
import argparse
import json
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('baseline',type=Path)
p.add_argument('candidate',type=Path)
p.add_argument('--feature',action='append',default=[],choices=['faint-motion','battle-exit-palette','ordinary-wild-transition'])
p.add_argument('--out',type=Path)
a=p.parse_args()
b=json.loads(a.baseline.read_text());c=json.loads(a.candidate.read_text())
assert not b['overlay_code_mismatches'] and not c['overlay_code_mismatches'], 'Loaded-code mismatch'
shared=set(b['inputs']) & set(c['inputs'])
assert len(shared)>=2 and all(b['inputs'][k]==c['inputs'][k] for k in shared), 'Save/checkpoint mismatch'
assert b['frames']==c['frames'], 'Different scenario frame totals'
for label in ['wild','move','hp-motion','faint','exp-motion','exit']:
    assert b['summary'][label]['calls'] and c['summary'][label]['calls'], 'Missing exercised phase'
for label in ['move','hp-motion','exp-motion']:
    x,y=b['summary'][label],c['summary'][label]
    assert x['calls']==y['calls'] and x['states']==y['states'], label+' state sequence changed'
    assert x['last_frame']-x['first_frame']==y['last_frame']-y['first_frame'], label+' span changed'
    bx=[(r['state'],r['frame']-x['first_frame']) for r in b['events'] if r['label']==label]
    cy=[(r['state'],r['frame']-y['first_frame']) for r in c['events'] if r['label']==label]
    assert bx==cy, label+' ordered state/frame trace changed'
for label,feature in [('wild','ordinary-wild-transition'),('exit','battle-exit-palette'),('faint','faint-motion')]:
    x,y=b['summary'][label],c['summary'][label]
    if feature in a.feature:
        assert y['calls']<x['calls'], label+' not faster in observed scenario'
    else:
        assert x['calls']==y['calls'] and x['states']==y['states'], label+' unexpectedly changed'
# Preserve the faint cry-wait state even when visual collapse is shortened.
assert b['summary']['faint']['states'].get('5')==c['summary']['faint']['states'].get('5'), 'Cry wait changed'
report=dict(status='passed-observed-scenario-invariants',features=a.feature,
            scope='One controlled ordinary wild battle; not all moves, trainers, audio, save-write or Delta',
            baseline=b['summary'],candidate=c['summary'])
if a.out:
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
print(report['status'])
