"""
Settings is a collection of utilities to display, read & write the settings and position widgets.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import ConfigParser
import os, sys

def getSkeinPyPyConfigInformation():
	return {
		'carve': {
			'Add_Layer_Template_to_SVG': 'ignore',
			'Edge_Width_mm': 'save',
			'Extra_Decimal_Places_float': 'ignore',
			'Import_Coarseness_ratio': 'ignore',
			'Layer_Height_mm': 'save',
			'Layers_From_index': 'ignore',
			'Layers_To_index': 'ignore',
			'Correct_Mesh': 'ignore',
			'Unproven_Mesh': 'ignore',
			'SVG_Viewer': 'ignore',
		},'scale': {
			'Activate_Scale': 'ignore',
			'XY_Plane_Scale_ratio': 'ignore',
			'Z_Axis_Scale_ratio': 'ignore',
			'SVG_Viewer': 'ignore',
		},'bottom': {
			'Activate_Bottom': 'ignore',
			'Additional_Height_over_Layer_Thickness_ratio': 'ignore',
			'Altitude_mm': 'ignore',
			'SVG_Viewer': 'ignore',
		},'preface': {
			'Meta': 'ignore',
			'Set_Positioning_to_Absolute': 'ignore',
			'Set_Units_to_Millimeters': 'ignore',
			'Start_at_Home': 'ignore',
			'Turn_Extruder_Off_at_Shut_Down': 'ignore',
			'Turn_Extruder_Off_at_Start_Up': 'ignore',
		},'widen': {
			'Activate_Widen': 'save',
		},'inset': {
			'Add_Custom_Code_for_Temperature_Reading': 'ignore',
			'Infill_in_Direction_of_Bridge': 'ignore',
			'Infill_Width_over_Thickness_ratio': 'ignore',
			'Loop_Order_Choice': 'ignore',
			'Overlap_Removal_Width_over_Perimeter_Width_ratio': 'ignore',
			'Turn_Extruder_Heater_Off_at_Shut_Down': 'ignore',
			'Volume_Fraction_ratio': 'ignore',
		},'fill': {
			'Activate_Fill': 'save',
			'Diaphragm_Period_layers': 'save',
			'Diaphragm_Thickness_layers': 'save',
			'Extra_Shells_on_Alternating_Solid_Layer_layers': 'save',
			'Extra_Shells_on_Base_layers': 'save',
			'Extra_Shells_on_Sparse_Layer_layers': 'save',
			'Grid_Circle_Separation_over_Perimeter_Width_ratio': 'ignore',
			'Grid_Extra_Overlap_ratio': 'ignore',
			'Grid_Junction_Separation_Band_Height_layers': 'ignore',
			'Grid_Junction_Separation_over_Octogon_Radius_At_End_ratio': 'ignore',
			'Grid_Junction_Separation_over_Octogon_Radius_At_Middle_ratio': 'ignore',
			'Infill_Begin_Rotation_degrees': 'ignore',
			'Infill_Begin_Rotation_Repeat_layers': 'ignore',
			'Infill_Odd_Layer_Extra_Rotation_degrees': 'ignore',
			'Grid_Circular': 'ignore',
			'Grid_Hexagonal': 'ignore',
			'Grid_Rectangular': 'ignore',
			'Line': 'ignore',
			'Infill_Perimeter_Overlap_ratio': 'save',
			'Infill_Solidity_ratio': 'save',
			'Infill_Width': 'use:carve:Edge_Width_mm',
			'Solid_Surface_Thickness_layers': 'save',
			'Start_From_Choice': 'ignore',
			'Surrounding_Angle_degrees': 'ignore',
			'Thread_Sequence_Choice': 'save',
		},'multiply': {
			'Activate_Multiply': 'ignore',
			'Center_X_mm': 'save',
			'Center_Y_mm': 'save',
			'Number_of_Columns_integer': 'save',
			'Number_of_Rows_integer': 'save',
			'Reverse_Sequence_every_Odd_Layer': 'ignore',
			'Separation_over_Perimeter_Width_ratio': 'save',
		},'speed': {
			'Activate_Speed': 'ignore',
			'Add_Flow_Rate': 'ignore',
			'Bridge_Feed_Rate_Multiplier_ratio': 'ignore',
			'Bridge_Flow_Rate_Multiplier_ratio': 'ignore',
			'Duty_Cyle_at_Beginning_portion': 'ignore',
			'Duty_Cyle_at_Ending_portion': 'ignore',
			'Feed_Rate_mm/s': 'save',
			'Flow_Rate_Setting_float': 'use:speed:Feed_Rate_mm/s',
			'Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio': 'save',
			'Object_First_Layer_Feed_Rate_Perimeter_Multiplier_ratio': 'use:speed:Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio',
			'Object_First_Layer_Feed_Rate_Travel_Multiplier_ratio': 'use:speed:Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio',
			'Object_First_Layer_Flow_Rate_Infill_Multiplier_ratio': 'use:speed:Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio',
			'Object_First_Layer_Flow_Rate_Perimeter_Multiplier_ratio': 'use:speed:Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio',
			'Object_First_Layers_Amount_Of_Layers_For_Speed_Change': 'save',
			'Orbital_Feed_Rate_over_Operating_Feed_Rate_ratio': 'ignore',
			'Maximum_Z_Feed_Rate_mm/s': 'save',
			'Perimeter_Feed_Rate_Multiplier_ratio': 'ignore',
			'Perimeter_Flow_Rate_Multiplier_ratio': 'ignore',
			'Travel_Feed_Rate_mm/s': 'save',
		},'temperature': {
			'Activate_Temperature': 'ignore',
			'Cooling_Rate_Celcius/second': 'ignore',
			'Heating_Rate_Celcius/second': 'ignore',
			'Base_Temperature_Celcius': 'ignore',
			'Interface_Temperature_Celcius': 'ignore',
			'Object_First_Layer_Infill_Temperature_Celcius': 'ignore',
			'Object_First_Layer_Perimeter_Temperature_Celcius': 'ignore',
			'Object_Next_Layers_Temperature_Celcius': 'ignore',
			'Support_Layers_Temperature_Celcius': 'ignore',
			'Supported_Layers_Temperature_Celcius': 'ignore',
		},'raft': {
			'Activate_Raft': 'ignore',
			'Add_Raft,_Elevate_Nozzle,_Orbit': 'ignore',
			'Base_Feed_Rate_Multiplier_ratio': 'ignore',
			'Base_Flow_Rate_Multiplier_ratio': 'ignore',
			'Base_Infill_Density_ratio': 'ignore',
			'Base_Layer_Thickness_over_Layer_Thickness': 'ignore',
			'Base_Layers_integer': 'ignore',
			'Base_Nozzle_Lift_over_Base_Layer_Thickness_ratio': 'ignore',
			'Initial_Circling': 'ignore',
			'Infill_Overhang_over_Extrusion_Width_ratio': 'ignore',
			'Interface_Feed_Rate_Multiplier_ratio': 'ignore',
			'Interface_Flow_Rate_Multiplier_ratio': 'ignore',
			'Interface_Infill_Density_ratio': 'ignore',
			'Interface_Layer_Thickness_over_Layer_Thickness': 'ignore',
			'Interface_Layers_integer': 'ignore',
			'Interface_Nozzle_Lift_over_Interface_Layer_Thickness_ratio': 'ignore',
			'Name_of_Support_End_File': 'ignore',
			'Name_of_Support_Start_File': 'ignore',
			'Operating_Nozzle_Lift_over_Layer_Thickness_ratio': 'ignore',
			'Raft_Additional_Margin_over_Length_%': 'ignore',
			'Raft_Margin_mm': 'ignore',
			'Support_Cross_Hatch': 'save',
			'Support_Flow_Rate_over_Operating_Flow_Rate_ratio': 'save',
			'Support_Gap_over_Perimeter_Extrusion_Width_ratio': 'save',
			'Support_Material_Choice_': 'save',
			'Support_Minimum_Angle_degrees': 'save',
		},'skirt': {
			'Activate_Skirt': 'save',
			'Convex': 'ignore',
			'Gap_Width_mm': 'save',
			'Layers_To_index': 'ignore',
		},'chamber': {
			'Activate_Chamber': 'ignore',
			'Bed_Temperature_Celcius': 'ignore',
			'Bed_Temperature_Begin_Change_Height_mm': 'ignore',
			'Bed_Temperature_End_Change_Height_mm': 'ignore',
			'Bed_Temperature_End_Celcius': 'ignore',
			'Chamber_Temperature_Celcius': 'ignore',
			'Holding_Force_bar': 'ignore',
		},'tower': {
			'Activate_Tower': 'ignore',
			'Extruder_Possible_Collision_Cone_Angle_degrees': 'ignore',
			'Maximum_Tower_Height_layers': 'ignore',
			'Tower_Start_Layer_integer': 'ignore',
		},'jitter': {
			'Activate_Jitter': 'ignore',
			'Jitter_Over_Perimeter_Width_ratio': 'ignore',
		},'clip': {
			'Activate_Clip': 'ignore',
			'Clip_Over_Perimeter_Width_ratio': 'ignore',
			'Maximum_Connection_Distance_Over_Perimeter_Width_ratio': 'ignore',
		},'smooth': {
			'Activate_Smooth': 'ignore',
			'Layers_From_index': 'ignore',
			'Maximum_Shortening_over_Width_float': 'ignore',
		},'stretch': {
			'Activate_Stretch': 'ignore',
			'Cross_Limit_Distance_Over_Perimeter_Width_ratio': 'ignore',
			'Loop_Stretch_Over_Perimeter_Width_ratio': 'ignore',
			'Path_Stretch_Over_Perimeter_Width_ratio': 'ignore',
			'Perimeter_Inside_Stretch_Over_Perimeter_Width_ratio': 'ignore',
			'Perimeter_Outside_Stretch_Over_Perimeter_Width_ratio': 'ignore',
			'Stretch_From_Distance_Over_Perimeter_Width_ratio': 'ignore',
		},'skin': {
			'Activate_Skin': 'ignore',
			'Horizontal_Infill_Divisions_integer': 'ignore',
			'Horizontal_Perimeter_Divisions_integer': 'ignore',
			'Vertical_Divisions_integer': 'ignore',
			'Hop_When_Extruding_Infill': 'ignore',
			'Layers_From_index': 'ignore',
		},'comb': {
			'Activate_Comb': 'ignore',
			'Running_Jump_Space_mm': 'ignore',
		},'cool': {
			'Activate_Cool': 'save',
			'Bridge_Cool_Celcius': 'ignore',
			'Cool_Type': 'save',
			'Maximum_Cool_Celcius': 'ignore',
			'Minimum_Layer_Time_seconds': 'save',
			'Minimum_Orbital_Radius_millimeters': 'ignore',
			'Name_of_Cool_End_File': 'ignore',
			'Name_of_Cool_Start_File': 'ignore',
			'Orbital_Outset_millimeters': 'ignore',
			'Turn_Fan_On_at_Beginning': 'ignore',
			'Turn_Fan_Off_at_Ending': 'ignore',
		},'hop': {
			'Activate_Hop': 'ignore',
			'Hop_Over_Layer_Thickness_ratio': 'ignore',
			'Minimum_Hop_Angle_degrees': 'ignore',
		},'wipe': {
			'Activate_Wipe': 'ignore',
			'Arrival_X_mm': 'ignore',
			'Arrival_Y_mm': 'ignore',
			'Arrival_Z_mm': 'ignore',
			'Departure_X_mm': 'ignore',
			'Departure_Y_mm': 'ignore',
			'Departure_Z_mm': 'ignore',
			'Wipe_X_mm': 'ignore',
			'Wipe_Y_mm': 'ignore',
			'Wipe_Z_mm': 'ignore',
			'Wipe_Period_layers': 'ignore',
		},'oozebane': {
			'Activate_Oozebane': 'ignore',
			'After_Startup_Distance_millimeters': 'ignore',
			'Early_Shutdown_Distance_millimeters': 'ignore',
			'Early_Startup_Distance_Constant_millimeters': 'ignore',
			'Early_Startup_Maximum_Distance_millimeters': 'ignore',
			'First_Early_Startup_Distance_millimeters': 'ignore',
			'Minimum_Distance_for_Early_Startup_millimeters': 'ignore',
			'Minimum_Distance_for_Early_Shutdown_millimeters': 'ignore',
			'Slowdown_Startup_Steps_positive_integer': 'ignore',
		},'dwindle': {
			'Activate_Dwindle': 'ignore',
			'End_Rate_Multiplier_ratio': 'ignore',
			'Pent_Up_Volume_cubic_millimeters': 'ignore',
			'Slowdown_Steps_positive_integer': 'ignore',
			'Slowdown_Volume_cubic_millimeters': 'ignore',
		},'splodge': {
			'Activate_Splodge': 'ignore',
			'Initial_Lift_over_Extra_Thickness_ratio': 'ignore',
			'Initial_Splodge_Feed_Rate_mm/s': 'ignore',
			'Operating_Splodge_Feed_Rate_mm/s': 'ignore',
			'Operating_Splodge_Quantity_Length_millimeters': 'ignore',
			'Initial_Splodge_Quantity_Length_millimeters': 'ignore',
			'Operating_Lift_over_Extra_Thickness_ratio': 'ignore',
		},'home': {
			'Activate_Home': 'ignore',
			'Name_of_Home_File': 'ignore',
		},'lash': {
			'Activate_Lash': 'ignore',
			'X_Backlash_mm': 'ignore',
			'Y_Backlash_mm': 'ignore',
		},'fillet': {
			'Activate_Fillet': 'ignore',
			'Arc_Point': 'ignore',
			'Arc_Radius': 'ignore',
			'Arc_Segment': 'ignore',
			'Bevel': 'ignore',
			'Corner_Feed_Rate_Multiplier_ratio': 'ignore',
			'Fillet_Radius_over_Perimeter_Width_ratio': 'ignore',
			'Reversal_Slowdown_Distance_over_Perimeter_Width_ratio': 'ignore',
			'Use_Intermediate_Feed_Rate_in_Corners': 'ignore',
		},'limit': {
			'Activate_Limit': 'ignore',
			'Maximum_Initial_Feed_Rate_mm/s': 'ignore',
		},'unpause': {
			'Activate_Unpause': 'ignore',
			'Delay_milliseconds': 'ignore',
			'Maximum_Speed_ratio': 'ignore',
		},'dimension': {
			'Activate_Dimension': 'ignore',
			'Absolute_Extrusion_Distance': 'ignore',
			'Relative_Extrusion_Distance': 'ignore',
			'Extruder_Retraction_Speed_mm/s': 'save',
			'Filament_Diameter_mm': 'save',
			'Filament_Packing_Density_ratio': 'save',
			'Maximum_E_Value_before_Reset_float': 'ignore',
			'Minimum_Travel_for_Retraction_millimeters': 'save',
			'Retract_Within_Island': 'save',
			'Retraction_Distance_millimeters': 'save',
			'Restart_Extra_Distance_millimeters': 'save',
		},'alteration': {
			'Activate_Alteration': 'ignore',
			'Name_of_End_File': 'ignore',
			'Name_of_Start_File': 'ignore',
			'Remove_Redundant_Mcode': 'ignore',
			'Replace_Variable_with_Setting': 'ignore',
		},'export': {
			'Activate_Export': 'ignore',
			'Add_Descriptive_Extension': 'ignore',
			'Add_Export_Suffix': 'ignore',
			'Add_Profile_Extension': 'ignore',
			'Add_Timestamp_Extension': 'ignore',
			'Also_Send_Output_To': 'ignore',
			'Analyze_Gcode': 'ignore',
			'Comment_Choice': 'ignore',
			'Do_Not_Change_Output': 'ignore',
			'binary_16_byte': 'ignore',
			'gcode_step': 'ignore',
			'gcode_time_segment': 'ignore',
			'gcode_small': 'ignore',
			'File_Extension': 'ignore',
			'Name_of_Replace_File': 'ignore',
			'Save_Penultimate_Gcode': 'ignore',
		}
	}

def loadGlobalConfig(filename):
	"Read a configuration file as global config"
	global globalConfigParser
	globalConfigParser = ConfigParser.ConfigParser()
	globalConfigParser.read(filename)

def saveGlobalConfig(filename):
	globalConfigParser.write(open(filename, 'w'))

def getDefaultConfigPath():
	return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../current_config.ini"))

def safeConfigName(name):
	return name.replace("=", "").replace(":", "").replace(" ", "_").replace("(", "").replace(")", "")

def getReadRepository(repository):
	"Read the configuration for this 'repository'"
	
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalConfigParser'):
		loadGlobalConfig(getDefaultConfigPath())
	
	info = getSkeinPyPyConfigInformation()
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
		#ignore this setting, use the default, always
		if info[name] == 'ignore':
			continue
		#Load this setting from another value.
		if info[name][0:4] == "use:":
			i = info[name][4:].split(':')
			p.setValueToString(globalConfigParser.get(i[0], i[1]))
			continue
		
		try:
			p.setValueToString(globalConfigParser.get(repository.name, name))
		except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
			#Value not in configuration, add it.
			try:
				globalConfigParser.add_section(repository.name)
			except:
				pass
			globalConfigParser.set(repository.name, name, str(p.value))
			#saveGlobalConfig(getDefaultConfigPath())
		#print "============" + str(p) + "|" + p.name + "|" + str(p.value) + "|" + str(type(p.value))
	return repository

def storeRepository(repository):
	"Store the configuration for this 'repository'"
	#Check if we have a configuration file loaded, else load the default.
	if not globals().has_key('globalConfigParser'):
		loadGlobalConfig(getDefaultConfigPath())
	
	info = getSkeinPyPyConfigInformation()
	if not info.has_key(repository.name):
		print "Warning: Plugin: " + repository.name + " missing from SkeinPyPy info"
		return repository
	info = info[repository.name]
	if not type(info) is dict:
		print "Ignoring plugin configuration: " + repository.name
		return repository
	
	for p in repository.preferences:
		name = safeConfigName(p.name)
		if not info.has_key(name):
			print "Setting: " + repository.name + ":" + name + " missing from SkeinPyPy info"
			continue

		if info[name] == "save":
			try:
				globalConfigParser.add_section(repository.name)
			except:
				pass
			globalConfigParser.set(repository.name, name, str(p.value))
	return repository

def printProgress(layerIndex, procedureName):
	print ("Progress[" + procedureName + ":" + str(layerIndex) + "]")
	sys.stdout.flush()

def printProgressByNumber(layerIndex, numberOfLayers, procedureName):
	print ("Progress[" + procedureName + ":" + str(layerIndex) + ":" + str(numberOfLayers) + "]")
	sys.stdout.flush()

def getAlterationFileLines(fileName):
	'Get the alteration file line and the text lines from the fileName in the alterations directories.'
	print ('getAlterationFileLines:', fileName)
	return []

def getAlterationLines(fileName):
	print ('getAlterationLines:', fileName)
	return []

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

