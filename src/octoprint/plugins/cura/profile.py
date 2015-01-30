# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import re

class SupportLocationTypes(object):
	NONE = "none"
	TOUCHING_BUILDPLATE = "buildplate"
	EVERYWHERE = "everywhere"

class SupportDualTypes(object):
	BOTH = "both"
	FIRST = "first"
	SECOND = "second"

class SupportTypes(object):
	GRID = "grid"
	LINES = "lines"

class PlatformAdhesionTypes(object):
	NONE = "none"
	BRIM = "brim"
	RAFT = "raft"

class MachineShapeTypes(object):
	SQUARE = "square"
	CIRCULAR = "circular"

class GcodeFlavors(object):
	REPRAP = "reprap"
	REPRAP_VOLUME = "reprap_volume"
	ULTIGCODE = "ultigcode"
	MAKERBOT = "makerbot"
	BFB = "bfb"
	MACH3 = "mach3"


defaults = dict(
    layer_height=0.1,
    wall_thickness=0.8,
    solid_layer_thickness=0.6,
    print_temperature=[220, 0, 0, 0],
    print_bed_temperature=70,
    platform_adhesion=PlatformAdhesionTypes.NONE,
    filament_diameter=[2.85, 0, 0, 0],
    filament_flow=100.0,
    bottom_thickness=0.3,
    first_layer_width_factor=100.0,
    object_sink=0.0,

    fill_density=20,
    solid_top=True,
    solid_bottom=True,
    fill_overlap=15,

    # speeds
    print_speed=50.0,
    travel_speed=150.0,
    bottom_layer_speed=20.0,
    infill_speed=0.0,
    outer_shell_speed=0.0,
    inner_shell_speed=0.0,

    # dual extrusion
    overlap_dual=0.15,
    wipe_tower=False,
    wipe_tower_volume=15,
    ooze_shield=False,

    # retraction
    retraction_enable=True,
    retraction_speed=40.0,
    retraction_amount=4.5,
    retraction_dual_amount=16.5,
    retraction_min_travel=1.5,
    retraction_combing=True,
    retraction_minimal_extrusion=0.02,
    retraction_hop=0.0,

    # cooling
    cool_min_layer_time=5,
    fan_enabled=True,
    fan_full_height=0.5,
    fan_speed=100,
    fan_speed_max=100,
    cool_min_feedrate=10,
    cool_head_lift=False,

    # support
    support=SupportLocationTypes.NONE,
    support_type=SupportTypes.GRID,
    support_angle=60.0,
    support_fill_rate=15,
    support_xy_distance=0.7,
    support_z_distance=0.15,
    support_dual_extrusion=SupportDualTypes.BOTH,

    # platform adhesion
    skirt_line_count=1,
    skirt_gap=3.0,
    skirt_minimal_length=150.0,
    brim_line_count=20,
    raft_margin=5.0,
    raft_line_spacing=3.0,
    raft_base_thickness=0.3,
    raft_base_linewidth=1.0,
    raft_interface_thickness=0.27,
    raft_interface_linewidth=0.4,
    raft_airgap=0.22,
    raft_surface_layers=2,

    # repairing
    fix_horrible_union_all_type_a=True,
    fix_horrible_union_all_type_b=False,
    fix_horrible_use_open_bits=False,
    fix_horrible_extensive_stitching=False,

    # extras
    spiralize=False,
    follow_surface=False,

    machine_width=205,
    machine_depth=205,
    machine_center_is_zero=False,
    has_heated_bed=False,
    gcode_flavor=GcodeFlavors.REPRAP,
    extruder_amount=1,
    steps_per_e=0,
    start_gcode=[
        # 1 extruder
        """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M109 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M82        ;set extruder to absolute mode
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

G92 E0                  ;zero the extruded length
G1 F200 E3              ;extrude 3mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""",
        # 2 extruders
        """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M104 S{print_temperature} ;Uncomment to add your own temperature line
;M109 T1 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T0 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

T1                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T0                      ;Switch to the first extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""",
        # 3 extruders
        """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M104 S{print_temperature} ;Uncomment to add your own temperature line
;M109 T1 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T0 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

T2                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T1                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T0                      ;Switch to the first extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""",
        # 4 extruders
        """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M104 S{print_temperature} ;Uncomment to add your own temperature line
;M109 T2 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T1 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T0 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

T3                      ;Switch to the 4th extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T2                      ;Switch to the 3th extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T1                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T0                      ;Switch to the first extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
"""
    ],
    end_gcode=[
        # 1 extruder
        """;End GCode
M104 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
""",
        # 2 extruders
        """;End GCode
M104 T0 S0                     ;extruder heater off
M104 T1 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
""",
        # 3 extruders
        """;End GCode
M104 T0 S0                     ;extruder heater off
M104 T1 S0                     ;extruder heater off
M104 T2 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
""",
        # 4 extruders
        """;End GCode
M104 T0 S0                     ;extruder heater off
M104 T1 S0                     ;extruder heater off
M104 T2 S0                     ;extruder heater off
M104 T3 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
"""
    ],
    preSwitchExtruder_gcode=""";Switch between the current extruder and the next extruder, when printing with multiple extruders.
;This code is added before the T(n)
""",
    postSwitchExtruder_gcode=""";Switch between the current extruder and the next extruder, when printing with multiple extruders.
;This code is added after the T(n)
"""
)


