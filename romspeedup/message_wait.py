"""Guarded manual miss/immunity waits on the exact partial European candidate."""
import struct

import ndspy.code
import ndspy.narc
import ndspy.rom

from .overlay_patch import digest
from .rom import inspect

BASELINE = 'cdf7059ea67936816d724df8d5336e1b5c364a5d41acef7e4e5f8280db6e9e92'
HANDLER = 0x0223E2F0
HANDLER_SIZE = 156
HANDLER_DIGEST = '233a3d7c1e202aecede2cd48d5e6d75518ee420edc223367f917aed284c3bf84'
SCRIPT_DIGESTS = {
    7: '3813512a246a7005bb9080b322e2cfbe44c7d5958b5f6bb6b02600d3b9d2ddf2',
    176: 'b6c9c44f5162c371c0d01a18598dc1b3dcade9384d70684b3282d824d7402f71',
}


def patch_scripts(archive):
    """Retarget selected messages; keep original shared waits and branches intact."""
    narc = ndspy.narc.NARC(archive)
    for sid, expected in SCRIPT_DIGESTS.items():
        if digest(narc.files[sid]) != expected:
            raise ValueError('Unexpected battle subscript digest')
    words = list(struct.unpack('<195I', narc.files[7]))
    # A separate tail checks the existing link-battle bit before using -1.
    # Branch displacements count words from the end of each command.
    manual, avoided = 195, 205
    for command in [80, 96, 118, 133, 156, 174]:
        if words[command] != 59 or command + 2 + words[command+1] != 180:
            raise ValueError('Unexpected result-message branch')
        words[command+1] = manual - (command+2)
    for parameter in [164, 169]:
        if parameter+1+words[parameter] != 176:
            raise ValueError('Unexpected avoided-attack branch')
        words[parameter] = avoided - (parameter+1)
    words += [14, 32, 4, 0, 4, (181-201) & 0xffffffff,
              30, 0xffffffff, 59, (183-205) & 0xffffffff,
              18, 24, 2, 2, 59, (manual-211) & 0xffffffff]
    narc.files[7] = struct.pack('<'+'I'*len(words), *words)
    words = list(struct.unpack('<12I', narc.files[176]))
    if words[5:7] != [30, 30]:
        raise ValueError('Unexpected avoided-attack wait')
    # Replace its original wait with a jump to a guarded appended wait.
    words[5:7] = [59, 12-7]
    words += [32, 4, 0, 4, 21-17, 30, 0xffffffff, 59, (7-21) & 0xffffffff,
              30, 30, 59, (7-25) & 0xffffffff]
    narc.files[176] = struct.pack('<'+'I'*len(words), *words)
    packed = narc.save()
    check = ndspy.narc.NARC(packed)
    original = ndspy.narc.NARC(archive)
    if len(check.files) != len(original.files):
        raise ValueError('Battle archive member count changed')
    for sid, (a, b) in enumerate(zip(original.files, check.files)):
        if sid not in SCRIPT_DIGESTS and a != b:
            raise ValueError('Unselected battle script changed')
    return packed


def patch_manual_wait(source, code):
    if digest(source) != BASELINE:
        raise ValueError('Manual wait requires the exact partial European candidate')
    if len(code) != HANDLER_SIZE:
        raise ValueError('Manual wait handler does not fit its verified slot')
    sections = inspect(source)['sections']
    rom = ndspy.rom.NintendoDSRom(source)
    ov = ndspy.code.loadOverlayTable(rom.arm9OverlayTable,
                                    lambda oid, fid: rom.files[fid], {12})[12]
    at = HANDLER-ov.ramAddress
    if digest(ov.data[at:at+HANDLER_SIZE]) != HANDLER_DIGEST:
        raise ValueError('Unexpected wait handler digest')
    # Check the real script-command dispatch table, not just a matching function.
    table_at = 0x0226C6C8-ov.ramAddress
    if struct.unpack_from('<I', ov.data, table_at+30*4)[0] != HANDLER | 1:
        raise ValueError('Unexpected wait command dispatch')
    ov.data[at:at+HANDLER_SIZE] = code
    archive_id = rom.filenames.idOf('a/0/0/1')
    if archive_id != 130 or digest(rom.files[archive_id]) != '4bdd8f93da7831add2db84671be9cc4c5d3ab2f981c391f3f84ad4b451cc08aa':
        raise ValueError('Unexpected battle archive')
    replacements = {ov.fileID: ov.save(compress=ov.compressed),
                    archive_id: patch_scripts(rom.files[archive_id])}
    fat, fat_size = struct.unpack_from('<II', source, 0x48)
    entries = [struct.unpack_from('<II', source, fat+i*8) for i in range(fat_size//8)]
    result = bytearray(source)
    for fid, data in replacements.items():
        start, end = entries[fid]
        boundaries = [a for a, b in entries if a > start]
        boundaries += [s['offset'] for s in sections.values() if s['size'] and s['offset'] > start]
        capacity = min(boundaries+[len(source)])
        if start+len(data) > capacity or (start+len(data) > end and
                any(x not in (0, 255) for x in source[end:start+len(data)])):
            raise ValueError('Updated file exceeds verified padding capacity')
        result[start:start+len(data)] = data
        struct.pack_into('<I', result, fat+fid*8+4, start+len(data))
    table, table_size = struct.unpack_from('<II', source, 0x50)
    rows = [pos for pos in range(table, table+table_size, 32)
            if struct.unpack_from('<I', source, pos)[0] == 12]
    if len(rows) != 1:
        raise ValueError('Unexpected overlay table')
    flags = struct.unpack_from('<I', source, rows[0]+28)[0] & 0xff000000
    struct.pack_into('<I', result, rows[0]+28, flags | len(replacements[ov.fileID]))
    target = bytes(result)
    inspect(target)
    check = ndspy.rom.NintendoDSRom(target)
    if len(target) != len(source) or target[:0x200] != source[:0x200]:
        raise ValueError('Cartridge/header changed')
    fnt = sections['fnt']
    if (check.arm9 != rom.arm9 or check.arm7 != rom.arm7 or
            target[fnt['offset']:fnt['offset']+fnt['size']] !=
            source[fnt['offset']:fnt['offset']+fnt['size']]):
        raise ValueError('Protected executable/filesystem changed')
    for fid, (a, b) in enumerate(zip(rom.files, check.files)):
        if fid not in replacements and a != b:
            raise ValueError('Unselected asset changed')
    rebuilt = ndspy.code.loadOverlayTable(check.arm9OverlayTable,
                                         lambda oid,fid:check.files[fid], {12})[12]
    if rebuilt.data != ov.data:
        raise ValueError('Overlay compression roundtrip failed')
    for field in ['ramAddress', 'ramSize', 'bssSize', 'staticInitStart', 'staticInitEnd']:
        if getattr(rebuilt, field) != getattr(ov, field):
            raise ValueError('Overlay memory layout changed')
    return target, dict(source_sha256=digest(source), target_sha256=digest(target),
                        changed_files=sorted(replacements), scripts=[7,176],
                        file_sizes={str(k): len(v) for k,v in replacements.items()})
