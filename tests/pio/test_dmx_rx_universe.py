import json
from typing import List, Tuple

import pytest
from helpers import TestFrame, get_test_pulse, make_testframes, print_trace
from pioemu import State, emulate

PioCode = List[int]

# List of breakpoints in the PIO code
BP_BREAK = 3
BP_MAB = 4
BP_STARTBIT = 5
BP_READBITS = 8
BP_STOPBITS = 9


# time in us, 8 bit value
# GPIO 0 = bit 0 , is rightmost bit
DMX_1F_SHORT = make_testframes(0, [0, 1, 2, 3, 4, 5, 6, 7, 8])
DMX_1F_SHORT_T = make_testframes(0, [0, 1, 2, 3, 4, 5, 6, 7, 8], timing=True)


@pytest.mark.parametrize(
    "detect, inputs, timings",
    [
        pytest.param(
            True,
            make_testframes(0, [0x00, 0xFF]),
            make_testframes(0, [0x00, 0xFF], timing=True),
            id="1 channel",
        ),
        pytest.param(
            True,
            make_testframes(0, [0x00] + [0xFF] * 4),
            make_testframes(0, [0x00] + [0xFF] * 4, timing=True),
            id="4 channel",
        ),
        pytest.param(
            True,
            make_testframes(0, [0x00] + [0xFF] * 5),
            make_testframes(0, [0x00] + [0xFF] * 5, timing=True),
            id="5 channel",
        ),
        pytest.param(
            True,
            make_testframes(0, [0x00] + [0xFF] * 6),
            make_testframes(0, [0x00] + [0xFF] * 6, timing=True),
            id="6 channel",
        ),
        pytest.param(
            True,
            make_testframes(0, [0x00] + [0xFF] * 8),
            make_testframes(0, [0x00] + [0xFF] * 8, timing=True),
            id="8 channel",
        ),
        pytest.param(
            True,
            make_testframes(0, [0x00] + [0xFF] * 16),
            make_testframes(0, [0x00] + [0xFF] * 16, timing=True),
            id="16 channel",
        ),
        pytest.param(
            True,
            make_testframes(0, [0x00] + [0xFF] * 128),
            make_testframes(0, [0x00] + [0xFF] * 128, timing=True),
            id="128 channel",
        ),
        pytest.param(
            True,
            make_testframes(0, [0x00] + [0xFF] * 512),
            make_testframes(0, [0x00] + [0xFF] * 512, timing=True),
            id="512 channel",
        ),
    ],
)
def test_2_3_startbit(detect, pio_code: PioCode, incoming_signals, inputs: List[TestFrame],timings: List[TestFrame]):
    # TEST Detect START Bit

    RUN_TO = BP_STARTBIT
    state = State()

    channel = len(timings) -1
    MIN_TICKS = timings[channel][0] - 4
    MAX_TICKS = timings[channel][0] + 50

    now = state.clock

    def detect_startbit(opcode, state: State) -> bool:
        # make sure the receive fifo does not fill up as that would block the test
        # so emulate the fifo being read
        # NOTE: Currently only 1/4 of the capacilty is used 
        # NOTE 2: Emulator does not currently support FIFO chaining 
        if len(state.receive_fifo) == 4:
            # pop per 4 channels
            for i in range(4):
                value = state.receive_fifo.popleft() >> 24
                print(f"RECEIVED Channel {channel-4+i} Value: {value}")

        if state.clock < MIN_TICKS: 
            return False
        return state.program_counter == RUN_TO or state.clock > now + MAX_TICKS

    emu = emulate(
        pio_code,
        stop_when=detect_startbit,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
        wrap_target= 4
    )

    steps = list(emu)
    print_trace(steps, since=MIN_TICKS)
    if steps:
        state = steps[-1][1]
    if detect:
        print(f"start bit pulse for channel: {channel} starts at: tick {timings[channel][0]}")
        assert state.program_counter == RUN_TO, "Start bit not detected"
        assert state.pin_values & 0b0000_0001 == 0b0000_0000, "Pin 0 DMX RX should be low"

        # look for the start bit in the inputs
        found = get_test_pulse(inputs, state)
        assert found is not None, "Start bit not found in inputs"
        assert found[3] == "START", "other signal detected START bit"
    else:
        raise NotImplementedError("False Positive, Start bit detected")


