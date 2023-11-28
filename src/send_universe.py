# Create a universe that we want to send.
# The universe must be maximum 512 bytes + 1 byte of start code
UNIVERSE_LENGTH = 512

import time
from array import array
from typing import Optional

from machine import Pin
from rp2 import StateMachine
# -----------------------------------------------
# add type hints for the rp2.PIO Instructions
from typing_extensions import TYPE_CHECKING

from pio_dmx import dmx_receive, dmx_send

if TYPE_CHECKING:
    from rp2.asm_pio import *
# -----------------------------------------------

# -----------------------------------------------
# Wiring schema for the DMX TX
pin_dmx_tx = Pin(15, Pin.OUT)  # send data to the DMX bus
pin_dmx_rx = Pin(14, Pin.IN, pull=Pin.PULL_DOWN)  # receive data from the DMX bus

max485_send = Pin(12, Pin.OUT, Pin.PULL_DOWN)  # switch send/receive for the MAX485 chip


class DMX:
    """
    DMX class for controlling DMX universe.

    Args:
        dmx_tx (Pin): The pin used for transmitting DMX data.
        size (int, optional): The size of the DMX universe. Defaults to 512.
        max485_send (Optional[Pin], optional): The pin used for controlling the MAX485 chip. Defaults to None.

    Attributes:
        universe (array): The DMX universe array.
        sm_tx (StateMachine): The state machine for transmitting DMX data.
        max485_send (Optional[Pin]): The pin used for controlling the MAX485 chip.

    Methods:
        send: Send the universe to the DMX bus.
        set_channel: Set the value of a specific DMX channel.
        get_channel: Get the value of a specific DMX channel.
        blackout: Set all channels to 0.
    """
    
    def __init__(self, dmx_tx: Pin , size:int = 512, max485_send: Optional[Pin] = None):
        self.universe = array("B", [0] + [0] * (size))  # 1 start code + 512 channels
        machine_nr = 0
        self.max485_send = max485_send
        self.sm_tx = StateMachine(
            machine_nr,
            dmx_send,
            freq=1_000_000,
            out_base=dmx_tx,
            set_base=dmx_tx,
            sideset_base=dmx_tx
        )
        self.sm_tx.active(0)
        self.sm_tx.restart()

    def set_channel(self, channel: int, value: int):
        """
        Set the value of a specific DMX channel.

        Args:
            channel (int): The channel number.
            value (int): The value to set.
        """
        self.universe[channel] = value


    def get_channel(self, channel: int):
        """
        Get the value of a specific DMX channel.

        Args:
            channel (int): The channel number.

        Returns:
            int: The value of the channel.
        """
        return self.universe[channel]

    def blackout(self):
        """
        Set all channels to 0.
        """	
        for i in range(UNIVERSE_LENGTH):
            self.universe[i] = 0


    def send(self):
        """
        Send the universe to the DMX bus.
        """	
        if self.max485_send:
            self.max485_send.on()  # switch the MAX485 chip for transmitting
        self.sm_tx.restart()
        self.sm_tx.active(1)            
        self.sm_tx.put(self.universe)
        if self.max485_send:
            time.sleep_us(4 * 50)  # wait for the last 4 frames (4 x 44us and some) in the tx FIFO to be sent before switching the 485 driver
            self.max485_send.off()  # switch the MAX485 chip for receiving


#####################################################################
p1 = Pin(1, Pin.OUT, value=0)  # Debugging aid to sync view on the the logic analyzer


size = 512
dmx = DMX(pin_dmx_tx, size=512, max485_send=max485_send)


for i in range(1,512):
    dmx.set_channel(i, i % 256)

dmx.set_channel(0, 123)  # test Start Code


while 1:
    p1.on()
    dmx.send()

    p1.off()
    time.sleep_ms(300)


