#!/usr/bin/env python3
"""Exercise ROM wait instructions with input stubs and audit script result paths.

This is not a full-emulator gameplay or link-battle test. Source code and scripts
are read from the user's private ROMs; only measurements enter the report.
"""
import argparse
import itertools
import json
from pathlib import Path
import struct
import sys

import ndspy.code
import ndspy.narc
import ndspy.rom
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import *

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from romspeedup.message_wait import HANDLER
from romspeedup.overlay_patch import digest

CTX, BSYS, STOP, SYSTEM = 0x02310000, 0x02320000, 0x02001000, 0x021d110c


class Machine:
    def __init__(self, rom):
        ov = ndspy.code.loadOverlayTable(rom.arm9OverlayTable,
                                        lambda oid,fid:rom.files[fid], {12})[12]
        self.cpu = c = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        c.mem_map(0x02000000, 0x400000)
        c.mem_write(ov.ramAddress, bytes(ov.data))
        self.touch = 0
        self.calls = 0
        def hook(uc, address, size, user):
            if address == STOP:
                uc.emu_stop()
            elif address == 0x02025358:
                self.calls += 1
                uc.reg_write(UC_ARM_REG_R0, self.touch)
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        c.hook_add(UC_HOOK_CODE, hook)

    def write(self, at, value):
        self.cpu.mem_write(at, struct.pack('<I', value & 0xffffffff))

    def read(self, at):
        return struct.unpack('<I', self.cpu.mem_read(at,4))[0]

    def reset(self, frames, counter=0, battle_type=0, special=0):
        self.write(CTX+0xf0,counter)
        self.write(CTX+0xb4,0)
        self.write(CTX+0x2700,30)
        self.write(CTX+0x2704,frames)
        self.write(CTX+0x3154,0xa0)
        self.write(BSYS+0x2c,battle_type)
        self.write(BSYS+0x240c,special)

    def tick(self, keys=0, touch=0):
        c = self.cpu
        self.write(SYSTEM+0x48, keys)
        self.touch, self.calls = touch, 0
        c.reg_write(UC_ARM_REG_R0,BSYS)
        c.reg_write(UC_ARM_REG_R1,CTX)
        c.reg_write(UC_ARM_REG_SP,0x023fff00)
        c.reg_write(UC_ARM_REG_LR,STOP|1)
        preserved = [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,
                     UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]
        for i, reg in enumerate(preserved): c.reg_write(reg,0x1100+i)
        c.emu_start(HANDLER|1,0,count=1000)
        assert c.reg_read(UC_ARM_REG_PC) == STOP
        assert c.reg_read(UC_ARM_REG_R0) == 0
        assert c.reg_read(UC_ARM_REG_SP) == 0x023fff00
        assert all(c.reg_read(reg)==0x1100+i for i,reg in enumerate(preserved))
        return (self.read(CTX+0xb4),self.read(CTX+0xf0),
                self.read(CTX+0x3154),self.calls)


def words(rom, sid):
    data = ndspy.narc.NARC(rom.files[130]).files[sid]
    return struct.unpack('<'+'I'*(len(data)//4),data)


def script_result(code, status=0, battle_type=0, move_range=0, move=1):
    variables = {0:battle_type,6:0,9:0,10:status,24:move}
    pc, messages, waits = 0, [], []
    for step in range(200):
        op = code[pc]
        if op in [14,17]: pc += 1
        elif op == 18:
            msg, tag = code[pc+1:pc+3]
            messages.append(msg)
            pc += 3+{0:0,2:1,10:2,11:2}[tag]
        elif op == 20:
            messages.append('buffered');pc += 1
        elif op == 30:
            waits.append(code[pc+1]);pc += 2
        elif op == 32:
            cmp, var, val, relative = code[pc+1:pc+5]
            actual = variables.get(var,0)
            condition = {0:actual==val,1:actual!=val,4:bool(actual&val),
                         5:not bool(actual&val)}[cmp]
            pc += 5
            if condition: pc += signed(relative)
        elif op == 59: pc += 2+signed(code[pc+1])
        elif op in [60,65]: pc += 2
        elif op == 50:
            mode,var,value = code[pc+1:pc+4]
            if mode==7: variables[var]=value
            elif mode==10: variables[var]=variables.get(var,0)|value
            else: raise AssertionError('Unreviewed script operation')
            pc += 4
        elif op == 195: pc += 4
        elif op == 183: variables[9]=move_range;pc += 2
        elif op == 224: return messages,waits
        else: raise AssertionError(f'Unreviewed script opcode {op} at {pc}')
        assert 0 <= pc < len(code)
    raise AssertionError('Script did not terminate')


def signed(value):
    return value if value < 0x80000000 else value-0x100000000


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('baseline',type=Path)
p.add_argument('candidate',type=Path)
p.add_argument('--out',type=Path,required=True)
a = p.parse_args()
baseline_bytes,candidate_bytes = a.baseline.read_bytes(),a.candidate.read_bytes()
baseline,candidate = map(ndspy.rom.NintendoDSRom,[baseline_bytes,candidate_bytes])
old,new = Machine(baseline),Machine(candidate)
count = 0
for frames,counter,btype,special,keys,touch in itertools.product(
        [0,1,2,30,90],[0,1,29,30,0x7fffffff],[0,4],[0,16],
        [0,1,2,4,0x400,0x800,0x1000],[0,1]):
    old.reset(frames,counter,btype,special)
    new.reset(frames,counter,btype,special)
    assert old.tick(keys,touch) == new.tick(keys,touch), (frames,counter,btype,special,keys,touch)
    count += 1
# No countdown: first-frame press is consumed; held keys supply no new edge.
new.reset(0xffffffff)
assert new.tick(1)[:3] == (0,0xffffffff,0xa1)
for frame in range(1200):
    assert new.tick(0,frame%2)[:3] == (0,0xffffffff,0xa1)
for key in [4,0x400,0x800,0x1000]:
    assert new.tick(key,1)[:3] == (0,0xffffffff,0xa1)
assert new.tick(2)[:3] == (2,0,0xa1)
for key in [1,2]:
    new.reset(0xffffffff)
    assert new.tick(key)[0] == 0
    assert new.tick(0)[0] == 0
    assert new.tick(key)[:3] == (2,0,0xa1)
cases = [
    (0,0,12,True), (0,4,24,True), (0,8,24,True),
    (8,0,27,True), (2048,0,21,True), (1048576,0,1036,True),
    (262144,0,18,True), (4096,0,342,True),
    (32768,0,15,False), (64,0,796,False),
    (524288,0,625,False), (131072,0,'buffered',False),
    (65536,0,12,True),
]
paths = 0
for status,move_range,message,manual in cases:
    for battle_type in [0,4]:
        kwargs=dict(status=status,battle_type=battle_type,move_range=move_range)
        original=script_result(words(baseline,7),**kwargs)
        patched=script_result(words(candidate,7),**kwargs)
        assert original[0] == patched[0] == [message]
        assert original[1] == [30,30]
        assert patched[1] == [30,0xffffffff if manual and not battle_type else 30]
        paths += 1
for btype in [0,4]:
    assert script_result(words(candidate,176),battle_type=btype) == ([24],[30 if btype else 0xffffffff])
    paths += 1
a.out.parent.mkdir(parents=True,exist_ok=True)
report=dict(status='passed',source_sha256=digest(baseline_bytes),
            target_sha256=digest(candidate_bytes),timed_wait_differential_cases=count,
            no_input_ticks=1200,script_paths=paths,
            scope='Actual Thumb instructions with touch API stub; script control-flow simulation. Not full gameplay, audio or link validation.')
a.out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
