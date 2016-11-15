; resume file for {{ file }}
; generated on {{ timestamp }}
; reason: {{ reason }}

; home print head in X and Y
G28 X0 Y0 F1200

; set all temperatures back to original targets
{% for temp in temperatures %}
M104 T{{ temp.t }} S{{ temp.target }}
{% endfor %}
M116 ; wait for all temperatures to reach target

; reposition nozzle X, Y, Z, E and feedrate
G1 X{{ position.x }} Y{{ position.y }} Z{{ position.z }} F4500
G92 E{{ position.e }}
G1 F{{ movement.f }}

; feed- and flowrate modifiers
M220 {{ movement.fm }}
M221 {{ movement.em }}

; fan speeds
{% for fan in fans %}
M106 P{{ fan.p }} S{{ fan.speed }}
{% endfor %}

; ---
; {{ file }}, starting at byte {{ pos }}
; ---

