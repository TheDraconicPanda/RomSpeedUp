"""V6.4: wait for the cutscene texture upload before freeing its source."""
import struct
import ndspy.code
import ndspy.rom

from .v63 import build as build_v63
from .v6_native import compile_code
from .overlay_patch import digest
from .rom import inspect

READY_INIT = 0x021F198C


def build(source):
    base, report = build_v63(source)
    if digest(base) != '5b4a5e458ff82e8a5af3e3dcffc72ee36e24a1313c297e1e12207761cb2a05e4':
        raise ValueError('V6.4 requires the verified V6.3 baseline')
    prior = ndspy.rom.NintendoDSRom(base)
    overlay = ndspy.code.loadOverlayTable(prior.arm9OverlayTable,
        lambda oid, fid: prior.files[fid], {1})[1]
    before = bytes(overlay.data)
    off = READY_INIT-overlay.ramAddress
    if overlay.data[off:off+2] != compile_code('movs r0,#1', READY_INIT):
        raise ValueError('Unexpected cutscene resource-ready initialization')
    # ov01_021F19B4 sets ready=1 AFTER uploading in VBlank. VWait cleanup can
    # run first under the accelerated loop; initialize pending, not complete.
    overlay.data[off:off+2] = compile_code('movs r0,#0', READY_INIT)
    payload = overlay.save(compress=True)
    result = bytearray(base)
    fat = struct.unpack_from('<I', base, 0x48)[0]
    entries = [struct.unpack_from('<II', base, fat+i*8) for i in range(len(prior.files))]
    start, end = entries[overlay.fileID]
    if start+len(payload) > min(a for a,b in entries if a>start):
        raise ValueError('Field overlay slot overflow')
    result[start:start+len(payload)] = payload
    struct.pack_into('<I', result, fat+overlay.fileID*8+4, start+len(payload))
    table, size = struct.unpack_from('<II', base, 0x50)
    row = [at for at in range(table, table+size, 32) if struct.unpack_from('<I', base, at)[0]==1][0]
    flags = struct.unpack_from('<I', base, row+28)[0] & 0xFF000000
    struct.pack_into('<I', result, row+28, flags | len(payload))
    target = bytes(result)
    inspect(target)
    check = ndspy.rom.NintendoDSRom(target)
    for attr in ('arm9','arm7','arm9PostData','arm7OverlayTable','iconBanner'):
        if getattr(check,attr)!=getattr(prior,attr):
            raise ValueError(f'Protected V6.3 asset changed: {attr}')
    if len(target)!=len(base) or len(check.files)!=len(prior.files):
        raise ValueError('Cartridge or file count changed')
    for fid,(old,new) in enumerate(zip(prior.files,check.files)):
        if fid!=overlay.fileID and old!=new:
            raise ValueError(f'Protected file changed: {fid}')
    loaded = ndspy.code.loadOverlayTable(check.arm9OverlayTable,
        lambda oid, fid: check.files[fid], {1})[1]
    if loaded.data!=overlay.data or len(loaded.data)!=len(before) or loaded.bssSize!=overlay.bssSize:
        raise ValueError('Field overlay readback/layout changed')
    if any(not off<=i<off+2 for i,(a,b) in enumerate(zip(before,loaded.data)) if a!=b):
        raise ValueError('Unexpected field overlay change')
    report.update(version='v6.4',target_sha256=digest(target),cutscene_ready_init=READY_INIT,
        cutscene_texture_state='pending until VBlank upload callback completes')
    return target,report
