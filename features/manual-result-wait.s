// Own implementation, assembled for the verified European overlay-12 slot.
// r0: BattleSystem*, r1: BattleContext*. -1 frames selects a manual A/B wait.
// All ordinary timed waits retain their existing input and link behavior.
push {r3, r4, r5, r6, r7, lr}
movs r4, r0
movs r5, r1
movs r0, r1
movs r1, #1
bl 0x02245508
movs r0, r5
bl 0x022454e8
movs r6, r0
movs r7, r5
adds r7, #0xf0
adds r0, r6, #1
beq manual
ldr r0, [r4, #0x2c]
movs r1, #4
tst r0, r1
bne increment
ldr r0, system
ldr r1, [r0, #0x48]
ldr r0, input_mask
tst r0, r1
bne done
bl 0x02025358
cmp r0, #0
bne done
increment:
movs r2, #1
ldr r0, [r4, #0x2c]
movs r1, #4
tst r0, r1
beq compare
ldr r1, special_offset
ldr r0, [r4, r1]
movs r1, #0x10
tst r0, r1
bne compare
movs r2, #2
compare:
ldr r0, [r7]
cmp r6, r0
ble done
adds r0, r0, r2
str r0, [r7]
b rewind
manual:
ldr r0, [r7]
cmp r0, #0
beq arm
ldr r0, system
ldr r0, [r0, #0x48]
movs r1, #3
tst r0, r1
bne done
b rewind
arm:
str r6, [r7]
rewind:
movs r0, r5
movs r1, #1
mvns r1, r1
bl 0x02245508
b finish
done:
movs r0, #0
str r0, [r7]
finish:
ldr r1, continue_offset
ldr r0, [r5, r1]
movs r2, #1
orrs r0, r2
str r0, [r5, r1]
movs r0, #0
pop {r3, r4, r5, r6, r7, pc}
.balign 4
system: .word 0x021d110c
input_mask: .word 0x00000c03
special_offset: .word 0x240c
continue_offset: .word 0x3154
