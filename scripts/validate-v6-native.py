#!/usr/bin/env python3
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import importlib.util,json,itertools,struct
import ndspy.rom
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
spec=importlib.util.spec_from_file_location('v5','scripts/validate-v5.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
p=argparse.ArgumentParser(description='Execute ROM-only V6 timing, graphics gates, movement and cipher checks')
p.add_argument('original',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists():p.error('Fresh report required')
r=ndspy.rom.NintendoDSRom(a.candidate.read_bytes());m=v.Machine(r);c=m.cpu;info=json.loads(a.candidate.with_name('build.json').read_text());D=info['data'];S=0x21d110c;ARG=0x2334000;calls=[];cost=0

def hook(c,at,n,u):
 global calls
 if at in [0x2004208,0x20d0e6c,0x21e6220,0x2333000,0x201f880,0x2024eb4,0x2026e60]:
  calls.append((at,c.reg_read(UC_ARM_REG_R0),c.reg_read(UC_ARM_REG_R1)))
  if at==0x2004208:m.write(S+0x30,m.read(S+0x30)+cost)
  c.reg_write(UC_ARM_REG_R0,0);c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
c.hook_add(UC_HOOK_CODE,hook)
mask=0xffffffff
n=0
for ready,phase,hw,ld,ad,cost in itertools.product([0,1],[0,1],[0,1,100,0xfffffff0],[-20,-9,-8,-1,0,1,8,9,20],[-20,-9,-8,-2,-1,0,1,8,9,20],[0,2,10]):
 logic=(hw+ld)&mask;audio=(hw+ad)&mask;m.write(S+0x30,hw);c.mem_write(D,struct.pack('<5I',phase,logic,audio,ready,99));calls=[]
 previous_parity=logic&1
 expected_hw=hw
 if not ready:logic=hw;audio=(hw-2)&mask
 else:logic=(logic+1)&mask
 budget=4;expected_calls=0
 while True:
  delta=(expected_hw-audio)&mask
  if delta>8:audio=expected_hw;break
  if delta<2:break
  audio=(audio+2)&mask;expected_calls+=1;expected_hw=(expected_hw+cost)&mask;budget-=1
  if not budget:audio=expected_hw;break
 debt=(expected_hw-logic)&mask
 if debt>8:logic=expected_hw;next_phase=1
 else:next_phase=int(debt<=1)
 m.call(info['clock']);actual=struct.unpack('<5I',c.mem_read(D,20))
 assert actual==(next_phase,logic,audio,1,previous_parity),(ready,phase,hw,ld,ad,cost,actual,(next_phase,logic,audio,1,previous_parity))
 assert len(calls)==expected_calls
 assert c.reg_read(UC_ARM_REG_SP)==v.STACK
 n+=1
for phase in [0,1]:
 for label,target,args in [('wait',0x20d0e6c,(1,1)),('render',0x21e6220,(ARG,)),('vwait',0x201f880,(ARG,)),('callback',0x2333000,(0xdeadbeef,0x2333001)),('sprite',0x2024eb4,(ARG,)),('swap',0x2026e60,(ARG,))]:
  c.mem_write(D,struct.pack('<5I',phase,phase,0,1,phase));m.write(S+4,ARG);c.reg_write(UC_ARM_REG_R4,S);calls=[]
  m.call(info[label],*args)
  expected=(target,1,1) if label=='wait' else (target,ARG,0x2333001) if label=='callback' else None
  if not phase:assert not calls
  else:
   assert len(calls)==1 and calls[0][0]==target
   assert calls[0][1]==(1 if label=='wait' else ARG),(label,calls)
  assert c.reg_read(UC_ARM_REG_R4)==S
old=v.Machine(ndspy.rom.NintendoDSRom(a.original.read_bytes()));steps=0
for mid,cmd in itertools.product([39,76,79,153],list(range(4,24))+list(range(84,92))):
 assert old.step(mid,cmd)==m.step(mid,cmd),(mid,cmd);steps+=1

arm_calls=[]
def arm_hook(cpu,address,size,user):
 if address in (0x20b741c,0x20bfccc):
  arm_calls.append(address)
  assert cpu.reg_read(UC_ARM_REG_SP)==v.STACK-8
  assert struct.unpack('<II',cpu.mem_read(v.STACK-8,8))==(0x11223344,v.STOP|1)
  cpu.reg_write(UC_ARM_REG_SP,v.STACK)
  cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
c.hook_add(UC_HOOK_CODE,arm_hook)
for phase,target in itertools.product([0,1],[0x20b7418,0x20bfcc8]):
 m.write(D,phase);m.write(D+4,phase);arm_calls.clear()
 for reg,value in [(UC_ARM_REG_R0,123),(UC_ARM_REG_R1,321),(UC_ARM_REG_R2,456),(UC_ARM_REG_R3,654),(UC_ARM_REG_R4,0x11223344),(UC_ARM_REG_SP,v.STACK),(UC_ARM_REG_LR,v.STOP|1)]:c.reg_write(reg,value)
 c.emu_start(target,0,count=100)
 assert len(arm_calls)==phase
 assert [c.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]==[123,321,456,654]
 assert c.reg_read(UC_ARM_REG_SP)==v.STACK
clock_cases=n
state_cases=0
for move,prior,check,script,paused,kind in itertools.product(range(4),range(5),range(4),range(2),range(2),range(2)):
 args=(move,prior,[check,script,paused,kind])
 assert old.state(*args)==m.state(*args),args
 state_cases+=1

import random
new=m
r=random.Random(2764);address=0x02360000
cases=[(size,seed) for size in [0,1,2,3,4,127,128,135,136,255,256,511,512] for seed in [0,1,0xffffffff,0x80000000,0x12345678]]
cases += [(r.randrange(513),r.getrandbits(32)) for _ in range(500)]
for size,seed in cases:
 data=r.randbytes(size+16);expected=bytearray(data);state=seed
 for off in range(0,size//2*2,2):
  state=(state*0x41c64e6d+0x6073)&0xffffffff
  value=struct.unpack_from('<H',data,off)[0]^(state>>16);struct.pack_into('<H',expected,off,value)
 outputs=[]
 for machine in [old,new]:
  machine.cpu.mem_write(address,data)
  for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]:machine.cpu.reg_write(reg,0x11223344+reg)
  machine.call(0x0201ff44,address,size,seed)
  outputs.append(bytes(machine.cpu.mem_read(address,len(data))))
  assert machine.cpu.reg_read(UC_ARM_REG_SP)==v.STACK
  for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]:assert machine.cpu.reg_read(reg)==0x11223344+reg
 assert outputs[0]==outputs[1]==expected,(size,seed)
print('Passed',len(cases),'original/optimized/reference data cipher comparisons')

report=dict(clock_cases=clock_cases,thumb_gate_cases=12,arm_gate_cases=4,
 movement_cases=steps,state_cases=state_cases,cipher_cases=len(cases),status='passed',
 scope='Native instructions with explicit environmental stubs; not Delta hardware')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
