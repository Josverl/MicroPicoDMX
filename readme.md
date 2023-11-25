MicroPython DMX using Pico PIO



datasheets.raspberrypi.org/rp2040/rp2040-datasheet.pdf

https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-python-sdk.pdf


# 

### Expirimentation 
https://wokwi.com/projects/381858468736889857

online PIO assembler ( c)
https://wokwi.com/tools/pioasm

### Testing with input signals
https://github.com/NathanY3G/rp2040-pio-emulator

- RX: add tests for BREAK , MAB ,Start bits 

todo: 
- RX: bitloop , stop bits 
- RX: End of universe 
- TX: add tests for BREAK , MAB ,Start bits [ bitloop and stop bits ]
- add fuzzing test by varying timing 

### Debugging and input manipultaion 


Based on:
- Communication Engineering I - https://erg.abdn.ac.uk/users/gorry/eg3576/

### Ispired by 
- [jostlowe/Pico-DMX: A library for inputting and outputting the DMX512-A lighting control protocol from a Raspberry Pi Pico (github.com)](https://github.com/jostlowe/Pico-DMX)

PIO code improvements
- DMX timing to account for spec differences between sender and receiver

- rx: timing changes in the bitloop to keep to center of the bits 
- rx: stop bit detection 
- [rp2040-DMA](https://github.com/drtimcollins/RP2040-DMA)
-
