"""Repack selected compressed overlays in their existing FAT slots.

This deliberately preserves ARM9 (including v3's frame/text edits), ARM7,
file identities, RAM addresses, BSS layout and every unselected file.
"""
import hashlib
import struct

import ndspy.code
import ndspy.rom

from .rom import inspect


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_overlays(source, spec, selected):
    if digest(source) != spec['source_sha256']:
        raise ValueError('Wrong baseline SHA256; this candidate requires the exact supplied v3')
    if not selected or not set(selected) <= set(spec['features']):
        raise ValueError('Select only explicitly implemented features')
    inspect(source)
    rom = ndspy.rom.NintendoDSRom(source)
    overlay_ids = {e['overlay'] for e in spec['edits'] if e['feature'] in selected}
    overlays = ndspy.code.loadOverlayTable(rom.arm9OverlayTable,
                                          lambda oid, fid: rom.files[fid], overlay_ids)
    fat, fat_size = struct.unpack_from('<II', source, 0x48)
    table, table_size = struct.unpack_from('<II', source, 0x50)
    entries = [struct.unpack_from('<II', source, fat + i * 8) for i in range(fat_size // 8)]
    sections = inspect(source)['sections']
    result = bytearray(source)
    report = []
    for oid in sorted(overlay_ids):
        ov = overlays[oid]
        if digest(ov.data) != spec['overlay_sha256'][str(oid)]:
            raise ValueError('Unexpected decompressed overlay digest')
        original = bytes(ov.data)
        touched = set()
        for edit in (e for e in spec['edits'] if e['overlay'] == oid and e['feature'] in selected):
            at = edit['ram_address'] - ov.ramAddress
            before, after = bytes.fromhex(edit['before']), bytes.fromhex(edit['after'])
            positions = set(range(at, at + len(before)))
            if (at < 0 or at + len(before) > len(original) or not before or
                    len(before) != len(after) or before == after or touched & positions):
                raise ValueError('Invalid or overlapping fixed-size overlay edit')
            if original[at:at+len(before)] != before:
                raise ValueError('Instruction guard mismatch')
            ov.data[at:at+len(after)] = after
            touched |= positions
        packed = ov.save(compress=ov.compressed)
        start, end = entries[ov.fileID]
        # Never relocate a file or cross another file/header-table boundary.
        boundaries = [a for a, b in entries if a > start]
        boundaries += [s['offset'] for s in sections.values() if s['size'] and s['offset'] > start]
        capacity_end = min(boundaries + [len(source)])
        if start + len(packed) > capacity_end:
            raise ValueError('Recompressed overlay exceeds its existing slot')
        if start + len(packed) > end and any(b not in (0, 255) for b in source[end:start+len(packed)]):
            raise ValueError('Slot expansion would overwrite nonpadding bytes')
        rows = [at for at in range(table, table + table_size, 32)
                if struct.unpack_from('<I', source, at)[0] == oid]
        if len(rows) != 1:
            raise ValueError('Missing/duplicate overlay ID')
        flags = struct.unpack_from('<I', source, rows[0]+28)[0] & 0xFF000000
        result[start:start+len(packed)] = packed
        struct.pack_into('<I', result, fat + ov.fileID * 8 + 4, start + len(packed))
        struct.pack_into('<I', result, rows[0]+28, flags | len(packed))
        report.append(dict(overlay=oid, file_id=ov.fileID, before_size=end-start,
                           after_size=len(packed), decompressed_before=digest(original),
                           decompressed_after=digest(ov.data)))
    target = bytes(result)
    inspect(target)
    rebuilt = ndspy.rom.NintendoDSRom(target)
    if len(source) != len(target) or source[:0x200] != target[:0x200]:
        raise ValueError('Unexpected cartridge/header change')
    fnt = sections['fnt']
    if (rom.arm9 != rebuilt.arm9 or rom.arm7 != rebuilt.arm7 or
            source[fnt['offset']:fnt['offset']+fnt['size']] !=
            target[fnt['offset']:fnt['offset']+fnt['size']]):
        raise ValueError('Protected executable/filesystem metadata changed')
    modified_files = {overlays[i].fileID for i in overlay_ids}
    if len(rom.files) != len(rebuilt.files):
        raise ValueError('File count changed')
    for fid, (before, after) in enumerate(zip(rom.files, rebuilt.files)):
        if fid not in modified_files and before != after:
            raise ValueError('Unselected asset changed')
    reparsed = ndspy.code.loadOverlayTable(rebuilt.arm9OverlayTable,
                                           lambda oid, fid: rebuilt.files[fid], overlay_ids)
    for oid in overlay_ids:
        if reparsed[oid].data != overlays[oid].data:
            raise ValueError('Overlay recompression roundtrip failed')
    return target, report
