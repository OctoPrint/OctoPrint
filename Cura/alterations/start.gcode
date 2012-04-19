G21        ;metric values
G90        ;absolute positioning

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

; if your prints start too high, try changing the Z0.0 below
; to Z1.0 - the number after the Z is the actual, physical
; height of the nozzle in mm. This can take some messing around
; with to get just right...
G92 X0 Y0 Z0 E0         ;reset software position to front/left/z=0.0
G1 Z15.0 F{max_z_speed} ;move the platform down 15mm
G92 E0                  ;zero the extruded length

G1 F200 E5              ;extrude 5mm of feed stock
G1 F200 E3.5            ;reverse feed stock by 1.5mm
G92 E0                  ;zero the extruded length again

;go to the middle of the platform, and move to Z=0 before starting the print.
G1 X{machine_center_x} Y{machine_center_y} F{travel_speed}
G1 Z0.0 F{max_z_speed}
