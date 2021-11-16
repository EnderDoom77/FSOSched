# FSOSched

This module is a simple visualizer for process queues. It stems from the core concept of a CPU and IO queue. 
These queues can be nested practically indefinitely to support superqueues.

Available priority systems are "FIFO", "FILO", "SJF", "SRTF", "Priority", and "RR q" (where q is a number representing the quantum).

Any system can be marked as pre-emptive or non-pre-emptive; though using this in non-intuitive ways might cause the system to behave oddly.

All processes support customization options; you must set at least "bursts" and "queues" (which must be of the same length); 
"color" is the only way to differentiate processes; so it's recommended you set it as well. 
"bursts" refers to the length of each burst.
"queues" refers to the insertion queue for the process in each burst; you should alternate between "IO" (or subqueues) and "CPU" (or subqueues), but this isn't enforced.
Setting the insertion queue of a process to a superqueue will have it randomly inserted into one of the queues subqueues.

Once rendered, pressing "Down" (down arrow) or "Up" (up arrow) will move the resulting rendered graphic.

## Requirements and Dependencies

* Python 3.10+
* graphics.py v5.0+ (included in repository)
* tkinter library
