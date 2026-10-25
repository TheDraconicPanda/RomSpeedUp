// Equivalent timed/input wait prefix, tail-sharing the verified original WaitTime.
// Stack layout matches WaitTime's push {r3,r4,r5,lr}; r3 is caller-clobbered.
push {r3, r4, r5, lr}
movs r4, r0
movs r5, r1
movs r0, r1
movs r1, #1
bl 0x02245508
movs r0, r5
bl 0x022454e8
str r0, [sp]
ldr r0, [r4, #0x2c]
movs r1, #4
tst r0, r1
bne tail
ldr r0, system
ldr r1, [r0, #0x48]
ldr r0, input_mask
tst r0, r1
bne pressed
bl 0x02025358
cmp r0, #0
beq tail
pressed:
ldr r1, [sp]
movs r0, r5
adds r0, #0xf0
str r1, [r0]
tail:
ldr r0, [sp]
ldr r3, wait_body
bx r3
.balign 4
system: .word 0x021d110c
input_mask: .word 0x00000c03
wait_body: .word 0x02245339
