#!/usr/bin/env python3
"""Execute V6.3 printer instructions; graphics APIs are explicit test stubs."""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import struct
import sys
import ndspy.codeCompression
import ndspy.rom
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.overlay_patch import digest
spec=importlib.util.spec_from_file_location('native',Path(__file__).with_name('validate-v5.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

class PrinterMachine(v.Machine):
    def call(self,address,*args):
        c=self.cpu
        for reg,value in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):c.reg_write(reg,value)
        c.reg_write(UC_ARM_REG_SP,v.STACK);c.reg_write(UC_ARM_REG_LR,v.STOP|1)
        c.emu_start(address|1,0,count=250000)
        assert c.reg_read(UC_ARM_REG_PC)==v.STOP,hex(c.reg_read(UC_ARM_REG_PC))
        return c.reg_read(UC_ARM_REG_R0)

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists():p.error('Fresh report required')
base,target=(ndspy.rom.NintendoDSRom.fromFile(f) for f in (a.baseline,a.candidate))
old,new=PrinterMachine(base),PrinterMachine(target)
counts={'instant_page_cases':0,'callback_regression_cases':0,'paused_cases':0,'control_boundary_cases':0,'native_delay_cases':0,'battle_callback_cases':0,'preserved_register_cases':0}
for length,speed in itertools.product([0,1,2,32,96,256,1024],[0x80,0x83,0x87]):
    got=new.render(speed,length,False)
    assert got==(True,1,[length]),got
    counts['instant_page_cases']+=1
for length,speed,pause in itertools.product([0,1,16,64],[0x80,0x83,0x87],[False,True]):
    assert old.render(speed,length,True,pause)==new.render(speed,length,True,pause)
    counts['callback_regression_cases']+=1
for speed in [0x80,0x83,0x87]:
    assert old.render(speed,32,False,True)==new.render(speed,32,False,True)
    counts['paused_cases']+=1
for length,callback,pause in itertools.product([0,1,64],[False,True],[False,True]):
    registers={reg:0x12340000+index for index,reg in enumerate([UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11])}
    for reg,value in registers.items():new.cpu.reg_write(reg,value)
    new.render(0x87,length,callback,pause)
    assert all(new.cpu.reg_read(reg)==value for reg,value in registers.items())
    counts['preserved_register_cases']+=1

# Drive the actual RunTextPrinter/RenderFont instructions with an explicit
# renderer event stream. Each UPDATE is a boundary, never drained as glyphs.
for state in [1,2,3,4,5,6,7,8]:
    machine=PrinterMachine(target);c=machine.cpu;events=[0]*37+[3,0,0,1];seen=[];copies=[];destroyed=[]
    machine.cpu.mem_write(v.PRINTER,bytes(0x100));machine.write(v.PRINTER+4,v.DATA)
    c.mem_write(v.PRINTER+0x29,b'\x87');machine.write(0x021d1f6c,0)
    def hook(c,at,size,user):
        result=None
        if at==0x0202036c:result=0
        elif at==0x02002e98:
            result=events.pop(0);seen.append(result)
            if result==3:c.mem_write(v.PRINTER+0x28,bytes([state]))
        elif at==0x0201d578:copies.append(c.reg_read(UC_ARM_REG_R0));result=0
        elif at==0x02020020:destroyed.append(c.reg_read(UC_ARM_REG_R0));result=0
        if result is not None:
            c.reg_write(UC_ARM_REG_R0,result);c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
    c.hook_add(UC_HOOK_CODE,hook)
    machine.call(0x020202ec,v.DATA,v.PRINTER)
    assert seen==[0]*37+[3] and events==[0,0,1] and not destroyed and copies==[v.DATA]
    assert bytes(c.mem_read(v.PRINTER+0x28,1))==bytes([state])
    machine.call(0x020202ec,v.DATA,v.PRINTER)
    assert events==[] and len(destroyed)==1 and copies==[v.DATA,v.DATA]
    counts['control_boundary_cases']+=1

# Run the REAL font dispatcher and RenderText state-6 delay/EOS path, stubbing
# only palette generation, final VRAM transfer and task destruction.
for delay in [0,1,2,8,24,255]:
    timelines=[]
    for rom in (base,target):
        machine=PrinterMachine(rom);c=machine.cpu;destroyed=[]
        machine.cpu.mem_write(v.PRINTER,bytes(0x100));machine.write(v.PRINTER,v.DATA+0x100)
        c.mem_write(v.DATA+0x100,b'\xff\xff');machine.write(v.PRINTER+4,v.DATA)
        c.mem_write(v.PRINTER+9,b'\x01');c.mem_write(v.PRINTER+0x28,bytes([6,0x87,delay]));machine.write(0x021d1f6c,0)
        def hook(c,at,size,user):
            if at in (0x0202036c,0x0201d578,0x02020020):
                if at==0x02020020:destroyed.append(True)
                c.reg_write(UC_ARM_REG_R0,0);c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
        c.hook_add(UC_HOOK_CODE,hook);trace=[]
        for tick in range(delay+4):
            machine.call(0x020202ec,v.DATA,v.PRINTER)
            trace.append((bytes(c.mem_read(v.PRINTER+0x28,1))[0],None if destroyed else bytes(c.mem_read(v.PRINTER+0x2a,1))[0],bool(destroyed)))
            if destroyed:break
        assert destroyed
        timelines.append(trace)
    assert timelines[0]==timelines[1],(delay,timelines)
    counts['native_delay_cases']+=1

# The unchanged real battle message entry must still supply its callback, so
# those printers take the stock path regardless of current graphics callback.
for rom in (base,target):
    machine=PrinterMachine(rom);callbacks=[]
    def hook(c,at,size,user):
        if at==0x020200a8:callbacks.append(machine.read(c.reg_read(UC_ARM_REG_SP)+8))
    machine.cpu.hook_add(UC_HOOK_CODE,hook)
    for mid,link,same in itertools.product([0,17,100],[False,True],[False,True]):
        machine.emit(mid,link,same)
        assert callbacks[-1]==0x0223cf15,hex(callbacks[-1])
        counts['battle_callback_cases']+=1
report=dict(status='passed',baseline_sha256=digest(a.baseline.read_bytes()),target_sha256=digest(a.candidate.read_bytes()),**counts)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
