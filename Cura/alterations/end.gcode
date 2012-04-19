M104 S0                    ;extruder heat off
G91                        ;relative positioning
G1 Z+10 E-5 F{max_z_speed} ;move Z up a bit and retract filament by 5mm
G28 X0 Y0                  ;move X/Y to min endstops, so the head is out of the way
M84                        ;steppers off
G90                        ;absolute positioning
