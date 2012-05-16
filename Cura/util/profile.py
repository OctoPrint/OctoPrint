from __future__ import absolute_import
from __future__ import division
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import ConfigParser, os, traceback, math, re, zlib, base64

#########################################################
## Default settings when none are found.
#########################################################

#Single place to store the defaults, so we have a consistent set of default settings.
profileDefaultSettings = {
	'nozzle_size': '0.4',
	'layer_height': '0.2',
	'wall_thickness': '0.8',
	'solid_layer_thickness': '0.6',
	'fill_density': '20',
	'skirt_line_count': '1',
	'skirt_gap': '3.0',
	'print_speed': '50',
	'print_temperature': '0',
	'support': 'None',
	'filament_diameter': '2.89',
	'filament_density': '1.00',
	'machine_center_x': '100',
	'machine_center_y': '100',
	'retraction_min_travel': '5.0',
	'retraction_speed': '40.0',
	'retraction_amount': '0.0',
	'retraction_extra': '0.0',
	'travel_speed': '150',
	'max_z_speed': '3.0',
	'bottom_layer_speed': '20',
	'cool_min_layer_time': '10',
	'fan_enabled': 'True',
	'fan_layer': '1',
	'fan_speed': '100',
	'model_scale': '1.0',
	'flip_x': 'False',
	'flip_y': 'False',
	'flip_z': 'False',
	'swap_xz': 'False',
	'swap_yz': 'False',
	'model_rotate_base': '0',
	'model_multiply_x': '1',
	'model_multiply_y': '1',
	'extra_base_wall_thickness': '0.0',
	'sequence': 'Loops > Perimeter > Infill',
	'force_first_layer_sequence': 'True',
	'infill_type': 'Line',
	'solid_top': 'True',
	'fill_overlap': '15',
	'support_rate': '50',
	'support_distance': '0.5',
	'support_margin': '3.0',
	'joris': 'False',
	'enable_skin': 'False',
	'enable_raft': 'False',
	'cool_min_feedrate': '5',
	'bridge_speed': '100',
	'bridge_material_amount': '100',
	'raft_margin': '5',
	'raft_base_material_amount': '100',
	'raft_interface_material_amount': '100',
	'bottom_thickness': '0.3',
	
	'enable_dwindle': 'False',
	'dwindle_pent_up_volume': '0.4',
	'dwindle_slowdown_volume': '5.0',

	'add_start_end_gcode': 'True',
	'gcode_extension': 'gcode',
	'alternative_center': '',
	'clear_z': '0.0',
	'extruder': '0',
}
alterationDefault = {
#######################################################################################
	'start.gcode': """;Start GCode
G21        ;metric values
G90        ;absolute positioning
M107       ;start with the fan off

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
""",
#######################################################################################
	'end.gcode': """;End GCode
M104 S0                    ;extruder heat off
G91                        ;relative positioning
G1 Z+10 E-5 F{max_z_speed} ;move Z up a bit and retract filament by 5mm
G28 X0 Y0                  ;move X/Y to min endstops, so the head is out of the way
M84                        ;steppers off
G90                        ;absolute positioning
""",
#######################################################################################
	'support_start.gcode': '',
	'support_end.gcode': '',
	'cool_start.gcode': '',
	'cool_end.gcode': '',
	'replace.csv': '',
#######################################################################################
	'nextobject.gcode': """;Move to next object on the platform. clear_z is the minimal z height we need to make sure we do not hit any objects.
G92 E0
G1 Z{clear_z} E-5 F{max_z_speed}
G92 E0
G1 X{machine_center_x} Y{machine_center_y} F{travel_speed}
G1 F200 E5.5
G92 E0
G1 Z0 F{max_z_speed}
""",
#######################################################################################
	'switchExtruder.gcode': """;Switch between the current extruder and the next extruder, when printing with multiple extruders.
G1 E-5 F5000
G92 E0
T{extruder}
G1 E5 F5000
G92 E0
""",
}
preferencesDefaultSettings = {
	'wizardDone': 'False',
	'startMode': 'Simple',
	'lastFile': '',
	'machine_width': '205',
	'machine_depth': '205',
	'machine_height': '200',
	'extruder_amount': '1',
	'extruder_offset_x1': '-22.0',
	'extruder_offset_y1': '0.0',
	'extruder_offset_x2': '0.0',
	'extruder_offset_y2': '0.0',
	'extruder_offset_x3': '0.0',
	'extruder_offset_y3': '0.0',
	'filament_density': '1300',
	'steps_per_e': '0',
	'serial_port': 'AUTO',
	'serial_baud': '250000',
	'slicer': 'Cura (Skeinforge based)',
	'save_profile': 'False',
	'filament_cost_kg': '0',
	'filament_cost_meter': '0',
	
	'extruder_head_size_min_x': '70.0',
	'extruder_head_size_min_y': '18.0',
	'extruder_head_size_max_x': '18.0',
	'extruder_head_size_max_y': '35.0',
}

