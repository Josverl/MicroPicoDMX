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



@asm_pio(
    set_init=PIO.OUT_LOW,
    sideset_init=PIO.OUT_LOW,
    out_init=PIO.OUT_LOW, 
    out_shiftdir=PIO.SHIFT_RIGHT,  # data is shifted out LSB first
    push_thresh=8,
)
# fmt: off
def dmx_send():
    """
    - valid values for the data channels are 0-255
    Minimum universe length is 10 channels / slots

    
    The pio Statemachine must be reset before sending a new universe of data,
    this will send the BREAK and the MAB signals
    the universe is an bytearray of a 1 + 512 bytes
    The first byte is the START_CODE , the next 512 bytes are the data channels
    - the START_CODE is 0x00 for DMX Data Packets
    - the START_CODE is 0xCC for RDM Data Packets
    - the START_CODE is 0xFE for RDM Discovery Data Packets


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

def send_example():
    # -----------------------------------------------
    # Wiring schema for the DMX TX
    import time
    from array import array

    pin_dmx_tx = Pin(15, Pin.OUT)  # send data to the DMX bus
    pin_dmx_rx = Pin(14, Pin.IN, pull=Pin.PULL_DOWN)  # receive data from the DMX bus

    max485_send = Pin(12, Pin.OUT, Pin.PULL_DOWN)  # switch send/receive for the MAX485 chip


    # Usage example
    sm_dmx_tx = StateMachine(
        1,
        dmx_send,
        freq=1_000_000,
        set_base=pin_dmx_tx,
        out_base=pin_dmx_tx,
        sideset_base=pin_dmx_tx,
    )
    sm_dmx_tx.active(1)
    max485_send.on()  # switch the MAX485 chip for transmitting

    size = 512

    universe = array("B", [0] + [255] * (size))  # 1 start code + 512 channels
    sm_dmx_tx.put(universe)  
    
    time.sleep_us(4 * 50)  # wait for the last 4 frames (4 x 44us and some) in the tx FIFO to be sent before switching the 485 driver
    max485_send.off()  # switch the MAX485 chip for receiving



def example_receive():
    pin_dmx_tx = Pin(15, Pin.OUT)  # send data to the DMX bus
    pin_dmx_rx = Pin(14, Pin.IN, pull=Pin.PULL_DOWN)  # receive data from the DMX bus
    sig_max485_send = Pin(12, Pin.OUT, Pin.PULL_DOWN)  # enable/disable the MAX485 chip
