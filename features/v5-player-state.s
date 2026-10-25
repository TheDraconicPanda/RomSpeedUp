// Own compact equivalent of the verified player movement-state routine.
// Its original 220-byte slot also hosts the separately tested city initializer.
push {r3, r4, r5, r6, r7, lr}
movs r5, r0
ldr r6, [r5, #0x10]
ldr r4, [r5, #0x14]
ldr r7, [r5, #0x30]
movs r1, #0
str r1, [r5, #0x14]
mvns r1, r1
bl 0x0205d01c
cmp r0, #0
beq active
cmp r0, #2
bne two
active:
movs r0, r7
bl 0x02062108
cmp r0, #0
bne scripted
cmp r6, #2
beq two
cmp r6, #1
bne finish
movs r0, r7
bl 0x0205f4d4
bl 0x0205de64
cmp r0, #1
beq finish
cmp r4, #0
beq one
cmp r4, #3
bne two
one:
movs r0, #1
b store
two:
movs r0, #2
b store
scripted:
movs r0, r7
bl 0x02062198
cmp r0, #1
bne finish
subs r6, #1
cmp r6, #1
bhi finish
cmp r4, #0
beq finish
movs r0, #0
cmp r4, #3
beq store
movs r0, #3
store:
str r0, [r5, #0x14]
finish:
pop {r3, r4, r5, r6, r7, pc}
.balign 4
