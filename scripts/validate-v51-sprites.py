#!/usr/bin/env python3
"""Exercise the real field sprite dispatcher with a stubbed graphics backend."""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import struct
import sys

import ndspy.rom
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('v5_validation',Path(__file__).with_name('validate-v5.py'))
v5=importlib.util.module_from_spec(spec);spec.loader.exec_module(v5)
from romspeedup.overlay_patch import digest


class SpriteMachine(v5.Machine):
    def __init__(self,rom):
        super().__init__(rom)
        self.paused=False
        self.sprite_trace=[]
        def hook(c,address,size,user):
            if self.mode!='sprite':return
            value=None
            if address in (0x021fa2d4,0x021fa3e8,0x021f8c88):value=0
            elif address==0x021f9344:value=int(self.paused)
            elif address in (0x02023ee0,0x02023f40,0x02023f04,0x021f8c64,0x021f8c3c,0x021f8c30):
                self.sprite_trace.append((address,c.reg_read(UC_ARM_REG_R0),c.reg_read(UC_ARM_REG_R1)))
                value=0
            if value is not None:
                c.reg_write(UC_ARM_REG_R0,value)
                c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
        self.cpu.hook_add(UC_HOOK_CODE,hook)

    def sprite(self,mid,animation,previous,paused):
        self.reset(mid)
        self.write(v5.OBJECT+0xa0,animation)
        self.write(v5.OBJECT+0x10c,v5.PRINTER)
        self.cpu.mem_write(v5.OBJECT+0x108,bytes([0,0,previous,0]))
        self.mode='sprite';self.paused=paused;self.sprite_trace=[]
        self.call(0x021f7e6c,v5.OBJECT)
        self.mode=None
        assert self.cpu.reg_read(UC_ARM_REG_SP)==v5.STACK
        return list(self.sprite_trace),bytes(self.cpu.mem_read(v5.OBJECT,0x12c))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('Fresh output required')
    old,new=(SpriteMachine(ndspy.rom.NintendoDSRom(p.read_bytes())) for p in (a.baseline,a.candidate))
    count=0;selected=0
    for mid,state,player,allowed,paused,animation,previous in itertools.product(
            [39,40,76,78,79,6],range(3),[False,True],[False,True],[False,True],[3,9],[0,3,9]):
        old.config=new.config=(state,player,allowed)
        before,old_mem=old.sprite(mid,animation,previous,paused)
        after,new_mem=new.sprite(mid,animation,previous,paused)
        accelerated=mid in (76,78,6) and state==0 and player and allowed
        expected=[(address,sprite,6144 if accelerated and address==0x02023f04 else speed)
                  for address,sprite,speed in before]
        assert after==expected,(mid,state,player,allowed,paused,animation,previous,before,after)
        assert old_mem==new_mem
        if not paused:
            assert any(address==0x02023f04 for address,_,_ in after)
        else:assert not any(address==0x02023f04 for address,_,_ in after)
        selected+=int(accelerated and not paused);count+=1
    interruption_cases=0
    for command,state,allowed,mid in itertools.product(list(range(12,16))+list(range(88,92)),range(3),[False,True],[39,76]):
        new.config=(0,True,True);new.reset(76);new.mode='step'
        new.write(v5.OBJECT+0xa4,command)
        assert new.call(v5.mapping.DISPATCH,v5.OBJECT,command,0)==1
        new.config=(state,True,allowed)
        new.write(v5.AVATAR+0x18,state);new.write(v5.mapping.LOCATION,mid)
        for tick in range(1,9):
            result=new.call(v5.mapping.DISPATCH,v5.OBJECT,command,1)
            if result==1:break
        assert tick==(6 if command<16 else 3)
        assert sum(abs(v) for v in struct.unpack('<iii',new.cpu.mem_read(v5.OBJECT+0x70,12)))==65536
        new.mode=None;interruption_cases+=1
    report=dict(status='passed',source_sha256=digest(a.baseline.read_bytes()),
                target_sha256=digest(a.candidate.read_bytes()),sprite_dispatcher_cases=count,
                boosted_cases=selected,mid_tile_change_cases=interruption_cases,
                limits='Real dispatcher/handlers; graphics backend stubbed. Live pose rendering requires emulator/Delta checks.')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
