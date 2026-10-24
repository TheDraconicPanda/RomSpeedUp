#!/usr/bin/env python3
"""Replay a private checkpoint and record guarded battle callback evidence.

Run under Xvfb. Screenshots, checkpoints, saves and output reports stay private.
This does not pass/fail gameplay automatically; inspect the scenes and compare
traces. A checkpoint inside an already loaded battle is not suitable for testing
changed overlay loading. Make it in the overworld before the encounter instead.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import ndspy.code
import ndspy.rom
from desmume.emulator import DeSmuME
from desmume.controls import Keys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('rom', type=Path)
p.add_argument('--save', required=True, type=Path)
p.add_argument('--checkpoint', required=True, type=Path)
p.add_argument('--scenario', default='tests/scenarios/cave-battle.json', type=Path)
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
if a.out.exists():
    sys.exit('Fresh output directory required')
a.rom, a.save, a.checkpoint, a.out = (x.resolve() for x in (a.rom,a.save,a.checkpoint,a.out))
inputs = {str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (a.rom,a.save,a.checkpoint)}
scenario = json.loads(a.scenario.read_text())
spec = json.loads(Path('features/v4-experimental.json').read_text())
rom = ndspy.rom.NintendoDSRom(a.rom.read_bytes())
expected_overlays = ndspy.code.loadOverlayTable(rom.arm9OverlayTable,
                                               lambda oid,fid:rom.files[fid], {1,12,120})
a.out.mkdir(parents=True)
events, faults, snapshots = [], [], []
frame = 0
old_dir = Path.cwd()
with tempfile.TemporaryDirectory(prefix='v4-replay-', dir='/workspace') as tmp:
    tmp = Path(tmp)
    shutil.copyfile(a.rom,tmp/'game.nds')
    shutil.copyfile(a.save,tmp/'game.sav')
    os.environ.update(HOME=str(tmp), XDG_CONFIG_HOME=str(tmp), XDG_DATA_HOME=str(tmp))
    (tmp/'.config/desmume').mkdir(parents=True)
    os.chdir(tmp)
    emu = DeSmuME()
    try:
        emu.open(str(tmp/'game.nds'))
        if not emu.backup.import_file(str(tmp/'game.sav'),524288):
            raise RuntimeError('Battery-save import failed')
        emu.savestate.load_file(str(a.checkpoint))
        for address,label,offset,oid in [(0x22600F0,'faint',0x66,12),
                (0x226037C,'exit',6,12),(0x225FD14,'move',0x6A,12),
                (0x21EFB38,'wild',0,1),(0x22590D4,'hp',None,12),
                (0x22590E8,'exp',None,12),
                (0x225FFDC,'hp-motion',0,12),(0x2260030,'exp-motion',0,12)]:
            expected = bytes(expected_overlays[oid].data[address-expected_overlays[oid].ramAddress:
                         address-expected_overlays[oid].ramAddress+4])
            def hook(addr,size,address=address,label=label,offset=offset,oid=oid,expected=expected):
                # Overlays can reuse addresses: ignore unrelated loaded code.
                if emu.memory.read(address,address+4,1,False) != expected:
                    return
                ctx = emu.memory.register_arm9.r1
                if not 0x02000000 <= ctx < 0x02400000:
                    return
                state = emu.memory.read(ctx+offset,ctx+offset,1,False) if offset is not None else None
                # Prove the target overlay's edits actually loaded from this ROM;
                # a stock savestate must not silently supply the patched code.
                check_oid = 120 if label == 'wild' else 12
                for edit in (x for x in spec['edits'] if x['overlay'] == check_oid):
                    at = edit['ram_address']
                    block = expected_overlays[check_oid]
                    intended = bytes(block.data[at-block.ramAddress:at-block.ramAddress+len(bytes.fromhex(edit['before']))])
                    if emu.memory.read(at,at+len(intended),1,False) != intended:
                        if len(faults)<20: faults.append(dict(frame=frame,address=at,label=label))
                events.append(dict(frame=frame,label=label,state=state))
            emu.memory.register_exec(address,hook)
        for action in scenario['actions']:
            mask = sum(1<<(getattr(Keys,'KEY_'+key)-1) for key in action.get('keys',[]))
            emu.input.keypad_update(mask)
            for tick in range(action['frames']):
                emu.cycle(with_joystick=False)
                frame += 1
            emu.input.keypad_update(0)
            if 'shot' in action:
                name = action['shot']+'.png'
                emu.screenshot().save(a.out/name)
                snapshots.append(dict(name=name,frame=frame))
    finally:
        emu.destroy()
        os.chdir(old_dir)
for path, old_hash in inputs.items():
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != old_hash:
        raise RuntimeError('Original input was modified')
summary = {}
for label in ['wild','move','hp','hp-motion','faint','exp','exp-motion','exit']:
    rows = [r for r in events if r['label']==label]
    summary[label] = dict(calls=len(rows),states=dict(Counter(r['state'] for r in rows)),
                          first_frame=rows[0]['frame'] if rows else None,
                          last_frame=rows[-1]['frame'] if rows else None)
report = dict(status='captured-not-automatically-gameplay-approved',inputs=inputs,
              frames=frame, overlay_code_mismatches=faults, summary=summary,
              snapshots=snapshots,events=events)
(a.out/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(summary=summary,overlay_code_mismatches=faults),indent=2))
if faults:
    sys.exit('Loaded code differs from selected ROM; reject this replay')
if not all(summary[k]['calls'] for k in ['wild','move','hp','hp-motion','faint','exp','exp-motion','exit']):
    sys.exit('Scenario did not exercise every intended battle phase; not a passing test')
