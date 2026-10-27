// Clamp initialized player/follower city steps even after eligibility changes.
push {r3, r4, r5, r6, r7, lr}
movs r4, r0
movs r5, r1
movs r6, r2
movs r3, r0
adds r3, #0xfa
ldrh r3, [r3]
cmp r3, #1
bne original
movs r3, r0
adds r3, #0xa4
ldr r3, [r3]
subs r3, #12
cmp r3, #7
bls check
subs r3, #76
cmp r3, #3
bhi original
check:
lsrs r7, r6, #12
cmp r7, #3
beq clamp
cmp r7, #6
bne original
clamp:
movs r6, #1
cmp r7, #3
beq walk
lsls r6, r6, #2
walk:
lsls r6, r6, #12
original:
movs r0, r4
movs r1, r5
movs r2, r6
bl 0x0206101c
pop {r3, r4, r5, r6, r7, pc}
.balign 4
