# Example using PIO to drive a set of WS2812 LEDs.

import array
import time

import rp2
from machine import Pin

from ws2812_pio import ws2812

# Configure the number of WS2812 LEDs.
NUM_LEDS = 8

# Create the StateMachine with the ws2812 program, outputting on Pin(22).
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(2))

# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

# Display a pattern on the LEDs via an array of LED RGB values.
ar = array.array("I", [0 for _ in range(NUM_LEDS)])

# Cycle colours.
for i in range(8 * NUM_LEDS):
    for j in range(NUM_LEDS):
        r = j * 100 // (NUM_LEDS - 1)
        b = 100 - j * 100 // (NUM_LEDS - 1)
        if j != i % NUM_LEDS:
            r >>= 3
            b >>= 3
        ar[j] = r << 16 | b
    sm.put(ar, 8)
    time.sleep_ms(50)

# Fade out.
for _ in range(24):
    for j in range(NUM_LEDS):
        ar[j] >>= 1
    sm.put(ar, 8)
    time.sleep_ms(50)