#########################################################
## Profile and preferences functions
#########################################################

## Profile functions
def getDefaultProfilePath():
	return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../current_profile.ini"))

def loadGlobalProfile(filename):
	#Read a configuration file as global config
	global globalProfileParser
	globalProfileParser = ConfigParser.ConfigParser()
	globalProfileParser.read(filename)

def saveGlobalProfile(filename):
	#Save the current profile to an ini file
	globalProfileParser.write(open(filename, 'w'))

def loadGlobalProfileFromString(options):
	global globalProfileParser
	globalProfileParser = ConfigParser.ConfigParser()
	globalProfileParser.add_section('profile')
	globalProfileParser.add_section('alterations')
	options = base64.b64decode(options)
	options = zlib.decompress(options)
	(profileOpts, alt) = options.split('\f', 1)
	for option in profileOpts.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			globalProfileParser.set('profile', key, value)
	for option in alt.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			globalProfileParser.set('alterations', key, value)

def getGlobalProfileString():
	global globalProfileParser
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	
	p = []
	alt = []
	tempDone = []
	if globalProfileParser.has_section('profile'):
		for key in globalProfileParser.options('profile'):
			if key in tempOverride:
				p.append(key + "=" + unicode(tempOverride[key]))
				tempDone.append(key)
			else:
				p.append(key + "=" + globalProfileParser.get('profile', key))
	if globalProfileParser.has_section('alterations'):
		for key in globalProfileParser.options('alterations'):
			if key in tempOverride:
				p.append(key + "=" + tempOverride[key])
				tempDone.append(key)
			else:
				alt.append(key + "=" + globalProfileParser.get('alterations', key))
	for key in tempOverride:
		if key not in tempDone:
			p.append(key + "=" + unicode(tempOverride[key]))
	ret = '\b'.join(p) + '\f' + '\b'.join(alt)
	ret = base64.b64encode(zlib.compress(ret, 9))
	return ret

def getProfileSetting(name):
	if name in tempOverride:
		return unicode(tempOverride[name])
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_option('profile', name):
		if name in profileDefaultSettings:
			default = profileDefaultSettings[name]
		else:
			print "Missing default setting for: '" + name + "'"
			profileDefaultSettings[name] = ''
			default = ''
		if not globalProfileParser.has_section('profile'):
			globalProfileParser.add_section('profile')
		globalProfileParser.set('profile', name, str(default))
		#print name + " not found in profile, so using default: " + str(default)
		return default
	return globalProfileParser.get('profile', name)

def getProfileSettingFloat(name):
	try:
		return float(eval(getProfileSetting(name), {}, {}))
	except (ValueError, SyntaxError):
		return 0.0

def putProfileSetting(name, value):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_section('profile'):
		globalProfileParser.add_section('profile')
	globalProfileParser.set('profile', name, str(value))

def isProfileSetting(name):
	if name in profileDefaultSettings:
		return True
	return False

## Preferences functions
global globalPreferenceParser
globalPreferenceParser = None

def getPreferencePath():
	return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../preferences.ini"))

def getPreferenceFloat(name):
	try:
		return float(eval(getPreference(name), {}, {}))
	except (ValueError, SyntaxError):
		return 0.0

