# type: ignore
"""WS2812 driver for Raspberry Pi Pico (RP2040) microcontroller using PIO state machine."""
import rp2


@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=8)
def DmxInputInverted():
    .define dmx_bit 4                     ; As DMX has a baudrate of 250.000kBaud, a single bit is 4us

    break_reset:
        set x, 29                         ; Setup a counter to count the iterations on break_loop
    break_in_progress:
        jmp pin break_continue
        jmp break_reset                   ; break should be high the entire time. if it goes low, start over
    break_continue:
        jmp x-- break_in_progress
        wait 0 pin 0                      ; wait until MAB started

    .wrap_target
        wait 1 pin 0                      ; Stall until start bit is asserted, i.e. MAB is over
        set x, 7             [dmx_bit]    ; Preload bit counter, then delay until halfway through

    bitloop:
        in pins, 1                        ; Shift data bit into ISR
        jmp x-- bitloop      [dmx_bit-2]  ; Loop 8 times, each loop iteration is 4us
        wait 0 pin 0                      ; Wait for pin to go high for stop bits
        mov isr, ~ isr                    ; invert result before pushing
        in NULL, 24                       ; Push 24 more bits into the ISR so that our one byte is at the position where the DMA expects it
        push                              ; Should probably do error checking on the stop bits some time in the future....

    .wrap

