// r0 object -> bool. Shared by motion and sprite clocks; preserves r4-r7.
push {r4, lr}
movs r4, r0
bl 0x0205f52c
ldr r1, [r0, #0x40]
cmp r1, #0
beq no
ldr r2, [r1, #0x30]
cmp r2, r4
bne no
ldr r1, [r1, #0x18]
cmp r1, #0
bne no
movs r4, r0
bl 0x0203e13c
cmp r0, #0
beq no
ldr r0, [r4, #0x20]
ldr r0, [r0]
bl 0x0203b4dc
cmp r0, #1
bne no
movs r0, #1
pop {r4, pc}
no:
movs r0, #0
pop {r4, pc}
.balign 4
