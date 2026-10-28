#!/usr/bin/env python3
"""Trace real sprite buffer/upload hand-offs during private battle replays.

Only use a checkpoint created by the selected ROM, before battle entry. This
does not migrate savestate code or certify Delta graphics. Outputs are private.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from desmume.emulator import DeSmuME

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('rom',type=Path);p.add_argument('checkpoint',type=Path)
p.add_argument('--actions',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--repel',action='store_true',help='Private trainer fixture: set a disposable 255-step repel')
p.add_argument('--repel-steps',type=int,help='Private fixture: set a disposable repel counter (0 clears it)')
p.add_argument('--require-no-active-losses',action='store_true')
p.add_argument('--min-battles',type=int,default=0)
p.add_argument('--end-in-field',action='store_true')
a=p.parse_args()
repel_steps=255 if a.repel else a.repel_steps
if repel_steps is not None and not 0<=repel_steps<=255:p.error('Repel steps must fit one byte')
rom,state,out=[x.resolve() for x in (a.rom,a.checkpoint,a.out)]
actions=json.loads(a.actions.read_text())
if out.exists():p.error('Fresh output directory required')
out.mkdir(parents=True)
events=[];counts={};frame=0;draw_before={};losses=[];battles=[];repel=[]
cwd=Path.cwd()
with tempfile.TemporaryDirectory(dir='/workspace',prefix='sprite-handoff-') as tmp:
    tmp=Path(tmp);os.environ['XDG_CONFIG_HOME']=str(tmp/'.config')
    (tmp/'.config/desmume').mkdir(parents=True)
    shutil.copyfile(rom,tmp/'game.nds');os.chdir(tmp)
    e=DeSmuME();e.open(str(tmp/'game.nds'));e.savestate.load_file(str(state))
    rd=e.memory.unsigned
    def flags(manager):return list(rd[manager+0x331:manager+0x333])
    def active_mask(manager):return sum((rd[manager+i*0xac]&1)<<i for i in range(4))
    def hook(at,n):
        counts[hex(at)]=counts.get(hex(at),0)+1
        if at==0x0205ce68 and repel_steps is not None and not repel:
            avatar=e.memory.register_arm9.r0
            obj=rd[avatar+0x30:avatar+0x34:4][0]
            manager=rd[obj+0xb4:obj+0xb8:4][0]
            field=rd[manager+0x128:manager+0x12c:4][0]
            save=rd[field+0xc:field+0x10:4][0]
            header=save+0x23014+21*16
            ident,size,offset=rd[header:header+12:4]
            assert ident==21 and size>=0x68 and offset<0x23000
            repel_at=save+0x10+offset+0x65
            repel.append(dict(address=hex(repel_at),original=rd[repel_at]))
            rd[repel_at]=repel_steps
        elif at==0x022378c0:
            state_ptr=e.memory.register_arm9.r1
            if 0x02000000<=state_ptr<0x02400000 and rd[state_ptr:state_ptr+4:4][0]==0:
                battles.append(dict(frame=frame,state_ptr=hex(state_ptr)))
        elif at==0x02008120:
            manager=e.memory.register_arm9.r0
            draw_before[manager]=flags(manager)
        elif at==0x02008130:
            manager=e.memory.register_arm9.r5
            before=draw_before.pop(manager,None);after=flags(manager)
            if before is not None:
                for slot,kind in enumerate(('image','palette')):
                    if before[slot] and not after[slot]:
                        losses.append(dict(frame=frame,manager=hex(manager),kind=kind,active_mask=active_mask(manager)))
            events.append(dict(frame=frame,kind='buffer',manager=hex(manager),flags=after,active_mask=active_mask(manager)))
        elif at==0x02009418:
            manager=e.memory.register_arm9.r0
            events.append(dict(frame=frame,kind='upload',manager=hex(manager),flags=flags(manager)))
    for address in [0x02008120,0x02008130,0x02009418,0x02239730,0x02000e84,0x02004208,0x022378c0,0x0205ce68]:
        e.memory.register_exec(address,hook)
    try:
        for index,action in enumerate(actions):
            for tick in range(action['frames']):
                keys=action.get('keys',0)
                if action.get('pulse') and tick%36>=6:keys=0
                e.input.keypad_update(keys)
                if 'touch' in action and tick<8:e.input.touch_set_pos(*action['touch'])
                else:e.input.touch_release()
                e.cycle(with_joystick=False)
                if frame%action.get('capture_every',30)==0:
                    e.screenshot().save(out/f'frame-{frame:05d}.png')
                frame+=1
            e.input.keypad_update(0);e.input.touch_release()
            e.screenshot().save(out/f'action-{index}.png')
            e.savestate.save_file(str(out/f'action-{index}.dst'))
            print(json.dumps(dict(action=index,frame=frame,losses=len(losses))),flush=True)
        e.backup.export_file(str(out/'battery.sav'))
        final_callback=rd[0x021d110c:0x021d1110:4][0]
    finally:e.destroy();os.chdir(cwd)
report=dict(frames=frame,counts=counts,pending_upload_losses=losses,
    active_sprite_upload_losses=[x for x in losses if x['active_mask']],
    events=events,battles=battles,repel_fixture=repel,final_callback=hex(final_callback))
(out/'trace.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(frames=frame,counts=counts,pending_upload_losses=len(losses))))
if a.require_no_active_losses and report['active_sprite_upload_losses']:raise SystemExit('Active sprite upload was lost')
if len(battles)<a.min_battles:raise SystemExit('Required battle-entry count was not reached')
if a.end_in_field and final_callback!=0x021e5901:raise SystemExit('Scenario did not return to the field')
