"""V6.3: immediate ordinary dialogue pages, preserving callback-driven text."""
import struct
import ndspy.code
import ndspy.codeCompression
import ndspy.rom

from .v62 import build as build_v62
from .v61 import BASE
from .v6_native import compile_code
from .overlay_patch import digest
from .rom import crc16, inspect

RENDER = 0x020626F4  # Unreferenced former V6.1 sprite gate, exactly 40 bytes.
PRINT_CALL = 0x02020312


def build(source):
    base, report = build_v62(source)
    if digest(base) != 'b5416f371ae5c8ec53bb5814be59d7e34a186975fdfe7c8d09e377f25e29eba5':
        raise ValueError('V6.3 requires the verified V6.2 baseline')
    prior = ndspy.rom.NintendoDSRom(base)
    before = bytes(ndspy.codeCompression.decompress(prior.arm9))
    arm = bytearray(before)
    # Called only from RunTextPrinter, whose saved r4 is the printer. A task
    # with a callback retains stock pacing and callback visits. All ordinary
    # asynchronous battle messages use ov12_0223CF14; synchronous battle labels
    # call RenderFont directly and never enter this helper.
    # Callback-free dialogue drains PRINT results until a control/wait or EOS.
    # Clearing only the base glyph delay leaves explicit delayCounter waits,
    # page/scroll states, manual advancement and task lifetime intact.
    helper = compile_code('''push {r4,r5,r6,lr}
ldr r5,[r4,#0x1c]
cmp r5,#0
bne loop
movs r6,#0x29
movs r0,#0x80
strb r0,[r4,r6]
loop:
movs r0,r4
bl 0x02020358
cmp r5,#0
bne done
cmp r0,#0
beq loop
movs r5,r0
ldr r0,[r4,#4]
bl 0x0201d578
movs r0,r5
done:
pop {r4,r5,r6,pc}
''', RENDER)
    if len(helper) != 40 or struct.pack('<I', RENDER|1) in before:
        raise ValueError('Unexpected or still-referenced text helper allocation')
    arm[RENDER-BASE:RENDER-BASE+40] = helper
    branch = lambda at, target: compile_code(f'bl {target}', at)
    at = PRINT_CALL-BASE
    if arm[at:at+4] != branch(PRINT_CALL, 0x02020358):
        raise ValueError('Unexpected asynchronous printer call')
    arm[at:at+4] = branch(PRINT_CALL, RENDER)
    settings = ndspy.code.MainCodeFile(prior.arm9, BASE).codeSettingsOffs
    packed = bytearray(ndspy.codeCompression.compress(arm, True))
    struct.pack_into('<I', packed, settings+20, BASE+len(packed))
    struct.pack_into('<I', arm, settings+20, BASE+len(packed))
    if ndspy.codeCompression.decompress(packed) != arm:
        raise ValueError('ARM9 compression roundtrip failed')
    result = bytearray(base)
    start = struct.unpack_from('<I', base, 0x20)[0]
    if start+len(packed)+len(prior.arm9PostData) > struct.unpack_from('<I', base, 0x50)[0]:
        raise ValueError('ARM9 slot overflow')
    result[start:start+len(packed)+len(prior.arm9PostData)] = packed+prior.arm9PostData
    struct.pack_into('<I', result, 0x2C, len(packed))
    struct.pack_into('<H', result, 0x15E, crc16(result[:0x15E]))
    target = bytes(result)
    inspect(target)
    check = ndspy.rom.NintendoDSRom(target)
    if ndspy.codeCompression.decompress(check.arm9) != arm:
        raise ValueError('Executable readback failed')
    edits = [(RENDER-BASE,40),(PRINT_CALL-BASE,4),(settings+20,4)]
    allowed = {i for at, n in edits for i in range(at, at+n)}
    if len(arm) != len(before) or any(i not in allowed for i, (a,b) in enumerate(zip(before,arm)) if a!=b):
        raise ValueError('Unexpected V6.2 executable edit')
    for attr in ('arm7','arm9PostData','arm9OverlayTable','arm7OverlayTable','iconBanner'):
        if getattr(check,attr) != getattr(prior,attr):
            raise ValueError(f'Protected asset changed: {attr}')
    if len(target)!=len(base) or check.files!=prior.files:
        raise ValueError('Cartridge size or protected NitroFS payload changed')
    layout = lambda r: [(s.ramAddress,len(s.data),s.bssSize,s.implicit)
        for s in ndspy.code.MainCodeFile(r.arm9,BASE).sections]
    if layout(check)!=layout(prior):
        raise ValueError('Executable layout changed')
    report.update(version='v6.3',target_sha256=digest(target),packed=len(packed),
        instant_text_render=RENDER,instant_text_print_call=PRINT_CALL,
        field_text='callback-free asynchronous pages fill immediately; control/input waits retained',
        battle_text='callback-driven battle messages and all battle overlays retained from V6.2')
    return target,report
