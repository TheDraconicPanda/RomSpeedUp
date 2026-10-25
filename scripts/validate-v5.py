#!/usr/bin/env python3
"""Execute v5 instructions with explicit environmental stubs; not a Delta test."""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import struct
import sys

import ndspy.code
import ndspy.codeCompression
import ndspy.narc
import ndspy.rom
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from romspeedup.overlay_patch import digest

spec=importlib.util.spec_from_file_location('movement_map',Path(__file__).with_name('map-city-movement.py'))
mapping=importlib.util.module_from_spec(spec);spec.loader.exec_module(mapping)
AVATAR,OBJECT,FIELD,STACK,STOP=mapping.AVATAR,mapping.OBJECT,mapping.FIELD,mapping.STACK,mapping.STOP
CTX,BSYS,PRINTER,MSG,DATA=AVATAR,0x02320000,0x02330000,0x02331000,0x02332000


class Machine(mapping.Machine):
    def __init__(self,rom):
        super().__init__(bytes(ndspy.codeCompression.decompress(rom.arm9)))
        for ov in ndspy.code.loadOverlayTable(rom.arm9OverlayTable,lambda oid,fid:rom.files[fid],{1,12}).values():
            self.cpu.mem_write(ov.ramAddress,bytes(ov.data))
        self.config=(0,True,True)
        self.state_returns={}
        self.trace=[]
        self.touch=0
        self.font_count=0
        self.glyphs=0
        self.done=False
        self.copies=0
        self.cb_result=0
        self.emitted=None
        def hook(c,address,size,user):
            result=None
            if address==0x0203e13c and self.mode in ('step','sprite'):
                assert c.reg_read(UC_ARM_REG_R0)==FIELD
                result=int(self.config[2])
            elif self.mode=='state' and address in self.state_returns:
                self.trace.append(address)
                result=self.state_returns[address]
            elif self.mode=='wait' and address==0x02025358:result=self.touch
            elif self.mode=='emit' and address in [0x0223c558,0x0223c754,0x0223cef4,0x0201d978]:result=0
            elif self.mode=='emit' and address==0x020200a8:
                self.emitted=self.read(c.reg_read(UC_ARM_REG_SP)+4)
                result=3
            elif self.mode=='render':
                if address==0x0202036c:result=0
                elif address==0x02002e98:
                    self.font_count+=1
                    if self.glyphs:
                        self.glyphs-=1;result=0
                    else:self.done=True;result=1
                elif address==0x0201d578:self.copies+=1;result=0
                elif address==0x02020020:result=0
                elif address==0x02333000:result=self.cb_result
            if result is not None:
                c.reg_write(UC_ARM_REG_R0,result)
                c.reg_write(UC_ARM_REG_PC,c.reg_read(UC_ARM_REG_LR))
        self.cpu.hook_add(UC_HOOK_CODE,hook)

    def reset(self,mid):
        super().reset(mid)
        state,player,allowed=self.config
        self.write(AVATAR+0x18,state)
        if not player:self.write(AVATAR+0x30,OBJECT+0x400)

    def state(self,move,old,checks):
        self.reset(76)
        self.write(AVATAR+0x10,move)
        self.write(AVATAR+0x14,old)
        self.write(OBJECT+0xa4,12)
        self.state_returns=dict(zip([0x0205d01c,0x02062108,0x02062198,0x0205de64],checks))
        self.mode='state';self.trace=[]
        self.call(0x0205ce68,AVATAR)
        self.mode=None
        return bytes(self.cpu.mem_read(AVATAR,64)),bytes(self.cpu.mem_read(OBJECT,0x12c)),list(self.trace)

    def wait_reset(self,frames,counter,btype,special):
        self.mode='wait'
        for at,value in [(CTX+0xf0,counter),(CTX+0xb4,0),(CTX+0x2700,30),
                         (CTX+0x2704,frames),(CTX+0x3154,0xa0),
                         (BSYS+0x2c,btype),(BSYS+0x240c,special)]:self.write(at,value)

    def wait_tick(self,address,keys,touch):
        self.write(0x021d110c+0x48,keys);self.touch=touch
        assert self.call(address,BSYS,CTX)==0
        assert self.cpu.reg_read(UC_ARM_REG_SP)==STACK
        return tuple(self.read(CTX+x) for x in [0xb4,0xf0,0x3154])

    def emit(self,mid,link,same_bank):
        self.cpu.mem_write(BSYS,bytes(0x300))
        self.cpu.mem_write(MSG,bytes(64))
        for at,value in [(BSYS+8,DATA+0x100),(BSYS+12,DATA),(BSYS+0x18,DATA+0x200),(BSYS+0x2c,link)]:self.write(at,value)
        self.cpu.mem_write(MSG+2,struct.pack('<H',mid))
        self.mode='emit';self.emitted=None
        self.call(0x0223c494,BSYS,DATA if same_bank else DATA+0x400,MSG,2)
        self.mode=None
        assert self.cpu.reg_read(UC_ARM_REG_SP)==STACK
        return self.emitted

    def render(self,marker,length,callback,pause=False):
        self.cpu.mem_write(PRINTER,bytes(0x100))
        self.write(PRINTER+4,DATA)
        self.write(PRINTER+0x1c,0x02333001 if callback else 0)
        self.cpu.mem_write(PRINTER+0x29,bytes([marker]))
        self.write(0x021d1f6c,int(pause))
        self.mode='render';self.font_count=0;self.glyphs=length;self.done=False;self.copies=0
        self.cb_result=0
        per_call=[]
        for i in range(length+3):
            before=self.glyphs
            self.call(0x020202ec,DATA,PRINTER)
            assert self.cpu.reg_read(UC_ARM_REG_SP)==STACK
            per_call.append(before-self.glyphs)
            if self.done or pause:break
        self.mode=None
        return self.done,self.copies,per_call


