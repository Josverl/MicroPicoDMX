
from typing import List, Tuple, Union


def print_trace(steps, last=-10):
    """
    Prints the trace of the steps in the given list.

    Args:
        steps (list): List of tuples representing the steps.
        last (int, optional): Index of the last step to print. Defaults to -10.

    Returns:
        None
    """
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

def DMXTestFrame(
    t=0,
    value: Union[int, List] = 0,
    *,
    add_break=176,
    add_mab=12,
    time_between_slots=0,
    timing=False,
) -> List[Tuple[int, int]]:
    """Generates one or more DMX frames for testing"""
    l = []
    timings = []
    # generate a list
    if isinstance(value, list):
        for i in range(len(value)):
            timings.append((t, value[i]))
            f = DMXTestFrame(t, value[i], add_break=add_break, add_mab=add_mab)
            l.extend(f)
            add_break, add_mab = 0, 0
            # next frame starts 4us after last bit of this frame
            t = f[-1][0] + 4 + time_between_slots
        if timing:
            # only return the timings
            return timings
        else:
            return l
    # generate a single frame
    offset = 0
    if add_break:
        l.append((t, 0b0000_0000))  # BREAK
        add_mab = add_mab or 12  # MAB minumum 12 us
        offset += 176  # min 92 us - average 176 us
    if add_mab:
        l.append((t + offset, 0b0000_0001))  # MAB
        offset += add_mab
    l.append((t + offset, 0b0000_0000))  # 1 Start bit
    offset += 4
    # 8 data bits
    for i in range(8):
        l.append((t + offset + i * 4, (value >> i) & 1))
    # 2 stop bits
    l.append((t + offset + 32, 0b0000_0001))  # 2 stop bits
    l.append((t + offset + 36, 0b0000_0001))  # 2 stop bits
    return l