// r0 object -> 1 player, 2 active ordinary follower, 0 otherwise.
// Both require on-foot city play with normal control enabled.
push {r4, r5, r6, lr}
movs r4, r0
bl 0x0205f52c
movs r5, r0
ldr r1, [r5, #0x40]
cmp r1, #0
beq no
ldr r2, [r1, #0x18]
cmp r2, #0
bne no
movs r6, #1
ldr r2, [r1, #0x30]
cmp r2, r4
beq city
movs r0, r5
adds r0, #0xe4
ldr r0, [r0]
cmp r0, r4
bne no
movs r0, r5
adds r0, #0xfa
ldrb r0, [r0]
cmp r0, #1
bne no
ldr r0, [r4, #0x14]
cmp r0, #48
bne no
ldr r0, [r4]
lsls r0, r0, #1
bmi no
ldr r0, [r4]
movs r2, #64
tst r0, r2
bne no
movs r6, #2
city:
movs r0, r5
bl 0x0203e13c
cmp r0, #0
beq no
ldr r0, [r5, #0x20]
ldr r0, [r0]
bl 0x0203b4dc
cmp r0, #1
bne no
movs r0, r6
pop {r4, r5, r6, pc}
no:
movs r0, #0
pop {r4, r5, r6, pc}
.balign 4
