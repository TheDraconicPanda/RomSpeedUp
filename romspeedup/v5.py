"""Guarded experimental v5: local city motion and visible automatic result text."""
from pathlib import Path
import struct

from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
import ndspy.code
import ndspy.codeCompression
import ndspy.narc
import ndspy.rom

from .message_wait import BASELINE, patch_scripts
from .overlay_patch import digest
from .rom import inspect, crc16

BASE = 0x02000000


def assemble(name, address):
    path = Path(__file__).resolve().parents[1]/'features'/(name+'.s')
    source = '\n'.join(line for line in path.read_text().splitlines()
                       if not line.startswith('//'))
    result=bytes(Ks(KS_ARCH_ARM,KS_MODE_THUMB).asm(source,addr=address)[0])
    literal_bytes=sum('.word' in line for line in source.splitlines())*4
    code=result[:len(result)-literal_bytes] if literal_bytes else result
    instructions=list(Cs(CS_ARCH_ARM,CS_MODE_THUMB).disasm(code,address))
    if sum(i.size for i in instructions)!=len(code) or any(i.size==4 and i.mnemonic not in ['bl','blx'] for i in instructions):
        raise ValueError('Assembler emitted unsupported ARM9 Thumb instructions')
    return result


def build(source):
    if digest(source) != BASELINE:
        raise ValueError('v5 requires the exact reproduced European partial V4')
    sections = inspect(source)['sections']
    rom = ndspy.rom.NintendoDSRom(source)
    original_arm = bytes(ndspy.codeCompression.decompress(rom.arm9))
    arm = bytearray(original_arm)
    edits = []
    def edit_arm(address,data,guard=None):
        at=address-BASE
        old=original_arm[at:at+len(data)]
        if guard and digest(old)!=guard: raise ValueError('ARM9 guard mismatch')
        if at<0 or at+len(data)>len(arm): raise ValueError('ARM9 edit out of bounds')
        if any(set(range(address,address+len(data))) & set(range(e['address'],e['address']+e['size'])) for e in edits):
            raise ValueError('Overlapping ARM9 edit')
        arm[at:at+len(data)]=data
        edits.append(dict(address=address,size=len(data),before_sha256=digest(old)))
    state=assemble('v5-player-state',0x0205ce68)
    city_at=0x0205ce68+len(state)
    city=assemble('v5-city-init',city_at)
    yield_at=city_at+len(city)
    yielding=assemble('v5-yield-text',yield_at)
    code=state+city+yielding
    if len(code)>220 or len(code)%2: raise ValueError('Player slot overflow')
    code += bytes.fromhex('c046')*((220-len(code))//2)
    edit_arm(0x0205ce68,code,'c7e49fddd8037410c2565ed9bab135b1e5c1c50de6a546f8c1adc6642c9448d2')
    # BL enters a tail continuation using the printer's existing {r4,lr} frame.
    branch=lambda at,target: bytes(Ks(KS_ARCH_ARM,KS_MODE_THUMB).asm(f'bl {target}',addr=at)[0])
    edit_arm(0x02020320,branch(0x02020320,yield_at),
             '858a6bd30b57be3ecb4c34c957c3ce1d7c611869e527c66307621275c1f61a50')
    edit_arm(0x0202032c,branch(0x0202032c,yield_at+4),
             'b5a6a469886dd4556089e8a9d07d79ce2d8c5c396db0e1e67ebf907127657fb6')
    callbacks={12:0x02062608,13:0x02062620,14:0x02062634,15:0x02062648,
               88:0x02062758,89:0x02062770,90:0x02062784,91:0x02062798}
    calls={}
    table=struct.unpack_from('<I',arm,0x0206246c-BASE)[0]
    for command,entry in callbacks.items():
        row=struct.unpack_from('<I',arm,table-BASE+command*4)[0]
        if struct.unpack_from('<I',arm,row-BASE)[0] != entry|1:
            raise ValueError('Unexpected movement callback')
        candidates=[]
        for at in range(entry,entry+24,2):
            if original_arm[at-BASE:at-BASE+4]==branch(at,0x020624cc):candidates.append(at)
        if len(candidates)!=1:raise ValueError('Unexpected movement initializer call')
        calls[command]=candidates[0]
        edit_arm(candidates[0],branch(candidates[0],city_at))
    # Retain the original autoload layout and change only the packed-end pointer.
    settings=ndspy.code.MainCodeFile(rom.arm9,BASE).codeSettingsOffs
    if settings is None or struct.unpack_from('<I',original_arm,settings+20)[0]!=BASE+len(rom.arm9):
        raise ValueError('Unexpected ARM9 compression settings')
    packed=bytearray(ndspy.codeCompression.compress(arm,True))
    struct.pack_into('<I',packed,settings+20,BASE+len(packed))
    expected_arm=bytearray(arm)
    struct.pack_into('<I',expected_arm,settings+20,BASE+len(packed))
    if bytes(ndspy.codeCompression.decompress(packed))!=expected_arm:
        raise ValueError('ARM9 compression roundtrip failed')
    allowed=set(range(settings+20,settings+24))
    for e in edits:allowed.update(range(e['address']-BASE,e['address']-BASE+e['size']))
    if any(i not in allowed for i,(a,b) in enumerate(zip(original_arm,expected_arm)) if a!=b):
        raise ValueError('Unselected ARM9 code changed')
    ov=ndspy.code.loadOverlayTable(rom.arm9OverlayTable,lambda oid,fid:rom.files[fid],{12})[12]
    original_ov=bytes(ov.data)
    at=0x0223e2f0-ov.ramAddress
    if digest(ov.data[at:at+156])!='233a3d7c1e202aecede2cd48d5e6d75518ee420edc223367f917aed284c3bf84':
        raise ValueError('Wait command guard mismatch')
    if digest(ov.data[0x02245324-ov.ramAddress:0x02245390-ov.ramAddress])!='b416e7980d9c823603f0507989d3bd8e8bc49bf1df602960fc479ffb4413235b':
        raise ValueError('Shared WaitTime body guard mismatch')
    wait=assemble('v5-normal-wait',0x0223e2f0)
    speed_at=0x0223e2f0+len(wait)
    speed=assemble('v5-result-speed',speed_at)
    combined=wait+speed
    if len(combined)>156 or len(combined)%2: raise ValueError('Battle slot overflow')
    combined+=bytes.fromhex('c046')*((156-len(combined))//2)
    ov.data[at:at+156]=combined
    print_at=0x0223c49e-ov.ramAddress
    if digest(ov.data[print_at:print_at+4])!='4e1fba1bc7f7c9220c1bfea3432f11b6ccdaed06086ba0416dde43932cf47987':
        raise ValueError('Result print guard mismatch')
    ov.data[print_at:print_at+4]=branch(0x0223c49e,speed_at)
    for i,(a,b) in enumerate(zip(original_ov,ov.data)):
        if a!=b and not (at<=i<at+156 or print_at<=i<print_at+4):raise ValueError('Unselected overlay code changed')
    archive=ndspy.narc.NARC(patch_scripts(rom.files[130]))
    for sid,index in [(7,201),(176,17)]:
        words=list(struct.unpack('<'+'I'*(len(archive.files[sid])//4),archive.files[sid]))
        if words[index:index+2]!=[30,0xffffffff]:raise ValueError('Unexpected result wait')
        words[index:index+2]=[218,24]
        archive.files[sid]=struct.pack('<'+'I'*len(words),*words)
    archive=archive.save()
    # Replace bounded slots without relocating files or overlays.
    result=bytearray(source)
    fat,fat_size=struct.unpack_from('<II',source,0x48)
    entries=[struct.unpack_from('<II',source,fat+i*8) for i in range(fat_size//8)]
    replacements={ov.fileID:ov.save(compress=ov.compressed),130:archive}
    def put_slot(start,end,data):
        boundaries=[a for a,b in entries if a>start]
        boundaries += [s['offset'] for s in sections.values() if s['size'] and s['offset']>start]
        limit=min(boundaries+[len(source)])
        if start+len(data)>limit or (start+len(data)>end and any(x not in (0,255) for x in source[end:start+len(data)])):
            raise ValueError(f'New data exceeds existing slot padding: start={start:#x}, old={end-start}, new={len(data)}, capacity={limit-start}')
        result[start:start+len(data)]=data
    arm_start=sections['arm9']['offset']
    # Nitro's 12-byte footer follows the packed ARM9 and must move with its end.
    post=bytes(rom.arm9PostData)
    if len(post)!=12 or source[arm_start+len(rom.arm9):arm_start+len(rom.arm9)+12]!=post:
        raise ValueError('Unexpected ARM9 Nitro footer')
    put_slot(arm_start,arm_start+len(rom.arm9)+len(post),packed+post)
    struct.pack_into('<I',result,0x2c,len(packed))
    struct.pack_into('<H',result,0x15e,crc16(result[:0x15e]))
    for fid,data in replacements.items():
        start,end=entries[fid]
        put_slot(start,end,data)
        struct.pack_into('<I',result,fat+fid*8+4,start+len(data))
    table_at,table_size=struct.unpack_from('<II',source,0x50)
    row=[a for a in range(table_at,table_at+table_size,32) if struct.unpack_from('<I',source,a)[0]==12]
    if len(row)!=1:raise ValueError('Overlay table mismatch')
    flags=struct.unpack_from('<I',result,row[0]+28)[0]&0xff000000
    struct.pack_into('<I',result,row[0]+28,flags|len(replacements[ov.fileID]))
    target=bytes(result)
    inspect(target)
    check=ndspy.rom.NintendoDSRom(target)
    check_ov=ndspy.code.loadOverlayTable(check.arm9OverlayTable,lambda oid,fid:check.files[fid],{12})[12]
    if bytes(ndspy.codeCompression.decompress(check.arm9))!=expected_arm or check_ov.data!=ov.data:
        raise ValueError('Executable container roundtrip failed')
    if (len(target)!=len(source) or check.arm7!=rom.arm7 or
            check.arm9PostData!=rom.arm9PostData or len(check.files)!=len(rom.files)):
        raise ValueError('Protected cartridge layout changed')
    for field in ['ramAddress','ramSize','bssSize','staticInitStart','staticInitEnd']:
        if getattr(check_ov,field)!=getattr(ov,field):raise ValueError('Overlay memory layout changed')
    fnt=sections['fnt']
    if source[fnt['offset']:fnt['offset']+fnt['size']]!=target[fnt['offset']:fnt['offset']+fnt['size']]:
        raise ValueError('Filesystem names changed')
    for fid,(a,b) in enumerate(zip(rom.files,check.files)):
        if fid not in replacements and a!=b:raise ValueError('Unselected asset changed')
    # Retain autoload section addresses/sizes/BSS, including the prior global FPS edit.
    before_main=ndspy.code.MainCodeFile(rom.arm9,BASE)
    after_main=ndspy.code.MainCodeFile(check.arm9,BASE)
    layout=lambda m:[(s.ramAddress,len(s.data),s.bssSize,s.implicit) for s in m.sections]
    if layout(before_main)!=layout(after_main):raise ValueError('ARM9 autoload layout changed')
    report=dict(version='v5',status='experimental',release_ready=False,
                source_sha256=digest(source),target_sha256=digest(target),
                city_multiplier=2,result_wait_updates=24,result_print='one glyph per printer task invocation',
                state_address=0x0205ce68,city_address=city_at,yield_address=yield_at,
                speed_address=speed_at,init_calls=calls,arm9_edits=edits,
                arm9_packed_size=len(packed),overlay12_packed_size=len(replacements[ov.fileID]),
                pending=['Delta city speed calibration','full city/follower/camera regression','selective attack acceleration'])
    return target,report
