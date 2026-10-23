import hashlib
import struct
import copy

import ndspy.codeCompression
import ndspy.rom
import pytest

from romspeedup.overlay_patch import patch_overlays, digest
from test_pipeline import fixture_rom, fix_crc


def overlay_fixture():
    raw = b'0123456789' * 80
    packed = ndspy.codeCompression.compress(raw)
    source = bytearray(fixture_rom())
    start = 0x500
    source[start:start+len(packed)] = packed
    struct.pack_into('<II', source, 0x400, start, start+len(packed))
    struct.pack_into('<II', source, 0x50, 0x420, 32)
    struct.pack_into('<8I', source, 0x420, 12, 0x22378C0, len(raw), 32, 0, 0, 0,
                     0x01000000 | len(packed))
    source = fix_crc(source)
    spec = dict(source_sha256=digest(source), overlay_sha256={'12':digest(raw)},
                features=['motion'], edits=[dict(feature='motion', overlay=12,
                ram_address=0x22378C2, before='32', after='78')])
    return source, spec, raw


def test_overlay_roundtrip_and_unchanged_assets():
    source, spec, raw = overlay_fixture()
    target, report = patch_overlays(source, spec, ['motion'])
    assert target[:0x200] == source[:0x200] and len(target) == len(source)
    before, after = ndspy.rom.NintendoDSRom(source), ndspy.rom.NintendoDSRom(target)
    assert before.arm9 == after.arm9 and before.arm7 == after.arm7
    decoded = ndspy.codeCompression.decompress(after.files[0])
    assert decoded == raw[:2] + b'x' + raw[3:]
    assert report[0]['overlay'] == 12
    assert patch_overlays(source, spec, ['motion'])[0] == target


@pytest.mark.parametrize('bad', ['source', 'overlay', 'bytes', 'overlap', 'bounds', 'unknown', 'empty'])
def test_overlay_guards(bad):
    source, spec, raw = overlay_fixture()
    selected = ['motion']
    if bad == 'source': spec['source_sha256'] = '0'*64
    if bad == 'overlay': spec['overlay_sha256']['12'] = '0'*64
    if bad == 'bytes': spec['edits'][0]['before'] = 'ff'
    if bad == 'overlap': spec['edits'] *= 2
    if bad == 'bounds': spec['edits'][0]['ram_address'] += len(raw)
    if bad == 'unknown': selected = ['unimplemented']
    if bad == 'empty': selected = []
    with pytest.raises(ValueError): patch_overlays(source, spec, selected)
