from __future__ import absolute_import
from __future__ import division
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import ConfigParser
import os
import traceback
import math

#########################################################
## Profile and preferences functions
#########################################################

#Single place to store the defaults, so we have a consistent set of default settings.
profileDefaultSettings = {
	'nozzle_size': '0.4',
	'layer_height': '0.2',
	'wall_thickness': '0.8',
	'solid_layer_thickness': '0.6',
	'fill_density': '20',
	'skirt_line_count': '1',
	'skirt_gap': '6.0',
	'print_speed': '50',
	'print_temperature': '0',
	'support': 'None',
	'filament_diameter': '2.89',
	'filament_density': '1.00',
	'machine_center_x': '100',
	'machine_center_y': '100',
	'retraction_min_travel': '5.0',
	'retraction_speed': '13.5',
	'retraction_amount': '0.0',
	'retraction_extra': '0.0',
	'travel_speed': '150',
	'max_z_speed': '1.0',
	'bottom_layer_speed': '25',
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
	for option in options.split('#'):
		(key, value) = option.split('=', 1)
		globalProfileParser.set('profile', key, value)

def getGlobalProfileString():
	global globalProfileParser
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	
	ret = []
	for key in globalProfileParser.options('profile'):
		ret.append(key + "=" + globalProfileParser.get('profile', key))
	return '#'.join(ret)

def getProfileSetting(name):
	if name in profileDefaultSettings:
		default = profileDefaultSettings[name]
	else:
		print "Missing default setting for: '" + name + "'"
		profileDefaultSettings[name] = ''
		default = ''
	
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_option('profile', name):
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
	if name in preferencesDefaultSettings:
		default = preferencesDefaultSettings[name]
	else:
		print "Missing default setting for: '" + name + "'"
		preferencesDefaultSettings[name] = ''
		default = ''

	global globalPreferenceParser
	if globalPreferenceParser == None:
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_option('preference', name):
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
	globalPreferenceParser.set('preference', name, str(value).encode("utf-8"))
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
def getCuraBasePath():
	return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def getAlterationFilePath(filename):
	return os.path.join(getCuraBasePath(), "alterations", filename)

def getAlterationFileContents(filename, allowMagicPrefix = True):
	"Get the file from the fileName or the lowercase fileName in the alterations directories."
	prefix = ''
	if allowMagicPrefix:
		if filename == 'start.gcode':
			#For the start code, hack the temperature and the steps per E value into it. So the temperature is reached before the start code extrusion.
			#We also set our steps per E here, if configured.
			eSteps = float(getPreference('steps_per_e'))
			if eSteps > 0:
				prefix += 'M92 E'+str(eSteps)+'\n'
			temp = getProfileSettingFloat('print_temperature')
			if temp > 0:
				prefix += 'M109 S'+str(temp)+'\n'
		elif filename == 'replace.csv':
			prefix = 'M101\nM103\n'
	fullFilename = getAlterationFilePath(filename)
	if os.path.isfile(fullFilename):
		file = open(fullFilename, "r")
		fileText = file.read()
		file.close()
		return prefix + fileText
	return prefix

