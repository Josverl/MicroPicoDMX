from machine import Pin, Signal
from rp2 import PIO, StateMachine, asm_pio

# -----------------------------------------------
from typing_extensions import TYPE_CHECKING  # type: ignore

if TYPE_CHECKING:
    from rp2.asm_pio import *
# -----------------------------------------------



# fmt: off
@asm_pio()
def dmx_receive():
    """PIO program to receive a DMX Universe frame of 512 channels."""
    # Constants
    dmx_bit = 4  # As DMX has a baudrate of 250.000kBaud, a single bit is 4us

    # Break loop
    # Receiver DMX break signal is 88us, so we need to loop 22 times to get 88us
    label("break_reset")
    set(x, 29)                          # 0

    label("break_loop")                 # BREAK = low for 88us
    jmp(pin, "break_reset")             # 1 | Go back to start if pin goes high during BREAK
    jmp(x_dec, "break_loop")        [1] # 2 | wait until BREAK time over (22 loops * 4us = 88us)
    
    wait(1, pin, 0)                     # 3 | wait for the Mark-After-Break (MAB)

    # Data loop
    # First start bit   - no need to detect end of frame
    label("wrap_target")                    # Start of a byte
    wait(0, pin, 0)                 [1] # 4 | Wait for START bit (low) + 1+1us - measure halfway through the bit
    set(x, 7)                       [3] # 5 | 7 more bit;  skip to halfway first bit

    label("bitloop")
    in_(pins, 1)                    [1] # 6 Shift data bit into ISR
    jmp(x_dec, "bitloop")           [1] # 7 Loop 8 times, each loop iteration is 4us

    # Stop bits
    wait(1, pin, 0)                 [3]  # 8 Wait for pin to go high for stop bit-1
    wait(1, pin, 0)                      # 9 Wait for pin to go high for stop bit-2
    #  in_(null, 24 )                      
    # TODO check if STOP bits are at 8us long
    # if longer than 8 us then we are at the end of the frame  MARK Time after Slot 512
    # this can be up to  1 second - which may be too long for a PIO program to count
    push()                           [0]  # 9
# fmt: on


def example_usage():
    pin_dmx_tx = Pin(15, Pin.OUT)  # send data to the DMX bus
    pin_dmx_rx = Pin(14, Pin.IN, pull=Pin.PULL_DOWN)  # receive data from the DMX bus
    sig_max485_send = Pin(12, Pin.OUT, Pin.PULL_DOWN)  # enable/disable the MAX485 chip
