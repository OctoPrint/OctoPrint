from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import ConfigParser
import os
import traceback

#Single place to store the defaults, so we have a consistent set of default settings.
profileDefaultSettings = {
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
	'nozzle_size': '0.4',
	'retraction_min_travel': '5.0',
	'retraction_speed': '13.5',
	'retraction_amount': '0.0',
	'retraction_extra': '0.0',
	'travel_speed': '150',
	'max_z_speed': '1.0',
	'bottom_layer_speed': '25',
	'cool_min_layer_time': '10',
	'model_scale': '1.0',
	'flip_x': 'False',
	'flip_y': 'False',
	'flip_z': 'False',
	'model_rotate_base': '0',
	'model_multiply_x': '1',
	'model_multiply_y': '1',
	'extra_base_wall_thickness': '0.0',
	'sequence': 'Loops > Perimeter > Infill',
	'force_first_layer_sequence': 'True',
	'infill_type': 'Line',
	'solid_top': 'True',
	'fill_overlap': '15',
	'support_rate': '100',
	'support_distance': '0.5',
	'joris': 'False',
}
preferencesDefaultSettings = {
	'wizardDone': 'False',
	'lastFile': 'None',
	'machine_width': '205',
	'machine_depth': '205',
	'machine_height': '200',
	'steps_per_e': '0',
	'serial_port': 'AUTO',
	'serial_baud': '250000',
}

def getDefaultProfilePath():
	return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../current_profile.ini"))

def loadGlobalProfile(filename):
	"Read a configuration file as global config"
	global globalProfileParser
	globalProfileParser = ConfigParser.ConfigParser()
	globalProfileParser.read(filename)

def saveGlobalProfile(filename):
	globalProfileParser.write(open(filename, 'w'))

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
		print name + " not found in profile, so using default: " + str(default)
		return default
	return globalProfileParser.get('profile', name)

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
		print name + " not found in preferences, so using default: " + str(default)
		return default
	return globalPreferenceParser.get('preference', name)

def putPreference(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global globalPreferenceParser
	if globalPreferenceParser == None:
		globalPreferenceParser = ConfigParser.ConfigParser()
		globalPreferenceParser.read(getPreferencePath())
	if not globalPreferenceParser.has_section('preference'):
		globalPreferenceParser.add_section('preference')
	globalPreferenceParser.set('preference', name, str(value))
	globalPreferenceParser.write(open(getPreferencePath(), 'w'))
