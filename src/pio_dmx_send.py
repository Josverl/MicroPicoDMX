
from machine import Pin, Signal
from rp2 import PIO, StateMachine, asm_pio

# -----------------------------------------------
from typing_extensions import TYPE_CHECKING  # type: ignore

if TYPE_CHECKING:
    from rp2.asm_pio import *
# -----------------------------------------------



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

