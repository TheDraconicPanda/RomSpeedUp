// Existing follower renderers keep the object in r5. Accelerate only ordinary
// moving follower poses (3/4); idle, interaction and special poses pass through.
push {r4, r5, r6, lr}
movs r4, r0
movs r6, r1
movs r0, r5
bl ELIGIBLE
cmp r0, #2
bne original
movs r0, r5
adds r0, #0xa0
ldr r0, [r0]
subs r0, #3
cmp r0, #1
bhi original
lsrs r0, r6, #1
adds r6, r6, r0
original:
movs r0, r4
movs r1, r6
bl 0x02023f04
pop {r4, r5, r6, pc}
.balign 4
