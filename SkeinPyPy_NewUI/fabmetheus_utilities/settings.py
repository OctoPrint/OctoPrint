"""
Settings is a collection of utilities to display, read & write the settings and position widgets.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import ConfigParser
import os, sys
import types

from fabmetheus_utilities import archive

def defaultSetting(setting):
	return setting.value

def storedSetting(name):
	return lambda setting: getSetting(name, setting.value)

def getSkeinPyPyProfileInformation():
	return {
		'carve': {
			'Add_Layer_Template_to_SVG': defaultSetting,
			'Edge_Width_mm': defaultSetting,
			'Extra_Decimal_Places_float': defaultSetting,
			'Import_Coarseness_ratio': defaultSetting,
			'Layer_Height_mm': storedSetting("layer_height"),
			'Layers_From_index': defaultSetting,
			'Layers_To_index': defaultSetting,
			'Correct_Mesh': defaultSetting,
			'Unproven_Mesh': defaultSetting,
			'SVG_Viewer': defaultSetting,
		},'scale': {
			'Activate_Scale': defaultSetting,
			'XY_Plane_Scale_ratio': defaultSetting,
			'Z_Axis_Scale_ratio': defaultSetting,
			'SVG_Viewer': defaultSetting,
		},'bottom': {
			'Activate_Bottom': defaultSetting,
			'Additional_Height_over_Layer_Thickness_ratio': defaultSetting,
			'Altitude_mm': defaultSetting,
			'SVG_Viewer': defaultSetting,
		},'preface': {
			'Meta': defaultSetting,
			'Set_Positioning_to_Absolute': defaultSetting,
			'Set_Units_to_Millimeters': defaultSetting,
			'Start_at_Home': defaultSetting,
			'Turn_Extruder_Off_at_Shut_Down': defaultSetting,
			'Turn_Extruder_Off_at_Start_Up': defaultSetting,
		},'widen': {
			'Activate_Widen': defaultSetting,
		},'inset': {
			'Add_Custom_Code_for_Temperature_Reading': defaultSetting,
			'Infill_in_Direction_of_Bridge': defaultSetting,
			'Infill_Width_over_Thickness_ratio': defaultSetting,
			'Loop_Order_Choice': defaultSetting,
			'Overlap_Removal_Width_over_Perimeter_Width_ratio': defaultSetting,
			'Turn_Extruder_Heater_Off_at_Shut_Down': defaultSetting,
			'Volume_Fraction_ratio': defaultSetting,
		},'fill': {
			'Activate_Fill': defaultSetting,
			'Diaphragm_Period_layers': defaultSetting,
			'Diaphragm_Thickness_layers': defaultSetting,
			'Extra_Shells_on_Alternating_Solid_Layer_layers': defaultSetting,
			'Extra_Shells_on_Base_layers': defaultSetting,
			'Extra_Shells_on_Sparse_Layer_layers': defaultSetting,
			'Grid_Circle_Separation_over_Perimeter_Width_ratio': defaultSetting,
			'Grid_Extra_Overlap_ratio': defaultSetting,
			'Grid_Junction_Separation_Band_Height_layers': defaultSetting,
			'Grid_Junction_Separation_over_Octogon_Radius_At_End_ratio': defaultSetting,
			'Grid_Junction_Separation_over_Octogon_Radius_At_Middle_ratio': defaultSetting,
			'Infill_Begin_Rotation_degrees': defaultSetting,
			'Infill_Begin_Rotation_Repeat_layers': defaultSetting,
			'Infill_Odd_Layer_Extra_Rotation_degrees': defaultSetting,
			'Grid_Circular': defaultSetting,
			'Grid_Hexagonal': defaultSetting,
			'Grid_Rectangular': defaultSetting,
			'Line': defaultSetting,
			'Infill_Perimeter_Overlap_ratio': defaultSetting,
			'Infill_Solidity_ratio': defaultSetting,
			'Infill_Width': defaultSetting,
			'Solid_Surface_Thickness_layers': defaultSetting,
			'Start_From_Choice': defaultSetting,
			'Surrounding_Angle_degrees': defaultSetting,
			'Thread_Sequence_Choice': defaultSetting,
		},'multiply': {
			'Activate_Multiply': "True",
			'Center_X_mm': storedSetting("centerX"),
			'Center_Y_mm': storedSetting("centerY"),
			'Number_of_Columns_integer': "1",
			'Number_of_Rows_integer': "1",
			'Reverse_Sequence_every_Odd_Layer': defaultSetting,
			'Separation_over_Perimeter_Width_ratio': defaultSetting,
		},'speed': {
			'Activate_Speed': "True",
			'Add_Flow_Rate': "True",
			'Bridge_Feed_Rate_Multiplier_ratio': defaultSetting,
			'Bridge_Flow_Rate_Multiplier_ratio': defaultSetting,
			'Duty_Cyle_at_Beginning_portion': defaultSetting,
			'Duty_Cyle_at_Ending_portion': defaultSetting,
			'Feed_Rate_mm/s': storedSetting("print_speed"),
			'Flow_Rate_Setting_float': storedSetting("print_speed"),
			'Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio': defaultSetting,
			'Object_First_Layer_Feed_Rate_Perimeter_Multiplier_ratio': defaultSetting,
			'Object_First_Layer_Feed_Rate_Travel_Multiplier_ratio': defaultSetting,
			'Object_First_Layer_Flow_Rate_Infill_Multiplier_ratio': defaultSetting,
			'Object_First_Layer_Flow_Rate_Perimeter_Multiplier_ratio': defaultSetting,
			'Object_First_Layers_Amount_Of_Layers_For_Speed_Change': defaultSetting,
			'Orbital_Feed_Rate_over_Operating_Feed_Rate_ratio': defaultSetting,
			'Maximum_Z_Feed_Rate_mm/s': defaultSetting,
			'Perimeter_Feed_Rate_Multiplier_ratio': defaultSetting,
			'Perimeter_Flow_Rate_Multiplier_ratio': defaultSetting,
			'Travel_Feed_Rate_mm/s': storedSetting("travel_speed"),
		},'temperature': {
			'Activate_Temperature': defaultSetting,
			'Cooling_Rate_Celcius/second': defaultSetting,
			'Heating_Rate_Celcius/second': defaultSetting,
			'Base_Temperature_Celcius': defaultSetting,
			'Interface_Temperature_Celcius': defaultSetting,
			'Object_First_Layer_Infill_Temperature_Celcius': defaultSetting,
			'Object_First_Layer_Perimeter_Temperature_Celcius': defaultSetting,
			'Object_Next_Layers_Temperature_Celcius': defaultSetting,
			'Support_Layers_Temperature_Celcius': defaultSetting,
			'Supported_Layers_Temperature_Celcius': defaultSetting,
		},'raft': {
			'Activate_Raft': defaultSetting,
			'Add_Raft,_Elevate_Nozzle,_Orbit': defaultSetting,
			'Base_Feed_Rate_Multiplier_ratio': defaultSetting,
			'Base_Flow_Rate_Multiplier_ratio': defaultSetting,
			'Base_Infill_Density_ratio': defaultSetting,
			'Base_Layer_Thickness_over_Layer_Thickness': defaultSetting,
			'Base_Layers_integer': defaultSetting,
			'Base_Nozzle_Lift_over_Base_Layer_Thickness_ratio': defaultSetting,
			'Initial_Circling': defaultSetting,
			'Infill_Overhang_over_Extrusion_Width_ratio': defaultSetting,
			'Interface_Feed_Rate_Multiplier_ratio': defaultSetting,
			'Interface_Flow_Rate_Multiplier_ratio': defaultSetting,
			'Interface_Infill_Density_ratio': defaultSetting,
			'Interface_Layer_Thickness_over_Layer_Thickness': defaultSetting,
			'Interface_Layers_integer': defaultSetting,
			'Interface_Nozzle_Lift_over_Interface_Layer_Thickness_ratio': defaultSetting,
			'Name_of_Support_End_File': defaultSetting,
			'Name_of_Support_Start_File': defaultSetting,
			'Operating_Nozzle_Lift_over_Layer_Thickness_ratio': defaultSetting,
			'Raft_Additional_Margin_over_Length_%': defaultSetting,
			'Raft_Margin_mm': defaultSetting,
			'Support_Cross_Hatch': defaultSetting,
			'Support_Flow_Rate_over_Operating_Flow_Rate_ratio': defaultSetting,
			'Support_Gap_over_Perimeter_Extrusion_Width_ratio': defaultSetting,
			'Support_Material_Choice_': defaultSetting,
			'Support_Minimum_Angle_degrees': defaultSetting,
		},'skirt': {
			'Skirt_line_count': storedSetting("skirt_line_count"),
			'Convex': "True",
			'Gap_Width_mm': storedSetting("skirt_gap"),
			'Layers_To_index': "1",
		},'chamber': {
			'Activate_Chamber': defaultSetting,
			'Bed_Temperature_Celcius': defaultSetting,
			'Bed_Temperature_Begin_Change_Height_mm': defaultSetting,
			'Bed_Temperature_End_Change_Height_mm': defaultSetting,
			'Bed_Temperature_End_Celcius': defaultSetting,
			'Chamber_Temperature_Celcius': defaultSetting,
			'Holding_Force_bar': defaultSetting,
		},'tower': {
			'Activate_Tower': defaultSetting,
			'Extruder_Possible_Collision_Cone_Angle_degrees': defaultSetting,
			'Maximum_Tower_Height_layers': defaultSetting,
			'Tower_Start_Layer_integer': defaultSetting,
		},'jitter': {
			'Activate_Jitter': defaultSetting,
			'Jitter_Over_Perimeter_Width_ratio': defaultSetting,
		},'clip': {
			'Activate_Clip': defaultSetting,
			'Clip_Over_Perimeter_Width_ratio': defaultSetting,
			'Maximum_Connection_Distance_Over_Perimeter_Width_ratio': defaultSetting,
		},'smooth': {
			'Activate_Smooth': defaultSetting,
			'Layers_From_index': defaultSetting,
			'Maximum_Shortening_over_Width_float': defaultSetting,
		},'stretch': {
			'Activate_Stretch': defaultSetting,
			'Cross_Limit_Distance_Over_Perimeter_Width_ratio': defaultSetting,
			'Loop_Stretch_Over_Perimeter_Width_ratio': defaultSetting,
			'Path_Stretch_Over_Perimeter_Width_ratio': defaultSetting,
			'Perimeter_Inside_Stretch_Over_Perimeter_Width_ratio': defaultSetting,
			'Perimeter_Outside_Stretch_Over_Perimeter_Width_ratio': defaultSetting,
			'Stretch_From_Distance_Over_Perimeter_Width_ratio': defaultSetting,
		},'skin': {
			'Activate_Skin': defaultSetting,
			'Horizontal_Infill_Divisions_integer': defaultSetting,
			'Horizontal_Perimeter_Divisions_integer': defaultSetting,
			'Vertical_Divisions_integer': defaultSetting,
			'Hop_When_Extruding_Infill': defaultSetting,
			'Layers_From_index': defaultSetting,
		},'comb': {
			'Activate_Comb': defaultSetting,
			'Running_Jump_Space_mm': defaultSetting,
		},'cool': {
			'Activate_Cool': defaultSetting,
			'Bridge_Cool_Celcius': defaultSetting,
			'Cool_Type': defaultSetting,
			'Maximum_Cool_Celcius': defaultSetting,
			'Minimum_Layer_Time_seconds': defaultSetting,
			'Minimum_Orbital_Radius_millimeters': defaultSetting,
			'Name_of_Cool_End_File': defaultSetting,
			'Name_of_Cool_Start_File': defaultSetting,
			'Orbital_Outset_millimeters': defaultSetting,
			'Turn_Fan_On_at_Beginning': defaultSetting,
			'Turn_Fan_Off_at_Ending': defaultSetting,
		},'hop': {
			'Activate_Hop': defaultSetting,
			'Hop_Over_Layer_Thickness_ratio': defaultSetting,
			'Minimum_Hop_Angle_degrees': defaultSetting,
		},'wipe': {
			'Activate_Wipe': defaultSetting,
			'Arrival_X_mm': defaultSetting,
			'Arrival_Y_mm': defaultSetting,
			'Arrival_Z_mm': defaultSetting,
			'Departure_X_mm': defaultSetting,
			'Departure_Y_mm': defaultSetting,
			'Departure_Z_mm': defaultSetting,
			'Wipe_X_mm': defaultSetting,
			'Wipe_Y_mm': defaultSetting,
			'Wipe_Z_mm': defaultSetting,
			'Wipe_Period_layers': defaultSetting,
		},'oozebane': {
			'Activate_Oozebane': defaultSetting,
			'After_Startup_Distance_millimeters': defaultSetting,
			'Early_Shutdown_Distance_millimeters': defaultSetting,
			'Early_Startup_Distance_Constant_millimeters': defaultSetting,
			'Early_Startup_Maximum_Distance_millimeters': defaultSetting,
			'First_Early_Startup_Distance_millimeters': defaultSetting,
			'Minimum_Distance_for_Early_Startup_millimeters': defaultSetting,
			'Minimum_Distance_for_Early_Shutdown_millimeters': defaultSetting,
			'Slowdown_Startup_Steps_positive_integer': defaultSetting,
		},'dwindle': {
			'Activate_Dwindle': defaultSetting,
			'End_Rate_Multiplier_ratio': defaultSetting,
			'Pent_Up_Volume_cubic_millimeters': defaultSetting,
			'Slowdown_Steps_positive_integer': defaultSetting,
			'Slowdown_Volume_cubic_millimeters': defaultSetting,
		},'splodge': {
			'Activate_Splodge': defaultSetting,
			'Initial_Lift_over_Extra_Thickness_ratio': defaultSetting,
			'Initial_Splodge_Feed_Rate_mm/s': defaultSetting,
			'Operating_Splodge_Feed_Rate_mm/s': defaultSetting,
			'Operating_Splodge_Quantity_Length_millimeters': defaultSetting,
			'Initial_Splodge_Quantity_Length_millimeters': defaultSetting,
			'Operating_Lift_over_Extra_Thickness_ratio': defaultSetting,
		},'home': {
			'Activate_Home': defaultSetting,
			'Name_of_Home_File': defaultSetting,
		},'lash': {
			'Activate_Lash': defaultSetting,
			'X_Backlash_mm': defaultSetting,
			'Y_Backlash_mm': defaultSetting,
		},'fillet': {
			'Activate_Fillet': defaultSetting,
			'Arc_Point': defaultSetting,
			'Arc_Radius': defaultSetting,
			'Arc_Segment': defaultSetting,
			'Bevel': defaultSetting,
			'Corner_Feed_Rate_Multiplier_ratio': defaultSetting,
			'Fillet_Radius_over_Perimeter_Width_ratio': defaultSetting,
			'Reversal_Slowdown_Distance_over_Perimeter_Width_ratio': defaultSetting,
			'Use_Intermediate_Feed_Rate_in_Corners': defaultSetting,
		},'limit': {
			'Activate_Limit': defaultSetting,
			'Maximum_Initial_Feed_Rate_mm/s': defaultSetting,
		},'unpause': {
			'Activate_Unpause': defaultSetting,
			'Delay_milliseconds': defaultSetting,
			'Maximum_Speed_ratio': defaultSetting,
		},'dimension': {
			'Activate_Dimension': defaultSetting,
			'Absolute_Extrusion_Distance': defaultSetting,
			'Relative_Extrusion_Distance': defaultSetting,
			'Extruder_Retraction_Speed_mm/s': defaultSetting,
			'Filament_Diameter_mm': defaultSetting,
			'Filament_Packing_Density_ratio': defaultSetting,
			'Maximum_E_Value_before_Reset_float': defaultSetting,
			'Minimum_Travel_for_Retraction_millimeters': defaultSetting,
			'Retract_Within_Island': defaultSetting,
			'Retraction_Distance_millimeters': defaultSetting,
			'Restart_Extra_Distance_millimeters': defaultSetting,
		},'alteration': {
			'Activate_Alteration': defaultSetting,
			'Name_of_End_File': defaultSetting,
			'Name_of_Start_File': defaultSetting,
			'Remove_Redundant_Mcode': defaultSetting,
			'Replace_Variable_with_Setting': defaultSetting,
		},'export': {
			'Activate_Export': defaultSetting,
			'Add_Descriptive_Extension': defaultSetting,
			'Add_Export_Suffix': defaultSetting,
			'Add_Profile_Extension': defaultSetting,
			'Add_Timestamp_Extension': defaultSetting,
			'Also_Send_Output_To': defaultSetting,
			'Analyze_Gcode': defaultSetting,
			'Comment_Choice': defaultSetting,
			'Do_Not_Change_Output': defaultSetting,
			'binary_16_byte': defaultSetting,
			'gcode_step': defaultSetting,
			'gcode_time_segment': defaultSetting,
			'gcode_small': defaultSetting,
			'File_Extension': defaultSetting,
			'Name_of_Replace_File': defaultSetting,
			'Save_Penultimate_Gcode': defaultSetting,
		}
	}

def loadGlobalProfile(filename):
	"Read a configuration file as global config"
	global globalProfileParser
	globalProfileParser = ConfigParser.ConfigParser()
	globalProfileParser.read(filename)

def saveGlobalProfile(filename):
	globalProfileParser.write(open(filename, 'w'))

def getSetting(name, default = ""):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_option("profile", name):
		if not globalProfileParser.has_section("profile"):
			globalProfileParser.add_section("profile")
		globalProfileParser.set("profile", name, str(default))
		return default
	return globalProfileParser.get("profile", name)

def putSetting(name, value):
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalProfileParser'):
		loadGlobalProfile(getDefaultProfilePath())
	if not globalProfileParser.has_section("profile"):
		globalProfileParser.add_section("profile")
	globalProfileParser.set("profile", name, str(value))

def getDefaultProfilePath():
	return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../current_profile.ini"))

def safeConfigName(name):
	return name.replace("=", "").replace(":", "").replace(" ", "_").replace("(", "").replace(")", "")

def getReadRepository(repository):
	"Read the configuration for this 'repository'"
	
	info = getSkeinPyPyProfileInformation()
	if not info.has_key(repository.name):
		print "Warning: Plugin: " + repository.name + " missing from SkeinPyPy info"
		return repository
	info = info[repository.name]
	if not type(info) is dict:
		print "Ignoring plugin configuration: " + repository.name
		return repository
	
	#print('getReadRepository:', repository.name)
	for p in repository.preferences:
		name = safeConfigName(p.name)
		if not info.has_key(name):
			print "Setting: " + repository.name + ":" + name + " missing from SkeinPyPy info"
			continue
		if isinstance(info[name], types.FunctionType):
			p.setValueToString(str(info[name](p)))
		else:
			p.setValueToString(str(info[name]))

	return repository

def printProgress(layerIndex, procedureName):
	print ("Progress[" + procedureName + ":" + str(layerIndex+1) + "]")
	sys.stdout.flush()

def printProgressByNumber(layerIndex, numberOfLayers, procedureName):
	print ("Progress[" + procedureName + ":" + str(layerIndex+1) + ":" + str(numberOfLayers) + "]")
	sys.stdout.flush()

def getAlterationFileLines(fileName):
	'Get the alteration file line and the text lines from the fileName in the alterations directories.'
	return getAlterationLines(fileName)

def getAlterationLines(fileName):
	#print ('getAlterationLines:', fileName)
	return archive.getTextLines(getAlterationFile(fileName))

def getAlterationFile(fileName):
	"Get the file from the fileName or the lowercase fileName in the alterations directories."
	alterationsDirectory = archive.getSkeinforgePath('alterations')
	fullFilename = os.path.join(alterationsDirectory, fileName)
	if os.path.isfile(fullFilename):
		return archive.getFileText( fullFilename )
	return ''

####################################
## Configuration settings classes ##
####################################

class GeneralSetting:
	"Just a basic setting subclass"
	def getFromValue( self, name, repository, value ):
		#print('GeneralSetting:', name, repository, value )
		self.name = name
		self.value = value
		repository.preferences.append(self)
		return self

class StringSetting(GeneralSetting):
	"A class to display, read & write a string."
	def setValueToString(self, value):
		self.value = value

class BooleanSetting( GeneralSetting ):
	"A class to display, read & write a boolean."
	def setValueToString(self, value):
		self.value = str(value) == "True"

class LatentStringVar:
	"This is actually used as 'group' object for Radio buttons. (Did I mention the code is a mess?)"
	"This class doesn't have a name, and isn't really used for anything. It doesn't even know which repository it belongs to"

class Radio( BooleanSetting ):
	"A class to display, read & write a boolean with associated radio button."
	def getFromRadio( self, latentStringVar, name, repository, value ):
		"Initialize."
		#print('Radio->getFromRadio:', latentStringVar, name, repository, value )
		self.name = name
		self.value = value
		repository.preferences.append(self)
		return self

class RadioCapitalized( Radio ):
	"A class to display, read & write a boolean with associated radio button."

class RadioCapitalizedButton( Radio ):
	"A class to display, read & write a boolean with associated radio button. With an added configuration dialog button"
	"Only used for the extra export options, which we are not using, so ignore the path for now"
	def getFromPath( self, latentStringVar, name, path, repository, value ):
		"Initialize."
		#print('RadioCapitalizedButton->getFromPath:', latentStringVar, name, path, repository, value )
		self.name = name
		self.value = value
		repository.preferences.append(self)
		return self
		
class FileNameInput(StringSetting ):
	"A class to display, read & write a fileName."
	def getFromFileName( self, fileTypes, name, repository, value ):
		#print('FileNameInput:getFromFileName:', self, fileTypes, name, repository, value )
		self.name = name
		self.value = value
		return self

class HelpPage:
    "A class to open a help page."
    def getOpenFromAbsolute( self, hypertextAddress ):
        return self

class MenuButtonDisplay:
	"A class to add a combo box selection."
	def getFromName( self, name, repository ):
		#print('MenuButtonDisplay->getFromName:', name, repository )
		self.name = name
		self.value = "ERROR"
		self.radioList = []
		repository.preferences.append(self)
		return self
	
	def addRadio(self, radio, default):
		if default:
			self.value = radio.name
		self.radioList.append(radio)
	
	def setValueToString(self, value):
		valueFound = False
		for radio in self.radioList:
			if radio.name == value:
				valueFound = True;
		if valueFound:
			self.value = value
			for radio in self.radioList:
				radio.value = (radio.name == value)

class MenuRadio( BooleanSetting ):
	"A class to display, read & write a boolean with associated combo box selection."
	def getFromMenuButtonDisplay( self, menuButtonDisplay, name, repository, value ):
		"Initialize."
		#print('MenuRadio->getFromMenuButtonDisplay:', menuButtonDisplay, name, repository, value )
		self.name = name
		self.value = value
		menuButtonDisplay.addRadio(self, value)
		return self

class LabelDisplay:
	"A class to add a label."
	def getFromName( self, name, repository ):
		"Initialize."
		return self

class FloatSetting(GeneralSetting):
	"A class to display, read & write a float."
	def setValueToString(self, value):
		self.value = float(value)

class FloatSpin( FloatSetting ):
	"A class to display, read & write an float in a spin box."
	def getFromValue(self, from_, name, repository, to, value):
		"Initialize."
		self.name = name
		self.value = value
		if repository != None:
			repository.preferences.append(self)
		return self

class LabelSeparator:
	"A class to add a label and menu separator."
	def getFromRepository( self, repository ):
		"Initialize."
		return self

class IntSpin(FloatSpin):
	"A class to display, read & write an int in a spin box."
	def getSingleIncrementFromValue( self, from_, name, repository, to, value ):
		"Initialize."
		self.name = name
		self.value = value
		repository.preferences.append(self)
		return self

	def setValueToString(self, value):
		self.value = int(value)

##########################
# Helper classes
##########################

class LayerCount:
	'A class to handle the layerIndex.'
	def __init__(self):
		'Initialize.'
		self.layerIndex = -1

	def __repr__(self):
		'Get the string representation of this LayerCount.'
		return str(self.layerIndex)

	def printProgressIncrement(self, procedureName):
		'Print progress then increment layerIndex.'
		self.layerIndex += 1
		printProgress(self.layerIndex, procedureName)