@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_1F_SHORT, id="normal"),
        # pytest.param(True, DMX_BREAK_GLITCH, id="BREAK glitched"),
    ],
)
def test_2_40_frame_startcode(detect, pio_code: PioCode, incoming_signals):
    RUN_TO = BP_READBITS
    MAX_TICKS = 1500
    state = State()
    now = state.clock

    def detect_startbit(opcode, state: State):
        return state.program_counter == RUN_TO or state.clock > now + MAX_TICKS

    emu = emulate(
        pio_code,
        stop_when=detect_startbit,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
        wrap_target= 4,
    )

    steps = list(emu)
    print_trace(steps, -20)
    if steps:
        state = steps[-1][1]
    print(state)
    # print the first 8 bits
    print(bin(state.input_shift_register.contents >> 24))

    if detect:
        assert state.program_counter == RUN_TO, "Start bit not detected"
        assert state.input_shift_register.contents >> 24 == 0, "incorrect channel data"
    else:
        raise NotImplementedError("False Positive, Start bit detected")


@pytest.mark.parametrize("sample", DMX_1F_SHORT_T)
@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_1F_SHORT, id="normal"),
    ],
)
def test_2_41_frame_channel(detect, pio_code: PioCode, incoming_signals, sample: Tuple[int, int]):
    sample_time = sample[0]
    sample_value = sample[1]
    RUN_TO = BP_READBITS
    MAX_TICKS = sample_time + 1000
    state = State()
    now = state.clock

    def detect_data(opcode, state: State):
        # make sure the receive fifo does not fill up as that would block the test
        # so emulate the fifo being read
        if len(state.receive_fifo) == 4:
            # pop per 4 channels
            for i in range(4):
                value = state.receive_fifo.popleft() >> 24
        # only stop after the start of the desired sample time
        return (
            state.program_counter == RUN_TO and state.clock >= sample_time
        ) or state.clock > now + MAX_TICKS

    emu = emulate(
        pio_code,
        stop_when=detect_data,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
        wrap_target= 4,
    )

    steps = list(emu)
    print_trace(steps, -20)
    if steps:
        state = steps[-1][1]
    print(state)
    # print the first 8 bits
    data = state.input_shift_register.contents >> 24
    print("Channel Data: {0} , 0x{0:x}, 0b{0:_b} ".format(data))

    if detect:
        assert state.program_counter == RUN_TO
        assert data == sample_value, "incorrect channel data, expected {sample_value} got {data}"
    else:
        raise NotImplementedError("False Positive, channel data detected")


@pytest.mark.parametrize(
    "detect, inputs",
    [
        pytest.param(True, DMX_1F_SHORT, id="normal"),
        # pytest.param(True, DMX_BREAK_GLITCH, id="BREAK glitched"),
        # pytest.param(False, DMX_NO_STOP, id="No Stopbits"),
    ],
)
def test_2_5_stopbits(detect, pio_code: PioCode, incoming_signals):
    # TEST Detect START Bit

    RUN_TO = BP_STOPBITS
    MAX_TICKS = 350
    state = State()

    now = state.clock

    def detect_startbit(opcode, state: State):
        return state.program_counter == RUN_TO or state.clock > now + MAX_TICKS

    emu = emulate(
        pio_code,
        stop_when=detect_startbit,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
        wrap_target= 4,
    )

    steps = list(emu)
    print_trace(steps, -20)
    if steps:
        state = steps[-1][1]
    print(state)
    assert state.program_counter == RUN_TO, "stop bit(s) not detected"
    assert state.pin_values & 0b0000_0001 == 0b0000_0001, "Pin 0 DMX RX should be high"
