// Called only from ordinary walk/run rendering. The original handler keeps
// the map object in r5 and passes sprite/speed in r0/r1.
push {r4, r5, r6, lr}
movs r4, r0
movs r6, r1
movs r0, r5
bl ELIGIBLE
cmp r0, #0
beq original
lsrs r0, r6, #1
adds r6, r6, r0
original:
movs r0, r4
movs r1, r6
bl 0x02023f04
pop {r4, r5, r6, pc}
.balign 4