class Profile(object):

	regex_extruder_offset = re.compile("extruder_offset_([xy])(\d)")
	regex_filament_diameter = re.compile("filament_diameter(\d?)")
	regex_print_temperature = re.compile("print_temperature(\d?)")
	regex_strip_comments = re.compile(";.*$", flags=re.MULTILINE)

	@classmethod
	def from_cura_ini(cls, path):
		import os
		if not os.path.exists(path) or not os.path.isfile(path):
			return None

		import ConfigParser
		config = ConfigParser.ConfigParser()
		try:
			config.read(path)
		except:
			return None

		arrayified_options = ["print_temperature", "filament_diameter", "start.gcode", "end.gcode"]
		translated_options = dict(
			inset0_speed="outer_shell_speed",
			insetx_speed="inner_shell_speed",
			layer0_width_factor="first_layer_width_factor",
			simple_mode="follow_surface",
		)
		translated_options["start.gcode"] = "start_gcode"
		translated_options["end.gcode"] = "end_gcode"
		value_conversions = dict(
			platform_adhesion={
				"None": PlatformAdhesionTypes.NONE,
				"Brim": PlatformAdhesionTypes.BRIM,
				"Raft": PlatformAdhesionTypes.RAFT
			},
			support={
				"None": SupportLocationTypes.NONE,
				"Touching buildplate": SupportLocationTypes.TOUCHING_BUILDPLATE,
				"Everywhere": SupportLocationTypes.EVERYWHERE
			},
			support_type={
				"Lines": SupportTypes.LINES,
				"Grid": SupportTypes.GRID
			},
			support_dual_extrusion={
				"Both": SupportDualTypes.BOTH,
				"First extruder": SupportDualTypes.FIRST,
				"Second extruder": SupportDualTypes.SECOND
			}
		)

		result = dict()
		for section in config.sections():
			if not section in ("profile", "alterations"):
				continue

			for option in config.options(section):
				ignored = False
				key = option

				# try to fetch the value in the correct type
				try:
					value = config.getboolean(section, option)
				except:
					# no boolean, try int
					try:
						value = config.getint(section, option)
					except:
						# no int, try float
						try:
							value = config.getfloat(section, option)
						except:
							# no float, use str
							value = config.get(section, option)
				index = None

				for opt in arrayified_options:
					if key.startswith(opt):
						if key == opt:
							index = 0
						else:
							try:
								# try to convert the target index, e.g. print_temperature2 => print_temperature[1]
								index = int(key[len(opt):]) - 1
							except ValueError:
								# ignore entries for which that fails
								ignored = True
						key = opt
						break
				if ignored:
					continue

				if key in translated_options:
					# if the key has to be translated to a new value, do that now
					key = translated_options[key]

				if key in value_conversions and value in value_conversions[key]:
					value = value_conversions[key][value]

				if index is not None:
					# if we have an array to fill, make sure the target array exists and has the right size
					if not key in result:
						result[key] = []
					if len(result[key]) <= index:
						for n in xrange(index - len(result[key]) + 1):
							result[key].append(None)
					result[key][index] = value
				else:
					# just set the value if there's no array to fill
					result[key] = value

		# merge it with our default settings, the imported profile settings taking precedence
		return cls.merge_profile(result)


	@classmethod
	def merge_profile(cls, profile, overrides=None):
		result = dict()
		for key in defaults.keys():
			r = cls.merge_profile_key(key, profile, overrides=overrides)
			if r is not None:
				result[key] = r
		return result

	@classmethod
	def merge_profile_key(cls, key, profile, overrides=None):
		profile_value = None
		override_value = None

		if not key in defaults:
			return None
		import copy
		result = copy.deepcopy(defaults[key])

		if key in profile:
			profile_value = profile[key]
		if overrides and key in overrides:
			override_value = overrides[key]

		if profile_value is None and override_value is None:
			# neither override nor profile, no need to handle this key further
			return None

		if key in ("filament_diameter", "print_temperature", "start_gcode", "end_gcode"):
			# the array fields need some special treatment. Basically something like this:
			#
			#    override_value: [None, "b"]
			#    profile_value : ["a" , None, "c"]
			#    default_value : ["d" , "e" , "f", "g"]
			#
			# should merge to something like this:
			#
			#                    ["a" , "b" , "c", "g"]
			#
			# So override > profile > default, if neither override nor profile value are available
			# the default value should just be left as is

			for x in xrange(len(result)):
				if override_value is not None and  x < len(override_value) and override_value[x] is not None:
					# we have an override value for this location, so we use it
					result[x] = override_value[x]
				elif profile_value is not None and x < len(profile_value) and profile_value[x] is not None:
					# we have a profile value for this location, so we use it
					result[x] = profile_value[x]

		else:
			# just change the result value to the override_value if available, otherwise to the profile_value if
			# that is given, else just leave as is
			if override_value is not None:
				result = override_value
			elif profile_value is not None:
				result = profile_value

		return result

	def __init__(self, profile, printer_profile, posX, posY, overrides=None):
		self._profile = self.__class__.merge_profile(profile, overrides=overrides)
		self._printer_profile = printer_profile
		self._posX = posX
		self._posY = posY

	def profile(self):
		import copy
		return copy.deepcopy(self._profile)

	def get(self, key):
		if key in ("machine_width", "machine_depth", "machine_center_is_zero"):
			if key == "machine_width":
				return self._printer_profile["volume"]["width"]
			elif key == "machine_depth":
				return self._printer_profile["volume"]["depth"]
			elif key == "machine_height":
				return self._printer_profile["volume"]["height"]
			elif key == "machine_center_is_zero":
				return self._printer_profile["volume"]["formFactor"] == "circular"
			else:
				return None

		elif key == "extruder_amount":
			return self._printer_profile["extruder"]["count"]

		elif key.startswith("extruder_offset_"):
			extruder_offsets = self._printer_profile["extruder"]["offsets"]
			match = Profile.regex_extruder_offset.match(key)
			if not match:
				return 0.0

			axis, number = match.groups()
			axis = axis.lower()
			number = int(number)

			if not axis in ("x", "y"):
				return 0.0
			if number >= len(extruder_offsets):
				return 0.0

			if axis == "x":
				return extruder_offsets[number][0]
			elif axis == "y":
				return extruder_offsets[number][1]
			else:
				return 0.0

		elif key == "has_heated_bed":
			return self._printer_profile["heatedBed"]

		elif key.startswith("filament_diameter"):
			match = Profile.regex_filament_diameter.match(key)
			if not match:
				return 0.0

			diameters = self._get("filament_diameter")
			if not match.group(1):
				return diameters[0]
			index = int(match.group(1))
			if index >= len(diameters):
				return 0.0
			return diameters[index]

		elif key.startswith("print_temperature"):
			match = Profile.regex_print_temperature.match(key)
			if not match:
				return 0.0

			temperatures = self._get("print_temperature")
			if not match.group(1):
				return temperatures[0]
			index = int(match.group(1))
			if index >= len(temperatures):
				return 0.0
			return temperatures[index]

		else:
			return self._get(key)

	def _get(self, key):
		if key in self._profile:
			return self._profile[key]
		elif key in defaults:
			return defaults[key]
		else:
			return None

	def get_int(self, key, default=None):
		value = self.get(key)
		if value is None:
			return default

		try:
			return int(value)
		except ValueError:
			return default

	def get_float(self, key, default=None):
		value = self.get(key)
		if value is None:
			return default

		if isinstance(value, (str, unicode, basestring)):
			value = value.replace(",", ".").strip()

		try:
			return float(value)
		except ValueError:
			return default

	def get_boolean(self, key, default=None):
		value = self.get(key)
		if value is None:
			return default

		if isinstance(value, bool):
			return value
		elif isinstance(value, (str, unicode, basestring)):
			return value.lower() == "true" or value.lower() == "yes" or value.lower() == "on" or value == "1"
		elif isinstance(value, (int, float)):
			return value > 0
		else:
			return value == True

	def get_microns(self, key, default=None):
		value = self.get_float(key, default=None)
		if value is None:
			return default
		return int(value * 1000)

	def get_gcode_template(self, key):
		extruder_count = self.get_int("extruder_amount")

		if key in self._profile:
			gcode = self._profile[key]
		else:
			gcode = defaults[key]

		if key in ("start_gcode", "end_gcode"):
			return gcode[extruder_count-1]
		else:
			return gcode

	def get_profile_string(self):
		import base64
		import zlib

		import copy
		profile = copy.deepcopy(defaults)
		profile.update(self._profile)
		for key in ("print_temperature", "print_temperature2", "print_temperature3", "print_temperature4",
		            "filament_diameter", "filament_diameter2", "filament_diameter3", "filament_diameter4"):
			profile[key] = self.get(key)

		result = []
		for k, v in profile.items():
			if isinstance(v, (str, unicode)):
				result.append("{k}={v}".format(k=k, v=v.encode("utf-8")))
			else:
				result.append("{k}={v}".format(k=k, v=v))

		return base64.b64encode(zlib.compress("\b".join(result), 9))

	def replaceTagMatch(self, m):
		import time

		pre = m.group(1)
		tag = m.group(2)

		if tag == 'time':
			return pre + time.strftime('%H:%M:%S')
		if tag == 'date':
			return pre + time.strftime('%d-%m-%Y')
		if tag == 'day':
			return pre + ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][int(time.strftime('%w'))]
		if tag == 'profile_string':
			return pre + 'CURA_OCTO_PROFILE_STRING:%s' % (self.get_profile_string())

		if pre == 'F' and tag == 'max_z_speed':
			f = self.get_float("travel_speed") * 60
		elif pre == 'F' and tag in ['print_speed', 'retraction_speed', 'travel_speed', 'bottom_layer_speed', 'cool_min_feedrate']:
			f = self.get_float(tag) * 60
		elif self.get(tag):
			f = self.get(tag)
		else:
			return '%s?%s?' % (pre, tag)

		if (f % 1) == 0:
			return pre + str(int(f))

		return pre + str(f)

	def get_gcode(self, key):
		extruder_count = self.get_int("extruder_amount")

		prefix = ""
		postfix = ""

		if self.get("gcode_flavor") == GcodeFlavors.ULTIGCODE:
			if key == "end_gcode":
				return "M25 ;Stop reading from this point on.\n;CURA_PROFILE_STRING:%s\n" % (self.get_profile_string())
			return ""

		if key == "start_gcode":
			contents = self.get_gcode_template("start_gcode")

			e_steps = self.get_float("steps_per_e")
			if e_steps > 0:
				prefix += "M92 E{e_steps}\n" % (e_steps)
			temp = self.get_float("print_temperature")

			bed_temp = 0
			if self.get_boolean("has_heated_bed"):
				bed_temp = self.get_float("print_bed_temperature")
			include_bed_temp = bed_temp > 0 and not "{print_bed_temperature}" in Profile.regex_strip_comments.sub("", contents)

			if include_bed_temp:
				prefix += "M140 S{bed_temp}\n".format(bed_temp=bed_temp)

			if temp > 0 and not "{print_temperature}" in Profile.regex_strip_comments.sub("", contents):
				if extruder_count > 0:
					def temp_line(temp, extruder, template):
						t = temp
						if extruder > 0:
							print_temp = self.get_float("print_temperature%d" % (extruder + 1))
							if print_temp > 0:
								t = print_temp
						return template.format(extruder=extruder, temp=t)

					prefix_preheat = ""
					prefix_waitheat = ""
					for n in xrange(0, extruder_count):
						if n > 0:
							prefix_preheat += temp_line(temp, n, "M104 T{extruder} S{temp}\n")
						prefix_waitheat += temp_line(temp, n, "M109 T{extruder} S{temp}\n")
					prefix += prefix_preheat + prefix_waitheat + "T0\n"
				else:
					prefix += "M109 S{temp}\n".format(temp=temp)

			if include_bed_temp:
				prefix += "M190 S{bed_temp}\n".format(bed_temp=bed_temp)

		else:
			contents = self.get_gcode_template(key)

		return unicode(prefix + re.sub("(.)\{([^\}]*)\}", self.replaceTagMatch, contents).rstrip() + '\n' + postfix).strip().encode('utf-8') + '\n'

	def calculate_edge_width_and_line_count(self):
		wall_thickness = self.get_float("wall_thickness")
		nozzle_size = self._printer_profile["extruder"]["nozzleDiameter"]

		if self.get_boolean("spiralize") or self.get_boolean("follow_surface"):
			return wall_thickness, 1
		if wall_thickness < 0.01:
			return nozzle_size, 0
		if wall_thickness < nozzle_size:
			return wall_thickness, 1

		edge_width = None
		line_count = int(wall_thickness / (nozzle_size - 0.0001))
		if line_count < 1:
			edge_width = nozzle_size
			line_count = 1
		line_width = wall_thickness / line_count
		line_width_alt = wall_thickness / (line_count + 1)
		if line_width > nozzle_size * 1.5:
			return line_width_alt, line_count + 1
		if not edge_width:
			edge_width = line_width
		return edge_width, line_count

	def calculate_solid_layer_count(self):
		layer_height = self.get_float("layer_height")
		solid_thickness = self.get_float("solid_layer_thickness")
		if layer_height == 0.0:
			return 1
		import math
		return int(math.ceil(solid_thickness / (layer_height - 0.0001)))

	def calculate_minimal_extruder_count(self):
		extruder_count = self.get("extruder_amount")
		if extruder_count < 2:
			return 1
		if self.get("support") == SupportLocationTypes.NONE:
			return 1
		if self.get("support_dual_extrusion") == SupportDualTypes.SECOND:
			return 2
		return 1

	def get_pos_x(self):
		if self._posX:
			try:
				return int(float(self._posX) * 1000)
			except ValueError:
				pass

		return int(self.get_float("machine_width") / 2.0 * 1000) if not self.get_boolean("machine_center_is_zero") else 0.0

	def get_pos_y(self):
		if self._posY:
			try:
				return int(float(self._posY) * 1000)
			except ValueError:
				pass

		return int(self.get_float("machine_depth") / 2.0 * 1000) if not self.get_boolean("machine_center_is_zero") else 0.0

	def convert_to_engine(self):

		edge_width, line_count = self.calculate_edge_width_and_line_count()
		solid_layer_count = self.calculate_solid_layer_count()

		extruder_count = self.get_int("extruder_amount")
		minimal_extruder_count = self.calculate_minimal_extruder_count()

		settings = {
			"layerThickness": self.get_microns("layer_height"),
			"initialLayerThickness": self.get_microns("bottom_thickness") if self.get_float("bottom_thickness") > 0.0 else self.get_microns("layer_height"),
			"filamentDiameter": self.get_microns("filament_diameter"),
			"filamentFlow": self.get_int("filament_flow"),
			"extrusionWidth": edge_width * 1000,
			"layer0extrusionWidth": int(edge_width * self.get_float("first_layer_width_factor") / 100 * 1000),
			"insetCount": line_count,
			"downSkinCount": solid_layer_count if self.get_boolean("solid_bottom") else 0,
			"upSkinCount": solid_layer_count if self.get_boolean("solid_top") else 0,
			"infillOverlap": self.get_int("fill_overlap"),
			"initialSpeedupLayers": int(4),
			"initialLayerSpeed": self.get_int("bottom_layer_speed"),
			"printSpeed": self.get_int("print_speed"),
			"infillSpeed": self.get_int("infill_speed") if self.get_int("infill_speed") > 0 else self.get_int("print_speed"),
			"inset0Speed": self.get_int("outer_shell_speed") if self.get_int("outer_shell_speed") > 0 else self.get_int("print_speed"),
			"insetXSpeed": self.get_int("inner_shell_speed") if self.get_int("inner_shell_speed") > 0 else self.get_int("print_speed"),
			"moveSpeed": self.get_int("travel_speed"),
			"fanSpeedMin": self.get_int("fan_speed") if self.get_boolean("fan_enabled") else 0,
			"fanSpeedMax": self.get_int("fan_speed_max") if self.get_boolean("fan_enabled") else 0,
			"supportAngle": int(-1) if self.get("support") == SupportLocationTypes.NONE else self.get_int("support_angle"),
			"supportEverywhere": int(1) if self.get("support") == SupportLocationTypes.EVERYWHERE else int(0),
			"supportLineDistance": int(100 * edge_width * 1000 / self.get_float("support_fill_rate")) if self.get_float("support_fill_rate") > 0 else -1,
			"supportXYDistance": int(1000 * self.get_float("support_xy_distance")),
			"supportZDistance": int(1000 * self.get_float("support_z_distance")),
			"supportExtruder": 0 if self.get("support_dual_extrusion") == SupportDualTypes.FIRST else (1 if self.get("support_dual_extrusion") == SupportDualTypes.SECOND and minimal_extruder_count > 1 else -1),
			"retractionAmount": self.get_microns("retraction_amount") if self.get_boolean("retraction_enable") else 0,
			"retractionSpeed": self.get_int("retraction_speed"),
			"retractionMinimalDistance": self.get_microns("retraction_min_travel"),
			"retractionAmountExtruderSwitch": self.get_microns("retraction_dual_amount"),
			"retractionZHop": self.get_microns("retraction_hop"),
			"minimalExtrusionBeforeRetraction": self.get_microns("retraction_minimal_extrusion"),
			"enableCombing": 1 if self.get_boolean("retraction_combing") else 0,
			"multiVolumeOverlap": self.get_microns("overlap_dual"),
			"objectSink": max(0, self.get_microns("object_sink")),
			"minimalLayerTime": self.get_int("cool_min_layer_time"),
			"minimalFeedrate": self.get_int("cool_min_feedrate"),
			"coolHeadLift": 1 if self.get_boolean("cool_head_lift") else 0,

			# model positioning
			"posx": self.get_pos_x(),
			"posy": self.get_pos_y(),

			# gcodes
			"startCode": self.get_gcode("start_gcode"),
			"endCode": self.get_gcode("end_gcode"),
			"preSwitchExtruderCode": self.get_gcode("preSwitchExtruder_gcode"),
			"postSwitchExtruderCode": self.get_gcode("postSwitchExtruder_gcode"),

			# fixing
			"fixHorrible": 0,
		}

		for extruder in range(1, extruder_count):
			for axis in ("x", "y"):
				settings["extruderOffset[{extruder}].{axis}".format(extruder=extruder, axis=axis.upper())] = self.get("extruder_offset_{axis}{extruder}".format(extruder=extruder, axis=axis.lower()))

		fanFullHeight = self.get_microns("fan_full_height")
		settings["fanFullOnLayerNr"] = (fanFullHeight - settings["initialLayerThickness"] - 1) / settings["layerThickness"] + 1
		if settings["fanFullOnLayerNr"] < 0:
			settings["fanFullOnLayerNr"] = 0

		if self.get("support_type") == SupportTypes.LINES:
			settings["supportType"] = 1

		# infill
		if self.get_float("fill_density") == 0:
			settings["sparseInfillLineDistance"] = -1

		elif self.get_float("fill_density") == 100:
			settings["sparseInfillLineDistance"] = settings["extrusionWidth"]
			settings["downSkinCount"] = 10000
			settings["upSkinCount"] = 10000

		else:
			settings["sparseInfillLineDistance"] = int(100 * edge_width * 1000 / self.get_float("fill_density"))

		# brim/raft/skirt
		if self.get("platform_adhesion") == PlatformAdhesionTypes.BRIM:
			settings["skirtDistance"] = 0
			settings["skirtLineCount"] = self.get_int("brim_line_count")

		elif self.get("platform_adhesion") == PlatformAdhesionTypes.RAFT:
			settings["skirtDistance"] = 0
			settings["skirtLineCount"] = 0
			settings["raftMargin"] = self.get_microns("raft_margin")
			settings["raftLineSpacing"] = self.get_microns("raft_line_spacing")
			settings["raftBaseThickness"] = self.get_microns("raft_base_thickness")
			settings["raftBaseLinewidth"] = self.get_microns("raft_base_linewidth")
			settings["raftInterfaceThickness"] = self.get_microns("raft_interface_thickness")
			settings["raftInterfaceLinewidth"] = self.get_microns("raft_interface_linewidth")
			settings["raftInterfaceLineSpacing"] = self.get_microns("raft_interface_linewidth") * 2
			settings["raftAirGapLayer0"] = self.get_microns("raft_airgap")
			settings["raftBaseSpeed"] = self.get_int("bottom_layer_speed")
			settings["raftFanSpeed"] = 100
			settings["raftSurfaceThickness"] = settings["raftInterfaceThickness"]
			settings["raftSurfaceLinewidth"] = int(edge_width * 1000)
			settings["raftSurfaceLineSpacing"] = int(edge_width * 1000 * 0.9)
			settings["raftSurfaceLayers"] = self.get_int("raft_surface_layers")
			settings["raftSurfaceSpeed"] = self.get_int("bottom_layer_speed")

		else:
			settings["skirtDistance"] = self.get_microns("skirt_gap")
			settings["skirtLineCount"] = self.get_int("skirt_line_count")
			settings["skirtMinLength"] = self.get_microns("skirt_minimal_length")

		# fixing
		if self.get_boolean("fix_horrible_union_all_type_a"):
			settings["fixHorrible"] |= 0x01
		if self.get_boolean("fix_horrible_union_all_type_b"):
			settings["fixHorrible"] |= 0x02
		if self.get_boolean("fix_horrible_use_open_bits"):
			settings["fixHorrible"] |= 0x10
		if self.get_boolean("fix_horrible_extensive_stitching"):
			settings["fixHorrible"] |= 0x04

		if settings["layerThickness"] <= 0:
			settings["layerThickness"] = 1000

		# gcode flavor
		if self.get("gcode_flavor") == GcodeFlavors.ULTIGCODE:
			settings["gcodeFlavor"] = 1
		elif self.get("gcode_flavor") == GcodeFlavors.MAKERBOT:
			settings["gcodeFlavor"] = 2
		elif self.get("gcode_flavor") == GcodeFlavors.BFB:
			settings["gcodeFlavor"] = 3
		elif self.get("gcode_flavor") == GcodeFlavors.MACH3:
			settings["gcodeFlavor"] = 4
		elif self.get("gcode_flavor") == GcodeFlavors.REPRAP_VOLUME:
			settings["gcodeFlavor"] = 5

		# extras
		if self.get_boolean("spiralize"):
			settings["spiralizeMode"] = 1
		if self.get_boolean("follow_surface"):
			settings["simpleMode"] = 1

		# dual extrusion
		if self.get_boolean("wipe_tower") and extruder_count > 1:
			import math
			settings["wipeTowerSize"] = int(math.sqrt(self.get_float("wipe_tower_volume") * 1000 * 1000 * 1000 / settings["layerThickness"]))
		if self.get_boolean("ooze_shield"):
			settings["enableOozeShield"] = 1

		return settings
