;Move to next object on the platform. clear_z is the minimal z height we need to make sure we do not hit any objects.
G92 E0
G1 Z{clear_z} E-5 F{max_z_speed}
G92 E0
G1 X{machine_center_x} Y{machine_center_y} F{travel_speed}
G1 F200 E7.5
G1 Z0 F{max_z_speed}

