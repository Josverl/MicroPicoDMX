# DMX Frame information
 
 ## Frame Composition
 **Break**
   The start of each DMX frame is prefixed by a "break" signal that provides the first part of the synchronisation sequence that indicates the start of a multiplexing frame. 
   This is followed by a Mark After Break (MAB). The MAB helps to ensure the Break is an actual start sequence, and also provides sufficient time for even slow receivers to reset after the previous frame and then reliably process the first slot.
   Break signal at a data rate of 250 k baud.
   
   In DMX, the break (**at the sender**) is longer than the minimum, with a duration of **92 µS** of continuous low signal. 
   This is followed by a 12 µS high level (Mark After Break) The next low transition indicates the control slot (start code). 
   This longer duration provides more reliable detection of the start of a frame.
   
   **At the receiver**, the start of a DMX packet is indicated by a break of 88µS, or greater, followed by a Mark After Break, MAB, of 8uS or greater. This break is used by the receiver to start reception of the DMX slots. The MTBF, Mark Time Between Frames can be up to 1 second. The MTBF is set high
 
  **Mark After Break** 
   Note: **A transmitter** must always be set to produce a _Break of at least 92 microseconds_. 
   The 1986 version of the Standard specified a 4 microsecond MAB period. 
   The 1990 version of the standard changed that value to 8 microseconds.

 **Start Code**
   The first slot (0) within the frame carries the START Code. This defines the format of the information in the subsequent slots in the frame. The interoperability of equipment complying with the Standard is largely due to support of the NULL START Code, which provides the most basic functions and must be implemented by all receivers. A receiver that does not know how to interpret an Alternate START Code (e.g. non-zero) must discard the entire contents of the frame. Alternate START Codes are reserved for special purposes or for future development of the Standard.
 
 For each data slot, the receiver must also check the first stop bit and should check the second stop bit of all received slots to determine if they have the correct value. If a missing stop bit is detected, the receiver needs to discard the improperly framed slot data and all following slots in the frame.
 
 The frame composition of a n-byte DMX Frame may be summarised as:
 1. Break
 2. Mark After Break (MAB)
 3. Start Code
    -  Start bit
    -  Start Code (8-bit Value)
    -  STOP Bit
    -  Stop bit
 4. Mark time before 1st data slot
 5. For count := 1 to n ( Max. n of 512)
    - Start bit
    - 8-bit Slot Value
    - Stop Bit
    - Stop bit
    - Mark time between slots
 The total frame-to-frame period must be in the range 1240 microseconds to 1 Second.


 ## sources
 (1) DMX Frame - University of Aberdeen. https://www.erg.abdn.ac.uk/users/gorry/eg3576/DMX-frame.html.
 (2) DMX512 - Wikipedia. https://en.wikipedia.org/wiki/DMX512.
 (3) undefined. https://support.etcconnect.com/ETC/FAQ/DMX_Speed.
 (4) undefined. https://www.shine.lighting/products/dmx-lighting-control/.
 (5) https://tsp.esta.org/tsp/documents/published_docs.php
 