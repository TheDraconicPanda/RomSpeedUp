"""Experimental V6.1: field-only draw pacing; resource publication stays live."""
import struct
from keystone import Ks,KS_ARCH_ARM,KS_MODE_ARM
import ndspy.rom,ndspy.code,ndspy.codeCompression
from .v51 import group,FAMILIES
from .v6_native import build as conservative_build,compile_code
from .overlay_patch import digest
from .rom import inspect,crc16

BASE=0x02000000
START,END=0x02062568,0x020627b0
SYSTEM=0x021d110c
FIELD_CB=0x021e5901


def build(source):
    base,_=conservative_build(source,graphics_safe=True)
    original=ndspy.rom.NintendoDSRom(source)
    stable=ndspy.rom.NintendoDSRom(base)
    arm=bytearray(ndspy.codeCompression.decompress(stable.arm9))
    raw=bytes(ndspy.codeCompression.decompress(original.arm9))
    data=END-12
    table=struct.unpack_from('<I',raw,0x6246c)[0]
    code=bytearray()
    for family,animation,power,duration in FAMILIES:
        at=START+len(code)
        for direction in range(4):
            row=struct.unpack_from('<I',raw,table-BASE+(family+direction)*4)[0]
            struct.pack_into('<I',arm,row-BASE,at+direction*4|1)
        code+=group(at,animation,power,duration,0x020624cc)
    clock_at=START+len(code)
    code+=compile_code(f'''push {{r3,r4,r5,r6,r7,lr}}
ldr r4,data_ptr
ldr r5,system_ptr
ldr r6,[r5,#0x30]
movs r7,#4
ldr r0,[r4,#4]
adds r0,#1
str r0,[r4,#4]
audio_check:
ldr r1,[r4,#8]
subs r0,r6,r1
cmp r0,#8
bhi audio_reset
cmp r0,#2
blo schedule
adds r1,#2
str r1,[r4,#8]
bl 0x02004208
ldr r6,[r5,#0x30]
subs r7,#1
beq audio_reset
b audio_check
audio_reset:
str r6,[r4,#8]
schedule:
ldr r0,[r4,#4]
subs r0,r6,r0
cmp r0,#8
bhi resync
cmp r0,#1
bls ready
movs r0,#0
b store
resync:
str r6,[r4,#4]
ready:
movs r0,#1
store:
str r0,[r4]
pop {{r3,r4,r5,r6,r7,pc}}
.balign 4
data_ptr:.word {data}
system_ptr:.word {SYSTEM}
''',clock_at)
    def thumb_gate(target,variable,*,field_only=False,parity=True):
        at=START+len(code)
        guard='''ldr r2,system_ptr
ldr r2,[r2]
ldr r3,field_ptr
cmp r2,r3
bne enabled
''' if field_only else ''
        literals=f'system_ptr:.word {SYSTEM}\nfield_ptr:.word {FIELD_CB}\n' if field_only else ''
        condition='lsls r3,r3,#31' if parity else 'cmp r3,#0'
        code.extend(compile_code(f'''{guard}ldr r3,phase_ptr
ldr r3,[r3]
{condition}
beq done
enabled:
ldr r3,target_ptr
bx r3
done:
bx lr
.balign 4
phase_ptr:.word {variable}
target_ptr:.word {target}
{literals}''',at))
        return at
    wait_at=thumb_gate(0x020d0e6c,data,field_only=True,parity=False)
    field_at=thumb_gate(0x021e6221,data+4)
    sprite_at=thumb_gate(0x02024eb5,data+4,field_only=True)
    arm_gates={}
    for target in (0x020b7418,0x020bfcc8):
        at=START+len(code)
        assert at%4==0 and raw[target-BASE:target-BASE+4]==bytes.fromhex('10402de9')
        # Execute the original prologue first: r4 becomes a safe scratch, and
        # either path restores the caller's original r4/lr/stack correctly.
        payload=bytes(Ks(KS_ARCH_ARM,KS_MODE_ARM).asm(f'''push {{r4,lr}}
ldr ip,system_ptr
ldr ip,[ip]
ldr r4,field_ptr
cmp ip,r4
bne enabled
ldr ip,phase_ptr
ldr ip,[ip]
tst ip,#1
popeq {{r4,pc}}
enabled:
b {target+4}
system_ptr:.word {SYSTEM}
field_ptr:.word {FIELD_CB}
phase_ptr:.word {data+4}
''',addr=at)[0])
        code+=payload
        arm[target-BASE:target-BASE+4]=bytes(Ks(KS_ARCH_ARM,KS_MODE_ARM).asm(f'b {at}',addr=target)[0])
        arm_gates[target]=at
    if START+len(code)>data:raise ValueError('V6.1 wrapper allocation overflow')
    used=len(code)
    code+=bytes.fromhex('c046')*((data-START-len(code))//2)+struct.pack('<3I',1,0,0)
    arm[START-BASE:END-BASE]=code
    branch=lambda at,target:compile_code(f'bl {target}',at)
    arm[0xe1e:0xe22]=branch(0x02000e1e,wait_at)
    arm[0xe3c:0xe40]=branch(0x02000e3c,clock_at)
    struct.pack_into('<I',arm,0xf6318,sprite_at|1)
    # These paths must always run, for every field/battle/loading callback.
    for at,size in ((0xe10,4),(0xe38,4),(0xe42,4)):
        if arm[at:at+size]!=raw[at:at+size]:raise ValueError('Resource publication was gated')
    ov=ndspy.code.loadOverlayTable(original.arm9OverlayTable,lambda oid,fid:original.files[fid],{1})[1]
    off=0x021e6022-ov.ramAddress
    if ov.data[off:off+4]!=branch(0x021e6022,0x021e6220):raise ValueError('Field draw call mismatch')
    ov.data[off:off+4]=branch(0x021e6022,field_at)
    if ov.data.count(struct.pack('<I',FIELD_CB))<1:raise ValueError('Field callback identity mismatch')
    settings=ndspy.code.MainCodeFile(original.arm9,BASE).codeSettingsOffs
    packed=bytearray(ndspy.codeCompression.compress(arm,True))
    struct.pack_into('<I',packed,settings+20,BASE+len(packed))
    struct.pack_into('<I',arm,settings+20,BASE+len(packed))
    if ndspy.codeCompression.decompress(packed)!=arm:raise ValueError('ARM9 roundtrip failed')
    result=bytearray(source)
    start=struct.unpack_from('<I',source,0x20)[0]
    limit=struct.unpack_from('<I',source,0x50)[0]
    if start+len(packed)+len(original.arm9PostData)>limit:raise ValueError('ARM9 slot overflow')
    result[start:start+len(packed)+len(original.arm9PostData)]=packed+original.arm9PostData
    struct.pack_into('<I',result,0x2c,len(packed))
    struct.pack_into('<H',result,0x15e,crc16(result[:0x15e]))
    fat=struct.unpack_from('<I',source,0x48)[0]
    entries=[struct.unpack_from('<II',source,fat+i*8) for i in range(len(original.files))]
    start,end=entries[ov.fileID];payload=ov.save(compress=True)
    if start+len(payload)>min(a for a,b in entries if a>start):raise ValueError('Field overlay slot overflow')
    result[start:start+len(payload)]=payload
    struct.pack_into('<I',result,fat+ov.fileID*8+4,start+len(payload))
    table,size=struct.unpack_from('<II',source,0x50)
    row=[at for at in range(table,table+size,32) if struct.unpack_from('<I',source,at)[0]==1][0]
    flags=struct.unpack_from('<I',source,row+28)[0]&0xff000000
    struct.pack_into('<I',result,row+28,flags|len(payload))
    target=bytes(result);inspect(target)
    check=ndspy.rom.NintendoDSRom(target)
    if ndspy.codeCompression.decompress(check.arm9)!=arm:raise ValueError('Executable readback failed')
    if check.arm7!=original.arm7 or check.arm9PostData!=original.arm9PostData:raise ValueError('Protected CPU/footer changed')
    if len(target)!=len(source) or len(check.files)!=len(original.files):raise ValueError('Cartridge/file count changed')
    for attr in ('arm7OverlayTable','iconBanner'):
        if getattr(check,attr)!=getattr(original,attr):raise ValueError('Protected cartridge metadata changed')
    memory_layout=lambda r:[(s.ramAddress,len(s.data),s.bssSize,s.implicit) for s in ndspy.code.MainCodeFile(r.arm9,BASE).sections]
    if memory_layout(check)!=memory_layout(original):raise ValueError('Executable memory layout changed')
    regions=[(0xdf8,2),(0xdfe,4),(0xe1e,4),(0xe28,2),(0xe3c,4),
             (0x62568,584),(0x5ce68,220),(0x1ff44,44),(0xb7418,4),
             (0xbfcc8,4),(0xf6318,4),(settings+20,4)]
    for family,*_ in FAMILIES:
        for direction in range(4):
            row=struct.unpack_from('<I',raw,struct.unpack_from('<I',raw,0x6246c)[0]-BASE+(family+direction)*4)[0]
            regions.append((row-BASE,4))
    allowed={i for at,n in regions for i in range(at,at+n)}
    if len(raw)!=len(arm) or any(i not in allowed for i,(a,b) in enumerate(zip(raw,arm)) if a!=b):
        raise ValueError('Unexpected executable edit')
    loaded=ndspy.code.loadOverlayTable(check.arm9OverlayTable,lambda oid,fid:check.files[fid],{1})[1]
    if loaded.data!=ov.data:raise ValueError('Field overlay readback failed')
    for fid,(old,new) in enumerate(zip(original.files,check.files)):
        if fid!=ov.fileID and old!=new:raise ValueError(f'Protected file changed: {fid}')
    report=dict(version='v6.1',status='experimental',release_ready=False,
        source_sha256=digest(source),target_sha256=digest(target),clock=clock_at,wait=wait_at,
        render=field_at,sprite=sprite_at,arm_gates=arm_gates,data=data,field_callback=FIELD_CB,
        helper_bytes=used,packed=len(packed),physical_audio_update_period=2,
        graphics_publication='stock every update; low-level draw gates match exact field callback only')
    return target,report
