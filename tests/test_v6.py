"""Regressions for retail VLQ lengths and relocated music control flow."""
import struct

import ndspy.soundSequence as seq
from romspeedup.v6 import parse_events, encode_events, graph, retime_sequence


def sseq(data):
    result = bytearray(seq.SSEQ.fromEvents([]).save()[0]) + data
    struct.pack_into('<I',result,8,len(result))
    struct.pack_into('<I',result,0x14,len(result)-16)
    return bytes(result)


def test_overlong_vlq_does_not_create_phantom_notes():
    # Rest 48 is encoded in three bytes; the following note begins at offset3.
    events = parse_events(bytes.fromhex('8080303c7f803f ff'))
    assert [type(e) for e in events] == [seq.RestSequenceEvent,seq.NoteSequenceEvent,seq.EndTrackSequenceEvent]
    assert [events[0].duration,events[1].duration] == [48,63]


def test_retime_relocates_call_and_jump_after_vlq_growth():
    # Call note at offset11; rest48 uses a retail overlong VLQ; jump0 loops.
    raw = sseq(bytes.fromhex('950b000080803094000000 3c7f30fd'))
    result,counts = retime_sequence(raw)
    events = parse_events(result[28:])
    assert graph(events)==graph(parse_events(encode_events(events)))
    assert events[0].destination is events[3]
    assert events[2].destination is events[0]
    assert events[1].duration==144 and events[3].duration==144
    assert counts['NoteSequenceEvent']==1


def test_variable_instrument_preserves_following_command():
    result,_ = retime_sequence(sseq(bytes.fromhex('a18100c17f3c7f30ff')))
    events = parse_events(result[28:])
    assert events[0].variableID==0
    assert events[1].value==127
    assert events[2].duration==144


def test_modulation_delay_is_a_16_bit_value():
    result,_ = retime_sequence(sseq(bytes.fromhex('e0a000cb103c7f30ff')))
    events = parse_events(result[28:])
    assert events[0].value==480 and events[0].dataLength==3
    assert events[1].value==5
    assert events[2].duration==144
