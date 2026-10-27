"""Original Europe ROM calibrated for Delta's fixed 3x fast forward.

No ROM bytes are embedded. All unselected NitroFS files and sound payloads are
verified against the caller's exact original. This is an experimental build.
"""
import struct
from collections import Counter

import ndspy.code
import ndspy.codeCompression
import ndspy.rom
import ndspy.soundArchive
import ndspy.soundSequence as seq

from .overlay_patch import digest
from .rom import inspect, crc16
from .v5 import BASE, assemble
from .v51 import compile_code

SOURCE = '94ad298c32bbcc623d042ca20f46cfcaa399a8e814260cc5645dfe5f4c167c17'
ARM_SHA = '534df6737a9a852bf24c9e63e93453897d9018a17e0685346fd37050123305a5'
SOUND_FILE = 479
STATE = 0x0205ce68
WAIT_CALL = 0x02000e1e


class ModulationDelay(seq.SequenceEvent):
    # E0 has a 16-bit argument, unlike the byte-sized CB modulation rate.
    dataLength = 3
    def __init__(self,value):
        super().__init__(0xe0); self.value = value
    def save(self,eventsToOffsets=None):
        return b'\xe0'+struct.pack('<H',self.value)


def parse_events(data):
    """Traverse original byte offsets, including noncanonical retail VLQs.

    ndspy's graph reader advances by the *canonical* size of parsed integers;
    retail's overlong VLQs therefore need an explicit consumed-byte reader.
    """
    def vlq(at):
        value = 0; start = at
        while True:
            b = data[at]; at += 1; value = (value<<7)|(b&127)
            if not b&128: return value, at-start
            if at-start>4: raise ValueError('Unbounded sequence VLQ')
    def decode(at):
        op = data[at]; target = None
        if op<=0x7f:
            value,size = vlq(at+2)
            e = seq.NoteSequenceEvent.fromData(op,data,at)
            return e,2+size,target
        if op in (0x80,0x81):
            value,size = vlq(at+1)
            return seq._EVENT_TYPES[op].fromData(op,data,at),1+size,target
        if op in (0x93,0x94,0x95):
            p = at+(2 if op==0x93 else 1)
            target = int.from_bytes(data[p:p+3],'little')
            e = (seq.BeginTrackSequenceEvent(data[at+1],None) if op==0x93
                 else seq._EVENT_TYPES[op](None))
        elif op==0xe0:
            e = ModulationDelay(struct.unpack_from('<H',data,at+1)[0])
        elif op==0xa1:
            sub = data[at+1]
            if sub!=0x81: raise ValueError('Unmapped variable sequence opcode')
            e = seq.FromVariableSequenceEvent(sub,data[at+2])
        else:
            e = seq._EVENT_TYPES[op].fromData(op,data,at)
        return e,e.dataLength,target
    found = {}; spans = {}; links = {}; pending = [0]
    while pending:
        at = pending.pop()
        if at in found: continue
        if not 0<=at<len(data): raise ValueError('Sequence graph points outside file')
        e,size,target = decode(at)
        if at+size>len(data): raise ValueError('Truncated sequence command')
        found[at] = e; spans[at] = size
        if target is not None: links[at] = target; pending.append(target)
        if e.type not in (0x94,0xfd,0xff): pending.append(at+size)
        if e.type==0xa2:
            _,skip,_ = decode(at+size)
            pending.append(at+size+skip)
    for at,target in links.items():
        if found[at].type==0x93: found[at].firstEvent = found[target]
        else: found[at].destination = found[target]
    events = []; cursor = 0
    for at,e in sorted(found.items()):
        if at<cursor: raise ValueError('Overlapping sequence commands')
        if at>cursor: events.append(seq.RawDataSequenceEvent(data[cursor:at]))
        events.append(e); cursor = at+spans[at]
    if cursor<len(data): events.append(seq.RawDataSequenceEvent(data[cursor:]))
    return events