def script_flow(words,status=0,btype=0,move_range=0):
    v={0:btype,6:0,9:0,10:status,24:1};pc=0;messages=[];waits=[]
    signed=lambda x:x if x<0x80000000 else x-0x100000000
    for _ in range(200):
        op=words[pc]
        if op in [14,17]:pc+=1
        elif op==18:
            msg,tag=words[pc+1:pc+3];messages.append(msg);pc+=3+{0:0,2:1,10:2,11:2}[tag]
        elif op==20:messages.append('buffered');pc+=1
        elif op in [30,218]:waits.append((op,words[pc+1]));pc+=2
        elif op==32:
            mode,var,value,rel=words[pc+1:pc+5];actual=v.get(var,0)
            hit={0:actual==value,1:actual!=value,4:bool(actual&value),5:not bool(actual&value)}[mode]
            pc+=5
            if hit:pc+=signed(rel)
        elif op==59:pc+=2+signed(words[pc+1])
        elif op in [60,65]:pc+=2
        elif op==50:
            mode,var,value=words[pc+1:pc+4]
            v[var]=value if mode==7 else v.get(var,0)|value;pc+=4
        elif op==195:pc+=4
        elif op==183:v[9]=move_range;pc+=2
        elif op==224:return messages,waits
        else:raise AssertionError((pc,op))
    raise AssertionError('Script did not terminate')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--movement-revision',choices=['v5','v5.1'],default='v5')
    a=p.parse_args()
    if a.out.exists():p.error('Fresh output report required')
    source=a.baseline.read_bytes();target=a.candidate.read_bytes()
    oldrom,newrom=map(ndspy.rom.NintendoDSRom,[source,target])
    old,new=Machine(oldrom),Machine(newrom)
    count=0
    for move,oldstate,check,script,paused,kind in itertools.product(range(4),range(5),range(4),range(2),range(2),range(2)):
        inputs=(move,oldstate,[check,script,paused,kind])
        assert old.state(*inputs)==new.state(*inputs),inputs
        count+=1
    step_cases=0
    commands=(list(range(4,24))+list(range(84,92)) if a.movement_revision=='v5.1'
              else list(range(12,16))+list(range(88,92))+[8,16,20,84])
    for mid,state,player,allowed,command in itertools.product([39,40,76,78,79,6],range(3),[False,True],[False,True],commands):
        old.config=new.config=(state,player,allowed)
        base=old.step(mid,command);changed=new.step(mid,command)
        accelerated=mid in [76,78,6] and state==0 and player and allowed and command in list(range(12,16))+list(range(88,92))
        assert base['animation']==changed['animation']
        assert base['final_vector']==changed['final_vector']
        if a.movement_revision=='v5.1' and accelerated:
            assert base['advancing_updates']*3==changed['advancing_updates']*4
            assert changed['fixed_point_delta_per_update']*2==base['fixed_point_delta_per_update']*3
            previous=(0,0,0)
            for index,position in enumerate(changed['positions']):
                distance=sum(abs(a-b) for a,b in zip(position,previous))
                assert distance==(changed['fixed_point_delta_per_update'] if index<len(changed['positions'])-1
                                 else 16*4096-changed['fixed_point_delta_per_update']*index)
                previous=position
        else:
            assert base['advancing_updates']==changed['advancing_updates']*(2 if accelerated else 1)
            assert changed['fixed_point_delta_per_update']==base['fixed_point_delta_per_update']*(2 if accelerated else 1)
            if not accelerated:assert base==changed
        step_cases+=1
    wait_cases=0
    for frames,counter,btype,special,keys,touch in itertools.product([0,1,2,30,90],[0,1,29,30,0x7fffffff],[0,4],[0,16],[0,1,2,4,0x400,0x800,0x1000],[0,1]):
        old.wait_reset(frames,counter,btype,special);new.wait_reset(frames,counter,btype,special)
        before=old.wait_tick(0x0223e2f0,keys,touch)
        after=new.wait_tick(0x0223e2f0,keys,touch)
        assert before==after,(frames,counter,btype,special,keys,touch,before,after)
        wait_cases+=1
    for keys,touch in [(0,0),(3,1),(0xc03,1)]:
        new.wait_reset(24,0,0,0)
        for tick in range(25):
            result=new.wait_tick(0x02245324,keys,touch)
            assert result[0]==(2 if tick==24 else 0)
    print_cases=0
    selected={12,18,21,24,27,342,1036}
    for mid,link,bank in itertools.product(range(1200),[0,4],[False,True]):
        assert new.emit(mid,link,bank)==(65 if mid in selected and not link and bank else 2),(mid,link,bank)
        print_cases+=1
    render_cases=0
    for marker,length,callback,pause in itertools.product([0x80,0xc0],[1,10,40],[False,True],[False,True]):
        before=old.render(marker,length,callback,pause)
        after=new.render(marker,length,callback,pause)
        if pause:assert after==(False,0,[0])
        else:
            assert before[0] and after[0]
            assert before[1]==after[1]==length
            if marker==0xc0:assert after[2]==[1]*length+[0]
            else:assert before==after
        render_cases+=1
    archive=ndspy.narc.NARC(newrom.files[130]);script_cases=0
    for status,rng,manual in [(0,0,True),(0,4,True),(8,0,True),(2048,0,True),(1048576,0,True),(262144,0,True),(4096,0,True),(32768,0,False),(64,0,False),(524288,0,False),(131072,0,False)]:
        for link in [0,4]:
            code=struct.unpack('<'+'I'*(len(archive.files[7])//4),archive.files[7])
            msgs,waits=script_flow(code,status,link,rng)
            assert waits==[(30,30),(218,24) if manual and not link else (30,30)]
            script_cases+=1
    for link in [0,4]:
        code=struct.unpack('<'+'I'*(len(archive.files[176])//4),archive.files[176])
        assert script_flow(code,btype=link)[1]==[(30,30) if link else (218,24)]
        script_cases+=1
    assert digest(a.baseline.read_bytes())==digest(source) and digest(a.candidate.read_bytes())==digest(target)
    report=dict(status='passed',source_sha256=digest(source),target_sha256=digest(target),
                state_differential_cases=count,movement_cases=step_cases,timed_wait_differential_cases=wait_cases,
                result_selection_cases=print_cases,printer_cases=render_cases,script_cases=script_cases,
                auto_wait='25 command visits including completion; no input required; keys/touch do not skip',
                limits='Actual instructions with environmental/font/audio stubs; no live Delta scene, follower/camera, collision or full status-message gameplay verification.')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
