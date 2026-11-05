#!/usr/bin/env python3
"""Execute cutscene resource callbacks under both VBlank/VWait orders.

Only allocator, task-queue and texture APIs are mocked. The initializer and
both actual field-overlay callbacks execute as native Thumb instructions.
"""
import argparse,importlib.util,itertools,json,struct,sys
from pathlib import Path
import ndspy.rom
import ndspy.code
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.overlay_patch import digest
spec=importlib.util.spec_from_file_location('native',Path(__file__).with_name('validate-v5.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists():p.error('Fresh report required')
ENV,U_TASK,C_TASK,MANAGER=0x02360000,0x02361000,0x02362000,0x02363000

def replay(rom,order):
 m=v.Machine(rom);c=m.cpu;active={'U':True,'C':True};callbacks={};events=[];loaded=False;freed=False;env_freed=False;bad=[]
 c.mem_write(ENV,b'\xaa'*12)
 def hook(c,at,size,user):
  nonlocal loaded,freed,env_freed
  result=None
  if at==0x021f141c:result=ENV
  elif at in (0x0200e33c,0x0200e374):
   kind='U' if at==0x0200e33c else 'C';callbacks[kind]=(c.reg_read(UC_ARM_REG_R0),c.reg_read(UC_ARM_REG_R1));result=U_TASK if kind=='U' else C_TASK
  elif at==0x020259e0:
   if freed or env_freed:bad.append('upload after source/env cleanup')
   loaded=True;events.append('upload');result=0
  elif at==0x02025a48:
   if not loaded:bad.append('cleanup before upload')
   if freed:bad.append('duplicate cleanup')
   freed=True;events.append('cleanup');result=0
  elif at==0x021f1448:env_freed=True;result=0
  elif at==0x0200e390:
   task=c.reg_read(UC_ARM_REG_R0);assert task in (U_TASK,C_TASK);active['U' if task==U_TASK else 'C']=False;result=0
  if result is not None:c.reg_write(UC_ARM_REG_R0,result);c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
 c.hook_add(UC_HOOK_CODE,hook)
 m.call(0x021f197c,MANAGER,7,MANAGER+0x100)
 initial=m.read(ENV);assert callbacks=={'U':(0x021f19b5,ENV),'C':(0x021f19d1,ENV)}
 assert m.read(ENV+4)==7 and m.read(ENV+8)==MANAGER+0x100
 for kind in order:
  if active[kind]:
   m.call(callbacks[kind][0],U_TASK if kind=='U' else C_TASK,ENV)
   assert c.reg_read(UC_ARM_REG_SP)==v.STACK
 return dict(initial=initial,bad=bad,events=events,loaded=loaded,freed=freed,active=active)

base,target=(ndspy.rom.NintendoDSRom.fromFile(f) for f in (a.baseline,a.candidate))
orders=[''.join(x) for x in itertools.product('UC',repeat=6) if 'U' in x and 'C' in x[x.index('U')+1:]]
failures=0
for order in orders:
 old,new=replay(base,order),replay(target,order)
 assert old['initial']==1 and new['initial']==0
 if old['bad']:failures+=1
 assert not new['bad'] and new['events']==['upload','cleanup'] and not any(new['active'].values()),(order,new)
assert failures>0
report=dict(status='passed',ordering_cases=len(orders),baseline_unsafe_orders=failures,target_unsafe_orders=0,baseline_sha256=digest(a.baseline.read_bytes()),target_sha256=digest(a.candidate.read_bytes()))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
