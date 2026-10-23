#!/usr/bin/env python3
"""Exercise the actual ROM faint-motion instructions with isolated graphics stubs.

This is instruction-level validation, not a full Nintendo DS battle/audio test.
No proprietary instructions are embedded here; they are loaded from user inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import ndspy.rom
import ndspy.code
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC


def run(rom_path, initial_state, initial_value):
    data = Path(rom_path).read_bytes()
    rom = ndspy.rom.NintendoDSRom(data)
    overlay = ndspy.code.loadOverlayTable(rom.arm9OverlayTable,
                                          lambda oid, fid: rom.files[fid], {12})[12]
    cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    cpu.mem_map(0x02000000, 0x400000)
    cpu.mem_write(overlay.ramAddress, bytes(overlay.data))
    ctx, pic, stop = 0x02310000, 0x02310200, 0x02001000
    cpu.mem_write(ctx + 8, struct.pack('<I', pic))
    cpu.mem_write(ctx + 0x66, bytes([initial_state]))
    attrs = {1:0, 0x12:initial_value, 0x29:initial_value}
    deleted, traces, calls = [], [], []
    def hook(uc, address, size, user):
        # Stub only the environment/graphics APIs around the real state machine.
        if address == stop:
            uc.emu_stop()
            return
        if address == 0x0223A8DC:
            result = 0
        elif address == 0x02008A78:
            result = attrs[uc.reg_read(UC_ARM_REG_R1)]
        elif address == 0x020087A4:
            attrs[uc.reg_read(UC_ARM_REG_R1)] = uc.reg_read(UC_ARM_REG_R2)
            result = 0
        elif address == 0x02008780:
            deleted.append(True)
            result = 0
        elif address == 0x020708D8:
            result = 80
        elif address == 0x0200908C:
            result = 0
        else:
            return
        calls.append(address)
        uc.reg_write(UC_ARM_REG_R0, result)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    cpu.hook_add(UC_HOOK_CODE, hook)
    target_state = 9 if initial_state == 7 else 10
    for tick in range(1, 100):
        cpu.reg_write(UC_ARM_REG_R0, 0x02310300)
        cpu.reg_write(UC_ARM_REG_R1, ctx)
        cpu.reg_write(UC_ARM_REG_SP, 0x023FFF00)
        cpu.reg_write(UC_ARM_REG_LR, stop | 1)
        cpu.emu_start(0x022600F1, 0, count=10000)
        if cpu.reg_read(UC_ARM_REG_PC) != stop:
            raise RuntimeError('Actual faint callback did not return normally')
        state = cpu.mem_read(ctx+0x66,1)[0]
        traces.append(dict(tick=tick, state=state, attrs=dict(attrs)))
        if state == target_state:
            return dict(ticks=tick, deleted=len(deleted), traces=traces,
                        external_calls=sorted(set(calls)))
    raise RuntimeError('Faint motion did not finish')


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('baseline')
p.add_argument('candidate')
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
rows = []
for state in [7,9]:
    for value in [1,7,8,9,12,13,24,32,64,80,96,128]:
        base, cand = run(a.baseline,state,value), run(a.candidate,state,value)
        assert base['ticks'] == (value+7)//8
        assert cand['ticks'] == (value+11)//12
        assert cand['ticks'] <= base['ticks']
        assert cand['deleted'] == (1 if state==9 else 0)
        attr = 0x29 if state==7 else 0x12
        assert cand['traces'][-1]['attrs'][attr] == 0
        assert base['external_calls'] == cand['external_calls']
        for previous, current in zip(cand['traces'],cand['traces'][1:]):
            assert 0 <= current['attrs'][attr] <= previous['attrs'][attr]
        rows.append(dict(state=state, value=value, baseline_ticks=base['ticks'],
                         candidate_ticks=cand['ticks'], candidate_deleted=cand['deleted']))
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(dict(status='passed', cases=len(rows),
    scope='actual Thumb instructions; graphics APIs stubbed; not a gameplay pass',
    source_sha256=hashlib.sha256(Path(a.baseline).read_bytes()).hexdigest(),
    target_sha256=hashlib.sha256(Path(a.candidate).read_bytes()).hexdigest(), rows=rows),indent=2)+'\n')
print('Passed',len(rows),'actual-instruction faint-motion cases')
