from typing import List

import pytest
from pioemu import State, emulate

PioCode = List[int]

PIO_RX_PROGRAM = [0xE03D, 0xC0, 0x141, 0x20A0, 0x2120, 0xE327, 0x4001, 0x246, 0x20A0, 0x8020] # v1

PIO_RX_PROGRAM = [0xe03d, 0xc0, 0x141, 0x20a0, 0x2120, 0xe327, 0x4101, 0x146, 0x23a0, 0x20a0, 0x8020] # v2 

PIO_RX_PROGRAM = [0xfc3d, 0xc0, 0x141, 0x34a0, 0x2120, 0xe327, 0x5901, 0x146, 0x23a0, 0x20a0, 0x8020] # v2 
PIO_RX_PROGRAM = [0xfc3d, 0xc0, 0x141, 0x34a0, 0x2120, 0xe327, 0x5901, 0x146, 0x23a0, 0x34a0, 0x8020]
PIO_RX_PROGRAM = [0xfc3d, 0xc0, 0x141, 0x34a0, 0x2120, 0xe327, 0x5801, 0x1246, 0x20a0, 0xbe42, 0x9820, 0x4]
#                                              ~~~~~~                          ~~~~~~	      ~~~~~~
# PIO_RX_PROGRAM=[0xfc3d, 0xc0, 0x141, 0x34a0, 0x3520, 0xe327, 0x5901, 0x146, 0x37a0, 0x20a0, 0x9c20] # v3 with .side(0b11) for debugging


@pytest.fixture(scope="module")
def pio_code():
    """the dmx receive PIO code"""
    # setup code
    # TODO Assemble the code from source
    assembled = PIO_RX_PROGRAM
    yield assembled
    # teardown code



@pytest.fixture()
def incoming_signals(inputs):
    """yields a function that can be used as input_source for the emulator"""

    def incoming_signals(clock: int) -> int:
        # pio clock is 1MHz, so 1us per clock
        t = clock
        match = None
        for item in inputs:
            if item[0] <= t:
                match = item
            else:
                break
        if match is None:
            new_pin_values = 0
            raise ValueError("No input signal")
        else:
            new_pin_values = match[1]
        return new_pin_values

    yield incoming_signals
