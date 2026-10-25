"""V5.1 movement revision; retains the exact V5 battle changes."""
import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
import ndspy.code
import ndspy.codeCompression
import ndspy.rom

from .v5 import BASE, assemble
from .overlay_patch import digest
from .rom import inspect, crc16

SOURCE = '4872087cab43c11df33507aaef88186208a4a2c1ac9bab9abfe66835fbe16e7b'
START, END = 0x02062568, 0x020627b0
FAMILIES = [(4,1,11,32), (8,2,12,16), (12,3,13,8), (16,4,14,4),
            (20,5,15,2), (84,0,16,1), (88,9,14,4)]


def compile_code(source, address):
    data = bytes(Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(source, addr=address)[0])
    ins = list(Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(data, address))
    if sum(i.size for i in ins) != len(data) or any(i.size == 4 and i.mnemonic not in ('bl','blx') for i in ins):
        raise ValueError('Unsupported generated Thumb instruction')
    return data


def group(address, animation, power, duration, initializer):
    entries = '\n'.join(f'movs r1, #{d}\nb common' for d in range(4))
    return compile_code(entries + f'''
common:
push {{r3, lr}}
movs r2, #{animation}
str r2, [sp]
movs r2, #1
lsls r2, r2, #{power}
movs r3, #{duration}
bl {initializer}
movs r0, #1
pop {{r3, pc}}
''', address)


