import copy
import hashlib
import json
from pathlib import Path
import struct
import zlib

import pytest

from romspeedup.cli import main
from romspeedup.patch import apply, bps, number
from romspeedup.rom import InvalidROM, crc16, inspect, verify


def fixture_rom():
    # Synthetic header/data, no Nintendo ROM or logo bytes.
    data = bytearray(4096)
    data[:12] = b'TEST FIXTURE'
    data[12:16] = b'IPGE'
    struct.pack_into('<4I', data, 0x20, 0x200, 0x2000000, 0x2000000, 0x100)
    struct.pack_into('<4I', data, 0x30, 0x300, 0x2380000, 0x2380000, 0x100)
    struct.pack_into('<2I', data, 0x48, 0x400, 8)
    struct.pack_into('<2I', data, 0x400, 0x500, 0x600)
    data[0x200:0x204] = bytes.fromhex('0100a0e3')  # ARM mov r0, #1
    return fix_crc(data)


def fix_crc(data):
    data = bytearray(data)
    struct.pack_into('<H', data, 0x15C, crc16(data[0xC0:0x15C]))
    struct.pack_into('<H', data, 0x15E, crc16(data[:0x15E]))
    return bytes(data)


def manifest(source):
    target = bytearray(source)
    target[0x200] = 2
    return dict(schema=1, status='verified', features=['synthetic-test-only'],
                source_sha256=hashlib.sha256(source).hexdigest(),
                target_sha256=hashlib.sha256(target).hexdigest(),
                edits=[dict(offset=0x200, before='01', after='02', rationale='synthetic test')])


def profile(source):
    info = inspect(source)
    return {k: info[k] for k in ('game_code', 'revision', 'size', 'sha1')}


def test_structure_and_reference_identity():
    source = fixture_rom()
    assert inspect(source)['file_count'] == 1
    assert verify(source, profile(source))['game_code'] == 'IPGE'
    actual_profile = json.loads(Path('profiles/soulsilver-usa.json').read_text())
    with pytest.raises(InvalidROM):
        verify(source, actual_profile)


@pytest.mark.parametrize('field,at,value', [
    ('arm9 range', 0x20, 0xFFFFFF00), ('entry', 0x24, 0),
    ('fat alignment', 0x4C, 7), ('overlap', 0x30, 0x200),
    ('fat range', 0x404, 0xFFFFFF00), ('empty arm9', 0x2C, 0),
    ('overlay alignment', 0x54, 1),
])
def test_malformed_structure(field, at, value):
    data = bytearray(fixture_rom())
    struct.pack_into('<I', data, at, value)
    with pytest.raises(InvalidROM):
        inspect(fix_crc(data))


@pytest.mark.parametrize('at', [0, 0xC0, 0x15E])
def test_crc_rejects_corruption(at):
    data = bytearray(fixture_rom())
    data[at] ^= 1
    with pytest.raises(InvalidROM):
        inspect(data)


def test_truncated_header():
    with pytest.raises(InvalidROM):
        inspect(b'')


@pytest.mark.parametrize('change', ['source', 'target', 'before', 'overlap', 'size', 'bounds', 'header', 'draft', 'empty', 'noop'])
def test_unsafe_manifest_rejected(change):
    source = fixture_rom()
    m = manifest(source)
    if change in ('source', 'target'):
        m[change + '_sha256'] = '0' * 64
    elif change == 'before':
        m['edits'][0]['before'] = 'ff'
    elif change == 'overlap':
        m['edits'] *= 2
    elif change == 'size':
        m['edits'][0]['after'] = '0203'
    elif change == 'bounds':
        m['edits'][0]['offset'] = len(source)
    elif change == 'header':
        m['edits'][0]['offset'] = 0
    elif change == 'draft':
        m['status'] = 'draft'
    elif change == 'empty':
        m['edits'] = []
    elif change == 'noop':
        m['edits'][0]['after'] = '01'
    with pytest.raises(ValueError):
        apply(source, m)


def decode_bps(source, patch):
    # Independent BPS consumer used as a format oracle, including all CRC trailers.
    assert patch[:4] == b'BPS1'
    assert zlib.crc32(patch[:-4]) == struct.unpack('<I', patch[-4:])[0]
    at = 4
    def read():
        nonlocal at
        value, shift = 0, 1
        while True:
            byte = patch[at]
            at += 1
            value += (byte & 127) * shift
            if byte & 128:
                return value
            shift *= 128
            value += shift
    assert read() == len(source)
    size = read()
    metadata = read()
    at += metadata
    target = bytearray()
    while len(target) < size:
        action = read()
        length, kind = (action >> 2) + 1, action & 3
        if kind == 0:
            target += source[len(target):len(target)+length]
        elif kind == 1:
            target += patch[at:at+length]
            at += length
        else:
            raise AssertionError('unexpected action')
    assert at == len(patch) - 12
    assert struct.unpack('<II', patch[-12:-4]) == (zlib.crc32(source), zlib.crc32(target))
    return bytes(target)


@pytest.mark.parametrize('source,target', [(b'', b''), (b'abc', b'abc'), (b'abc', b'xyz'),
                                           (b'a' * 20000, b'a' * 10000 + b'b' + b'a' * 9999),
                                           (b'ab' * 100, b'ac' * 100)])
def test_bps_roundtrip(source, target):
    assert decode_bps(source, bps(source, target)) == target


def test_cli_build_and_no_overwrite(tmp_path):
    source = fixture_rom()
    rom = tmp_path / 'private.nds'
    rom.write_bytes(source)
    p = tmp_path / 'profile.json'
    p.write_text(json.dumps(profile(source)))
    m = tmp_path / 'manifest.json'
    m.write_text(json.dumps(manifest(source)))
    out = tmp_path / 'result'
    args = ['build', str(rom), str(m), '--profile', str(p), '--out', str(out)]
    assert main(args) == 0
    assert decode_bps(source, (out / 'patch.bps').read_bytes()) == (out / 'patched.nds').read_bytes()
    assert rom.read_bytes() == source
    assert main(args) == 1


def test_arm_disassembler_installed():
    import capstone
    arm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    op = list(arm.disasm(bytes.fromhex('0100a0e3'), 0x2000000))[0]
    assert op.mnemonic == 'mov' and op.op_str == 'r0, #1'
