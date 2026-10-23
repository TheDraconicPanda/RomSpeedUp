"""Fixed-size, original-byte-guarded edits and BPS v1 output."""
import hashlib
import struct
import zlib


def apply(source, manifest):
    if manifest.get('schema') != 1 or manifest.get('status') != 'verified':
        raise ValueError('Only reviewed, verified schema-1 manifests can build')
    if hashlib.sha256(source).hexdigest() != manifest['source_sha256']:
        raise ValueError('Wrong source SHA256')
    edits = manifest['edits']
    if not edits:
        raise ValueError('Empty patch; no enhancement implemented')
    parsed = []
    for edit in edits:
        at = edit['offset']
        old, new = bytes.fromhex(edit['before']), bytes.fromhex(edit['after'])
        if type(at) is not int or at < 0x200 or not old or len(old) != len(new):
            raise ValueError('Edits must be nonempty, fixed-size and outside the header')
        if old == new or at + len(old) > len(source) or source[at:at+len(old)] != old:
            raise ValueError('No-op, out-of-bounds edit or original-byte mismatch')
        if not edit.get('rationale'):
            raise ValueError('Each edit requires a rationale')
        parsed.append((at, old, new))
    parsed.sort()
    if any(a[0] + len(a[1]) > b[0] for a, b in zip(parsed, parsed[1:])):
        raise ValueError('Overlapping edits')
    target = bytearray(source)
    for at, old, new in parsed:
        target[at:at+len(old)] = new
    target = bytes(target)
    if hashlib.sha256(target).hexdigest() != manifest['target_sha256']:
        raise ValueError('Unexpected output SHA256')
    return target


def number(value):
    result = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if not value:
            result.append(b | 0x80)
            return result
        result.append(b)
        value -= 1


def bps(source, target):
    if len(source) != len(target):
        raise ValueError('Only fixed-size patches supported')
    result = bytearray(b'BPS1') + number(len(source)) + number(len(target)) + number(0)
    start = 0
    while start < len(source):
        same = source[start] == target[start]
        end = start + 1
        while end < len(source) and (source[end] == target[end]) == same:
            end += 1
        result += number(((end - start - 1) << 2) | (0 if same else 1))
        if not same:
            result += target[start:end]
        start = end
    result += struct.pack('<II', zlib.crc32(source), zlib.crc32(target))
    result += struct.pack('<I', zlib.crc32(result))
    return bytes(result)
