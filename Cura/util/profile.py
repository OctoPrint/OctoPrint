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
	'fan_layer': '0',
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
	'add_start_end_gcode': 'True',
	'gcode_extension': 'gcode',
}
alterationDefault = {
#######################################################################################
	'start.gcode': """;Start GCode
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
}
preferencesDefaultSettings = {
	'wizardDone': 'False',
	'startMode': 'Simple',
	'lastFile': 'None',
	'machine_width': '205',
	'machine_depth': '205',
	'machine_height': '200',
	'filament_density': '1300',
	'steps_per_e': '0',
	'serial_port': 'AUTO',
	'serial_baud': '250000',
	'slicer': 'Cura (Skeinforge based)',
	'save_profile': 'False',
	'filament_cost_kg': '0',
	'filament_cost_meter': '0',
}

#########################################################
## Profile and preferences functions
#########################################################

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
		(key, value) = option.split('=', 1)
		globalProfileParser.set('profile', key, value)
	for option in alt.split('\b'):
		(key, value) = option.split('=', 1)
		globalProfileParser.set('alterations', key, value)

def getGlobalProfileString():
	global globalProfileParser
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	
	p = []
	alt = []
	for key in globalProfileParser.options('profile'):
		p.append(key + "=" + globalProfileParser.get('profile', key))
	for key in globalProfileParser.options('alterations'):
		alt.append(key + "=" + globalProfileParser.get('alterations', key))
	ret = '\b'.join(p) + '\f' + '\b'.join(alt)
	ret = base64.b64encode(zlib.compress(ret, 9))
	return ret

def getProfileSetting(name):
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

global globalPreferenceParser
globalPreferenceParser = None

def getPreferencePath():
	return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../preferences.ini"))

def getPreference(name):
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
		return str(getProfileSettingFloat(tag) * 60)
	return str(getProfileSettingFloat(tag))

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
	if filename == 'start.gcode':
		#For the start code, hack the temperature and the steps per E value into it. So the temperature is reached before the start code extrusion.
		#We also set our steps per E here, if configured.
		eSteps = float(getPreference('steps_per_e'))
		if eSteps > 0:
			prefix += 'M92 E%f\n' % (eSteps)
		temp = getProfileSettingFloat('print_temperature')
		if temp > 0:
			prefix += 'M109 S%f\n' % (temp)
	elif filename == 'replace.csv':
		#Always remove the extruder on/off M codes. These are no longer needed in 5D printing.
		prefix = 'M101\nM103\n'
	
	return prefix + re.sub("\{[^\}]*\}", replaceTagMatch, getAlterationFile(filename))

