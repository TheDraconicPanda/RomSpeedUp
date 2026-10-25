// Replaces GetWindow's r1=0 and r6=delay setup, marking selected local results.
movs r6, r3
ldr r2, [r0, #0x0c]
cmp r1, r2
bne finish
ldr r2, [r0, #0x2c]
movs r3, #4
tst r2, r3
bne finish
ldrh r3, [r4, #2]
cmp r3, #27
bhi large
ldr r2, small_ids
lsrs r2, r2, r3
lsls r2, r2, #31
bmi selected
finish:
movs r1, #0
bx lr
large:
ldr r2, immunity342
cmp r3, r2
beq selected
ldr r2, immunity1036
cmp r3, r2
bne finish
selected:
movs r6, #0x41
b finish
.balign 4
small_ids: .word 0x09241000
immunity342: .word 342
immunity1036: .word 1036
