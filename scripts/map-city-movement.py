#!/usr/bin/env python3
"""Read-only European V3 movement map and instruction experiments; writes JSON only.

This does not build a patch. Environmental collision, terrain-height and graphics
callbacks are stubbed. Update counts are not Delta frame-rate measurements.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct

import ndspy.codeCompression
import ndspy.rom
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

BASE = 0x02000000
ARM9_SHA256 = 'fe4737fabcc20b149250e6ec10b3e18bf862077788d223fdd67c6283bef8e3a9'
MAP_TABLE = 0x020F6BE0
MAP_TYPE = 0x0203B4DC
SELECT = 0x0205D4B4
CHOICE = 0x0205D44C
DISPATCH = 0x0206245C
STOP = 0x02001000
AVATAR, OBJECT, MANAGER, FIELD, LOCATION, SAVE = (0x02310000+i*0x1000 for i in range(6))
STACK = 0x023FFF00
NAMES = {39:'Route 35',40:'Route 36',76:'Goldenrod',78:'Ecruteak',
         79:'Ecruteak Pokemart',6:'Bellchime Trail'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Machine:
    def __init__(self, arm9):
        self.cpu = c = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        c.mem_map(BASE,0x400000)
        c.mem_write(BASE,bytes(arm9))
        self.mode, self.selection = None, None
        self.stub_calls = set()
        def hook(uc,address,size,user):
            if address == STOP:
                uc.emu_stop()
                return
            if self.mode == 'select' and address == 0x0205DA1C:
                self.selection = uc.reg_read(UC_ARM_REG_R2)
                uc.emu_stop()
                return
            stubs = ({0x0205DA34,0x0205E048} if self.mode=='select'
                     else {0x02061070,0x0205F484} if self.mode=='step' else set())
            if address in stubs:
                self.stub_calls.add(address)
                uc.reg_write(UC_ARM_REG_R0,0)
                uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        c.hook_add(UC_HOOK_CODE,hook)

    def write(self,at,value):
        self.cpu.mem_write(at,struct.pack('<I',value & 0xffffffff))

    def read(self,at):
        return struct.unpack('<I',self.cpu.mem_read(at,4))[0]

    def call(self,address,*args):
        c = self.cpu
        for reg,value in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):
            c.reg_write(reg,value)
        c.reg_write(UC_ARM_REG_SP,STACK)
        c.reg_write(UC_ARM_REG_LR,STOP|1)
        c.emu_start(address|1,0,count=10000)
        if not (c.reg_read(UC_ARM_REG_PC)==STOP or
                (self.mode=='select' and self.selection is not None)):
            raise AssertionError(f'Experiment did not return: PC={c.reg_read(UC_ARM_REG_PC):08x}')
        return c.reg_read(UC_ARM_REG_R0)

    def reset(self,mid):
        self.cpu.mem_write(AVATAR,bytes(0x6000))
        self.write(AVATAR+0x30,OBJECT)
        self.write(AVATAR+0x38,SAVE)
        self.write(OBJECT+0xb4,MANAGER)
        self.write(MANAGER+0x128,FIELD)
        self.write(FIELD+0x20,LOCATION)
        self.write(FIELD+0x40,AVATAR)
        self.write(LOCATION,mid)
        self.write(SAVE,1)

    def select(self,mid,direction,run,shoes=True):
        self.reset(mid)
        self.write(SAVE,int(shoes))
        self.write(STACK,2 if run else 0)
        self.mode,self.selection='select',None
        self.call(SELECT,AVATAR,OBJECT,direction)
        result=self.selection
        self.mode=None
        assert result is not None
        return result

    def step(self,mid,command):
        self.reset(mid)
        self.mode='step'
        self.write(OBJECT+0xa4,command)
        assert self.call(DISPATCH,OBJECT,command,0)==1
        direction=self.read(OBJECT+0xfc)
        duration=struct.unpack('<h',self.cpu.mem_read(OBJECT+0xfa,2))[0]
        velocity=self.read(OBJECT+0x100)
        animation=struct.unpack('<H',self.cpu.mem_read(OBJECT+0xf8,2))[0]
        positions=[]
        for tick in range(1,65):
            result=self.call(DISPATCH,OBJECT,command,1)
            positions.append(struct.unpack('<iii',self.cpu.mem_read(OBJECT+0x70,12)))
            if result==1:break
        else:raise AssertionError('Movement did not complete')
        self.mode=None
        assert tick==duration
        assert self.read(OBJECT+0xa8)==2
        assert sum(abs(v) for v in positions[-1])==16*4096
        assert velocity*duration==16*4096
        return dict(command=command,direction=direction,advancing_updates=tick,
                    fixed_point_delta_per_update=velocity,animation=animation,
                    final_vector=list(positions[-1]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    if a.out.exists():p.error('Fresh output JSON required')
    data=a.rom.read_bytes()
    rom=ndspy.rom.NintendoDSRom(data)
    arm9=ndspy.codeCompression.decompress(rom.arm9)
    if rom.arm9RamAddress!=BASE or sha(arm9)!=ARM9_SHA256:
        p.error('Expected the exact supplied European V3 decompressed ARM9')
    m=Machine(arm9)
    maps=[]
    for mid in NAMES:
        m.reset(mid)
        assert m.call(0x0205F52C,OBJECT)==FIELD
        assert m.read(FIELD+0x20)==LOCATION
        map_type=m.call(MAP_TYPE,mid)
        assert map_type==((struct.unpack_from('<I',arm9,MAP_TABLE-BASE+mid*24+20)[0]>>8)&15)
        maps.append(dict(id=mid,name=NAMES[mid],map_type=map_type))
    selections=[]
    steps=[]
    for mid,direction,run,shoes in itertools.product([39,40,76,78],range(4),[False,True],[False,True]):
        command=m.select(mid,direction,run,shoes)
        expected=(88 if run and shoes else 12)+direction
        assert command==expected
        selections.append(dict(map=mid,direction=direction,run=run,shoes=shoes,command=command))
    for mid,command in itertools.product([39,40,76,78],list(range(12,16))+list(range(88,92))):
        result=m.step(mid,command)
        assert result['advancing_updates']==(8 if command<16 else 4)
        steps.append(dict(map=mid,**result))
    # Read-only confirmation of the player-specific decision boundary's behavior.
    m.reset(76)
    assert m.call(CHOICE,OBJECT,0,12)==12
    assert m.call(CHOICE,OBJECT,0,88)==88
    guards={}
    for name,address,length in [('map_type',MAP_TYPE,28),('map_object_field',0x0205F52C,12),
            ('selector',SELECT,0x15c),('choice',CHOICE,4),
            ('dispatcher',DISPATCH,20),('step_init',0x020624cc,72),
            ('step_advance',0x02062514,84)]:
        guards[name]=dict(address=f'0x{address:08x}',length=length,
                          sha256=sha(arm9[address-BASE:address-BASE+length]))
    report=dict(status='mapped-no-patch',rom_sha256=sha(data),arm9_sha256=sha(arm9),
                map_table=f'0x{MAP_TABLE:08x}',map_header_size=24,maps=maps,guards=guards,
                selector_cases=len(selections),step_cases=len(steps),selections=selections,
                steps=steps,stubbed_calls=[f'0x{x:08x}' for x in sorted(m.stub_calls)],
                conclusion='City and route ordinary walking/running use identical per-update parameters. City detection and a player-only movement decision boundary are mapped; real-time compensation is possible to research, not yet calibrated or implemented.',
                limits='Synthetic object state with collision/terrain/graphics stubs; not Delta, scene cadence, follower/camera, collision, or gameplay validation.')
    # Never write, replace or export ROM data.
    assert sha(a.rom.read_bytes())==sha(data)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','rom_sha256','selector_cases','step_cases','maps','guards','conclusion','limits']},indent=2))


if __name__=='__main__':main()
