import array
import rp2
from machine import Pin

from dmx_pio import DmxInputInverted

@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=8)
def DmxOutput():
    .side_set 1 opt

    ; Assert break condition
        set x, 21   side 0     ; Preload bit counter, assert break condition for 176us 
    breakloop:                 ; This loop will run 22 times
        jmp x-- breakloop [7]  ; Each loop iteration is 8 cycles.


    ; Assert start condition
        nop [7]    side 1      ; Assert MAB. 8 cycles nop and 8 cycles stop-bits = 16us


    ; Send data frame
    .wrap_target
        pull       side 1 [7]  ; Assert 2 stop bits, or stall with line in idle state
        set x, 7   side 0 [3]  ; Preload bit counter, assert start bit for 4 clocks
    bitloop:                   ; This loop will run 8 times (8n1 UART)
        out pins, 1            ; Shift 1 bit from OSR to the first OUT pin
        jmp x-- bitloop   [2]  ; Each loop iteration is 4 cycles.
    .wrap    


class DMXSender:
    def __init__(self, pin: Pin=Pin(1)):
        self.pin = pin
        self.sm = rp2.StateMachine(0, DmxOutput, freq=1_000_000, sideset_base=pin)
        self.sm.active(1)

    def send(self, data: array.array):
        self.sm.active(0)
        self.sm.restart()

        # // Start the DMX PIO program from the beginning
        # pio_sm_exec(_pio, _sm, pio_encode_jmp(_prgm_offset));

        self.sm.put(data)


# Create a universe that we want to send.
# The universe must be maximum 512 bytes + 1 byte of start code
UNIVERSE_LENGTH = 512
universe = array.array("I", [0 for _ in range(UNIVERSE_LENGTH + 1)])





# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)


