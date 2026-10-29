"""V6.2: publish 2D sprites every update; pace field-menu animations separately."""
import struct
import ndspy.code
import ndspy.codeCompression
import ndspy.rom

from .v61 import build as build_v61, BASE, START
from .v6_native import compile_code
from .overlay_patch import digest
from .rom import crc16, inspect

MENU_CALLS = (0x0225B112, 0x0225B1C0)
SET_ACTIVE = 0x0202484C
SPRITE_CALLBACK = 0xF6318


def build(source):
    base, report = build_v61(source)
    original, prior = map(ndspy.rom.NintendoDSRom, (source, base))
    raw = bytes(ndspy.codeCompression.decompress(original.arm9))
    before = bytes(ndspy.codeCompression.decompress(prior.arm9))
    arm = bytearray(before)
    helper = START + report['helper_bytes']
    payload = compile_code(f'''push {{r4,lr}}
movs r4,r0
bl {SET_ACTIVE}
movs r1,#1
lsls r1,r1,#12
str r1,[r4,#0x38]
pop {{r4,pc}}
''', helper)
    if helper + len(payload) > report['data']:
        raise ValueError('Menu helper overlaps scheduler state')
    if arm[helper-BASE:helper-BASE+len(payload)] != bytes.fromhex('c046') * (len(payload)//2):
        raise ValueError('Menu helper space is not unused padding')
    arm[helper-BASE:helper-BASE+len(payload)] = payload
    # An omitted 2D draw produces an empty OAM frame. Resource publication must
    # remain live, so restore drawing as well rather than skipping publication.
    arm[SPRITE_CALLBACK:SPRITE_CALLBACK+4] = raw[SPRITE_CALLBACK:SPRITE_CALLBACK+4]

    overlay = ndspy.code.loadOverlayTable(original.arm9OverlayTable,
        lambda oid, fid: original.files[fid], {27})[27]
    old_menu = bytes(overlay.data)
    for call in MENU_CALLS:
        off = call - overlay.ramAddress
        expected = compile_code(f'bl {SET_ACTIVE}', call)
        if overlay.data[off:off+4] != expected:
            raise ValueError('Field-menu animation activation call mismatch')
        overlay.data[off:off+4] = compile_code(f'bl {helper}', call)

    settings = ndspy.code.MainCodeFile(original.arm9, BASE).codeSettingsOffs
    packed = bytearray(ndspy.codeCompression.compress(arm, True))
    struct.pack_into('<I', packed, settings+20, BASE+len(packed))
    struct.pack_into('<I', arm, settings+20, BASE+len(packed))
    if ndspy.codeCompression.decompress(packed) != arm:
        raise ValueError('ARM9 compression roundtrip failed')
    result = bytearray(base)
    arm_start = struct.unpack_from('<I', source, 0x20)[0]
    if arm_start+len(packed)+len(original.arm9PostData) > struct.unpack_from('<I', source, 0x50)[0]:
        raise ValueError('ARM9 slot overflow')
    result[arm_start:arm_start+len(packed)+len(original.arm9PostData)] = packed+original.arm9PostData
    struct.pack_into('<I', result, 0x2C, len(packed))
    struct.pack_into('<H', result, 0x15E, crc16(result[:0x15E]))

    fat = struct.unpack_from('<I', source, 0x48)[0]
    entries = [struct.unpack_from('<II', source, fat+i*8) for i in range(len(original.files))]
    start, end = entries[overlay.fileID]
    menu_payload = overlay.save(compress=True)
    if start+len(menu_payload) > min(a for a, b in entries if a > start):
        raise ValueError('Field-menu overlay slot overflow')
    result[start:start+len(menu_payload)] = menu_payload
    struct.pack_into('<I', result, fat+overlay.fileID*8+4, start+len(menu_payload))
    table, size = struct.unpack_from('<II', source, 0x50)
    row = [at for at in range(table, table+size, 32)
           if struct.unpack_from('<I', source, at)[0] == 27][0]
    flags = struct.unpack_from('<I', source, row+28)[0] & 0xFF000000
    struct.pack_into('<I', result, row+28, flags | len(menu_payload))

    target = bytes(result)
    inspect(target)
    check = ndspy.rom.NintendoDSRom(target)
    if ndspy.codeCompression.decompress(check.arm9) != arm:
        raise ValueError('ARM9 readback failed')
    allowed = set(range(helper-BASE, helper-BASE+len(payload)))
    allowed.update(range(SPRITE_CALLBACK, SPRITE_CALLBACK+4))
    allowed.update(range(settings+20, settings+24))
    if len(arm) != len(before) or any(i not in allowed for i, (a, b) in enumerate(zip(before, arm)) if a != b):
        raise ValueError('Unexpected V6.1 executable change')
    if len(target) != len(source) or len(check.files) != len(original.files):
        raise ValueError('Cartridge or file count changed')
    for attr in ('arm7', 'arm9PostData', 'arm7OverlayTable', 'iconBanner'):
        if getattr(check, attr) != getattr(original, attr):
            raise ValueError(f'Protected cartridge asset changed: {attr}')
    layout = lambda r: [(s.ramAddress, len(s.data), s.bssSize, s.implicit)
        for s in ndspy.code.MainCodeFile(r.arm9, BASE).sections]
    if layout(check) != layout(original):
        raise ValueError('Executable layout changed')
    for fid, (old, new) in enumerate(zip(prior.files, check.files)):
        if fid != overlay.fileID and old != new:
            raise ValueError(f'Protected V6.1 file changed: {fid}')
    loaded = ndspy.code.loadOverlayTable(check.arm9OverlayTable,
        lambda oid, fid: check.files[fid], {27})[27]
    menu_allowed = {i for call in MENU_CALLS for i in range(call-overlay.ramAddress, call-overlay.ramAddress+4)}
    if loaded.data != overlay.data or len(loaded.data) != len(old_menu) or loaded.bssSize != overlay.bssSize:
        raise ValueError('Menu overlay readback/layout failed')
    if any(i not in menu_allowed for i, (a, b) in enumerate(zip(old_menu, loaded.data)) if a != b):
        raise ValueError('Unexpected field-menu edit')
    report.update(version='v6.2', status='experimental', target_sha256=digest(target),
        packed=len(packed), sprite=struct.unpack_from('<I', raw, SPRITE_CALLBACK)[0] & ~1,
        menu_helper=helper, menu_helper_bytes=len(payload), menu_activation_calls=list(MENU_CALLS),
        field_menu_animation_step=0.5, field_menu_animation_fx32=0x1000,
        sprite_publication='stock drawing every update',
        emulator_fast_forward_required=False)
    return target, report
