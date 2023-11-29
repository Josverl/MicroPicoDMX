
from typing import List, Tuple, Union

from pioemu import State, emulate

TestFrame = Tuple[int, int, int, str]

##################################################################################
def emu_dmx_rx(pio_code, incoming_signals, state, detect_break):
    emu = emulate(
        pio_code,
        stop_when=detect_break,
        initial_state=state,
        input_source=incoming_signals,
        jmp_pin=0b0000_0001,
        wrap_target= 4,
        side_set_base=4,
        side_set_count=2,
    )
    return emu

##################################################################################
def print_trace(steps, last=-10, *, since=0):
    """
    Prints the trace of the steps in the given list.

    Args:
        steps (list): List of tuples representing the steps.
        last (int, optional): Index of the last step to print. Defaults to -10.

    Returns:
        None
    """

    if since:
        report = [s for s in steps if s[0].clock >= since]
    else:
        report = steps[last:]
    print("\nClk, PC,      GPIO ->      GPIO,        X, ISR.....(l)")
    for before, after in report:
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

def add_pulse(l:list, value:int, duration_us:int, label = "", start_tick=0):
    """Add a pulse to the list"""
    if not isinstance(l, List):
        raise TypeError("l must be a list")
    if len(l) == 0:
        tick = start_tick
    else:
        # new start time is the end time of the last item in the list
        # plus the duration of the last item for 1MHz clock
        tick = l[-1][0] + l[-1][2]

    l.append((tick, value, duration_us, label))


def make_testframes(
    tick=0,
    value: Union[int, List] = 0,
    *,
    add_break=176,
    add_mab=12,
    time_between_slots=0,
    timing=False,
) -> List[TestFrame]:
    """Generates one or more DMX frames for testing
    Args:
        t (int, optional): time in us. Defaults to 0.
        value (Union[int, List], optional): 8 bit value or list of values. Defaults to 0.
        add_break (int, optional): Add a BREAK of this length in us. Defaults to 176.
        add_mab (int, optional): Add a MAB of this length in us. Defaults to 12.
        time_between_slots (int, optional): Time between slots in us. Defaults to 0.
        timing (bool, optional): Return only the timings. Defaults to False.
    Returns:
        List[TestFrane]: List of tuples (tick, value, duration_us)
    
    """
    l = []
    t_prev = tick
    timings = []
    # generate a list
    if isinstance(value, list):
        for i in range(len(value)):
            f = make_testframes(tick, value[i], add_break=add_break, add_mab=add_mab)
            l.extend(f)
            add_break, add_mab = 0, 0
            # next frame starts 4us after last bit of this frame
            if time_between_slots:
                add_pulse(l, 0b0000_0000, time_between_slots, "MARK time between slots")
            timings.append((tick, value[i], (tick - t_prev)))
            tick = f[-1][0] + f[-1][2]
            t_prev = tick
        if timing:
            # only return the timings
            return timings
        else:
            return l
    # generate a single frame

    if add_break:
        add_pulse(l, 0b0000_0000, add_break, "BREAK",start_tick=tick)
        add_mab = add_mab or 12  # MAB minumum 12 us
    if add_mab:
        add_pulse(l, 0b0000_0001, add_mab, "MAB",start_tick=tick)
    # 1 Start bit
    add_pulse(l, 0b0000_0000, 4, "START",start_tick=tick)
    # 8 data bits
    for i in range(8):
        add_pulse(l, (value >> i) & 1, 4, f"bit {i}")
    # 2 stop bits
    add_pulse(l, 0b0000_0001, 4, "STOP")
    add_pulse(l, 0b0000_0001, 4, "STOP")
    return l


def get_test_pulse(inputs: List[TestFrame], state: State):
    """
    Find the test pulse for the given state clock.

    Args:
        inputs (List[TestFrame]): List of test frames.
        state (State): Current state.

    Returns:
        TestFrame or None: The test pulse found for the given state clock, or None if not found.
    """
    found = None
    for i in inputs:
        if i[0] <= state.clock:
            found = i
        if i[0] > state.clock:
            break
    return found