"""Experimental ROM-only 2x scheduler, original sound clocks and assets.

Research measurements and device limitations are recorded in docs/v6-rom-only.md.
No external emulator acceleration is used by this build.
"""
import struct
import ndspy.rom,ndspy.codeCompression,ndspy.code
from .overlay_patch import digest
from .v51 import group,FAMILIES
from .rom import inspect,crc16
from keystone import Ks,KS_ARCH_ARM,KS_MODE_THUMB
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB

def compile_code(source,address):
 raw=bytes(Ks(KS_ARCH_ARM,KS_MODE_THUMB).asm(source,addr=address)[0]);literals=4*source.count('.word');body=raw[:-literals] if literals else raw
 ins=list(Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(body,address));assert sum(i.size for i in ins)==len(body)
 assert all(i.size==2 or i.mnemonic in ('bl','blx') for i in ins)
 return raw

def _build_exact(source, *, graphics_safe=True):
    r=ndspy.rom.NintendoDSRom(source);orig=bytes(ndspy.codeCompression.decompress(r.arm9));arm=bytearray(orig);BASE=0x2000000
    # Compact equivalent direction wrappers free room inside their original
    # allocation. The final five words are private scheduler state, not code.
    START,END=0x2062568,0x20627b0;DATA=END-20
    code=bytearray();table=struct.unpack_from('<I',arm,0x6246c)[0]
    for family,animation,power,duration in FAMILIES:
     address=START+len(code)
     for d in range(4):
      row=struct.unpack_from('<I',arm,table-BASE+(family+d)*4)[0];struct.pack_into('<I',arm,row-BASE,address+d*4|1)
     code+=group(address,animation,power,duration,0x20624cc)
    clock_at=START+len(code)
    clock=compile_code(f'''push {{r3,r4,r5,r6,r7,lr}}
    ldr r4,data_ptr
    ldr r5,system_ptr
    ldr r6,[r5,#0x30]
    movs r7,#4
    ldr r0,[r4,#4]
    movs r1,#1
    ands r0,r1
    str r0,[r4,#16]
    ldr r0,[r4,#12]
    cmp r0,#0
    bne advance
    movs r0,#1
    str r0,[r4,#12]
    str r6,[r4,#4]
    subs r0,r6,#2
    str r0,[r4,#8]
    b audio_check
    advance:
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
    str r0,[r4]
    pop {{r3,r4,r5,r6,r7,pc}}
    resync:
    str r6,[r4,#4]
    ready:
    movs r0,#1
    str r0,[r4]
    pop {{r3,r4,r5,r6,r7,pc}}
    .balign 4
    data_ptr:.word {DATA}
    system_ptr:.word 0x021d110c
    ''',clock_at)
    code+=clock
    # Conditional tail gates preserve the original caller's arguments.
    def gate(target,variable,parity=False):
     address=START+len(code)
     condition='lsls r3,r3,#31' if parity else 'cmp r3,#0'
     data=compile_code(f'''ldr r3,phase_ptr
    ldr r3,[r3]
    {condition}
    beq done
    ldr r3,target_ptr
    bx r3
    done:bx lr
    .balign 4
    phase_ptr:.word {variable}
    target_ptr:.word {target}
    ''',address)
     code.extend(data);return address
    wait_at=gate(0x20d0e6c,DATA)
    render_at=gate(0x21e6221,DATA+4,True)
    vwait_at=gate(0x201f881,DATA+16)
    callback_at=START+len(code)
    callback=compile_code(f'''ldr r0,[r4,#4]
    ldr r3,data_ptr
    ldr r3,[r3]
    lsls r3,r3,#31
    beq done
    bx r1
    done:bx lr
    .balign 4
    data_ptr:.word {DATA+4}
    ''',callback_at);code+=callback

    from keystone import KS_MODE_ARM
    arm_gates={}
    for target in [0x020b7418,0x020bfcc8]:
     assert orig[target-BASE:target-BASE+4]==bytes.fromhex('10402de9')
     gate_at=START+len(code);assert gate_at%4==0
     arm_code=bytes(Ks(KS_ARCH_ARM,KS_MODE_ARM).asm(f'''ldr ip,phase_ptr
     ldr ip,[ip]
     tst ip,#1
     bxeq lr
     push {{r4,lr}}
     b {target+4}
     phase_ptr:.word {DATA+4}
     ''',addr=gate_at)[0]);assert len(arm_code)==28
     code.extend(arm_code);arm[target-BASE:target-BASE+4]=bytes(Ks(KS_ARCH_ARM,KS_MODE_ARM).asm(f'b {gate_at}',addr=target)[0]);arm_gates[target]=gate_at
    sprite_at=gate(0x02024eb5,DATA+4,True)
    assert struct.unpack_from('<I',orig,0xf6318)[0]==0x02024eb5
    struct.pack_into('<I',arm,0xf6318,sprite_at|1)
    swap_at=gate(0x02026e61,DATA+4,True)


    assert START+len(code)<=DATA
    code+=bytes.fromhex('c046')*((DATA-START-len(code))//2)+struct.pack('<5I',1,1,0,0,1);assert len(code)==END-START
    arm[START-BASE:END-BASE]=code
    branch=lambda at,target:compile_code(f'bl {target}',at)
    arm[0xe10:0xe14]=branch(0x2000e10,swap_at)
    # Remove the original pair of waits and phase the final wait; leave hardware
    # time monotonic so the scheduler can measure debt. Virtual game counters double.
    arm[0xdf8:0xdfa]=bytes.fromhex('c046')
    arm[0xdfe:0xe02]=bytes.fromhex('c046c046')
    arm[0xe1e:0xe22]=branch(0x2000e1e,wait_at)
    arm[0xe28:0xe2a]=bytes.fromhex('c046')
    arm[0xe38:0xe3c]=branch(0x2000e38,callback_at)
    arm[0xe3c:0xe40]=branch(0x2000e3c,clock_at)
    arm[0xe42:0xe46]=branch(0x2000e42,vwait_at)
    ov=ndspy.code.loadOverlayTable(r.arm9OverlayTable,lambda oid,fid:r.files[fid],{1})[1];at=0x21e6022-ov.ramAddress;assert ov.data[at:at+4]==branch(0x21e6022,0x21e6220);ov.data[at:at+4]=branch(0x21e6022,render_at)


    from .v5 import assemble
    state=assemble('v5-player-state',0x0205ce68)
    cipher_at=0x0205ce68+len(state)
    cipher=bytes(Ks(KS_ARCH_ARM,KS_MODE_ARM).asm('''push {r4,r5,r6,lr}
    movs r1,r1,lsr #1
    beq cipher_done
    ldr r4,cipher_mul
    ldr r5,cipher_add
    tst r1,#3
    bne 0x0201ff4c
    cipher_loop:
    mla r2,r4,r2,r5
    ldrh r3,[r0]
    eor r3,r3,r2,lsr #16
    strh r3,[r0],#2
    mla r2,r4,r2,r5
    ldrh r3,[r0]
    eor r3,r3,r2,lsr #16
    strh r3,[r0],#2
    mla r2,r4,r2,r5
    ldrh r3,[r0]
    eor r3,r3,r2,lsr #16
    strh r3,[r0],#2
    mla r2,r4,r2,r5
    ldrh r3,[r0]
    eor r3,r3,r2,lsr #16
    strh r3,[r0],#2
    subs r1,r1,#4
    bne cipher_loop
    cipher_done:
    pop {r4,r5,r6,pc}
    cipher_mul:.word 0x41c64e6d
    cipher_add:.word 0x6073
    ''',addr=cipher_at)[0])
    assert len(state+cipher)<=220
    arm[0x5ce68:0x5cf44]=state+cipher+bytes.fromhex('c046')*((220-len(state+cipher))//2)
    cipher_jump=compile_code(f'''ldr r3,fast_cipher
    bx r3
    fast_cipher:.word {cipher_at}
    ''',0x0201ff44)
    fallback=bytes(Ks(KS_ARCH_ARM,KS_MODE_ARM).asm('''cipher_fallback:
    mla r2,r4,r2,r5
    ldrh r3,[r0]
    eor r3,r3,r2,lsr #16
    strh r3,[r0],#2
    subs r1,r1,#1
    bne cipher_fallback
    pop {r4,r5,r6,pc}
    ''',addr=0x0201ff4c)[0])
    assert len(fallback)<=36
    arm[0x1ff4c:0x1ff70]=fallback+bytes(36-len(fallback))
    assert len(cipher_jump)==8
    arm[0x1ff44:0x1ff4c]=cipher_jump

    if graphics_safe:
        # Graphics callbacks publish queued resources, not just pictures.
        # They must not be skipped when battle states allocate/free textures.
        # Keep an unconditional physical VBlank between game updates, and keep
        # every stock graphics entry/callback/queue/swap path intact.
        for offset,size in [(0xe10,4),(0xe1e,4),(0xe38,4),(0xe42,4),
                            (0xb7418,4),(0xbfcc8,4),(0xf6318,4)]:
            arm[offset:offset+size]=orig[offset:offset+size]
        ov.data[0x21e6022-ov.ramAddress:0x21e6026-ov.ramAddress]=branch(0x21e6022,0x21e6220)

    p=bytearray(ndspy.codeCompression.compress(arm,True));settings=ndspy.code.MainCodeFile(r.arm9,BASE).codeSettingsOffs;struct.pack_into('<I',p,settings+20,BASE+len(p));struct.pack_into('<I',arm,settings+20,BASE+len(p));assert ndspy.codeCompression.decompress(p)==arm
    start=struct.unpack_from('<I',source,0x20)[0];assert start+len(p)+len(r.arm9PostData)<=struct.unpack_from('<I',source,0x50)[0]
    result=bytearray(source);result[start:start+len(p)+len(r.arm9PostData)]=p+r.arm9PostData;struct.pack_into('<I',result,0x2c,len(p));struct.pack_into('<H',result,0x15e,crc16(result[:0x15e]))
    fat=struct.unpack_from('<I',source,0x48)[0];start,end=struct.unpack_from('<II',source,fat+ov.fileID*8);packed=ov.save(compress=True);nextstart=min(struct.unpack_from('<I',source,fat+i*8)[0] for i in range(len(r.files)) if struct.unpack_from('<I',source,fat+i*8)[0]>start);assert start+len(packed)<=nextstart;result[start:start+len(packed)]=packed;struct.pack_into('<I',result,fat+ov.fileID*8+4,start+len(packed))
    table,size=struct.unpack_from('<II',source,0x50);row=[a for a in range(table,table+size,32) if struct.unpack_from('<I',source,a)[0]==1][0];flags=struct.unpack_from('<I',source,row+28)[0]&0xff000000;struct.pack_into('<I',result,row+28,flags|len(packed));inspect(result)
    return bytes(result),dict(clock=clock_at,wait=wait_at,render=render_at,callback=callback_at,
     vwait=vwait_at,data=DATA,packed=len(p),sprite=sprite_at,swap=swap_at,
     arm_gates=arm_gates,cipher=cipher_at,state_bytes=len(state),cipher_bytes=len(cipher))


def build(source, *, graphics_safe=True):
    """Require exact original; verify executable edits and protected payloads."""
    expected='94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17'
    if digest(source)!=expected:
        raise ValueError('Standalone V6 requires the exact original Europe ROM')
    target,report=_build_exact(source,graphics_safe=graphics_safe)
    old,new=map(ndspy.rom.NintendoDSRom,[source,target])
    before,after=[bytes(ndspy.codeCompression.decompress(r.arm9)) for r in (old,new)]
    if digest(before)!='534df6737a9a852bf24c9e63e93453897d9018a17e0685346fd37050123305a5':
        raise ValueError('Original executable identity mismatch')
    regions=[(0xdf8,2),(0xdfe,4),(0xe10,4),(0xe1e,4),(0xe28,2),(0xe38,4),
             (0xe3c,4),(0xe42,4),(0x62568,584),(0x5ce68,220),(0x1ff44,44),
             (0xb7418,4),(0xbfcc8,4),(0xf6318,4),(0xba0+20,4)]
    table=struct.unpack_from('<I',before,0x6246c)[0]
    for family,*_ in FAMILIES:
        for direction in range(4):
            row=struct.unpack_from('<I',before,table-0x2000000+(family+direction)*4)[0]
            regions.append((row-0x2000000,4))
    allowed={i for at,n in regions for i in range(at,at+n)}
    if len(before)!=len(after) or any(i not in allowed for i,(a,b) in enumerate(zip(before,after)) if a!=b):
        raise ValueError('Unexpected executable changes')
    overlays=[ndspy.code.loadOverlayTable(r.arm9OverlayTable,lambda oid,fid,r=r:r.files[fid],{1})[1] for r in (old,new)]
    a,b=overlays
    if len(a.data)!=len(b.data) or any(i not in range(0x21e6022-a.ramAddress,0x21e6026-a.ramAddress) for i,(x,y) in enumerate(zip(a.data,b.data)) if x!=y):
        raise ValueError('Unexpected field overlay changes')
    for i,(x,y) in enumerate(zip(old.files,new.files)):
        if i!=a.fileID and x!=y: raise ValueError(f'Protected file changed: {i}')
    if len(old.files)!=len(new.files): raise ValueError('File count changed')
    for field in ['arm7','arm7OverlayTable','iconBanner','arm9PostData']:
        if getattr(old,field)!=getattr(new,field): raise ValueError(f'Protected cartridge metadata changed: {field}')
    oldmain,newmain=[ndspy.code.MainCodeFile(r.arm9,0x2000000) for r in (old,new)]
    layout=lambda m:[(s.ramAddress,len(s.data),s.bssSize,s.implicit) for s in m.sections]
    if layout(oldmain)!=layout(newmain): raise ValueError('Executable memory layout changed')
    if len(source)!=len(target): raise ValueError('Cartridge size changed')
    report.update(version='v6.1-candidate' if graphics_safe else 'v6-rom-only-rejected',
        status='under-validation' if graphics_safe else 'rejected-battle-graphics',release_ready=False,
        source_sha256=digest(source),target_sha256=digest(target),rom_bytes=len(target),
        emulator_fast_forward_required=False,nominal_gameplay_multiplier=2,
        audio_assets='byte-identical to original',physical_audio_update_period=2,
        graphics_safe=graphics_safe,
        measured_city_multiplier=None if graphics_safe else 1.75,
        measured_lighter_scene_multiplier=None if graphics_safe else 358/180,
        limitations=['Battle rendering and scene timing require regression validation',
                     'Device validation and full-game graphics coverage pending'])
    return target,report
