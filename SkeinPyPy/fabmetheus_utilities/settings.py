"""
Settings is a collection of utilities to display, read & write the settings and position widgets.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

import os, sys
import types, math

from newui import profile
from fabmetheus_utilities import archive

def DEFSET(setting):
	return setting.value

def storedSetting(name):
	return lambda setting: profile.getProfileSetting(name)
def storedPreference(name):
	return lambda setting: profile.getPreference(name)

def ifSettingAboveZero(name):
	return lambda setting: float(profile.getProfileSetting(name)) > 0

def ifSettingIs(name, value):
	return lambda setting: profile.getProfileSetting(name) == value

def raftLayerCount(setting):
	if profile.getProfileSetting('enable_raft') == "True":
		return '1'
	return '0'

def storedPercentSetting(name):
	return lambda setting: float(profile.getProfileSetting(name)) / 100

def calculateEdgeWidth(setting):
	wallThickness = float(profile.getProfileSetting('wall_thickness'))
	nozzleSize = float(profile.getPreference('nozzle_size'))
	
	if wallThickness < nozzleSize:
		return wallThickness

	lineCount = int(wallThickness / nozzleSize)
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineWidthAlt
	return lineWidth

def calculateShells(setting):
	return calculateShellsImp(float(profile.getProfileSetting('wall_thickness')))

def calculateShellsBase(setting):
	return calculateShellsImp(float(profile.getProfileSetting('wall_thickness')) + float(profile.getProfileSetting('extra_base_wall_thickness')))

def calculateShellsImp(wallThickness):
	nozzleSize = float(profile.getPreference('nozzle_size'))
	
	if wallThickness < nozzleSize:
		return 0

	lineCount = int(wallThickness / nozzleSize + 0.0001)
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineCount
	return lineCount - 1

def calculateSolidLayerCount(setting):
	layerHeight = float(profile.getProfileSetting('layer_height'))
	solidThickness = float(profile.getProfileSetting('solid_layer_thickness'))
	ret = int(math.ceil(solidThickness / layerHeight - 0.0001))
	return ret

def firstLayerSpeedRatio(setting):
	bottomSpeed = float(profile.getProfileSetting('bottom_layer_speed'))
	speed = float(profile.getProfileSetting('print_speed'))
	return bottomSpeed/speed

def calcSupportDistanceRatio(setting):
	edgeWidth = calculateEdgeWidth(setting)
	distance = float(profile.getProfileSetting('support_distance'))
	return distance / edgeWidth

def getSkeinPyPyProfileInformation():
	return {
		'carve': {
			'Add_Layer_Template_to_SVG': DEFSET,
			'Edge_Width_mm': calculateEdgeWidth,
			'Extra_Decimal_Places_float': DEFSET,
			'Import_Coarseness_ratio': DEFSET,
			'Layer_Height_mm': storedSetting("layer_height"),
			'Layers_From_index': DEFSET,
			'Layers_To_index': DEFSET,
			'Correct_Mesh': DEFSET,
			'Unproven_Mesh': DEFSET,
			'SVG_Viewer': DEFSET,
			'FlipX': storedSetting("flip_x"),
			'FlipY': storedSetting("flip_y"),
			'FlipZ': storedSetting("flip_z"),
			'Scale': storedSetting("model_scale"),
			'Rotate': storedSetting("model_rotate_base"),
		},'scale': {
			'Activate_Scale': "False",
			'XY_Plane_Scale_ratio': DEFSET,
			'Z_Axis_Scale_ratio': DEFSET,
			'SVG_Viewer': DEFSET,
		},'bottom': {
			'Activate_Bottom': DEFSET,
			'Additional_Height_over_Layer_Thickness_ratio': DEFSET,
			'Altitude_mm': DEFSET,
			'SVG_Viewer': DEFSET,
		},'preface': {
			'Meta': DEFSET,
			'Set_Positioning_to_Absolute': DEFSET,
			'Set_Units_to_Millimeters': DEFSET,
			'Start_at_Home': DEFSET,
			'Turn_Extruder_Off_at_Shut_Down': DEFSET,
			'Turn_Extruder_Off_at_Start_Up': DEFSET,
		},'widen': {
			'Activate_Widen': DEFSET,
		},'inset': {
			'Add_Custom_Code_for_Temperature_Reading': DEFSET,
			'Infill_in_Direction_of_Bridge': "True",
			'Infill_Width_over_Thickness_ratio': DEFSET,
			'Loop_Order_Choice': DEFSET,
			'Overlap_Removal_Width_over_Perimeter_Width_ratio': DEFSET,
			'Turn_Extruder_Heater_Off_at_Shut_Down': DEFSET,
			'Volume_Fraction_ratio': DEFSET,
		},'fill': {
			'Activate_Fill': "True",
			'Solid_Surface_Top': storedSetting("solid_top"),
			'Override_First_Layer_Sequence': storedSetting("force_first_layer_sequence"),
			'Diaphragm_Period_layers': DEFSET,
			'Diaphragm_Thickness_layers': DEFSET,
			'Extra_Shells_on_Alternating_Solid_Layer_layers': calculateShells,
			'Extra_Shells_on_Base_layers': calculateShellsBase,
			'Extra_Shells_on_Sparse_Layer_layers': calculateShells,
			'Grid_Circle_Separation_over_Perimeter_Width_ratio': DEFSET,
			'Grid_Extra_Overlap_ratio': DEFSET,
			'Grid_Junction_Separation_Band_Height_layers': DEFSET,
			'Grid_Junction_Separation_over_Octogon_Radius_At_End_ratio': DEFSET,
			'Grid_Junction_Separation_over_Octogon_Radius_At_Middle_ratio': DEFSET,
			'Infill_Begin_Rotation_degrees': DEFSET,
			'Infill_Begin_Rotation_Repeat_layers': DEFSET,
			'Infill_Odd_Layer_Extra_Rotation_degrees': DEFSET,
			'Grid_Circular': ifSettingIs('infill_type', 'Grid Circular'),
			'Grid_Hexagonal': ifSettingIs('infill_type', 'Grid Hexagonal'),
			'Grid_Rectangular': ifSettingIs('infill_type', 'Grid Rectangular'),
			'Line': ifSettingIs('infill_type', 'Line'),
			'Infill_Perimeter_Overlap_ratio': storedPercentSetting('fill_overlap'),
			'Infill_Solidity_ratio': storedPercentSetting('fill_density'),
			'Infill_Width': storedPreference("nozzle_size"),
			'Solid_Surface_Thickness_layers': calculateSolidLayerCount,
			'Start_From_Choice': DEFSET,
			'Surrounding_Angle_degrees': DEFSET,
			'Thread_Sequence_Choice': storedSetting('sequence'),
		},'multiply': {
			'Activate_Multiply': "True",
			'Center_X_mm': storedSetting("machine_center_x"),
			'Center_Y_mm': storedSetting("machine_center_y"),
			'Number_of_Columns_integer': storedSetting('model_multiply_x'),
			'Number_of_Rows_integer': storedSetting('model_multiply_y'),
			'Reverse_Sequence_every_Odd_Layer': DEFSET,
			'Separation_over_Perimeter_Width_ratio': DEFSET,
		},'speed': {
			'Activate_Speed': "True",
			'Add_Flow_Rate': "True",
			'Bridge_Feed_Rate_Multiplier_ratio': storedPercentSetting('bridge_speed'),
			'Bridge_Flow_Rate_Multiplier_ratio': storedPercentSetting('bridge_material_amount'),
			'Duty_Cyle_at_Beginning_portion': DEFSET,
			'Duty_Cyle_at_Ending_portion': DEFSET,
			'Feed_Rate_mm/s': storedSetting("print_speed"),
			'Flow_Rate_Setting_float': storedSetting("print_speed"),
			'Object_First_Layer_Feed_Rate_Infill_Multiplier_ratio': firstLayerSpeedRatio,
			'Object_First_Layer_Feed_Rate_Perimeter_Multiplier_ratio': firstLayerSpeedRatio,
			'Object_First_Layer_Feed_Rate_Travel_Multiplier_ratio': firstLayerSpeedRatio,
			'Object_First_Layer_Flow_Rate_Infill_Multiplier_ratio': firstLayerSpeedRatio,
			'Object_First_Layer_Flow_Rate_Perimeter_Multiplier_ratio': firstLayerSpeedRatio,
			'Object_First_Layers_Amount_Of_Layers_For_Speed_Change': DEFSET,
			'Orbital_Feed_Rate_over_Operating_Feed_Rate_ratio': DEFSET,
			'Maximum_Z_Feed_Rate_mm/s': DEFSET,
			'Perimeter_Feed_Rate_Multiplier_ratio': DEFSET,
			'Perimeter_Flow_Rate_Multiplier_ratio': DEFSET,
			'Travel_Feed_Rate_mm/s': storedSetting("travel_speed"),
		},'temperature': {
			'Activate_Temperature': DEFSET,#ifSettingAboveZero('print_temperature'),
			'Cooling_Rate_Celcius/second': DEFSET,
			'Heating_Rate_Celcius/second': DEFSET,
			'Base_Temperature_Celcius': DEFSET,#storedSetting("print_temperature"),
			'Interface_Temperature_Celcius': DEFSET,#storedSetting("print_temperature"),
			'Object_First_Layer_Infill_Temperature_Celcius': DEFSET,#storedSetting("print_temperature"),
			'Object_First_Layer_Perimeter_Temperature_Celcius': DEFSET,#storedSetting("print_temperature"),
			'Object_Next_Layers_Temperature_Celcius': DEFSET,#storedSetting("print_temperature"),
			'Support_Layers_Temperature_Celcius': DEFSET,#storedSetting("print_temperature"),
			'Supported_Layers_Temperature_Celcius': DEFSET,#storedSetting("print_temperature"),
		},'raft': {
			'Activate_Raft': "True",
			'Add_Raft,_Elevate_Nozzle,_Orbit': DEFSET,
			'Base_Feed_Rate_Multiplier_ratio': DEFSET,
			'Base_Flow_Rate_Multiplier_ratio': storedPercentSetting('raft_base_material_amount'),
			'Base_Infill_Density_ratio': DEFSET,
			'Base_Layer_Thickness_over_Layer_Thickness': DEFSET,
			'Base_Layers_integer': raftLayerCount,
			'Base_Nozzle_Lift_over_Base_Layer_Thickness_ratio': DEFSET,
			'Initial_Circling': DEFSET,
			'Infill_Overhang_over_Extrusion_Width_ratio': DEFSET,
			'Interface_Feed_Rate_Multiplier_ratio': DEFSET,
			'Interface_Flow_Rate_Multiplier_ratio': storedPercentSetting('raft_interface_material_amount'),
			'Interface_Infill_Density_ratio': DEFSET,
			'Interface_Layer_Thickness_over_Layer_Thickness': DEFSET,
			'Interface_Layers_integer': raftLayerCount,
			'Interface_Nozzle_Lift_over_Interface_Layer_Thickness_ratio': DEFSET,
			'Name_of_Support_End_File': DEFSET,
			'Name_of_Support_Start_File': DEFSET,
			'Operating_Nozzle_Lift_over_Layer_Thickness_ratio': DEFSET,
			'Raft_Additional_Margin_over_Length_%': DEFSET,
			'Raft_Margin_mm': storedSetting('raft_margin'),
			'Support_Cross_Hatch': 'False',
			'Support_Flow_Rate_over_Operating_Flow_Rate_ratio': storedPercentSetting('support_rate'),
			'Support_Gap_over_Perimeter_Extrusion_Width_ratio': calcSupportDistanceRatio,
			'Support_Material_Choice_': storedSetting('support'),
			'Support_Minimum_Angle_degrees': DEFSET,
		},'skirt': {
			'Skirt_line_count': storedSetting("skirt_line_count"),
			'Convex': "True",
			'Gap_Width_mm': storedSetting("skirt_gap"),
			'Layers_To_index': "1",
		},'joris': {
			'Activate_Joris': storedSetting("joris"),
			'Layers_From_index': calculateSolidLayerCount,
		},'chamber': {
			'Activate_Chamber': "False",
			'Bed_Temperature_Celcius': DEFSET,
			'Bed_Temperature_Begin_Change_Height_mm': DEFSET,
			'Bed_Temperature_End_Change_Height_mm': DEFSET,
			'Bed_Temperature_End_Celcius': DEFSET,
			'Chamber_Temperature_Celcius': DEFSET,
			'Holding_Force_bar': DEFSET,
		},'tower': {
			'Activate_Tower': "False",
			'Extruder_Possible_Collision_Cone_Angle_degrees': DEFSET,
			'Maximum_Tower_Height_layers': DEFSET,
			'Tower_Start_Layer_integer': DEFSET,
		},'jitter': {
			'Activate_Jitter': "False",
			'Jitter_Over_Perimeter_Width_ratio': DEFSET,
		},'clip': {
			'Activate_Clip': "False",
			'Clip_Over_Perimeter_Width_ratio': DEFSET,
			'Maximum_Connection_Distance_Over_Perimeter_Width_ratio': DEFSET,
		},'smooth': {
			'Activate_Smooth': "False",
			'Layers_From_index': DEFSET,
			'Maximum_Shortening_over_Width_float': DEFSET,
		},'stretch': {
			'Activate_Stretch': "False",
			'Cross_Limit_Distance_Over_Perimeter_Width_ratio': DEFSET,
			'Loop_Stretch_Over_Perimeter_Width_ratio': DEFSET,
			'Path_Stretch_Over_Perimeter_Width_ratio': DEFSET,
			'Perimeter_Inside_Stretch_Over_Perimeter_Width_ratio': DEFSET,
			'Perimeter_Outside_Stretch_Over_Perimeter_Width_ratio': DEFSET,
			'Stretch_From_Distance_Over_Perimeter_Width_ratio': DEFSET,
		},'skin': {
			'Activate_Skin': "False",
			'Horizontal_Infill_Divisions_integer': DEFSET,
			'Horizontal_Perimeter_Divisions_integer': DEFSET,
			'Vertical_Divisions_integer': DEFSET,
			'Hop_When_Extruding_Infill': DEFSET,
			'Layers_From_index': DEFSET,
		},'comb': {
			'Activate_Comb': "True",
			'Running_Jump_Space_mm': DEFSET,
		},'cool': {
			'Activate_Cool': "True",
			'Bridge_Cool_Celcius': DEFSET,
			'Cool_Type': DEFSET,
			'Maximum_Cool_Celcius': DEFSET,
			'Minimum_Layer_Time_seconds': storedSetting("cool_min_layer_time"),
			'Minimum_Orbital_Radius_millimeters': DEFSET,
			'Name_of_Cool_End_File': DEFSET,
			'Name_of_Cool_Start_File': DEFSET,
			'Orbital_Outset_millimeters': DEFSET,
			'Turn_Fan_On_at_Beginning': DEFSET,
			'Turn_Fan_Off_at_Ending': DEFSET,
			'Minimum_feed_rate_mm/s': storedSetting("cool_min_feedrate"),
		},'hop': {
			'Activate_Hop': "False",
			'Hop_Over_Layer_Thickness_ratio': DEFSET,
			'Minimum_Hop_Angle_degrees': DEFSET,
		},'wipe': {
			'Activate_Wipe': "False",
			'Arrival_X_mm': DEFSET,
			'Arrival_Y_mm': DEFSET,
			'Arrival_Z_mm': DEFSET,
			'Departure_X_mm': DEFSET,
			'Departure_Y_mm': DEFSET,
			'Departure_Z_mm': DEFSET,
			'Wipe_X_mm': DEFSET,
			'Wipe_Y_mm': DEFSET,
			'Wipe_Z_mm': DEFSET,
			'Wipe_Period_layers': DEFSET,
		},'oozebane': {
			'Activate_Oozebane': "False",
			'After_Startup_Distance_millimeters': DEFSET,
			'Early_Shutdown_Distance_millimeters': DEFSET,
			'Early_Startup_Distance_Constant_millimeters': DEFSET,
			'Early_Startup_Maximum_Distance_millimeters': DEFSET,
			'First_Early_Startup_Distance_millimeters': DEFSET,
			'Minimum_Distance_for_Early_Startup_millimeters': DEFSET,
			'Minimum_Distance_for_Early_Shutdown_millimeters': DEFSET,
			'Slowdown_Startup_Steps_positive_integer': DEFSET,
		},'dwindle': {
			'Activate_Dwindle': "False",
			'End_Rate_Multiplier_ratio': DEFSET,
			'Pent_Up_Volume_cubic_millimeters': DEFSET,
			'Slowdown_Steps_positive_integer': DEFSET,
			'Slowdown_Volume_cubic_millimeters': DEFSET,
		},'splodge': {
			'Activate_Splodge': "False",
			'Initial_Lift_over_Extra_Thickness_ratio': DEFSET,
			'Initial_Splodge_Feed_Rate_mm/s': DEFSET,
			'Operating_Splodge_Feed_Rate_mm/s': DEFSET,
			'Operating_Splodge_Quantity_Length_millimeters': DEFSET,
			'Initial_Splodge_Quantity_Length_millimeters': DEFSET,
			'Operating_Lift_over_Extra_Thickness_ratio': DEFSET,
		},'home': {
			'Activate_Home': "False",
			'Name_of_Home_File': DEFSET,
		},'lash': {
			'Activate_Lash': "False",
			'X_Backlash_mm': DEFSET,
			'Y_Backlash_mm': DEFSET,
		},'fillet': {
			'Activate_Fillet': "False",
			'Arc_Point': DEFSET,
			'Arc_Radius': DEFSET,
			'Arc_Segment': DEFSET,
			'Bevel': DEFSET,
			'Corner_Feed_Rate_Multiplier_ratio': DEFSET,
			'Fillet_Radius_over_Perimeter_Width_ratio': DEFSET,
			'Reversal_Slowdown_Distance_over_Perimeter_Width_ratio': DEFSET,
			'Use_Intermediate_Feed_Rate_in_Corners': DEFSET,
		},'limit': {
			'Activate_Limit': "False",
			'Maximum_Initial_Feed_Rate_mm/s': DEFSET,
		},'unpause': {
			'Activate_Unpause': "False",
			'Delay_milliseconds': DEFSET,
			'Maximum_Speed_ratio': DEFSET,
		},'dimension': {
			'Activate_Dimension': "True",
			'Absolute_Extrusion_Distance': "True",
			'Relative_Extrusion_Distance': "False",
			'Extruder_Retraction_Speed_mm/s': storedSetting('retraction_speed'),
			'Filament_Diameter_mm': storedSetting("filament_diameter"),
			'Filament_Packing_Density_ratio': storedSetting("filament_density"),
			'Maximum_E_Value_before_Reset_float': DEFSET,
			'Minimum_Travel_for_Retraction_millimeters': storedSetting("retraction_min_travel"),
			'Retract_Within_Island': DEFSET,
			'Retraction_Distance_millimeters': storedSetting('retraction_amount'),
			'Restart_Extra_Distance_millimeters': storedSetting('retraction_extra'),
		},'alteration': {
			'Activate_Alteration': "True",
			'Name_of_End_File': "end.gcode",
			'Name_of_Start_File': "start.gcode",
			'Remove_Redundant_Mcode': "True",
			'Replace_Variable_with_Setting': DEFSET,
		},'export': {
			'Activate_Export': "True",
			'Add_Descriptive_Extension': DEFSET,
			'Add_Export_Suffix': DEFSET,
			'Add_Profile_Extension': DEFSET,
			'Add_Timestamp_Extension': DEFSET,
			'Also_Send_Output_To': DEFSET,
			'Analyze_Gcode': DEFSET,
			'Comment_Choice': DEFSET,
			'Do_Not_Change_Output': DEFSET,
			'binary_16_byte': DEFSET,
			'gcode_step': DEFSET,
			'gcode_time_segment': DEFSET,
			'gcode_small': DEFSET,
			'File_Extension': DEFSET,
			'Name_of_Replace_File': DEFSET,
			'Save_Penultimate_Gcode': "False",
		}
	}

def safeConfigName(name):
	return name.replace("=", "").replace(":", "").replace(" ", "_").replace("(", "").replace(")", "")

def getReadRepository(repository):
	"Read the configuration for this 'repository'"
	
	info = getSkeinPyPyProfileInformation()
	if not info.has_key(repository.name):
		print "Warning: Plugin: " + repository.name + " missing from SkeinPyPy info"
		return repository
	info = info[repository.name]
	
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
	return archive.getTextLines(getAlterationFile(fileName))

def getAlterationFile(fileName, allowMagicPrefix = True):
	"Get the file from the fileName or the lowercase fileName in the alterations directories."
	#print ('getAlterationFile:', fileName)
	prefix = ''
	if allowMagicPrefix:
		if fileName == 'start.gcode':
			#For the start code, hack the temperature and the steps per E value into it. So the temperature is reached before the start code extrusion.
			#We also set our steps per E here, if configured.
			eSteps = float(profile.getPreference('steps_per_e'))
			if eSteps > 0:
				prefix += 'M92 E'+str(eSteps)+'\n'
			temp = float(profile.getProfileSetting('print_temperature'))
			if temp > 0:
				prefix += 'M109 S'+str(temp)+'\n'
		elif fileName == 'replace.csv':
			prefix = 'M101\nM103\n'
	alterationsDirectory = archive.getSkeinforgePath('alterations')
	fullFilename = os.path.join(alterationsDirectory, fileName)
	if os.path.isfile(fullFilename):
		return prefix + archive.getFileText( fullFilename )
	return prefix

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

