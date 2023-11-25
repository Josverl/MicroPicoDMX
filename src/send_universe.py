# Create a universe that we want to send.
# The universe must be maximum 512 bytes + 1 byte of start code
UNIVERSE_LENGTH = 512

import time

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio

# -----------------------------------------------
# add type hints for the rp2.PIO Instructions
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from rp2.asm_pio import *
# -----------------------------------------------

# -----------------------------------------------
# Wiring scema for the DMX TX
pin_dmx_tx = Pin(15, Pin.OUT)
pin_dmx_rx = Pin(14, Pin.IN)



# NOTE: In DMX the slots are identified by their position in the frame, the sender does not need to send the channel number at all.




@asm_pio(
    set_init=PIO.OUT_LOW,
    sideset_init=PIO.OUT_LOW,
    out_init=PIO.OUT_LOW,
    # autopull=True,  # ?
    out_shiftdir=PIO.SHIFT_RIGHT,  # ?
    push_thresh=8,
)
# fmt: off
def dmx_send():
    """
    - valid values for each of the data channels is:  0-255
    Minimum universe length is 10 channels / slots

    The pio Statemachine must be reset before sending a new universe of data,
    this will send the BREAK and the MAB signals
    the universe is an bytearray of a 1 + 512 bytes
    The first byte is the START_CODE , the next 512 bytes are the data channels
    - the START_CODE is 0x00 for DMX Data Packets
    - the START_CODE is 0xCC for RDM Data Packets
    - the START_CODE is 0xFE for RDM Discovery Data Packets

    Usage example:

    ```
    sm_dmx_tx = StateMachine(
        1,
        dmx_send,
        freq=1_000_000,
        set_base=pin_dmx_tx,
        out_base=pin_dmx_tx,
        sideset_base=pin_dmx_tx,
    )
    sm_dmx_tx.active(1)
    ```	

    """
    # Assert break condition
    # Sender DMX break signal is 92us >, so we need to loop at least 92 / 8 = 12 times
    # TODO: Actually should be at least 92us
    set(x, 21)      .side(0)                # BREAK condition for 176us

    label("breakloop")                      # Loop X times, each loop iteration is 8 cycles.
    jmp(x_dec, "breakloop")             [7] # Each loop iteration is 8 cycles.

    nop()                    .side(1)   [7] # Assert MAB. 8 cycles nop and 8 cycles stop-bits = 16us

    # Send data frame
    wrap_target()
    
    pull()                   .side(1)   [7] # 2 STOP bits,  1 + 7 clocks,   or stall with line in idle state (extending MAB) 
    set(x, 7)                .side(0)   [3] # 1 START BIT  1 + 4 clocks load bit counter, assert start bit for 4 clocks

    label("bitloop")
    out(pins, 1)                        [2]  # Shift 1 bit from OSR to the first OUT pin
    jmp(x_dec, "bitloop")                    # Each loop iteration is 4 cycles.

    wrap()
# fmt: on

@asm_pio(set_init=0, sideset_init=0)
def dmx_receive():
    """PIO program to receive a DMX Universe frame of 512 channels.	

    """
    # Constants
    dmx_bit = 4  # As DMX has a baudrate of 250.000kBaud, a single bit is 4us

    # Break loop 
    # Receiver DMX break signal is 88us, so we need to loop 22 times to get 88us
    label("break_reset")
    set(x, 29)
    label("break_loop")
    jmp(pin, "break_reset")                 # Go back to start if pin goes high during the break
    jmp(x_dec, "break_loop")            [1] # Decrease the counter and go back to break loop if x>0 so that the break is not done
    wait(1, pin, 0)                         # Stall until line goes high for the Mark-After-Break (MAB)

    # Data loop
    label("wrap_target")
    wait(0, pin, 0)                         # Stall until start bit is asserted
    set(x, 7)                     [dmx_bit] # Preload bit counter, then delay until halfway through

    label("bitloop")
    in_(pins, 1)                            # Shift data bit into ISR
    jmp(x_dec, "bitloop")       [dmx_bit-2] # Loop 8 times, each loop iteration is 4us

    # Stop bits
    wait(1, pin, 0)                         # Wait for pin to go high for stop bits

    in_(null, 24)                           # Push 24 more bits into the ISR so that our one byte is at the position where the DMA expects it
    # 
    push() # Should probably do error checking on the stop bits some time in the future....


# sm1.active(1)


class DMX:
    def __init__(self, dmx_tx: Pin):
        self.universe = bytearray(UNIVERSE_LENGTH + 1)
        machine_nr = 0

        self.sm = StateMachine(
            machine_nr,
            dmx_send,
            freq=1_000_000,
            out_base=dmx_tx,
            set_base=dmx_tx,
            sideset_base=dmx_tx
        )
        self.sm.active(1)

    def set_channel(self, channel: int, value: int):
        self.universe[channel] = value


    def get_channel(self, channel: int):
        return self.universe[channel]

    def blackout(self):
        for i in range(UNIVERSE_LENGTH):
            self.universe[i] = 0

    def swoop(self):
        for i in range(UNIVERSE_LENGTH):
            self.universe[i] = i % 256

    def send(self):
        self.sm.put(self.universe)


dmx = DMX(pin_dmx_tx)
dmx.swoop()

while 1:
    dmx.send()
    print("waiting")
    time.sleep(0.1)