def encode_events(events):
    """Keep ndspy's relocated branches; guard its known A1 length mismatch."""
    offsets = {}; size = 0
    for e in events:
        offsets[e] = size
        size += e.dataLength
    result = bytearray()
    for e in events:
        data = e.save(offsets)
        if isinstance(e, seq.FromVariableSequenceEvent):
            # These three original tracks use A1 81 00. ndspy reads one byte
            # beyond the instruction and emits four bytes for a three-byte op.
            if e.subType != 0x81 or e.dataLength != 3 or len(data) != 4:
                raise ValueError('Unmapped variable sequence command')
            data = data[:3]
        if len(data) != e.dataLength:
            raise ValueError('Sequence instruction length mismatch')
        result += data
    assert len(result) == size
    return bytes(result)


def graph(events):
    indexes = {e: i for i, e in enumerate(events)}
    def norm(value):
        if isinstance(value, seq.SequenceEvent): return ('event', indexes[value])
        if isinstance(value, (list, tuple)): return tuple(map(norm, value))
        if isinstance(value, dict): return tuple((k, norm(v)) for k,v in sorted(value.items()))
        return value
    return [(type(e).__name__, norm(vars(e))) for e in events]


def retime_sequence(raw):
    if struct.unpack_from('<I', raw, 0x18)[0] != 0x1c:
        raise ValueError('Unexpected sequence header')
    # Retail sometimes uses overlong VLQs (80 30 instead of 30). Verify the
    # complete event graph rather than requiring a canonical byte spelling.
    events = parse_events(raw[0x1c:])
    original_graph = graph(events)
    roundtrip = parse_events(encode_events(events))
    if graph(roundtrip) != original_graph:
        raise ValueError('Sequence serialization changed original semantics')
    counts = Counter()
    for event in events:
        if isinstance(event, (seq.NoteSequenceEvent, seq.RestSequenceEvent)):
            event.duration *= 3
            counts[type(event).__name__] += 1
        # Nintendo's modulation clock advances independently of score ticks.
        elif isinstance(event, seq.VibratoSpeedSequenceEvent):
            event.value = max(1, round(event.value / 3)) if event.value else 0
            counts['vibrato_speed'] += 1
        elif isinstance(event, ModulationDelay):
            event.value *= 3
            counts['vibrato_delay'] += 1
    expected = graph(events)
    data = encode_events(events)
    result = bytearray(raw[:0x1c]) + data
    struct.pack_into('<I', result, 8, len(result))
    struct.pack_into('<I', result, 0x14, len(result)-0x10)
    if graph(parse_events(data)) != expected:
        raise ValueError('Retimed sequence graph/branch validation failed')
    return bytes(result), counts


