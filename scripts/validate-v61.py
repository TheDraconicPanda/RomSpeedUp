#!/usr/bin/env python3
"""Execute V6.1/V6.2 clocks, context guards and unskipped upload dispatch."""
import argparse,importlib.util,itertools,json,random,struct,sys
from pathlib import Path
import ndspy.rom,ndspy.codeCompression
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.overlay_patch import digest
spec=importlib.util.spec_from_file_location('native',Path(__file__).with_name('validate-v5.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('original',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists():p.error('Fresh report required')
source,target=(ndspy.rom.NintendoDSRom.fromFile(f) for f in (a.original,a.candidate))
before,after=(bytes(ndspy.codeCompression.decompress(r.arm9)) for r in (source,target))
info=json.loads(a.candidate.with_name('build.json').read_text())
assert digest(a.candidate.read_bytes())==info['target_sha256']
assert all(before[at:at+n]==after[at:at+n] for at,n in [(0xe10,4),(0xe38,4),(0xe42,4),(0x8000,0x2000)])
old,new=v.Machine(source),v.Machine(target);cpu=new.cpu
S=0x021d110c;D=info['data'];STOP=v.STOP;MASK=0xffffffff;ARG=0x02334000
calls=[];cost=0
def hook(c,at,size,user):
    if at in (0x02004208,0x020d0e6c,0x021e6220,0x02024eb4):
        calls.append((at,c.reg_read(UC_ARM_REG_R0),c.reg_read(UC_ARM_REG_R1)))
        if at==0x02004208:new.write(S+0x30,new.read(S+0x30)+cost)
        c.reg_write(UC_ARM_REG_R0,0);c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
    elif at in (0x020b741c,0x020bfccc):
        calls.append((at,*[c.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]))
        sp=c.reg_read(UC_ARM_REG_SP)
        assert sp==v.STACK-8
        r4,ret=struct.unpack('<II',c.mem_read(sp,8));assert r4==0x11223344 and ret==STOP|1
        c.reg_write(UC_ARM_REG_R4,r4);c.reg_write(UC_ARM_REG_SP,sp+8);c.reg_write(UC_ARM_REG_PC,ret)
cpu.hook_add(UC_HOOK_CODE,hook)
clock_cases=0
for phase,hw,ld,ad,cost in itertools.product([0,1],[0,1,100,0xfffffff0],[-20,-9,-8,-1,0,1,8,9,20],[-20,-9,-8,-2,-1,0,1,8,9,20],[0,2,10]):
    logical=(hw+ld+1)&MASK;audio=(hw+ad)&MASK;physical=hw;budget=4;count=0
    cpu.mem_write(D,struct.pack('<3I',phase,(hw+ld)&MASK,audio));new.write(S+0x30,hw);calls.clear()
    while True:
        delta=(physical-audio)&MASK
        if delta>8:audio=physical;break
        if delta<2:break
        audio=(audio+2)&MASK;count+=1;physical=(physical+cost)&MASK;budget-=1
        if not budget:audio=physical;break
    debt=(physical-logical)&MASK
    if debt>8:logical=physical;ready=1
    else:ready=int(debt<=1)
    new.call(info['clock'])
    assert struct.unpack('<3I',cpu.mem_read(D,12))==(ready,logical,audio)
    assert len(calls)==count and cpu.reg_read(UC_ARM_REG_SP)==v.STACK
    clock_cases+=1
context_cases=0
for callback,phase in itertools.product([0,info['field_callback'],0x02239731,0x022397e5,0x021e5900,0x021e5903,0x02001001],[0,1]):
    new.write(S,callback);cpu.mem_write(D,struct.pack('<3I',phase,phase,0))
    for name,destination,args in [('wait',0x020d0e6c,(1,1)),('sprite',0x02024eb4,(ARG,0x12345678))]:
        calls.clear();new.call(info[name],*args)
        expected=int((name=='sprite' and info['version']=='v6.2') or callback!=info['field_callback'] or phase==1)
        assert len(calls)==expected,(callback,phase,name,calls)
        if expected:assert calls[0]==(destination,*args)
        assert cpu.reg_read(UC_ARM_REG_SP)==v.STACK
        context_cases+=1
    for destination in (0x020b7418,0x020bfcc8):
        calls.clear()
        for reg,value in [(UC_ARM_REG_R0,123),(UC_ARM_REG_R1,321),(UC_ARM_REG_R2,456),(UC_ARM_REG_R3,654),(UC_ARM_REG_R4,0x11223344),(UC_ARM_REG_SP,v.STACK),(UC_ARM_REG_LR,STOP|1)]:cpu.reg_write(reg,value)
        cpu.emu_start(destination,0,count=100)
        expected=int(callback!=info['field_callback'] or phase==1)
        assert len(calls)==expected,(callback,phase,destination,calls)
        if expected:assert calls[0][1:]==(123,321,456,654)
        assert cpu.reg_read(UC_ARM_REG_R4)==0x11223344 and cpu.reg_read(UC_ARM_REG_SP)==v.STACK
        context_cases+=1
publication=[]
def publish(c,at,size,user):
    if at==0x02333000:
        publication.append(c.reg_read(UC_ARM_REG_R0));c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
    elif at==0x02000e3c:c.emu_stop()
h=cpu.hook_add(UC_HOOK_CODE,publish)
for phase in (0,1):
    publication.clear();new.write(S+4,ARG);new.write(D+4,phase)
    for reg,value in [(UC_ARM_REG_R4,S),(UC_ARM_REG_R1,0x02333001),(UC_ARM_REG_SP,v.STACK),(UC_ARM_REG_LR,STOP|1)]:cpu.reg_write(reg,value)
    cpu.emu_start(0x02000e39,0,count=100)
    assert publication==[ARG] and cpu.reg_read(UC_ARM_REG_SP)==v.STACK
cpu.hook_del(h)
state_cases=0
for move,prior,check,script,paused,kind in itertools.product(range(4),range(5),range(4),range(2),range(2),range(2)):
    args=(move,prior,[check,script,paused,kind]);assert old.state(*args)==new.state(*args),args;state_cases+=1
movement_cases=0
for mid,command in itertools.product([39,76,79,153],list(range(4,24))+list(range(84,92))):
    assert old.step(mid,command)==new.step(mid,command);movement_cases+=1
rng=random.Random(2764);address=0x02360000
cases=[(size,seed) for size in [0,1,2,3,4,127,128,135,136,255,256,511,512] for seed in [0,1,0xffffffff,0x80000000,0x12345678]]
cases += [(rng.randrange(513),rng.getrandbits(32)) for _ in range(500)]
for size,seed in cases:
    data=rng.randbytes(size+16);expected=bytearray(data);state=seed
    for off in range(0,size//2*2,2):
        state=(state*0x41c64e6d+0x6073)&MASK
        struct.pack_into('<H',expected,off,struct.unpack_from('<H',data,off)[0]^(state>>16))
    for machine in (old,new):
        machine.cpu.mem_write(address,data);machine.call(0x0201ff44,address,size,seed)
        assert bytes(machine.cpu.mem_read(address,len(data)))==expected
        assert machine.cpu.reg_read(UC_ARM_REG_SP)==v.STACK
menu_cases=0
if info['version']=='v6.2':
    assert before[0xf6318:0xf631c]==after[0xf6318:0xf631c]
    ov=ndspy.code.loadOverlayTable(target.arm9OverlayTable,lambda oid,fid:target.files[fid],{27})[27]
    cpu.mem_write(ov.ramAddress,bytes(ov.data))
    for call,index in itertools.product(info['menu_activation_calls'],range(64)):
        data=rng.randbytes(0x104);active=index%2;expected=bytearray(data)
        expected[0x35]=active;struct.pack_into('<I',expected,0x38,0x1000)
        cpu.mem_write(address,data)
        preserved={reg:rng.getrandbits(32) for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]}
        for reg,value in preserved.items():cpu.reg_write(reg,value)
        def stop_after(c,at,size,user):
            if at==call+4:c.reg_write(UC_ARM_REG_PC,STOP|1)
        stop_hook=cpu.hook_add(UC_HOOK_CODE,stop_after)
        new.call(call,address,active)
        cpu.hook_del(stop_hook)
        assert bytes(cpu.mem_read(address,len(data)))==expected
        assert all(cpu.reg_read(reg)==value for reg,value in preserved.items())
        assert cpu.reg_read(UC_ARM_REG_SP)==v.STACK
        menu_cases+=1
report=dict(status='passed',clock_cases=clock_cases,context_cases=context_cases,publication_cases=2,state_cases=state_cases,movement_cases=movement_cases,cipher_cases=len(cases))
if menu_cases:report['menu_activation_cases']=menu_cases
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
