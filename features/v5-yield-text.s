// First entry restores r4 after the V3 callback path. Second entry checks NULL.
subs r4, #0x2d
b check
null_callback:
cmp r2, #0
bne return_to_callback
check:
movs r0, r4
adds r0, #0x29
ldrb r0, [r0]
cmp r0, #0xc0
beq yield
ldr r0, resume
bx r0
yield:
pop {r4, pc}
return_to_callback:
bx lr
.balign 4
resume: .word 0x020202f1