def retime_archive(raw):
    archive = ndspy.soundArchive.SDAT(raw)
    sym, symlen, info, infolen, fat, fatlen, file, filelen = struct.unpack_from('<8I',raw,0x10)
    if raw[fat:fat+4] != b'FAT ' or raw[file:file+4] != b'FILE':
        raise ValueError('Unexpected archive blocks')
    count = struct.unpack_from('<I',raw,fat+8)[0]
    entries = [struct.unpack_from('<II',raw,fat+12+i*16) for i in range(count)]
    selected = {}; selected_rows = {}; unselected = set()
    for row,(name, sound) in enumerate(archive.sequences):
        if sound is None: continue
        fid = sound.dataMergeOptimizationID
        if sound.playerID in (1,2,7):
            selected.setdefault(fid,[]).append(name)
            selected_rows.setdefault(fid,[]).append(row)
        else: unselected.add(fid)
    payloads = [bytes(raw[start:start+size]) for start,size in entries]
    stats = Counter(); changed = []; clones = {}
    for fid, names in sorted(selected.items()):
        original = payloads[fid]
        payload, counts = retime_sequence(original)
        if payload != original:
            destination = fid
            if fid in unselected:
                destination = len(payloads)
                clones[fid] = destination
                payloads.append(payload)
            else: payloads[fid] = payload
            changed.append(dict(file_id=destination,names=names,old_bytes=len(original),new_bytes=len(payload)))
        stats.update(counts)
    first = min(a for a,b in entries)
    extra = 16*len(clones)
    result = bytearray(raw[:fat+fatlen])+bytearray(extra)+bytearray(raw[fat+fatlen:first])
    file += extra
    struct.pack_into('<I',result,0x24,fatlen+extra)
    struct.pack_into('<I',result,0x28,file)
    struct.pack_into('<II',result,fat+4,fatlen+extra,len(payloads))
    struct.pack_into('<I',result,file+8,len(payloads))
    expected_info = bytearray(raw[info:info+infolen])
    table = struct.unpack_from('<I',raw,info+8)[0]
    for fid,newfid in clones.items():
        for row in selected_rows[fid]:
            off = struct.unpack_from('<I',raw,info+table+4+row*4)[0]
            if struct.unpack_from('<H',raw,info+off)[0]!=fid:
                raise ValueError('Music alias metadata mismatch')
            struct.pack_into('<H',result,info+off,newfid)
            struct.pack_into('<H',expected_info,off,newfid)
    result += bytes((-len(result)) % 128)
    for i, payload in enumerate(payloads):
        result += bytes((-len(result)) % 32)
        start = len(result); result += payload
        struct.pack_into('<II',result,fat+12+i*16,start,len(payload))
    result += bytes((-len(result)) % 32)
    struct.pack_into('<I',result,8,len(result))
    struct.pack_into('<I',result,0x2c,len(result)-file)
    struct.pack_into('<I',result,file+4,len(result)-file)
    if result[sym:sym+symlen] != raw[sym:sym+symlen] or result[info:info+infolen] != expected_info:
        raise ValueError('Sound names/metadata changed')
    # Check each internal file through the rebuilt table, including bank/waves.
    for i,payload in enumerate(payloads):
        at,size = struct.unpack_from('<II',result,fat+12+i*16)
        if bytes(result[at:at+size]) != payload:
            raise ValueError('Sound payload readback failed')
    verified = ndspy.soundArchive.SDAT(result)
    if len(verified.sequences) != len(archive.sequences):
        raise ValueError('Sound archive sequence count changed')
    return bytes(result), dict(changed_music_files=changed,event_counts=dict(stats),
                              protected_internal_files=count-len(changed)+len(clones),
                              music_only_clones=clones)


