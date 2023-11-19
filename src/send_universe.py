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
pin_dmx_rx = Pin(12, Pin.IN)

# -----------------------------------------------


@asm_pio(set_init=PIO.OUT_LOW, sideset_init=PIO.OUT_LOW, out_init=PIO.OUT_LOW)
# fmt: off
def dmx_send():
    """PIO program to send a DMX Universe frame.
    Author: Jostein Løwer, github: jostlowe
    SPDX-License-Identifier: BSD-3-Clause

    PIO program for outputting the DMX lighting protocol.
    Compliant with ANSI E1.11-2008 (R2018)
    The program assumes a PIO clock frequency of exactly 1MHz
    """
    # Assert break condition
    set(x, 21)               .side(0)       # Preload bit counter, assert break condition for 176us
    wrap_target()
    label("breakloop")
    jmp(x_dec, "breakloop")  .side(0) [7]   # Each loop iteration is 8 cycles.

    # Assert start condition
    nop()                    .side(1)       # Assert MAB. 8 cycles nop and 8 cycles stop-bits = 16us

    # Send data frame
    wrap_target()
    pull()                   .side(1) [7]   # Assert 2 stop bits, or stall with line in idle state
    set(x, 7)                .side(0) [3]   # Preload bit counter, assert start bit for 4 clocks
    label("bitloop")
    out(pins, 1)                            # Shift 1 bit from OSR to the first OUT pin
    jmp(x_dec, "bitloop")    .side(0) [2]   # Each loop iteration is 4 cycles.
    wrap()
# fmt: on


# Usage example
sm1 = StateMachine(
    1,
    dmx_send,
    freq=1_000_000,
    set_base=pin_dmx_tx,
    out_base=pin_dmx_tx,
    sideset_base=pin_dmx_tx,
)
sm1.active(1)


class DMX:
    def __init__(self, dmx_tx: Pin):
        self.universe = bytearray(UNIVERSE_LENGTH + 1)
        machine_nr = 0

        self.sm = StateMachine(
            machine_nr,
            dmx_send,
            freq=1_000_000,
            sideset_base=dmx_tx,
            out_base=dmx_tx,
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
        self.sm.active(0)
        self.sm.put(self.universe)


dmx = DMX(pin_dmx_tx)
dmx.swoop()

while 1:
    dmx.send()
    time.sleep(0.1)
