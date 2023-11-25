import json
from typing import List

import pytest
from pioemu import State, emulate

PioCode = List[int]

def print_trace(steps, last=-10):
    print("\nClk, PC,      GPIO ->      GPIO,        X, ISR.....(l)")
    for before, after in steps[last:]:
        isr = f"{after.input_shift_register.contents:b}"[:after.input_shift_register.counter]
        for i in reversed((4, 8, 16, 20, 24, 28)):
            isr = isr[:i] + ' ' + isr[i:]
        print(
            f"{before.clock:>3}, {before.program_counter:>2}, {before.pin_values:>9_b} -> {after.pin_values:>9_b} {after.x_register:>9_b} {isr:<35} {after.input_shift_register.counter} "
        )
    current = steps[-1][1]
    print(
        f"{current.clock:>3}, {current.program_counter:>2}, {current.pin_values:>9_b}"
    )

# List of breakpoints in the PIO code
BP_BREAK = 3
BP_MAB = 4
BP_STARTBIT = 5
BP_READBITS = 8
BP_STOPBITS = 9


from typing import List, Union


def DMXTestFrame(t=0,value:Union[int,List]=0, add_break = True, add_mab = True):
    """Generates one or more DMX frames for testing"""
    l = []
    # generate a list 
    if isinstance(value, list):
        for i in range(len(value)):
            f = DMXTestFrame(t, value[i], add_break, add_mab)
            l.extend(f)
            add_break, add_mab = False, False
            # next frame starts 4us after last bit of this frame
            t = f[-1][0] + 4
        return l
    # generate a single frame
    if add_break:
        l.append((t, 0b0000_0000))  # BREAK
        add_mab = True
    if add_mab:
        l.append((t+150, 0b0000_0001))  # MAB
    l.append((t+150 + 16, 0b0000_0000))  # 1 Start bit
    for i in range(8):
        l.append((t+150 +20 + i*4, (value >> i) & 1))
    l.append((t+ 150 +20 + 32, 0b0000_0001))  # 2 stop bits
    l.append((t+ 150 +20 + 36, 0b0000_0001))  # 2 stop bits
    return l

# time in us, 8 bit value
# GPIO 0 = bit 0 , is rightmost bit
DMX_OK= DMXTestFrame(0, 0b10101010) + [(300, 0b0000_0000)]

DMX_BREAK_GLITCH = [
    (000, 0b0000_0000),  # BREAK
    (50, 0b1111_1111),  # glitch on the line
    (51, 0b0000_0000),
] + DMXTestFrame(50, 0b10101010) + [(300, 0b0000_0000)]

DMX_MAB_GLITCH = [
    (000, 0b0000_0000),  # BREAK
    (150, 0b0000_0001),  # MAB
    (152, 0b1111_0000),  # glitch on the line
]

DMX_NO_STOP = DMXTestFrame(0, 0b10101010)[:-2] + [(300, 0b0000_0000)]

@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_OK, id="normal"),
        pytest.param(True, DMX_BREAK_GLITCH, id="BREAK_glitched"),
        pytest.param(True, [(0, 0b0000_0000)], id="only_break"),
        pytest.param(False, [(0, 0b0000_0001)], id="only_high"),

    ],
)
def test_1_detect_BREAK(pio_code: PioCode, inputs: List, incoming_signals, detect: bool):
    # TEST Detect BREAK
    # Test - Too short for a BREAK
    RUN_TO = BP_BREAK
    MAX_CYCLES = 250

    state = State()
    now = state.clock

    def detect_break(opcode, state: State):
        return state.program_counter == RUN_TO or state.clock > now + MAX_CYCLES

    emu = emulate(
        pio_code,
        stop_when=detect_break,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
    )

    steps = list(emu)
    print_trace(steps,-20)
    if steps:
        state = steps[-1][1]
    print(state)
    if detect:
        assert state.x_register < 0, "BREAK detected X register should be 0"
        assert state.pin_values & 0b0000_0001 == 0b0000_0000, "Pin 0 DMX RX should be low"
    else:
        assert state.pin_directions < RUN_TO, "BREAK not detected"
        assert state.pin_values & 0b0000_0001 == 0b0000_0001, "Pin 0 DMX RX should be high"