def build(source):
    if digest(source) != SOURCE: raise ValueError('V6 requires the exact user-supplied original Europe ROM')
    sections = inspect(source)['sections']
    rom = ndspy.rom.NintendoDSRom(source)
    old_arm = bytes(ndspy.codeCompression.decompress(rom.arm9))
    if digest(old_arm) != ARM_SHA: raise ValueError('Original executable mismatch')
    arm = bytearray(old_arm)
    state = assemble('v5-player-state',STATE)
    helper_at = STATE+len(state)
    helper = assemble('v6-wait',helper_at)
    code = state+helper
    if len(code)>220 or len(code)%2: raise ValueError('Helper exceeds original allocation')
    arm[STATE-BASE:STATE-BASE+220] = code+bytes.fromhex('c046')*((220-len(code))//2)
    branch = lambda at,to: compile_code(f'bl {to}',at)
    if old_arm[WAIT_CALL-BASE:WAIT_CALL-BASE+4] != compile_code('blx 0x020d0e6c',WAIT_CALL):
        raise ValueError('Main wait call guard failed')
    arm[WAIT_CALL-BASE:WAIT_CALL-BASE+4] = branch(WAIT_CALL,helper_at)
    settings = ndspy.code.MainCodeFile(rom.arm9,BASE).codeSettingsOffs
    if settings != 0xba0: raise ValueError('Original module settings mismatch')
    packed = bytearray(ndspy.codeCompression.compress(arm,True))
    struct.pack_into('<I',packed,settings+20,BASE+len(packed))
    struct.pack_into('<I',arm,settings+20,BASE+len(packed))
    if bytes(ndspy.codeCompression.decompress(packed)) != arm:
        raise ValueError('Executable compression roundtrip failed')
    allowed = set(range(STATE-BASE,STATE-BASE+220)) | set(range(WAIT_CALL-BASE,WAIT_CALL-BASE+4)) | set(range(settings+20,settings+24))
    if any(i not in allowed for i,(a,b) in enumerate(zip(old_arm,arm)) if a!=b):
        raise ValueError('Unselected executable edit')
    sound, music_report = retime_archive(rom.files[SOUND_FILE])
    fat,fatsize = struct.unpack_from('<II',source,0x48)
    entries = [struct.unpack_from('<II',source,fat+i*8) for i in range(fatsize//8)]
    start,end = entries[SOUND_FILE]
    if any(a<end and b>start for i,(a,b) in enumerate(entries) if i!=SOUND_FILE):
        raise ValueError('Overlapping sound file allocation')
    delta = (max(0,len(sound)-(end-start))+511)//512*512
    used = struct.unpack_from('<I',source,0x80)[0]
    if max(b for a,b in entries)>used or used+delta>len(source):
        raise ValueError('Insufficient cartridge free space')
    if any(v not in (0,255) for v in source[used:]):
        raise ValueError('Trailing cartridge data is occupied')
    for section in sections.values():
        if section['size'] and section['offset']>=end:
            raise ValueError('Unmapped header section relocation')
    result = bytearray(source[:end])+bytearray(delta)+bytearray(source[end:len(source)-delta] if delta else source[end:])
    result[start:start+len(sound)] = sound
    for i,(a,b) in enumerate(entries):
        if i==SOUND_FILE: b=start+len(sound)
        elif a>=end: a+=delta; b+=delta
        struct.pack_into('<II',result,fat+i*8,a,b)
    struct.pack_into('<I',result,0x80,used+delta)
    arm_at = sections['arm9']['offset']
    limit = min([a for a,b in entries if a>arm_at]+[s['offset'] for s in sections.values() if s['size'] and s['offset']>arm_at])
    post = bytes(rom.arm9PostData)
    if len(post)!=12 or arm_at+len(packed)+len(post)>limit:
        raise ValueError('Executable slot overflow')
    result[arm_at:arm_at+len(packed)+len(post)] = packed+post
    struct.pack_into('<I',result,0x2c,len(packed))
    struct.pack_into('<H',result,0x15e,crc16(result[:0x15e]))
    target = bytes(result); inspect(target)
    check = ndspy.rom.NintendoDSRom(target)
    if len(target)!=len(source) or bytes(ndspy.codeCompression.decompress(check.arm9))!=arm or check.arm9PostData!=post:
        raise ValueError('Cartridge executable readback failed')
    for attr in ('arm7','arm9OverlayTable','arm7OverlayTable','iconBanner'):
        if getattr(check,attr)!=getattr(rom,attr): raise ValueError('Protected cartridge metadata changed')
    for i,(a,b) in enumerate(zip(rom.files,check.files)):
        if b != (sound if i==SOUND_FILE else a): raise ValueError(f'Unselected NitroFS file changed: {i}')
    if len(check.files)!=len(rom.files): raise ValueError('NitroFS file count changed')
    oldmain,newmain = (ndspy.code.MainCodeFile(r.arm9,BASE) for r in (rom,check))
    layout = lambda m:[(s.ramAddress,len(s.data),s.bssSize,s.implicit) for s in m.sections]
    if layout(oldmain)!=layout(newmain): raise ValueError('Executable memory layout changed')
    return target, dict(version='v6',status='experimental',release_ready=False,
        source_sha256=digest(source),target_sha256=digest(target),rom_bytes=len(target),
        requires_delta_fast_forward=3,native_gameplay_ratio=2/3,native_music_ratio=1/3,
        nominal_effective_gameplay_ratio=2,nominal_effective_music_ratio=1,
        helper_address=helper_at,helper_bytes=len(helper),state_bytes=len(state),
        sound_bytes=len(sound),relocation_bytes=delta,music=music_report,
        limitations=['Delta hardware validation pending',
          'Music envelopes/portamento and effects are not globally time-stretched by the ROM',
          'Heavy scenes may miss the nominal update cadence; hardware-time clocks retain their behavior'])
