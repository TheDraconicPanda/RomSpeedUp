// Called only by ordinary walk/run initializers; retains each gait animation.
// Other objects, routes/interiors, nonwalking states and scripted control bypass.
push {r3, r4, r5, r6, r7, lr}
movs r4, r0
movs r5, r1
movs r6, r2
movs r7, r3
bl 0x0205f52c
ldr r1, [r0, #0x40]
cmp r1, #0
beq original
ldr r2, [r1, #0x30]
cmp r2, r4
bne original
ldr r1, [r1, #0x18]
cmp r1, #0
bne original
str r0, [sp]
bl 0x0203e13c
cmp r0, #0
beq original
ldr r0, [sp]
ldr r0, [r0, #0x20]
ldr r0, [r0]
bl 0x0203b4dc
cmp r0, #1
bne original
lsls r6, r6, #1
lsrs r7, r7, #1
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