def getPreference(name):
	if name in tempOverride:
		return unicode(tempOverride[name])
	global globalPreferenceParser
	if globalPreferenceParser == None:
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_option('preference', name):
		if name in preferencesDefaultSettings:
			default = preferencesDefaultSettings[name]
		else:
			print "Missing default setting for: '" + name + "'"
			preferencesDefaultSettings[name] = ''
			default = ''
		if not globalPreferenceParser.has_section('preference'):
			globalPreferenceParser.add_section('preference')
		globalPreferenceParser.set('preference', name, str(default))
		#print name + " not found in preferences, so using default: " + str(default)
		return default
	return unicode(globalPreferenceParser.get('preference', name), "utf-8")

def putPreference(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global globalPreferenceParser
	if globalPreferenceParser == None:
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_section('preference'):
		globalPreferenceParser.add_section('preference')
	globalPreferenceParser.set('preference', name, unicode(value).encode("utf-8"))
	globalPreferenceParser.write(open(getPreferencePath(), 'w'))

def isPreference(name):
	if name in preferencesDefaultSettings:
		return True
	return False

## Temp overrides for multi-extruder slicing and the project planner.
tempOverride = {}
def setTempOverride(name, value):
	tempOverride[name] = value
def resetTempOverride():
	tempOverride.clear()

#########################################################
## Utility functions to calculate common profile values
#########################################################
def calculateEdgeWidth():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')
	
	if wallThickness < nozzleSize:
		return wallThickness

	lineCount = int(wallThickness / nozzleSize)
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineWidthAlt
	return lineWidth

def calculateLineCount():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')
	
	if wallThickness < nozzleSize:
		return 1

	lineCount = int(wallThickness / nozzleSize + 0.0001)
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineCount + 1
	return lineCount

def calculateSolidLayerCount():
	layerHeight = getProfileSettingFloat('layer_height')
	solidThickness = getProfileSettingFloat('solid_layer_thickness')
	return int(math.ceil(solidThickness / layerHeight - 0.0001))

#########################################################
## Alteration file functions
#########################################################
def replaceTagMatch(m):
	tag = m.group(0)[1:-1]
	if tag in ['print_speed', 'retraction_speed', 'travel_speed', 'max_z_speed', 'bottom_layer_speed', 'cool_min_feedrate']:
		f = getProfileSettingFloat(tag) * 60
	elif isProfileSetting(tag):
		f = getProfileSettingFloat(tag)
	elif isPreference(tag):
		f = getProfileSettingFloat(tag)
	else:
		return tag
	if (f % 1) == 0:
		return str(int(f))
	return str(f)

### Get aleration raw contents. (Used internally in Cura)
def getAlterationFile(filename):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	
	if not globalProfileParser.has_option('alterations', filename):
		if filename in alterationDefault:
			default = alterationDefault[filename]
		else:
			print "Missing default alteration for: '" + filename + "'"
			alterationDefault[filename] = ''
			default = ''
		if not globalProfileParser.has_section('alterations'):
			globalProfileParser.add_section('alterations')
		#print "Using default for: %s" % (filename)
		globalProfileParser.set('alterations', filename, default)
	return unicode(globalProfileParser.get('alterations', filename), "utf-8")

def setAlterationFile(filename, value):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_section('alterations'):
		globalProfileParser.add_section('alterations')
	globalProfileParser.set('alterations', filename, value.encode("utf-8"))
	saveGlobalProfile(getDefaultProfilePath())

### Get the alteration file for output. (Used by Skeinforge)
def getAlterationFileContents(filename):
	prefix = ''
	alterationContents = getAlterationFile(filename)
	if filename == 'start.gcode':
		#For the start code, hack the temperature and the steps per E value into it. So the temperature is reached before the start code extrusion.
		#We also set our steps per E here, if configured.
		eSteps = getPreferenceFloat('steps_per_e')
		if eSteps > 0:
			prefix += 'M92 E%f\n' % (eSteps)
		temp = getProfileSettingFloat('print_temperature')
		if temp > 0 and not '{print_temperature}' in alterationContents:
			prefix += 'M109 S%f\n' % (temp)
	elif filename == 'replace.csv':
		#Always remove the extruder on/off M codes. These are no longer needed in 5D printing.
		prefix = 'M101\nM103\n'
	
	return unicode(prefix + re.sub("\{[^\}]*\}", replaceTagMatch, alterationContents).rstrip() + '\n').encode('utf-8')

