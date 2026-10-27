#!/usr/bin/env python3
"""Execute V6 pacing and retained movement against original ARM9 instructions."""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import ndspy.rom
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.v6 import STATE, BASE
from romspeedup.v5 import assemble

spec = importlib.util.spec_from_file_location('v5native',Path(__file__).with_name('validate-v5.py'))
v5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v5)
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('original',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--out',required=True,type=Path);a=p.parse_args()
if a.out.exists():p.error('Fresh report required')
old,new = (v5.Machine(ndspy.rom.NintendoDSRom.fromFile(f)) for f in (a.original,a.candidate))
state_cases = 0
for move,state,check,script,paused,kind in itertools.product(range(4),range(5),range(4),range(2),range(2),range(2)):
    args = (move,state,[check,script,paused,kind])
    assert old.state(*args)==new.state(*args),args
    state_cases += 1

system = 0x021d110c
waits = []; expected = []
def wait(c,at,size,user):
    if at==0x020d0e6c:
        assert c.reg_read(UC_ARM_REG_R0)==1 and c.reg_read(UC_ARM_REG_R1)==1
        new.write(system+0x30,new.read(system+0x30)+increment)
        waits.append(at)
        c.reg_write(UC_ARM_REG_R0,0xdeadbeef)
        c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
new.cpu.hook_add(UC_HOOK_CODE,wait)
helper = STATE+len(assemble('v5-player-state',STATE))
wait_cases = 0
for initial,increment in itertools.product(range(12),[1,2,3,5]):
    waits.clear();new.write(system+0x30,initial)
    new.cpu.reg_write(UC_ARM_REG_R3,0x11223344)
    for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7]:new.cpu.reg_write(reg,0xabcdef01)
    new.call(helper,1,1)
    count = max(0,(3-initial+increment-1)//increment)
    assert len(waits)==count and new.read(system+0x30)==initial+count*increment
    assert new.cpu.reg_read(UC_ARM_REG_R3)==0x11223344
    for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7]:assert new.cpu.reg_read(reg)==0xabcdef01
    assert new.cpu.reg_read(UC_ARM_REG_SP)==v5.STACK
    wait_cases += 1
report = dict(state_cases=state_cases,wait_cases=wait_cases,status='passed',
              scope='Native instructions with IRQ/collision/environment stubs; not Delta hardware')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
