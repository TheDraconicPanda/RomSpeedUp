#!/usr/bin/env python3
"""Execute V5.2 follower movement/render instructions with environment stubs."""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import struct
import sys

import ndspy.rom
import ndspy.code
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_R5

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('sprites',Path(__file__).with_name('validate-v51-sprites.py'))
sprites=importlib.util.module_from_spec(spec);spec.loader.exec_module(sprites)
v5=sprites.v5
from romspeedup.overlay_patch import digest


class FollowerMachine(sprites.SpriteMachine):
    def __init__(self,rom):
        super().__init__(rom)
        self.follow_config=(True,True,True,0)

    def reset(self,mid):
        super().reset(mid)
        active,registered,ordinary,flags=self.follow_config
        self.write(v5.FIELD+0xe4,v5.OBJECT if registered else v5.OBJECT+0x800)
        self.cpu.mem_write(v5.FIELD+0xfa,bytes([int(active)]))
        self.write(v5.OBJECT+0x14,48 if ordinary else 49)
        self.write(v5.OBJECT,flags)

    def generic_sprite(self,mid,animation,previous,paused):
        self.reset(mid)
        self.write(v5.OBJECT+0xa0,animation)
        self.cpu.mem_write(v5.OBJECT+0x108,bytes([0,0,0,previous]))
        self.paused=paused;self.mode='sprite';self.sprite_trace=[]
        self.call(0x021f79dc if animation==3 else 0x021f7a18,
                  v5.OBJECT,v5.PRINTER,v5.OBJECT+0x108,0)
        self.mode=None
        return list(self.sprite_trace)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('Fresh output required')
    old,new=(FollowerMachine(ndspy.rom.NintendoDSRom(p.read_bytes())) for p in (a.baseline,a.candidate))
    step_cases=0;selected_cases=0
    commands=list(range(12,20))+[8,20,88]
    for mid,state,allowed,active,registered,ordinary,flags,command in itertools.product(
            [39,76,78,79],range(3),[False,True],[False,True],[False,True],[False,True],
            [0,64,1<<30],commands):
        old.config=new.config=(state,False,allowed)
        old.follow_config=new.follow_config=(active,registered,ordinary,flags)
        before=old.step(mid,command);after=new.step(mid,command)
        eligible=mid in (76,78) and state==0 and allowed and active and registered and ordinary and not flags
        accelerated=eligible and 12<=command<20
        if accelerated:
            assert before['final_vector']==after['final_vector']
            assert before['animation']==after['animation']
            assert before['advancing_updates']*3==after['advancing_updates']*4
            assert before['fixed_point_delta_per_update']*3==after['fixed_point_delta_per_update']*2
            previous=(0,0,0)
            for n,position in enumerate(after['positions']):
                distance=sum(abs(a-b) for a,b in zip(position,previous))
                expected=(after['fixed_point_delta_per_update'] if n<len(after['positions'])-1
                          else 65536-after['fixed_point_delta_per_update']*n)
                assert distance==expected
                previous=position
            selected_cases+=1
        else:assert before==after,(mid,state,allowed,active,registered,ordinary,flags,command)
        step_cases+=1
    sprite_cases=0
    for mid,state,allowed,active,registered,ordinary,flags,paused,animation in itertools.product(
            [39,76,79],range(3),[False,True],[False,True],[False,True],[False,True],
            [0,64,1<<30],[False,True],[3,4]):
        old.config=new.config=(state,False,allowed)
        old.follow_config=new.follow_config=(active,registered,ordinary,flags)
        before=old.generic_sprite(mid,animation,animation,paused)
        after=new.generic_sprite(mid,animation,animation,paused)
        eligible=mid==76 and state==0 and allowed and active and registered and ordinary and not flags
        expected=[(address,sprite,speed*3//2 if eligible and address==0x02023f04 else speed)
                  for address,sprite,speed in before]
        assert after==expected,(mid,state,allowed,active,registered,ordinary,flags,paused,animation,before,after)
        sprite_cases+=1
    rom=ndspy.rom.NintendoDSRom(a.candidate.read_bytes())
    overlay=ndspy.code.loadOverlayTable(rom.arm9OverlayTable,lambda oid,fid:rom.files[fid],{1})[1]
    at=0x021f8e2e
    instruction=next(Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(bytes(overlay.data[at-overlay.ramAddress:at-overlay.ramAddress+4]),at))
    assert instruction.mnemonic=='bl'
    helper=int(instruction.op_str[1:],16)
    pose_cases=0
    for allowed,animation,speed in itertools.product([False,True],range(10),[0,4096,8192,16384]):
        new.config=(0,False,allowed);new.follow_config=(True,True,True,0);new.reset(76)
        new.write(v5.OBJECT+0xa0,animation);new.cpu.reg_write(UC_ARM_REG_R5,v5.OBJECT)
        new.mode='sprite';new.sprite_trace=[]
        new.call(helper,v5.PRINTER,speed)
        expected=speed*3//2 if allowed and animation in (3,4) else speed
        assert new.sprite_trace==[(0x02023f04,v5.PRINTER,expected)]
        new.mode=None;pose_cases+=1
    interruption_cases=0
    for command,change in itertools.product(range(12,20),range(4)):
        new.config=(0,False,True);new.follow_config=(True,True,True,0)
        new.reset(76);new.mode='step';new.write(v5.OBJECT+0xa4,command)
        assert new.call(v5.mapping.DISPATCH,v5.OBJECT,command,0)==1
        if change==0:new.config=(0,False,False)
        elif change==1:new.cpu.mem_write(v5.FIELD+0xfa,b'\0')
        elif change==2:new.write(v5.mapping.LOCATION,39)
        else:new.write(v5.OBJECT,64)
        for tick in range(1,9):
            if new.call(v5.mapping.DISPATCH,v5.OBJECT,command,1)==1:break
        assert tick==(6 if command<16 else 3)
        assert sum(abs(v) for v in struct.unpack('<iii',new.cpu.mem_read(v5.OBJECT+0x70,12)))==65536
        new.mode=None;interruption_cases+=1
    report=dict(status='passed',source_sha256=digest(a.baseline.read_bytes()),
                target_sha256=digest(a.candidate.read_bytes()),movement_cases=step_cases,
                selected_movement_cases=selected_cases,sprite_cases=sprite_cases,
                ordinary_and_special_pose_cases=pose_cases,mid_tile_change_cases=interruption_cases,
                limits='Actual instructions with environment/graphics stubs; special follower effects and Delta require live checks.')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
