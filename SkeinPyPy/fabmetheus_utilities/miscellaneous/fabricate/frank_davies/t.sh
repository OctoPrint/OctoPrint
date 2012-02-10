#!/bin/sh
stty -F /dev/ttyUSB0 19200 ixon ixoff  # set up the USB serial port for bring_to_temp.py
python bring_to_temp.py    # call a program that waits for the extruder to come to temp
stty -F /dev/ttyUSB0 19200 ixon ixoff  # set up the USB serial port again for the transfer
cat delay.gcode $1 >temp.gcode     # make temporary file with extra at the beginning
ascii-xfr -sv temp.gcode >/dev/ttyUSB0  # transfer the file
#cp $1 /dev/ttyUSB0  # alternate transfer method commented out.
echo DONE
