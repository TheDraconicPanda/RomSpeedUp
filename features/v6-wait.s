// Three physical VBlanks per game update, including any already elapsed.
push {r3, lr}
again:
ldr r0, system_ptr
ldr r0, [r0, #0x30]
cmp r0, #3
bhs done
movs r0, #1
movs r1, r0
ldr r3, wait_ptr
blx r3
b again
done:
pop {r3, pc}
.balign 4
system_ptr: .word 0x021d110c
wait_ptr: .word 0x020d0e6c
