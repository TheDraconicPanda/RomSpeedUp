#!/usr/bin/env python3
"""Private, target-owned field-menu replay with frame-by-frame sprite evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile

import ndspy.code
import ndspy.codeCompression
import ndspy.rom
from desmume.emulator import DeSmuME

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('rom', type=Path)
p.add_argument('checkpoint', type=Path)
p.add_argument('--actions', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--require-stable-icons', action='store_true')
p.add_argument('--require-half-menu-step', action='store_true')
a = p.parse_args()
rom, state, out = (x.resolve() for x in (a.rom, a.checkpoint, a.out))
actions = json.loads(a.actions.read_text())
if any('touch' in action and not (0 <= action['touch'][0] < 256 and 0 <= action['touch'][1] < 192) for action in actions):
    p.error('Touch coordinates must be relative to the 256x192 lower screen')
if out.exists():
    p.error('Fresh output required')
out.mkdir(parents=True)
loaded_rom = ndspy.rom.NintendoDSRom.fromFile(rom)
arm = ndspy.codeCompression.decompress(loaded_rom.arm9)
menu = ndspy.code.loadOverlayTable(loaded_rom.arm9OverlayTable,
    lambda oid, fid: loaded_rom.files[fid], {27})[27]
render_call = list(menu.data[0x0225A456-menu.ramAddress:0x0225A45A-menu.ramAddress])
frame = 0
context = menu_list = 0
draws = entries = 0
rows = []
with tempfile.TemporaryDirectory(dir='/workspace', prefix='field-ui-') as tmp:
    tmp = Path(tmp)
    os.environ['XDG_CONFIG_HOME'] = str(tmp/'.config')
    (tmp/'.config/desmume').mkdir(parents=True)
    shutil.copyfile(rom, tmp/'game.nds')
    cwd = Path.cwd()
    os.chdir(tmp)
    e = DeSmuME()
    e.open(str(tmp/'game.nds'))
    e.savestate.load_file(str(state))
    rd = e.memory.unsigned
    assert rd[0x020F6318:0x020F631C:4][0] == struct.unpack_from('<I', arm, 0xF6318)[0], 'Wrong loaded sprite callback'

    def hook(at, size):
        global context, menu_list, entries, draws
        if at == 0x0225A456:
            if list(rd[at:at+4]) != render_call:
                return
            context = e.memory.register_arm9.r5
            menu_list = rd[context+0x18:context+0x1C:4][0]
            entries += 1
        elif e.memory.register_arm9.r0 == menu_list:
            draws += 1

    e.memory.register_exec(0x0225A456, hook)
    e.memory.register_exec(0x02024EB4, hook)
    try:
        for index, action in enumerate(actions):
            for tick in range(action['frames']):
                entries = draws = 0
                e.input.keypad_update(action.get('keys', 0))
                if 'touch' in action and tick < 8:
                    e.input.touch_set_pos(*action['touch'])
                else:
                    e.input.touch_release()
                e.cycle(with_joystick=False)
                im = e.screenshot()
                sprites = []
                if entries:
                    for slot in range(15):
                        sprite = rd[context+0x390+slot*4:context+0x394+slot*4:4][0]
                        assert 0x02000000 <= sprite < 0x02400000
                        current = rd[sprite+0x48:sprite+0x4C:4][0]
                        seq = rd[sprite+0x64:sprite+0x68:4][0]
                        start = rd[seq+12:seq+16:4][0] if 0x02000000 <= seq < 0x02400000 else current
                        sprites.append(dict(slot=slot, speed=rd[sprite+0x38:sprite+0x3C:4][0],
                            visible=rd[sprite+0x34], active=rd[sprite+0x35],
                            sequence=rd[sprite+0xF0:sprite+0xF2:2][0], anim_frame=(current-start)//8))
                rows.append(dict(frame=frame, action=index, entries=entries, draws=draws,
                    icon_hash=hashlib.sha256(im.crop((20,225,60,260)).tobytes()).hexdigest(), sprites=sprites))
                if frame < 8:
                    im.save(out/f'frame-{frame:03d}.png')
                frame += 1
            e.input.keypad_update(0)
            e.input.touch_release()
            im.save(out/f'action-{index}.png')
            e.savestate.save_file(str(out/f'action-{index}.dst'))
    finally:
        e.destroy()
        os.chdir(cwd)
idle = [row for row in rows if row['action'] == 0]
changes = sum(x['icon_hash'] != y['icon_hash'] for x, y in zip(idle, idle[1:]))
report = dict(rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(), frames=frame,
    initial_idle_frames=len(idle), initial_idle_icon_changes=changes,
    initial_idle_menu_entries=sum(x['entries'] for x in idle),
    initial_idle_full_sprite_draws=sum(x['draws'] for x in idle), frames_trace=rows)
(out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='frames_trace'}))
if a.require_stable_icons and changes:
    raise SystemExit('Static menu icon changed during the idle replay')
if a.require_half_menu_step:
    menu_rows=[r for r in rows if r['sprites']]
    if not menu_rows or any(s['speed']!=0x1000 for r in menu_rows for s in r['sprites']):
        raise SystemExit('Menu animation step was not one half')