def build(source):
    if digest(source) != SOURCE:
        raise ValueError('V5.1 requires the exact delivered V5 ROM')
    sections = inspect(source)['sections']
    rom = ndspy.rom.NintendoDSRom(source)
    original = bytes(ndspy.codeCompression.decompress(rom.arm9))
    arm = bytearray(original)
    if digest(arm[START-BASE:END-BASE]) != '7079c0980b925ff6b6c92869064d78b2fd0ce4914b6690795eccc388111a3679':
        raise ValueError('Movement wrapper slot guard mismatch')
    # Share identical direction wrappers. Only callback table pointers refer to
    # the relocated entrypoints; verify that invariant before replacing them.
    callbacks = {}
    table = struct.unpack_from('<I', arm, 0x6246c)[0]
    for family, animation, power, duration in FAMILIES:
        for direction in range(4):
            command = family + direction
            row = struct.unpack_from('<I', arm, table-BASE+command*4)[0]
            old_entry = struct.unpack_from('<I', arm, row-BASE)[0]
            if not START <= old_entry & ~1 < END or original.count(struct.pack('<I',old_entry)) != 1:
                raise ValueError('Unexpected wrapper reference')
            callbacks[command] = (row, old_entry)
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.skipdata = True
    for i in md.disasm(original[:0xf0000], BASE):
        if i.mnemonic in ('bl','blx','b') and i.op_str.startswith('#'):
            destination = int(i.op_str[1:], 16)
            if any(destination == old & ~1 for _,old in callbacks.values()):
                raise ValueError('Direct reference to relocated wrapper')
    cursor = START
    for family, animation, power, duration in FAMILIES:
        cursor += len(group(cursor, animation, power, duration, 0x020624cc))
    eligible_at = cursor
    eligible = assemble('v51-city-eligible', eligible_at)
    initializer_at = eligible_at + len(eligible)
    defines = {'ELIGIBLE': eligible_at}
    initializer = assemble('v51-city-init', initializer_at, defines)
    delta_at = initializer_at + len(initializer)
    delta = assemble('v51-last-delta', delta_at, defines)
    sprite_at = delta_at + len(delta)
    sprite = assemble('v51-sprite-speed', sprite_at, defines)
    code = bytearray()
    new_entries = {}
    for family, animation, power, duration in FAMILIES:
        address = START + len(code)
        for direction in range(4):
            command = family + direction
            row, old = callbacks[command]
            new_entries[command] = address + direction*4
            struct.pack_into('<I',arm,row-BASE,new_entries[command]|1)
        code += group(address,animation,power,duration,
                      initializer_at if family in (12,88) else 0x020624cc)
    code += eligible + initializer + delta + sprite
    if len(code) > END-START:
        raise ValueError('Movement code exceeds original wrapper slot')
    code += bytes.fromhex('c046')*((END-START-len(code))//2)
    arm[START-BASE:END-BASE] = code
    branch = lambda at,target: compile_code(f'bl {target}',at)
    delta_call = 0x02062524
    if original[delta_call-BASE:delta_call-BASE+4] != branch(delta_call,0x0206101c):
        raise ValueError('Movement delta call guard mismatch')
    arm[delta_call-BASE:delta_call-BASE+4] = branch(delta_call,delta_at)
    ov = ndspy.code.loadOverlayTable(rom.arm9OverlayTable,lambda oid,fid:rom.files[fid],{1})[1]
    old_ov = bytes(ov.data)
    sprite_calls = [0x021f8014,0x021f82ea]
    for call in sprite_calls:
        at = call-ov.ramAddress
        if old_ov[at:at+4] != branch(call,0x02023f04):
            raise ValueError(f'Sprite advance call guard mismatch: {call:#x}')
        ov.data[at:at+4] = branch(call,sprite_at)
    # Unselected data, section layouts, footer and neighboring files stay intact.
    settings = ndspy.code.MainCodeFile(rom.arm9,BASE).codeSettingsOffs
    packed = bytearray(ndspy.codeCompression.compress(arm,True))
    struct.pack_into('<I',packed,settings+20,BASE+len(packed))
    struct.pack_into('<I',arm,settings+20,BASE+len(packed))
    if bytes(ndspy.codeCompression.decompress(packed)) != arm:
        raise ValueError('ARM9 compression roundtrip failed')
    allowed = set(range(START-BASE,END-BASE)) | set(range(delta_call-BASE,delta_call-BASE+4)) | set(range(settings+20,settings+24))
    for row,_ in callbacks.values(): allowed.update(range(row-BASE,row-BASE+4))
    if any(i not in allowed for i,(a,b) in enumerate(zip(original,arm)) if a!=b):
        raise ValueError('Unselected ARM9 edit')
    result = bytearray(source)
    fat,fat_size = struct.unpack_from('<II',source,0x48)
    entries = [struct.unpack_from('<II',source,fat+i*8) for i in range(fat_size//8)]
    def put(start,end,data):
        bounds = [a for a,b in entries if a>start]
        bounds += [s['offset'] for s in sections.values() if s['size'] and s['offset']>start]
        limit = min(bounds+[len(source)])
        if start+len(data)>limit or (start+len(data)>end and any(x not in (0,255) for x in source[end:start+len(data)])):
            raise ValueError(f'Container slot overflow: {start:#x}, {len(data)} bytes, capacity {limit-start}')
        result[start:start+len(data)] = data
    post = bytes(rom.arm9PostData)
    if len(post)!=12: raise ValueError('Unexpected ARM9 footer')
    start = sections['arm9']['offset']
    put(start,start+len(rom.arm9)+len(post),packed+post)
    struct.pack_into('<I',result,0x2c,len(packed))
    struct.pack_into('<H',result,0x15e,crc16(result[:0x15e]))
    packed_ov = ov.save(compress=ov.compressed)
    start,end = entries[ov.fileID]
    put(start,end,packed_ov)
    struct.pack_into('<I',result,fat+ov.fileID*8+4,start+len(packed_ov))
    table_at,table_size = struct.unpack_from('<II',source,0x50)
    rows = [at for at in range(table_at,table_at+table_size,32) if struct.unpack_from('<I',source,at)[0]==1]
    if len(rows)!=1: raise ValueError('Overlay table mismatch')
    flags = struct.unpack_from('<I',result,rows[0]+28)[0] & 0xff000000
    struct.pack_into('<I',result,rows[0]+28,flags|len(packed_ov))
    target = bytes(result)
    inspect(target)
    check = ndspy.rom.NintendoDSRom(target)
    checked_ov = ndspy.code.loadOverlayTable(check.arm9OverlayTable,lambda oid,fid:check.files[fid],{1})[1]
    if bytes(ndspy.codeCompression.decompress(check.arm9))!=arm or checked_ov.data!=ov.data:
        raise ValueError('Executable readback mismatch')
    if len(target)!=len(source) or check.arm7!=rom.arm7 or check.arm9PostData!=post:
        raise ValueError('Protected cartridge layout changed')
    for fid,(a,b) in enumerate(zip(rom.files,check.files)):
        if fid != ov.fileID and a!=b: raise ValueError('Unselected file changed')
    for field in ['ramAddress','ramSize','bssSize','staticInitStart','staticInitEnd']:
        if getattr(checked_ov,field)!=getattr(ov,field):raise ValueError('Overlay memory layout changed')
    old_main,new_main = (ndspy.code.MainCodeFile(a.arm9,BASE) for a in (rom,check))
    layout = lambda m:[(s.ramAddress,len(s.data),s.bssSize,s.implicit) for s in m.sections]
    if layout(old_main)!=layout(new_main):raise ValueError('ARM9 memory layout changed')
    report = dict(version='v5.1',status='experimental',release_ready=False,
                  source_sha256=digest(source),target_sha256=digest(target),
                  nominal_city_delta_multiplier=1.5,city_walk_advances=6,city_run_advances=3,
                  tile_average_advance_multiplier=4/3,city_sprite_multiplier=1.5,
                  result_text='exactly retained from V5',surf='unchanged; location-specific slowdown unresolved',
                  eligible_address=eligible_at,initializer_address=initializer_at,
                  delta_address=delta_at,sprite_address=sprite_at,entries=new_entries,
                  arm9_packed_size=len(packed),overlay1_packed_size=len(packed_ov))
    return target,report
