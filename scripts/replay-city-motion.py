#!/usr/bin/env python3
"""Private sprite-clock replay using a disposable V5 overworld checkpoint.

The city condition is simulated by changing the current cave map's type in RAM.
This exercises live movement/rendering, not Goldenrod geometry or Delta timing.
Only known code ranges are restored from the chosen ROM after state loading.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile

import ndspy.code
import ndspy.codeCompression
import ndspy.rom
from desmume.emulator import DeSmuME

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.v51 import BASE, SOURCE, FAMILIES

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('rom',type=Path);p.add_argument('--checkpoint',type=Path,required=True)
p.add_argument('--checkpoint-rom',type=Path,required=True)
p.add_argument('--gait',choices=['walk','run'],required=True)
p.add_argument('--frames',type=int,default=24)
p.add_argument('--pattern',choices=['straight','turn-stop'],default='straight')
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
for name in ('rom','checkpoint','checkpoint_rom','out'):setattr(a,name,getattr(a,name).resolve())
if a.out.exists():p.error('Fresh output directory required')
sha=lambda b:hashlib.sha256(b).hexdigest()
original_hashes={str(f):sha(f.read_bytes()) for f in (a.rom,a.checkpoint,a.checkpoint_rom)}
if original_hashes[str(a.checkpoint_rom)]!=SOURCE:p.error('Checkpoint must come from exact delivered V5')
source,target=(ndspy.rom.NintendoDSRom(f.read_bytes()) for f in (a.checkpoint_rom,a.rom))
source_arm,target_arm=(bytes(ndspy.codeCompression.decompress(r.arm9)) for r in (source,target))
source_ov,target_ov=(ndspy.code.loadOverlayTable(r.arm9OverlayTable,lambda oid,fid:r.files[fid],{1})[1]
                     for r in (source,target))
ranges=[(0x0205ce68,220),(0x02062524,4),(0x02062568,584)]
table=struct.unpack_from('<I',source_arm,0x6246c)[0]
for family,_,_,_ in FAMILIES:
    for d in range(4):ranges.append((struct.unpack_from('<I',source_arm,table-BASE+(family+d)*4)[0],4))
a.out.mkdir(parents=True)
old_dir=Path.cwd()
with tempfile.TemporaryDirectory(dir='/workspace',prefix='city-replay-') as tmp:
    tmp=Path(tmp);shutil.copyfile(a.rom,tmp/'game.nds');os.chdir(tmp)
    e=DeSmuME()
    try:
        e.open(str(tmp/'game.nds'));e.savestate.load_file(str(a.checkpoint))
        rd=e.memory.unsigned
        for at,size in ranges:
            if rd[at:at+size]!=source_arm[at-BASE:at-BASE+size]:
                raise RuntimeError(f'Checkpoint code mismatch at {at:#x}')
            rd[at:at+size:1]=target_arm[at-BASE:at-BASE+size]
        overlay_calls=(0x021f8014,0x021f82ea,0x021f7a10,0x021f7a4c,0x021f8e2e,0x021f8e60)
        for at in overlay_calls:
            offset=at-source_ov.ramAddress
            if rd[at:at+4]!=bytes(source_ov.data[offset:offset+4]):raise RuntimeError('Checkpoint overlay mismatch')
            rd[at:at+4:1]=bytes(target_ov.data[offset:offset+4])
        for at,size in ranges:
            assert rd[at:at+size]==target_arm[at-BASE:at-BASE+size]
        avatars=[]
        def avatar_hook(at,size):
            avatar=e.memory.register_arm9.r0
            if avatar not in avatars:avatars.append(avatar)
        e.memory.register_exec(0x0205ce68,avatar_hook)
        for _ in range(2):e.cycle(with_joystick=False)
        e.memory.register_exec(0x0205ce68,None)
        if len(avatars)!=1:raise RuntimeError('Expected one player avatar')
        avatar=avatars[0];obj=rd[avatar+0x30:avatar+0x34:4][0]
        manager=rd[obj+0xb4:obj+0xb8:4][0];field=rd[manager+0x128:manager+0x12c:4][0]
        loc=rd[field+0x20:field+0x24:4][0];mid=rd[loc:loc+4:4][0]
        if mid!=153:raise RuntimeError('Expected the disposable Union Cave checkpoint')
        type_byte=0x020f6be0+mid*24+21
        rd[type_byte]=(rd[type_byte]&0xf0)|1
        # Disable the checkpoint's locked running shoes in RAM for a real walk
        # replay. No battery-save file is written or changed.
        if a.gait=='walk':
            player_save=rd[avatar+0x38:avatar+0x3c:4][0]
            rd[player_save:player_save+2:2]=[0]
        sprite=rd[obj+0x10c:obj+0x110:4][0]
        follower=rd[field+0xe4:field+0xe8:4][0]
        # Follower graphics callbacks 0x21f7810/7894 store their sprite at +108;
        # ordinary generic handlers use +10C. Inspect the actual callback.
        follower_renderer=(rd[follower+0xc8:follower+0xcc:4][0]&~1) if follower else 0
        sprite_offset=0x108 if follower_renderer in (0x021f7810,0x021f7894) else 0x10c
        follower_sprite=rd[follower+sprite_offset:follower+sprite_offset+4:4][0] if follower else 0
        advances=[];trace=[];follower_advances=[];initializers=[];all_sprite_advances=[]
        def speed_hook(at,size):
            all_sprite_advances.append([frame,e.memory.register_arm9.r0,e.memory.register_arm9.r1])
            if e.memory.register_arm9.r0==sprite:advances.append([frame,e.memory.register_arm9.r1])
            if e.memory.register_arm9.r0==follower_sprite:follower_advances.append([frame,e.memory.register_arm9.r1])
        def init_hook(at,size):
            registers=e.memory.register_arm9
            if registers.r0 in (obj,follower):
                initializers.append(dict(frame=frame,object='player' if registers.r0==obj else 'follower',
                                         command=rd[registers.r0+0xa4:registers.r0+0xa8:4][0],
                                         velocity=registers.r2,duration=registers.r3))
        e.memory.register_exec(0x02023f04,speed_hook)
        e.memory.register_exec(0x020624cc,init_hook)
        for frame in range(a.frames):
            direction=64
            if a.pattern=='turn-stop':
                direction=64 if frame<24 else 0 if frame<36 else 128 if frame<60 else 0
            e.input.keypad_update(direction|((2 if a.gait=='run' else 0) if direction else 0))
            e.cycle(with_joystick=False)
            trace.append(dict(frame=frame,position=rd[obj+0x70:obj+0x7c:4],
                              movement=rd[obj+0xa0:obj+0xac:4],
                              animation=rd[sprite+0xb6:sprite+0xb8:2][0],
                              animation_phase=rd[sprite+0xb8:sprite+0xbc:4][0],
                              follower_position=rd[follower+0x70:follower+0x7c:4] if follower else [],
                              follower_movement=rd[follower+0xa0:follower+0xac:4] if follower else [],
                              follower_animation_phase=rd[follower_sprite+0xb8:follower_sprite+0xbc:4][0] if follower_sprite else 0))
            if frame in (1,3,5,7,9,11,15,23):e.screenshot().save(a.out/f'frame-{frame:02d}.png')
        report=dict(rom_sha256=original_hashes[str(a.rom)],checkpoint_sha256=original_hashes[str(a.checkpoint)],
                    gait=a.gait,pattern=a.pattern,map=mid,simulated_map_type=1,patched_code_readback=True,
                    advances=advances,follower_advances=follower_advances,initializers=initializers,trace=trace,
                    all_sprite_advances=all_sprite_advances,
                    follower_object=follower,follower_render_fields=list(rd[follower+0xc4:follower+0x128:4]) if follower else [],
                    limits='Synthetic city condition in live cave scene; not city geometry, actual Delta or wall-clock parity.')
        expected_command=12 if a.gait=='walk' else 88
        if not any(row['movement'][1]==expected_command for row in trace):
            raise RuntimeError('Requested gait did not execute')
        (a.out/'replay.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(gait=a.gait,speeds=sorted(set(speed for _,speed in advances)),
                             phases=sorted(set(row['animation_phase'] for row in trace)),
                             code_readback=True,limits=report['limits']),indent=2))
    finally:e.destroy();os.chdir(old_dir)
assert original_hashes=={str(f):sha(f.read_bytes()) for f in (a.rom,a.checkpoint,a.checkpoint_rom)}
