"""
This page is in the table of contents.
Raft is a plugin to create a raft, elevate the nozzle and set the temperature.  A raft is a flat base structure on top of which your object is being build and has a few different purposes. It fills irregularities like scratches and pits in your printbed and gives you a nice base parallel to the printheads movement. It also glues your object to the bed so to prevent warping in bigger object.  The rafts base layer performs these tricks while the sparser interface layer(s) help you removing the object from the raft after printing.  It is based on the Nophead's reusable raft, which has a base layer running one way, and a couple of perpendicular layers above.  Each set of layers can be set to a different temperature.  There is the option of having the extruder orbit the raft for a while, so the heater barrel has time to reach a different temperature, without ooze accumulating around the nozzle.

The raft manual page is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Raft

The important values for the raft settings are the temperatures of the raft, the first layer and the next layers.  These will be different for each material.  The default settings for ABS, HDPE, PCL & PLA are extrapolated from Nophead's experiments.

You don't necessarily need a raft and especially small object will print fine on a flat bed without one, sometimes its even better when you need a water tight base to print directly on the bed.  If you want to only set the temperature or only create support material or only elevate the nozzle without creating a raft, set the Base Layers and Interface Layers to zero.

<gallery perRow="1">
Image:Raft.jpg|Raft
</gallery>

Example of a raft on the left with the interface layers partially removed exposing the base layer. Notice that the first line of the base is rarely printed well because of the startup time of the extruder. On the right you see an object with its raft still attached.

The Raft panel has some extra settings, it probably made sense to have them there but they have not that much to do with the actual Raft. First are the Support material settings. Since close to all RepRap style printers have no second extruder for support material Skeinforge offers the option to print support structures with the same material set at a different speed and temperature. The idea is that the support sticks less to the actual object when it is extruded around the minimum possible working temperature. This results in a temperature change EVERY layer so build time will increase seriously.

Allan Ecker aka The Masked Retriever's has written two quicktips for raft which follow below.
"Skeinforge Quicktip: The Raft, Part 1" at:
http://blog.thingiverse.com/2009/07/14/skeinforge-quicktip-the-raft-part-1/
"Skeinforge Quicktip: The Raft, Part II" at:
http://blog.thingiverse.com/2009/08/04/skeinforge-quicktip-the-raft-part-ii/

Nophead has written about rafts on his blog:
http://hydraraptor.blogspot.com/2009/07/thoughts-on-rafts.html

More pictures of rafting in action are available from the Metalab blog at:
http://reprap.soup.io/?search=rafting

==Operation==
Default: On

When it is on, the functions described below will work, when it is off, nothing will be done, so no temperatures will be set, nozzle will not be lifted..

==Settings==
===Add Raft, Elevate Nozzle, Orbit===
Default: On

When selected, the script will also create a raft, elevate the nozzle, orbit and set the altitude of the bottom of the raft.  It also turns on support generation.

===Base===
Base layer is the part of the raft that touches the bed.

====Base Feed Rate Multiplier====
Default is one.

Defines the base feed rate multiplier.  The greater the 'Base Feed Rate Multiplier', the thinner the base, the lower the 'Base Feed Rate Multiplier', the thicker the base.

====Base Flow Rate Multiplier====
Default is one.

Defines the base flow rate multiplier.  The greater the 'Base Flow Rate Multiplier', the thicker the base, the lower the 'Base Flow Rate Multiplier', the thinner the base.

====Base Infill Density====
Default is 0.5.

Defines the infill density ratio of the base of the raft.

====Base Layer Height over Layer Thickness====
Default is two.

Defines the ratio of the height & width of the base layer compared to the height and width of the object infill.  The feed rate will be slower for raft layers which have thicker extrusions than the object infill.

====Base Layers====
Default is one.

Defines the number of base layers.

====Base Nozzle Lift over Base Layer Thickness====
Default is 0.4.

Defines the amount the nozzle is above the center of the base extrusion divided by the base layer thickness.

===Initial Circling===
Default is off.

When selected, the extruder will initially circle around until it reaches operating temperature.

===Infill Overhang over Extrusion Width===
Default is 0.05.

Defines the ratio of the infill overhang over the the extrusion width of the raft.

===Interface===
====Interface Feed Rate Multiplier====
Default is one.

Defines the interface feed rate multiplier.  The greater the 'Interface Feed Rate Multiplier', the thinner the interface, the lower the 'Interface Feed Rate Multiplier', the thicker the interface.

====Interface Flow Rate Multiplier====
Default is one.

Defines the interface flow rate multiplier.  The greater the 'Interface Flow Rate Multiplier', the thicker the interface, the lower the 'Interface Flow Rate Multiplier', the thinner the interface.

====Interface Infill Density====
Default is 0.5.

Defines the infill density ratio of the interface of the raft.

====Interface Layer Thickness over Extrusion Height====
Default is one.

Defines the ratio of the height & width of the interface layer compared to the height and width of the object infill.  The feed rate will be slower for raft layers which have thicker extrusions than the object infill.

====Interface Layers====
Default is two.

Defines the number of interface layers to print.

====Interface Nozzle Lift over Interface Layer Thickness====
Default is 0.45.

Defines the amount the nozzle is above the center of the interface extrusion divided by the interface layer thickness.

===Name of Alteration Files===
If support material is generated, raft looks for alteration files in the alterations folder in the .skeinforge folder in the home directory.  Raft does not care if the text file names are capitalized, but some file systems do not handle file name cases properly, so to be on the safe side you should give them lower case names.  If it doesn't find the file it then looks in the alterations folder in the skeinforge_plugins folder.

====Name of Support End File====
Default is support_end.gcode.

If support material is generated and if there is a file with the name of the "Name of Support End File" setting, it will be added to the end of the support gcode.

====Name of Support Start File====
If support material is generated and if there is a file with the name of the "Name of Support Start File" setting, it will be added to the start of the support gcode.

===Operating Nozzle Lift over Layer Thickness===
Default is 0.5.

Defines the amount the nozzle is above the center of the operating extrusion divided by the layer height.

===Raft Size===
The raft fills a rectangle whose base size is the rectangle around the bottom layer of the object expanded on each side by the 'Raft Margin' plus the 'Raft Additional Margin over Length (%)' percentage times the length of the side.

====Raft Additional Margin over Length====
Default is 1 percent.

====Raft Margin====
Default is three millimeters.

===Support===
Good articles on support material are at:
http://davedurant.wordpress.com/2010/07/31/skeinforge-support-part-1/
http://davedurant.wordpress.com/2010/07/31/skeinforge-support-part-2/

====Support Cross Hatch====
Default is off.

When selected, the support material will cross hatched.  Cross hatching the support makes it stronger and harder to remove, which is why the default is off.

====Support Flow Rate over Operating Flow Rate====
Default: 0.9.

Defines the ratio of the flow rate when the support is extruded over the operating flow rate.  With a number less than one, the support flow rate will be smaller so the support will be thinner and easier to remove.

====Support Gap over Perimeter Extrusion Width====
Default: 0.5.

Defines the gap between the support material and the object over the edge extrusion width.

====Support Material Choice====
Default is 'None' because the raft takes time to generate.

=====Empty Layers Only=====
When selected, support material will be only on the empty layers.  This is useful when making identical objects in a stack.

=====Everywhere=====
When selected, support material will be added wherever there are overhangs, even inside the object.  Because support material inside objects is hard or impossible to remove, this option should only be chosen if the object has a cavity that needs support and there is some way to extract the support material.

=====Exterior Only=====
When selected, support material will be added only the exterior of the object.  This is the best option for most objects which require support material.

=====None=====
When selected, raft will not add support material.

====Support Minimum Angle====
Default is sixty degrees.

Defines the minimum angle that a surface overhangs before support material is added.  If angle is lower then this value the support will be generated.  This angle is defined from the vertical, so zero is a vertical wall, ten is a wall with a bit of overhang, thirty is the typical safe angle for filament extrusion, sixty is a really high angle for extrusion and ninety is an unsupported horizontal ceiling.

==Examples==
The following examples raft the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and raft.py.

> python raft.py
This brings up the raft dialog.

> python raft.py Screw Holder Bottom.stl
The raft tool is parsing the file:
Screw Holder Bottom.stl
..
The raft tool has created the file:
Screw Holder Bottom_raft.gcode

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities.geometry.solids import triangle_mesh
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import intercircle
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import math
import os
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


#maybe later wide support
#raft outline temperature http://hydraraptor.blogspot.com/2008/09/screw-top-pot.html
def getCraftedText( fileName, text='', repository=None):
	'Raft the file or text.'
	return getCraftedTextFromText(archive.getTextIfEmpty(fileName, text), repository)

def getCraftedTextFromText(gcodeText, repository=None):
	'Raft a gcode linear move text.'
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'raft'):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( RaftRepository() )
	if not repository.activateRaft.value:
		return gcodeText
	return RaftSkein().getCraftedGcode(gcodeText, repository)

def getCrossHatchPointLine( crossHatchPointLineTable, y ):
	'Get the cross hatch point line.'
	if not crossHatchPointLineTable.has_key(y):
		crossHatchPointLineTable[ y ] = {}
	return crossHatchPointLineTable[ y ]

def getEndpointsFromYIntersections( x, yIntersections ):
	'Get endpoints from the y intersections.'
	endpoints = []
	for yIntersectionIndex in xrange( 0, len( yIntersections ), 2 ):
		firstY = yIntersections[ yIntersectionIndex ]
		secondY = yIntersections[ yIntersectionIndex + 1 ]
		if firstY != secondY:
			firstComplex = complex( x, firstY )
			secondComplex = complex( x, secondY )
			endpointFirst = euclidean.Endpoint()
			endpointSecond = euclidean.Endpoint().getFromOtherPoint( endpointFirst, secondComplex )
			endpointFirst.getFromOtherPoint( endpointSecond, firstComplex )
			endpoints.append( endpointFirst )
			endpoints.append( endpointSecond )
	return endpoints

def getExtendedLineSegment(extensionDistance, lineSegment, loopXIntersections):
	'Get extended line segment.'
	pointBegin = lineSegment[0].point
	pointEnd = lineSegment[1].point
	segment = pointEnd - pointBegin
	segmentLength = abs(segment)
	if segmentLength <= 0.0:
		print('This should never happen in getExtendedLineSegment in raft, the segment should have a length greater than zero.')
		print(lineSegment)
		return None
	segmentExtend = segment * extensionDistance / segmentLength
	lineSegment[0].point -= segmentExtend
	lineSegment[1].point += segmentExtend
	for loopXIntersection in loopXIntersections:
		setExtendedPoint(lineSegment[0], pointBegin, loopXIntersection)
		setExtendedPoint(lineSegment[1], pointEnd, loopXIntersection)
	return lineSegment

def getLoopsBySegmentsDictionary(segmentsDictionary, width):
	'Get loops from a horizontal segments dictionary.'
	points = []
	for endpoint in getVerticalEndpoints(segmentsDictionary, width, 0.1 * width, width):
		points.append(endpoint.point)
	for endpoint in euclidean.getEndpointsFromSegmentTable(segmentsDictionary):
		points.append(endpoint.point)
	return triangle_mesh.getDescendingAreaOrientedLoops(points, points, width + width)

def getNewRepository():
	'Get new repository.'
	return RaftRepository()

def getVerticalEndpoints(horizontalSegmentsTable, horizontalStep, verticalOverhang, verticalStep):
	'Get vertical endpoints.'
	interfaceSegmentsTableKeys = horizontalSegmentsTable.keys()
	interfaceSegmentsTableKeys.sort()
	verticalTableTable = {}
	for interfaceSegmentsTableKey in interfaceSegmentsTableKeys:
		interfaceSegments = horizontalSegmentsTable[interfaceSegmentsTableKey]
		for interfaceSegment in interfaceSegments:
			begin = int(round(interfaceSegment[0].point.real / verticalStep))
			end = int(round(interfaceSegment[1].point.real / verticalStep))
			for stepIndex in xrange(begin, end + 1):
				if stepIndex not in verticalTableTable:
					verticalTableTable[stepIndex] = {}
				verticalTableTable[stepIndex][interfaceSegmentsTableKey] = None
	verticalTableTableKeys = verticalTableTable.keys()
	verticalTableTableKeys.sort()
	verticalEndpoints = []
	for verticalTableTableKey in verticalTableTableKeys:
		verticalTable = verticalTableTable[verticalTableTableKey]
		verticalTableKeys = verticalTable.keys()
		verticalTableKeys.sort()
		xIntersections = []
		for verticalTableKey in verticalTableKeys:
			y = verticalTableKey * horizontalStep
			if verticalTableKey - 1 not in verticalTableKeys:
				xIntersections.append(y - verticalOverhang)
			if verticalTableKey + 1 not in verticalTableKeys:
				xIntersections.append(y + verticalOverhang)
		for segment in euclidean.getSegmentsFromXIntersections(xIntersections, verticalTableTableKey * verticalStep):
			for endpoint in segment:
				endpoint.point = complex(endpoint.point.imag, endpoint.point.real)
				verticalEndpoints.append(endpoint)
	return verticalEndpoints

def setExtendedPoint( lineSegmentEnd, pointOriginal, x ):
	'Set the point in the extended line segment.'
	if x > min( lineSegmentEnd.point.real, pointOriginal.real ) and x < max( lineSegmentEnd.point.real, pointOriginal.real ):
		lineSegmentEnd.point = complex( x, pointOriginal.imag )

def writeOutput(fileName, shouldAnalyze=True):
	'Raft a gcode linear move file.'
	skeinforge_craft.writeChainTextWithNounMessage(fileName, 'raft', shouldAnalyze)


class RaftRepository:
	'A class to handle the raft settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.craft_plugins.raft.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName(
			fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Raft', self, '')
		self.openWikiManualHelpPage = settings.HelpPage().getOpenFromAbsolute(
			'http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge_Raft')
		self.activateRaft = settings.BooleanSetting().getFromValue('Activate Raft', self, True)
		self.addRaftElevateNozzleOrbitSetAltitude = settings.BooleanSetting().getFromValue(
			'Add Raft, Elevate Nozzle, Orbit:', self, True)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Base -', self)
		self.baseFeedRateMultiplier = settings.FloatSpin().getFromValue(0.7, 'Base Feed Rate Multiplier (ratio):', self, 1.1, 1.0)
		self.baseFlowRateMultiplier = settings.FloatSpin().getFromValue(0.7, 'Base Flow Rate Multiplier (ratio):', self, 1.1, 1.0)
		self.baseInfillDensity = settings.FloatSpin().getFromValue(0.3, 'Base Infill Density (ratio):', self, 0.9, 0.5)
		self.baseLayerThicknessOverLayerThickness = settings.FloatSpin().getFromValue(
			1.0, 'Base Layer Thickness over Layer Thickness:', self, 3.0, 2.0)
		self.baseLayers = settings.IntSpin().getFromValue(0, 'Base Layers (integer):', self, 3, 0)
		self.baseNozzleLiftOverBaseLayerThickness = settings.FloatSpin().getFromValue(
			0.2, 'Base Nozzle Lift over Base Layer Thickness (ratio):', self, 0.8, 0.4)
		settings.LabelSeparator().getFromRepository(self)
		self.initialCircling = settings.BooleanSetting().getFromValue('Initial Circling:', self, False)
		self.infillOverhangOverExtrusionWidth = settings.FloatSpin().getFromValue(
			0.0, 'Infill Overhang over Extrusion Width (ratio):', self, 0.5, 0.05)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Interface -', self)
		self.interfaceFeedRateMultiplier = settings.FloatSpin().getFromValue(
			0.7, 'Interface Feed Rate Multiplier (ratio):', self, 1.1, 1.0)
		self.interfaceFlowRateMultiplier = settings.FloatSpin().getFromValue(
			0.7, 'Interface Flow Rate Multiplier (ratio):', self, 1.1, 1.0)
		self.interfaceInfillDensity = settings.FloatSpin().getFromValue(
			0.3, 'Interface Infill Density (ratio):', self, 0.9, 0.5)
		self.interfaceLayerThicknessOverLayerThickness = settings.FloatSpin().getFromValue(
			1.0, 'Interface Layer Thickness over Layer Thickness:', self, 3.0, 1.0)
		self.interfaceLayers = settings.IntSpin().getFromValue(
			0, 'Interface Layers (integer):', self, 3, 0)
		self.interfaceNozzleLiftOverInterfaceLayerThickness = settings.FloatSpin().getFromValue(
			0.25, 'Interface Nozzle Lift over Interface Layer Thickness (ratio):', self, 0.85, 0.45)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Name of Alteration Files -', self)
		self.nameOfSupportEndFile = settings.StringSetting().getFromValue('Name of Support End File:', self, 'support_end.gcode')
		self.nameOfSupportStartFile = settings.StringSetting().getFromValue(
			'Name of Support Start File:', self, 'support_start.gcode')
		settings.LabelSeparator().getFromRepository(self)
		self.operatingNozzleLiftOverLayerThickness = settings.FloatSpin().getFromValue(
			0.3, 'Operating Nozzle Lift over Layer Thickness (ratio):', self, 0.7, 0.5)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Raft Size -', self)
		self.raftAdditionalMarginOverLengthPercent = settings.FloatSpin().getFromValue(
			0.5, 'Raft Additional Margin over Length (%):', self, 1.5, 1.0)
		self.raftMargin = settings.FloatSpin().getFromValue(
			1.0, 'Raft Margin (mm):', self, 5.0, 3.0)
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Support -', self)
		self.supportCrossHatch = settings.BooleanSetting().getFromValue('Support Cross Hatch', self, False)
		self.supportFlowRateOverOperatingFlowRate = settings.FloatSpin().getFromValue(
			0.7, 'Support Flow Rate over Operating Flow Rate (ratio):', self, 1.1, 1.0)
		self.supportGapOverPerimeterExtrusionWidth = settings.FloatSpin().getFromValue(
			0.5, 'Support Gap over Perimeter Extrusion Width (ratio):', self, 1.5, 1.0)
		self.supportMaterialChoice = settings.MenuButtonDisplay().getFromName('Support Material Choice: ', self)
		self.supportChoiceNone = settings.MenuRadio().getFromMenuButtonDisplay(self.supportMaterialChoice, 'None', self, True)
		self.supportChoiceEmptyLayersOnly = settings.MenuRadio().getFromMenuButtonDisplay(self.supportMaterialChoice, 'Empty Layers Only', self, False)
		self.supportChoiceEverywhere = settings.MenuRadio().getFromMenuButtonDisplay(self.supportMaterialChoice, 'Everywhere', self, False)
		self.supportChoiceExteriorOnly = settings.MenuRadio().getFromMenuButtonDisplay(self.supportMaterialChoice, 'Exterior Only', self, False)
		self.supportMinimumAngle = settings.FloatSpin().getFromValue(40.0, 'Support Minimum Angle (degrees):', self, 80.0, 60.0)
		self.executeTitle = 'Raft'

	def execute(self):
		'Raft button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		for fileName in fileNames:
			writeOutput(fileName)


class RaftSkein:
	'A class to raft a skein of extrusions.'
	def __init__(self):
		self.addLineLayerStart = True
		self.baseTemperature = None
		self.beginLoop = None
		self.boundaryLayers = []
		self.coolingRate = None
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.edgeWidth = 0.6
		self.extrusionStart = True
		self.extrusionTop = 0.0
		self.feedRateMinute = 961.0
		self.heatingRate = None
		self.insetTable = {}
		self.interfaceTemperature = None
		self.isEdgePath = False
		self.isNestedRing = True
		self.isStartupEarly = False
		self.layerIndex = - 1
		self.layerStarted = False
		self.layerHeight = 0.4
		self.lineIndex = 0
		self.lines = None
		self.objectFirstLayerInfillTemperature = None
		self.objectFirstLayerPerimeterTemperature = None
		self.objectNextLayersTemperature = None
		self.oldFlowRate = None
		self.oldLocation = None
		self.oldTemperatureOutputString = None
		self.operatingFeedRateMinute = None
		self.operatingFlowRate = None
		self.operatingLayerEndLine = '(<operatingLayerEnd> </operatingLayerEnd>)'
		self.operatingJump = None
		self.orbitalFeedRatePerSecond = 2.01
		self.sharpestProduct = 0.94
		self.supportFlowRate = None
		self.supportLayers = []
		self.supportLayersTemperature = None
		self.supportedLayersTemperature = None
		self.travelFeedRateMinute = None

	def addBaseLayer(self):
		'Add a base layer.'
		baseLayerThickness = self.layerHeight * self.baseLayerThicknessOverLayerThickness
		zCenter = self.extrusionTop + 0.5 * baseLayerThickness
		z = zCenter + baseLayerThickness * self.repository.baseNozzleLiftOverBaseLayerThickness.value
		if len(self.baseEndpoints) < 1:
			print('This should never happen, the base layer has a size of zero.')
			return
		self.addLayerFromEndpoints(
			self.baseEndpoints,
			self.repository.baseFeedRateMultiplier.value,
			self.repository.baseFlowRateMultiplier.value,
			baseLayerThickness,
			self.baseLayerThicknessOverLayerThickness,
			self.baseStep,
			z)

	def addBaseSegments(self, baseExtrusionWidth):
		'Add the base segments.'
		baseOverhang = self.repository.infillOverhangOverExtrusionWidth.value * baseExtrusionWidth
		self.baseEndpoints = getVerticalEndpoints(self.interfaceSegmentsTable, self.interfaceStep, baseOverhang, self.baseStep)

	def addEmptyLayerSupport( self, boundaryLayerIndex ):
		'Add support material to a layer if it is empty.'
		supportLayer = SupportLayer([])
		self.supportLayers.append(supportLayer)
		if len( self.boundaryLayers[ boundaryLayerIndex ].loops ) > 0:
			return
		aboveXIntersectionsTable = {}
		euclidean.addXIntersectionsFromLoopsForTable( self.getInsetLoopsAbove(boundaryLayerIndex), aboveXIntersectionsTable, self.interfaceStep )
		belowXIntersectionsTable = {}
		euclidean.addXIntersectionsFromLoopsForTable( self.getInsetLoopsBelow(boundaryLayerIndex), belowXIntersectionsTable, self.interfaceStep )
		supportLayer.xIntersectionsTable = euclidean.getIntersectionOfXIntersectionsTables( [ aboveXIntersectionsTable, belowXIntersectionsTable ] )

	def addFlowRate(self, flowRate):
		'Add a flow rate value if different.'
		if flowRate != None:
			self.distanceFeedRate.addLine('M108 S' + euclidean.getFourSignificantFigures(flowRate))

	def addInterfaceLayer(self):
		'Add an interface layer.'
		interfaceLayerThickness = self.layerHeight * self.interfaceLayerThicknessOverLayerThickness
		zCenter = self.extrusionTop + 0.5 * interfaceLayerThickness
		z = zCenter + interfaceLayerThickness * self.repository.interfaceNozzleLiftOverInterfaceLayerThickness.value
		if len(self.interfaceEndpoints) < 1:
			print('This should never happen, the interface layer has a size of zero.')
			return
		self.addLayerFromEndpoints(
			self.interfaceEndpoints,
			self.repository.interfaceFeedRateMultiplier.value,
			self.repository.interfaceFlowRateMultiplier.value,
			interfaceLayerThickness,
			self.interfaceLayerThicknessOverLayerThickness,
			self.interfaceStep,
			z)

	def addInterfaceTables(self, interfaceExtrusionWidth):
		'Add interface tables.'
		overhang = self.repository.infillOverhangOverExtrusionWidth.value * interfaceExtrusionWidth
		self.interfaceEndpoints = []
		self.interfaceIntersectionsTableKeys = self.interfaceIntersectionsTable.keys()
		self.interfaceSegmentsTable = {}
		for yKey in self.interfaceIntersectionsTableKeys:
			self.interfaceIntersectionsTable[yKey].sort()
			y = yKey * self.interfaceStep
			lineSegments = euclidean.getSegmentsFromXIntersections(self.interfaceIntersectionsTable[yKey], y)
			xIntersectionIndexList = []
			for lineSegmentIndex in xrange(len(lineSegments)):
				lineSegment = lineSegments[lineSegmentIndex]
				endpointBegin = lineSegment[0]
				endpointEnd = lineSegment[1]
				endpointBegin.point = complex(self.baseStep * math.floor(endpointBegin.point.real / self.baseStep) - overhang, y)
				endpointEnd.point = complex(self.baseStep * math.ceil(endpointEnd.point.real / self.baseStep) + overhang, y)
				if endpointEnd.point.real > endpointBegin.point.real:
					euclidean.addXIntersectionIndexesFromSegment(lineSegmentIndex, lineSegment, xIntersectionIndexList)
			xIntersections = euclidean.getJoinOfXIntersectionIndexes(xIntersectionIndexList)
			joinedSegments = euclidean.getSegmentsFromXIntersections(xIntersections, y)
			if len(joinedSegments) > 0:
				self.interfaceSegmentsTable[yKey] = joinedSegments
			for joinedSegment in joinedSegments:
				self.interfaceEndpoints += joinedSegment

	def addLayerFromEndpoints(
		self,
		endpoints,
		feedRateMultiplier,
		flowRateMultiplier,
		layerLayerThickness,
		layerThicknessRatio,
		step,
		z):
		'Add a layer from endpoints and raise the extrusion top.'
		layerThicknessRatioSquared = layerThicknessRatio * layerThicknessRatio
		feedRateMinute = self.feedRateMinute * feedRateMultiplier / layerThicknessRatioSquared
		if len(endpoints) < 1:
			return
		aroundPixelTable = {}
		aroundWidth = 0.34321 * step
		paths = euclidean.getPathsFromEndpoints(endpoints, 1.5 * step, aroundPixelTable, self.sharpestProduct, aroundWidth)
		self.addLayerLine(z)
		if self.operatingFlowRate != None:
			self.addFlowRate(flowRateMultiplier * self.operatingFlowRate)
		for path in paths:
			simplifiedPath = euclidean.getSimplifiedPath(path, step)
			self.distanceFeedRate.addGcodeFromFeedRateThreadZ(feedRateMinute, simplifiedPath, self.travelFeedRateMinute, z)
		self.extrusionTop += layerLayerThickness
		self.addFlowRate(self.oldFlowRate)

	def addLayerLine(self, z):
		'Add the layer gcode line and close the last layer gcode block.'
		if self.layerStarted:
			self.distanceFeedRate.addLine('(</layer>)')
		self.distanceFeedRate.addLine('(<layer> %s )' % self.distanceFeedRate.getRounded(z)) # Indicate that a new layer is starting.
		if self.beginLoop != None:
			zBegin = self.extrusionTop + self.layerHeight
			intercircle.addOrbitsIfLarge(self.distanceFeedRate, self.beginLoop, self.orbitalFeedRatePerSecond, self.temperatureChangeTimeBeforeRaft, zBegin)
			self.beginLoop = None
		self.layerStarted = True

	def addOperatingOrbits(self, boundaryLoops, pointComplex, temperatureChangeTime, z):
		'Add the orbits before the operating layers.'
		if len(boundaryLoops) < 1:
			return
		insetBoundaryLoops = intercircle.getInsetLoopsFromLoops(boundaryLoops, self.edgeWidth)
		if len(insetBoundaryLoops) < 1:
			insetBoundaryLoops = boundaryLoops
		largestLoop = euclidean.getLargestLoop(insetBoundaryLoops)
		if pointComplex != None:
			largestLoop = euclidean.getLoopStartingClosest(self.edgeWidth, pointComplex, largestLoop)
		intercircle.addOrbitsIfLarge(self.distanceFeedRate, largestLoop, self.orbitalFeedRatePerSecond, temperatureChangeTime, z)

	def addRaft(self):
		'Add the raft.'
		if len(self.boundaryLayers) < 0:
			print('this should never happen, there are no boundary layers in addRaft')
			return
		self.baseLayerThicknessOverLayerThickness = self.repository.baseLayerThicknessOverLayerThickness.value
		baseExtrusionWidth = self.edgeWidth * self.baseLayerThicknessOverLayerThickness
		self.baseStep = baseExtrusionWidth / self.repository.baseInfillDensity.value
		self.interfaceLayerThicknessOverLayerThickness = self.repository.interfaceLayerThicknessOverLayerThickness.value
		interfaceExtrusionWidth = self.edgeWidth * self.interfaceLayerThicknessOverLayerThickness
		self.interfaceStep = interfaceExtrusionWidth / self.repository.interfaceInfillDensity.value
		self.setCornersZ()
		self.cornerMinimumComplex = self.cornerMinimum.dropAxis()
		originalExtent = self.cornerMaximumComplex - self.cornerMinimumComplex
		self.raftOutsetRadius = self.repository.raftMargin.value + self.repository.raftAdditionalMarginOverLengthPercent.value * 0.01 * max(originalExtent.real, originalExtent.imag)
		self.setBoundaryLayers()
		outsetSeparateLoops = intercircle.getInsetSeparateLoopsFromLoops(self.boundaryLayers[0].loops, -self.raftOutsetRadius, 0.8)
		self.interfaceIntersectionsTable = {}
		euclidean.addXIntersectionsFromLoopsForTable(outsetSeparateLoops, self.interfaceIntersectionsTable, self.interfaceStep)
		if len(self.supportLayers) > 0:
			supportIntersectionsTable = self.supportLayers[0].xIntersectionsTable
			euclidean.joinXIntersectionsTables(supportIntersectionsTable, self.interfaceIntersectionsTable)
		self.addInterfaceTables(interfaceExtrusionWidth)
		self.addRaftPerimeters()
		self.baseIntersectionsTable = {}
		complexRadius = complex(self.raftOutsetRadius, self.raftOutsetRadius)
		self.complexHigh = complexRadius + self.cornerMaximumComplex
		self.complexLow = self.cornerMinimumComplex - complexRadius
		self.beginLoop = euclidean.getSquareLoopWiddershins(self.cornerMinimumComplex, self.cornerMaximumComplex)
		if not intercircle.orbitsAreLarge(self.beginLoop, self.temperatureChangeTimeBeforeRaft):
			self.beginLoop = None
		if self.repository.baseLayers.value > 0:
			self.addTemperatureLineIfDifferent(self.baseTemperature)
			self.addBaseSegments(baseExtrusionWidth)
		for baseLayerIndex in xrange(self.repository.baseLayers.value):
			self.addBaseLayer()
		if self.repository.interfaceLayers.value > 0:
			self.addTemperatureLineIfDifferent(self.interfaceTemperature)
		self.interfaceIntersectionsTableKeys.sort()
		for interfaceLayerIndex in xrange(self.repository.interfaceLayers.value):
			self.addInterfaceLayer()
		self.operatingJump = self.extrusionTop + self.layerHeight * self.repository.operatingNozzleLiftOverLayerThickness.value
		for boundaryLayer in self.boundaryLayers:
			if self.operatingJump != None:
				boundaryLayer.z += self.operatingJump
		if self.repository.baseLayers.value > 0 or self.repository.interfaceLayers.value > 0:
			boundaryZ = self.boundaryLayers[0].z
			if self.layerStarted:
				self.distanceFeedRate.addLine('(</layer>)')
				self.layerStarted = False
			self.distanceFeedRate.addLine('(<raftLayerEnd> </raftLayerEnd>)')
			self.addLayerLine(boundaryZ)
			temperatureChangeTimeBeforeFirstLayer = self.getTemperatureChangeTime(self.objectFirstLayerPerimeterTemperature)
			self.addTemperatureLineIfDifferent(self.objectFirstLayerPerimeterTemperature)
			largestOutsetLoop = intercircle.getLargestInsetLoopFromLoop(euclidean.getLargestLoop(outsetSeparateLoops), -self.raftOutsetRadius)
			intercircle.addOrbitsIfLarge(self.distanceFeedRate, largestOutsetLoop, self.orbitalFeedRatePerSecond, temperatureChangeTimeBeforeFirstLayer, boundaryZ)
			self.addLineLayerStart = False

	def addRaftedLine( self, splitLine ):
		'Add elevated gcode line with operating feed rate.'
		self.oldLocation = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
		self.feedRateMinute = gcodec.getFeedRateMinute(self.feedRateMinute, splitLine)
		z = self.oldLocation.z
		if self.operatingJump != None:
			z += self.operatingJump
		temperature = self.objectNextLayersTemperature
		if self.layerIndex == 0:
			if self.isEdgePath:
				temperature = self.objectFirstLayerPerimeterTemperature
			else:
				temperature = self.objectFirstLayerInfillTemperature
		self.addTemperatureLineIfDifferent(temperature)
		self.distanceFeedRate.addGcodeMovementZWithFeedRate(self.feedRateMinute, self.oldLocation.dropAxis(), z)

	def addRaftPerimeters(self):
		'Add raft edges if there is a raft.'
		interfaceOutset = self.halfEdgeWidth * self.interfaceLayerThicknessOverLayerThickness
		for supportLayer in self.supportLayers:
			supportSegmentTable = supportLayer.supportSegmentTable
			if len(supportSegmentTable) > 0:
				outset = interfaceOutset
				self.addRaftPerimetersByLoops(getLoopsBySegmentsDictionary(supportSegmentTable, self.interfaceStep), outset)
		if self.repository.baseLayers.value < 1 and self.repository.interfaceLayers.value < 1:
			return
		overhangMultiplier = 1.0 + self.repository.infillOverhangOverExtrusionWidth.value + self.repository.infillOverhangOverExtrusionWidth.value
		outset = self.halfEdgeWidth
		if self.repository.interfaceLayers.value > 0:
			outset = max(interfaceOutset * overhangMultiplier, outset)
		if self.repository.baseLayers.value > 0:
			outset = max(self.halfEdgeWidth * self.baseLayerThicknessOverLayerThickness * overhangMultiplier, outset)
		self.addRaftPerimetersByLoops(getLoopsBySegmentsDictionary(self.interfaceSegmentsTable, self.interfaceStep), outset)

	def addRaftPerimetersByLoops(self, loops, outset):
		'Add raft edges to the gcode for loops.'
		loops = intercircle.getInsetSeparateLoopsFromLoops(loops, -outset)
		for loop in loops:
			self.distanceFeedRate.addLine('(<raftPerimeter>)')
			for point in loop:
				roundedX = self.distanceFeedRate.getRounded(point.real)
				roundedY = self.distanceFeedRate.getRounded(point.imag)
				self.distanceFeedRate.addTagBracketedLine('raftPoint', 'X%s Y%s' % (roundedX, roundedY))
			self.distanceFeedRate.addLine('(</raftPerimeter>)')

	def addSegmentTablesToSupportLayers(self):
		'Add segment tables to the support layers.'
		for supportLayer in self.supportLayers:
			supportLayer.supportSegmentTable = {}
			xIntersectionsTable = supportLayer.xIntersectionsTable
			for xIntersectionsTableKey in xIntersectionsTable:
				y = xIntersectionsTableKey * self.interfaceStep
				supportLayer.supportSegmentTable[ xIntersectionsTableKey ] = euclidean.getSegmentsFromXIntersections( xIntersectionsTable[ xIntersectionsTableKey ], y )

	def addSupportLayerTemperature(self, endpoints, z):
		'Add support layer and temperature before the object layer.'
		self.distanceFeedRate.addLine('(<supportLayer>)')
		self.distanceFeedRate.addLinesSetAbsoluteDistanceMode(self.supportStartLines)
		self.addTemperatureOrbits(endpoints, self.supportedLayersTemperature, z)
		aroundPixelTable = {}
		aroundWidth = 0.34321 * self.interfaceStep
		boundaryLoops = self.boundaryLayers[self.layerIndex].loops
		halfSupportOutset = 0.5 * self.supportOutset
		aroundBoundaryLoops = intercircle.getAroundsFromLoops(boundaryLoops, halfSupportOutset)
		for aroundBoundaryLoop in aroundBoundaryLoops:
			euclidean.addLoopToPixelTable(aroundBoundaryLoop, aroundPixelTable, aroundWidth)
		paths = euclidean.getPathsFromEndpoints(endpoints, 1.5 * self.interfaceStep, aroundPixelTable, self.sharpestProduct, aroundWidth)
		feedRateMinuteMultiplied = self.operatingFeedRateMinute
		supportFlowRateMultiplied = self.supportFlowRate
		if self.layerIndex == 0:
			feedRateMinuteMultiplied *= self.objectFirstLayerFeedRateInfillMultiplier
			if supportFlowRateMultiplied != None:
				supportFlowRateMultiplied *= self.objectFirstLayerFlowRateInfillMultiplier
		self.addFlowRate(supportFlowRateMultiplied)
		for path in paths:
			self.distanceFeedRate.addGcodeFromFeedRateThreadZ(feedRateMinuteMultiplied, path, self.travelFeedRateMinute, z)
		self.addFlowRate(self.oldFlowRate)
		self.addTemperatureOrbits(endpoints, self.supportLayersTemperature, z)
		self.distanceFeedRate.addLinesSetAbsoluteDistanceMode(self.supportEndLines)
		self.distanceFeedRate.addLine('(</supportLayer>)')

	def addSupportSegmentTable( self, layerIndex ):
		'Add support segments from the boundary layers.'
		aboveLayer = self.boundaryLayers[ layerIndex + 1 ]
		aboveLoops = aboveLayer.loops
		supportLayer = self.supportLayers[layerIndex]
		if len( aboveLoops ) < 1:
			return
		boundaryLayer = self.boundaryLayers[layerIndex]
		rise = aboveLayer.z - boundaryLayer.z
		outsetSupportLoops = intercircle.getInsetSeparateLoopsFromLoops(boundaryLayer.loops, -self.minimumSupportRatio * rise)
		numberOfSubSteps = 4
		subStepSize = self.interfaceStep / float( numberOfSubSteps )
		aboveIntersectionsTable = {}
		euclidean.addXIntersectionsFromLoopsForTable( aboveLoops, aboveIntersectionsTable, subStepSize )
		outsetIntersectionsTable = {}
		euclidean.addXIntersectionsFromLoopsForTable( outsetSupportLoops, outsetIntersectionsTable, subStepSize )
		euclidean.subtractXIntersectionsTable( aboveIntersectionsTable, outsetIntersectionsTable )
		for aboveIntersectionsTableKey in aboveIntersectionsTable.keys():
			supportIntersectionsTableKey = int( round( float( aboveIntersectionsTableKey ) / numberOfSubSteps ) )
			xIntersectionIndexList = []
			if supportIntersectionsTableKey in supportLayer.xIntersectionsTable:
				euclidean.addXIntersectionIndexesFromXIntersections( 0, xIntersectionIndexList, supportLayer.xIntersectionsTable[ supportIntersectionsTableKey ] )
			euclidean.addXIntersectionIndexesFromXIntersections( 1, xIntersectionIndexList, aboveIntersectionsTable[ aboveIntersectionsTableKey ] )
			supportLayer.xIntersectionsTable[ supportIntersectionsTableKey ] = euclidean.getJoinOfXIntersectionIndexes( xIntersectionIndexList )

	def addTemperatureLineIfDifferent(self, temperature):
		'Add a line of temperature if different.'
		if temperature == None:
			return
		temperatureOutputString = euclidean.getRoundedToThreePlaces(temperature)
		if temperatureOutputString == self.oldTemperatureOutputString:
			return
		if temperatureOutputString != None:
			self.distanceFeedRate.addLine('M104 S' + temperatureOutputString) # Set temperature.
		self.oldTemperatureOutputString = temperatureOutputString

	def addTemperatureOrbits( self, endpoints, temperature, z ):
		'Add the temperature and orbits around the support layer.'
		if self.layerIndex < 0:
			return
		boundaryLoops = self.boundaryLayers[self.layerIndex].loops
		temperatureTimeChange = self.getTemperatureChangeTime( temperature )
		self.addTemperatureLineIfDifferent( temperature )
		if len( boundaryLoops ) < 1:
			layerCornerHigh = complex(-987654321.0, -987654321.0)
			layerCornerLow = complex(987654321.0, 987654321.0)
			for endpoint in endpoints:
				layerCornerHigh = euclidean.getMaximum( layerCornerHigh, endpoint.point )
				layerCornerLow = euclidean.getMinimum( layerCornerLow, endpoint.point )
			squareLoop = euclidean.getSquareLoopWiddershins( layerCornerLow, layerCornerHigh )
			intercircle.addOrbitsIfLarge( self.distanceFeedRate, squareLoop, self.orbitalFeedRatePerSecond, temperatureTimeChange, z )
			return
		edgeInset = 0.4 * self.edgeWidth
		insetBoundaryLoops = intercircle.getInsetLoopsFromLoops(boundaryLoops, edgeInset)
		if len( insetBoundaryLoops ) < 1:
			insetBoundaryLoops = boundaryLoops
		largestLoop = euclidean.getLargestLoop( insetBoundaryLoops )
		intercircle.addOrbitsIfLarge( self.distanceFeedRate, largestLoop, self.orbitalFeedRatePerSecond, temperatureTimeChange, z )

	def addToFillXIntersectionIndexTables( self, supportLayer ):
		'Add fill segments from the boundary layers.'
		supportLoops = supportLayer.supportLoops
		supportLayer.fillXIntersectionsTable = {}
		if len(supportLoops) < 1:
			return
		euclidean.addXIntersectionsFromLoopsForTable( supportLoops, supportLayer.fillXIntersectionsTable, self.interfaceStep )

	def extendXIntersections( self, loops, radius, xIntersectionsTable ):
		'Extend the support segments.'
		xIntersectionsTableKeys = xIntersectionsTable.keys()
		for xIntersectionsTableKey in xIntersectionsTableKeys:
			lineSegments = euclidean.getSegmentsFromXIntersections( xIntersectionsTable[ xIntersectionsTableKey ], xIntersectionsTableKey )
			xIntersectionIndexList = []
			loopXIntersections = []
			euclidean.addXIntersectionsFromLoops( loops, loopXIntersections, xIntersectionsTableKey )
			for lineSegmentIndex in xrange( len( lineSegments ) ):
				lineSegment = lineSegments[ lineSegmentIndex ]
				extendedLineSegment = getExtendedLineSegment( radius, lineSegment, loopXIntersections )
				if extendedLineSegment != None:
					euclidean.addXIntersectionIndexesFromSegment( lineSegmentIndex, extendedLineSegment, xIntersectionIndexList )
			xIntersections = euclidean.getJoinOfXIntersectionIndexes( xIntersectionIndexList )
			if len( xIntersections ) > 0:
				xIntersectionsTable[ xIntersectionsTableKey ] = xIntersections
			else:
				del xIntersectionsTable[ xIntersectionsTableKey ]

	def getCraftedGcode(self, gcodeText, repository):
		'Parse gcode text and store the raft gcode.'
		self.repository = repository
		self.minimumSupportRatio = math.tan( math.radians( repository.supportMinimumAngle.value ) )
		self.supportEndLines = settings.getAlterationFileLines(repository.nameOfSupportEndFile.value)
		self.supportStartLines = settings.getAlterationFileLines(repository.nameOfSupportStartFile.value)
		self.lines = archive.getTextLines(gcodeText)
		self.parseInitialization()
		self.temperatureChangeTimeBeforeRaft = 0.0
		if self.repository.initialCircling.value:
			maxBaseInterfaceTemperature = max(self.baseTemperature, self.interfaceTemperature)
			firstMaxTemperature = max(maxBaseInterfaceTemperature, self.objectFirstLayerPerimeterTemperature)
			self.temperatureChangeTimeBeforeRaft = self.getTemperatureChangeTime(firstMaxTemperature)
		if repository.addRaftElevateNozzleOrbitSetAltitude.value:
			self.addRaft()
		self.addTemperatureLineIfDifferent( self.objectFirstLayerPerimeterTemperature )
		for line in self.lines[self.lineIndex :]:
			self.parseLine(line)
		return gcodec.getGcodeWithoutDuplication('M108', self.distanceFeedRate.output.getvalue())

	def getElevatedBoundaryLine( self, splitLine ):
		'Get elevated boundary gcode line.'
		location = gcodec.getLocationFromSplitLine(None, splitLine)
		if self.operatingJump != None:
			location.z += self.operatingJump
		return self.distanceFeedRate.getBoundaryLine( location )

	def getInsetLoops( self, boundaryLayerIndex ):
		'Inset the support loops if they are not already inset.'
		if boundaryLayerIndex not in self.insetTable:
			self.insetTable[ boundaryLayerIndex ] = intercircle.getInsetSeparateLoopsFromLoops(self.boundaryLayers[ boundaryLayerIndex ].loops, self.quarterEdgeWidth)
		return self.insetTable[ boundaryLayerIndex ]

	def getInsetLoopsAbove( self, boundaryLayerIndex ):
		'Get the inset loops above the boundary layer index.'
		for aboveLayerIndex in xrange( boundaryLayerIndex + 1, len(self.boundaryLayers) ):
			if len( self.boundaryLayers[ aboveLayerIndex ].loops ) > 0:
				return self.getInsetLoops( aboveLayerIndex )
		return []

	def getInsetLoopsBelow( self, boundaryLayerIndex ):
		'Get the inset loops below the boundary layer index.'
		for belowLayerIndex in xrange( boundaryLayerIndex - 1, - 1, - 1 ):
			if len( self.boundaryLayers[ belowLayerIndex ].loops ) > 0:
				return self.getInsetLoops( belowLayerIndex )
		return []

	def getStepsUntilEnd( self, begin, end, stepSize ):
		'Get steps from the beginning until the end.'
		step = begin
		steps = []
		while step < end:
			steps.append( step )
			step += stepSize
		return steps

	def getSupportEndpoints(self):
		'Get the support layer segments.'
		if len(self.supportLayers) <= self.layerIndex:
			return []
		supportSegmentTable = self.supportLayers[self.layerIndex].supportSegmentTable
		if self.layerIndex % 2 == 1 and self.repository.supportCrossHatch.value:
			return getVerticalEndpoints(supportSegmentTable, self.interfaceStep, 0.1 * self.edgeWidth, self.interfaceStep)
		return euclidean.getEndpointsFromSegmentTable(supportSegmentTable)

	def getTemperatureChangeTime( self, temperature ):
		'Get the temperature change time.'
		if temperature == None:
			return 0.0
		oldTemperature = 25.0 # typical chamber temperature
		if self.oldTemperatureOutputString != None:
			oldTemperature = float( self.oldTemperatureOutputString )
		if temperature == oldTemperature:
			return 0.0
		if temperature > oldTemperature:
			return ( temperature - oldTemperature ) / self.heatingRate
		return ( oldTemperature - temperature ) / abs( self.coolingRate )

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(<baseTemperature>':
				self.baseTemperature = float(splitLine[1])
			elif firstWord == '(<coolingRate>':
				self.coolingRate = float(splitLine[1])
			elif firstWord == '(<edgeWidth>':
				self.edgeWidth = float(splitLine[1])
				self.halfEdgeWidth = 0.5 * self.edgeWidth
				self.quarterEdgeWidth = 0.25 * self.edgeWidth
				self.supportOutset = self.edgeWidth + self.edgeWidth * self.repository.supportGapOverPerimeterExtrusionWidth.value
			elif firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addTagBracketedProcedure('raft')
			elif firstWord == '(<heatingRate>':
				self.heatingRate = float(splitLine[1])
			elif firstWord == '(<interfaceTemperature>':
				self.interfaceTemperature = float(splitLine[1])
			elif firstWord == '(<layer>':
				return
			elif firstWord == '(<layerHeight>':
				self.layerHeight = float(splitLine[1])
			elif firstWord == 'M108':
				self.oldFlowRate = float(splitLine[1][1 :])
			elif firstWord == '(<objectFirstLayerFeedRateInfillMultiplier>':
				self.objectFirstLayerFeedRateInfillMultiplier = float(splitLine[1])
			elif firstWord == '(<objectFirstLayerFlowRateInfillMultiplier>':
				self.objectFirstLayerFlowRateInfillMultiplier = float(splitLine[1])
			elif firstWord == '(<objectFirstLayerInfillTemperature>':
				self.objectFirstLayerInfillTemperature = float(splitLine[1])
			elif firstWord == '(<objectFirstLayerPerimeterTemperature>':
				self.objectFirstLayerPerimeterTemperature = float(splitLine[1])
			elif firstWord == '(<objectNextLayersTemperature>':
				self.objectNextLayersTemperature = float(splitLine[1])
			elif firstWord == '(<orbitalFeedRatePerSecond>':
				self.orbitalFeedRatePerSecond = float(splitLine[1])
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.operatingFeedRateMinute = 60.0 * float(splitLine[1])
				self.feedRateMinute = self.operatingFeedRateMinute
			elif firstWord == '(<operatingFlowRate>':
				self.operatingFlowRate = float(splitLine[1])
				self.oldFlowRate = self.operatingFlowRate
				self.supportFlowRate = self.operatingFlowRate * self.repository.supportFlowRateOverOperatingFlowRate.value
			elif firstWord == '(<sharpestProduct>':
				self.sharpestProduct = float(splitLine[1])
			elif firstWord == '(<supportLayersTemperature>':
				self.supportLayersTemperature = float(splitLine[1])
			elif firstWord == '(<supportedLayersTemperature>':
				self.supportedLayersTemperature = float(splitLine[1])
			elif firstWord == '(<travelFeedRatePerSecond>':
				self.travelFeedRateMinute = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)

	def parseLine(self, line):
		'Parse a gcode line and add it to the raft skein.'
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if firstWord == 'G1':
			if self.extrusionStart:
				self.addRaftedLine(splitLine)
				return
		elif firstWord == 'M101':
			if self.isStartupEarly:
				self.isStartupEarly = False
				return
		elif firstWord == 'M108':
			self.oldFlowRate = float(splitLine[1][1 :])
		elif firstWord == '(<boundaryPoint>':
			line = self.getElevatedBoundaryLine(splitLine)
		elif firstWord == '(</crafting>)':
			self.extrusionStart = False
			self.distanceFeedRate.addLine( self.operatingLayerEndLine )
		elif firstWord == '(<layer>':
			self.layerIndex += 1
			settings.printProgress(self.layerIndex, 'raft')
			boundaryLayer = None
			layerZ = self.extrusionTop + float(splitLine[1])
			if len(self.boundaryLayers) > 0:
				boundaryLayer = self.boundaryLayers[self.layerIndex]
				layerZ = boundaryLayer.z
			if self.operatingJump != None:
				line = '(<layer> %s )' % self.distanceFeedRate.getRounded( layerZ )
			if self.layerStarted and self.addLineLayerStart:
				self.distanceFeedRate.addLine('(</layer>)')
			self.layerStarted = False
			if self.layerIndex > len(self.supportLayers) + 1:
				self.distanceFeedRate.addLine( self.operatingLayerEndLine )
				self.operatingLayerEndLine = ''
			if self.addLineLayerStart:
				self.distanceFeedRate.addLine(line)
			self.addLineLayerStart = True
			line = ''
			endpoints = self.getSupportEndpoints()
			if self.layerIndex == 1:
				if len(endpoints) < 1:
					temperatureChangeTimeBeforeNextLayers = self.getTemperatureChangeTime( self.objectNextLayersTemperature )
					self.addTemperatureLineIfDifferent( self.objectNextLayersTemperature )
					if self.repository.addRaftElevateNozzleOrbitSetAltitude.value and len( boundaryLayer.loops ) > 0:
						self.addOperatingOrbits( boundaryLayer.loops, euclidean.getXYComplexFromVector3( self.oldLocation ), temperatureChangeTimeBeforeNextLayers, layerZ )
			if len(endpoints) > 0:
				self.addSupportLayerTemperature( endpoints, layerZ )
		elif firstWord == '(<edge>' or firstWord == '(<edgePath>)':
			self.isEdgePath = True
		elif firstWord == '(</edge>)' or firstWord == '(</edgePath>)':
			self.isEdgePath = False
		self.distanceFeedRate.addLine(line)

	def setBoundaryLayers(self):
		'Set the boundary layers.'
		if self.repository.supportChoiceNone.value:
			return
		if len(self.boundaryLayers) < 2:
			return
		if self.repository.supportChoiceEmptyLayersOnly.value:
			supportLayer = SupportLayer([])
			self.supportLayers.append(supportLayer)
			for boundaryLayerIndex in xrange(1, len(self.boundaryLayers) -1):
				self.addEmptyLayerSupport(boundaryLayerIndex)
			self.truncateSupportSegmentTables()
			self.addSegmentTablesToSupportLayers()
			return
		for boundaryLayer in self.boundaryLayers:
			# thresholdRadius of 0.8 is needed to avoid the ripple inset bug http://hydraraptor.blogspot.com/2010/12/crackers.html
			supportLoops = intercircle.getInsetSeparateLoopsFromLoops(boundaryLayer.loops, -self.supportOutset, 0.8)
			supportLayer = SupportLayer(supportLoops)
			self.supportLayers.append(supportLayer)
		for supportLayerIndex in xrange(len(self.supportLayers) - 1):
			self.addSupportSegmentTable(supportLayerIndex)
		self.truncateSupportSegmentTables()
		for supportLayerIndex in xrange(len(self.supportLayers) - 1):
			boundaryLoops = self.boundaryLayers[supportLayerIndex].loops
			self.extendXIntersections( boundaryLoops, self.supportOutset, self.supportLayers[supportLayerIndex].xIntersectionsTable)
		for supportLayer in self.supportLayers:
			self.addToFillXIntersectionIndexTables(supportLayer)
		if self.repository.supportChoiceExteriorOnly.value:
			for supportLayerIndex in xrange(1, len(self.supportLayers)):
				self.subtractJoinedFill(supportLayerIndex)
		for supportLayer in self.supportLayers:
			euclidean.subtractXIntersectionsTable(supportLayer.xIntersectionsTable, supportLayer.fillXIntersectionsTable)
		for supportLayerIndex in xrange(len(self.supportLayers) - 2, -1, -1):
			xIntersectionsTable = self.supportLayers[supportLayerIndex].xIntersectionsTable
			aboveXIntersectionsTable = self.supportLayers[supportLayerIndex + 1].xIntersectionsTable
			euclidean.joinXIntersectionsTables(aboveXIntersectionsTable, xIntersectionsTable)
		for supportLayerIndex in xrange(len(self.supportLayers)):
			supportLayer = self.supportLayers[supportLayerIndex]
			self.extendXIntersections(supportLayer.supportLoops, self.raftOutsetRadius, supportLayer.xIntersectionsTable)
		for supportLayer in self.supportLayers:
			euclidean.subtractXIntersectionsTable(supportLayer.xIntersectionsTable, supportLayer.fillXIntersectionsTable)
		self.addSegmentTablesToSupportLayers()

	def setCornersZ(self):
		'Set maximum and minimum corners and z.'
		boundaryLoop = None
		boundaryLayer = None
		layerIndex = - 1
		self.cornerMaximumComplex = complex(-912345678.0, -912345678.0)
		self.cornerMinimum = Vector3(912345678.0, 912345678.0, 912345678.0)
		self.firstLayerLoops = []
		for line in self.lines[self.lineIndex :]:
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			if firstWord == '(</boundaryPerimeter>)':
				boundaryLoop = None
			elif firstWord == '(<boundaryPoint>':
				location = gcodec.getLocationFromSplitLine(None, splitLine)
				if boundaryLoop == None:
					boundaryLoop = []
					boundaryLayer.loops.append(boundaryLoop)
				boundaryLoop.append(location.dropAxis())
				self.cornerMaximumComplex = euclidean.getMaximum(self.cornerMaximumComplex, location.dropAxis())
				self.cornerMinimum.minimize(location)
			elif firstWord == '(<layer>':
				z = float(splitLine[1])
				boundaryLayer = euclidean.LoopLayer(z)
				self.boundaryLayers.append(boundaryLayer)
			elif firstWord == '(<layer>':
				layerIndex += 1
				if self.repository.supportChoiceNone.value:
					if layerIndex > 1:
						return

	def subtractJoinedFill( self, supportLayerIndex ):
		'Join the fill then subtract it from the support layer table.'
		supportLayer = self.supportLayers[supportLayerIndex]
		fillXIntersectionsTable = supportLayer.fillXIntersectionsTable
		belowFillXIntersectionsTable = self.supportLayers[ supportLayerIndex - 1 ].fillXIntersectionsTable
		euclidean.joinXIntersectionsTables( belowFillXIntersectionsTable, supportLayer.fillXIntersectionsTable )
		euclidean.subtractXIntersectionsTable( supportLayer.xIntersectionsTable, supportLayer.fillXIntersectionsTable )

	def truncateSupportSegmentTables(self):
		'Truncate the support segments after the last support segment which contains elements.'
		for supportLayerIndex in xrange( len(self.supportLayers) - 1, - 1, - 1 ):
			if len( self.supportLayers[supportLayerIndex].xIntersectionsTable ) > 0:
				self.supportLayers = self.supportLayers[ : supportLayerIndex + 1 ]
				return
		self.supportLayers = []


class SupportLayer:
	'Support loops with segment tables.'
	def __init__( self, supportLoops ):
		self.supportLoops = supportLoops
		self.supportSegmentTable = {}
		self.xIntersectionsTable = {}

	def __repr__(self):
		'Get the string representation of this loop layer.'
		return '%s' % ( self.supportLoops )


def main():
	'Display the raft dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
