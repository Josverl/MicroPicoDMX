# Example using PIO to create a UART TX interface

from machine import Pin
from rp2 import PIO, StateMachine, asm_pio

UART_BAUD = 115200
PIN_BASE = 10
NUM_UARTS = 8


# -----------------------------------------------
# add type hints for the rp2.PIO Instructions
from typing_extensions import TYPE_CHECKING  # type: ignore

if TYPE_CHECKING:
    from rp2.asm_pio import *


# -----------------------------------------------
@asm_pio(
    sideset_init=PIO.OUT_HIGH,
    out_init=PIO.OUT_HIGH,
    out_shiftdir=PIO.SHIFT_RIGHT,
)
# fmt: off
def uart_tx():
    # Block with TX deasserted until data available
    pull()
    # Initialise bit counter, assert start bit for 8 cycles
    set(x, 7)  .side(0)       [7]
    # Shift out 8 data bits, 8 execution cycles per bit
    label("bitloop")
    out(pins, 1)              [6]
    jmp(x_dec, "bitloop")
    # Assert stop bit for 8 cycles total (incl 1 for pull())
    nop()      .side(1)       [6]
# fmt: on

i = 0
sm = StateMachine(
    i, uart_tx, freq=8 * UART_BAUD, sideset_base=Pin(PIN_BASE + i), out_base=Pin(PIN_BASE +i)
)
sm.active(1)


# We can print characters from each UART by pushing them to the TX FIFO
def pio_uart_print(sm, s):
    for c in s:
        sm.put(ord(c))

import time
while 1:
    print("en weer")
    pio_uart_print(sm, "Hello from UART 0")
    time.sleep(1)

