// Walk: either selected object. Fast walk (animation 4): follower only.
// Player run (animation 9): player only. Other families use original init.
push {r3, r4, r5, r6, r7, lr}
movs r4, r0
movs r5, r1
movs r6, r2
movs r7, r3
bl ELIGIBLE
cmp r0, #0
beq original
ldr r1, [sp, #24]
cmp r1, #4
beq follower_run
cmp r1, #9
bne scale
cmp r0, #1
bne original
b scale
follower_run:
cmp r0, #2
bne original
scale:
lsrs r0, r6, #1
adds r6, r6, r0
lsrs r0, r7, #2
subs r7, r7, r0
original:
ldr r0, [sp, #24]
str r0, [sp]
movs r0, r4
movs r1, r5
movs r2, r6
movs r3, r7
bl 0x020624cc
pop {r3, r4, r5, r6, r7, pc}
.balign 4
