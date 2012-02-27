M104 S0                ;extruder heat off
M106                   ;fan on
G91                    ;relative positioning
G1 Z+10 E-5 F400       ;move Z up a bit and retract filament by 5mm
G28 X0 Y0              ;move X/Y to min endstops, so the head is out of the way
M84                    ;steppers off
G90                    ;absolute positioning

