import hashlib
import struct


class InvalidROM(ValueError):
    pass


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def inspect(data):
    if len(data) < 0x200:
        raise InvalidROM("Truncated NDS header")
    if crc16(data[:0x15E]) != struct.unpack_from('<H', data, 0x15E)[0]:
        raise InvalidROM("Header CRC16 mismatch")
    if crc16(data[0xC0:0x15C]) != struct.unpack_from('<H', data, 0x15C)[0]:
        raise InvalidROM("Nintendo logo CRC16 mismatch")
    sections = {}
    ranges = []
    for name, at, executable in [('arm9', 0x20, True), ('arm7', 0x30, True),
                                  ('fnt', 0x40, False), ('fat', 0x48, False),
                                  ('arm9_overlays', 0x50, False), ('arm7_overlays', 0x58, False)]:
        if executable:
            offset, entry, ram, size = struct.unpack_from('<4I', data, at)
        else:
            offset, size = struct.unpack_from('<2I', data, at)
        if executable and not size:
            raise InvalidROM(f"Empty {name}")
        if size and (offset < 0x200 or offset + size > len(data)):
            raise InvalidROM(f"Out-of-bounds {name}")
        if executable and not ram <= (entry & ~1) < ram + size:
            raise InvalidROM(f"Entry outside {name} RAM range")
        sections[name] = dict(offset=offset, size=size)
        if executable:
            sections[name].update(entry=entry, ram=ram)
        if size:
            ranges.append((offset, offset + size, name))
    ranges.sort()
    if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise InvalidROM("Overlapping NDS sections")
    fat = sections['fat']
    if fat['size'] % 8:
        raise InvalidROM("Malformed FAT size")
    files = []
    for at in range(fat['offset'], fat['offset'] + fat['size'], 8):
        start, end = struct.unpack_from('<2I', data, at)
        if not 0x200 <= start <= end <= len(data):
            raise InvalidROM("Out-of-bounds FAT file")
        files.append((start, end))
    for name in ('arm9_overlays', 'arm7_overlays'):
        s = sections[name]
        if s['size'] % 32:
            raise InvalidROM("Malformed overlay table")
        for at in range(s['offset'], s['offset'] + s['size'], 32):
            file_id = struct.unpack_from('<I', data, at + 24)[0]
            if file_id >= len(files):
                raise InvalidROM("Overlay file ID outside FAT")
    return dict(title=data[:12].rstrip(b'\0').decode('ascii', errors='replace'),
                game_code=data[12:16].decode('ascii', errors='replace'),
                revision=data[0x1E], size=len(data), sha1=hashlib.sha1(data).hexdigest(),
                sha256=hashlib.sha256(data).hexdigest(), sections=sections, file_count=len(files))


def verify(data, profile):
    report = inspect(data)
    for key in ('game_code', 'revision', 'size', 'sha1'):
        if report[key] != profile[key]:
            raise InvalidROM(f"ROM {key} differs from verified USA profile")
    return report