@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_OK, id="normal"),
        pytest.param(True, DMX_BREAK_GLITCH, id="BREAK glitched"),
        pytest.param(False, DMX_MAB_GLITCH, id="MAB glitched",marks=pytest.mark.xfail), # TODO: This is a false positive
        pytest.param(False, [(0, 0b0000_0000)], id="No MAB"),

    ],
)
def test_2_detect_MAB(pio_code: PioCode, inputs: List, incoming_signals, detect: bool):
    # TEST Detect BREAK + MAB
    # start at t=140

    RUN_TO = BP_MAB
    MAX_CYCLES = 350
    state = State()

    now = state.clock

    def detect_MAB(opcode, state: State):
        return state.program_counter == RUN_TO or state.clock > now + MAX_CYCLES

    emu = emulate(
        pio_code,
        stop_when=detect_MAB,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
    )

    steps = list(emu)
    print_trace(steps,-20)
    if steps:
        state = steps[-1][1]
    print(state)
    if detect:
        assert state.program_counter == RUN_TO, "MAB not detected"
        assert state.pin_values & 0b0000_0001 == 0b0000_0001, "Pin 0 DMX RX should be high"
    else:
        assert state.program_counter < RUN_TO, "False Positive, MAB detected"

@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_OK, id="normal"),
        pytest.param(True, DMX_BREAK_GLITCH, id="BREAK glitched"),
    ])
def test_3_startbit(detect, pio_code: PioCode, incoming_signals):
    # TEST Detect START Bit

    RUN_TO = BP_STARTBIT
    MAX_CYCLES = 250
    state = State()

    now = state.clock

    def detect_startbit(opcode, state: State):
        return state.program_counter == RUN_TO or state.clock > now + MAX_CYCLES

    emu = emulate(
        pio_code,
        stop_when=detect_startbit,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
    )

    steps = list(emu)
    print_trace(steps)
    if steps:
        state = steps[-1][1]
    if detect:
        assert state.program_counter == RUN_TO, "Start bit not detected"
        assert state.pin_values & 0b0000_0001 == 0b0000_0000, "Pin 0 DMX RX should be low"
    else:
        raise NotImplementedError("False Positive, Start bit detected")

@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_OK, id="normal"),
        # pytest.param(True, DMX_BREAK_GLITCH, id="BREAK glitched"),
    ])
def test_4_readbits(detect, pio_code: PioCode, incoming_signals):

    RUN_TO = BP_READBITS
    MAX_CYCLES = 250
    state = State()
    now = state.clock

    def detect_startbit(opcode, state: State):
        return state.program_counter == RUN_TO or state.clock > now + MAX_CYCLES

    emu = emulate(
        pio_code,
        stop_when=detect_startbit,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
    )

    steps = list(emu)
    print_trace(steps,-20)
    if steps:
        state = steps[-1][1]
    print(state)
    # print the first 8 bits
    print(bin(state.input_shift_register.contents>>24))

    if detect:
        assert state.program_counter == RUN_TO, "Start bit not detected"
        assert state.input_shift_register.contents>>24 == 0b10101010, "incorrect channel data"
    else:
        raise NotImplementedError("False Positive, Start bit detected")


@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_OK, id="normal"),
        pytest.param(True, DMX_BREAK_GLITCH, id="BREAK glitched"),
        pytest.param(False, DMX_NO_STOP, id="No Stopbits"),
    ])
def test_5_stopbits(detect, pio_code: PioCode, incoming_signals):
    # TEST Detect START Bit

    RUN_TO = BP_STOPBITS
    MAX_CYCLES = 350
    state = State()

    now = state.clock

    def detect_startbit(opcode, state: State):
        return state.program_counter == RUN_TO or state.clock > now + MAX_CYCLES

    emu = emulate(
        pio_code,
        stop_when=detect_startbit,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
    )

    steps = list(emu)
    print_trace(steps,-20)
    if steps:
        state = steps[-1][1]
    print(state)
    assert state.program_counter == RUN_TO, "stop bit(s) not detected"
    assert state.pin_values & 0b0000_0001 == 0b0000_0001, "Pin 0 DMX RX should be high"

