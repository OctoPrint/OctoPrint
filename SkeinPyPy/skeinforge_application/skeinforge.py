#!/usr/bin/python
"""
This page is in the table of contents.
==Overview==
===Introduction===
Skeinforge is a GPL tool chain to forge a gcode skein for a model.

The tool chain starts with carve, which carves the model into layers, then the layers are modified by other tools in turn like fill, comb, tower, raft, stretch, hop, wipe, fillet & export.  Each tool automatically gets the gcode from the previous tool.  So if you want a carved & filled gcode, call the fill tool and it will call carve, then it will fill and output the gcode.  If you want to use all the tools, call export and it will call in turn all the other tools down the chain to produce the gcode file.

If you do not want a tool after preface to modify the output, deselect the Activate checkbox for that tool.  When the Activate checkbox is off, the tool will just hand off the gcode to the next tool without modifying it.

The skeinforge module provides a single place to call up all the setting dialogs.  When the 'Skeinforge' button is clicked, skeinforge calls export, since that is the end of the chain.

The plugin buttons which are commonly used are bolded and the ones which are rarely used have normal font weight.

There are also tools which handle settings for the chain, like polyfile.

The analyze tool calls plugins in the analyze_plugins folder, which will analyze the gcode in some way when it is generated if their Activate checkbox is selected.

The interpret tool accesses and displays the import plugins.

The default settings are similar to those on Nophead's machine.  A setting which is often different is the 'Layer Height' in carve.

===Command Line Interface===
To bring up the skeinforge dialog without a file name, type:
python skeinforge_application/skeinforge.py

Slicing a file from skeinforge_utilities/skeinforge_craft.py, for example:
python skeinforge_application/skeinforge_utilities/skeinforge_craft.py test.stl

will slice the file and exit. This is the correct option for programs which use skeinforge to only generate a gcode file.

Slicing a file from skeinforge.py, for example:
python skeinforge_application/skeinforge.py test.stl

will slice the file and bring up the skeinforge window and the analyze windows and then skeinforge will wait for user input.

Slicing a file from skeinforge_plugins/craft.py, for example:
python skeinforge_application/skeinforge_plugins/craft.py test.stl

will slice the file and bring up the analyze windows only and then skeinforge will wait for user input.

===Contribute===
You can contribute by helping develop the manual at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge

There is also a forum thread about how to contribute to skeinforge development at:
http://dev.forums.reprap.org/read.php?12,27562

I will only reply to emails from contributors or to complete bug reports.

===Documentation===
There is a manual at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge

There is also documentation is in the documentation folder, in the doc strings for each module and it can be called from the '?' button or the menu or by clicking F1 in each setting dialog.

A list of other tutorials is at:
http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge#Tutorials

Skeinforge tagged pages on thingiverse can be searched for at:
http://www.thingiverse.com/search?cx=015525747728168968820%3Arqnsgx1xxcw&cof=FORID%3A9&ie=UTF-8&q=skeinforge&sa=Search&siteurl=www.thingiverse.com%2F#944

===Fabrication===
To fabricate a model with gcode and the Arduino you can use the send.py in the fabricate folder.  The documentation for it is in the folder as send.html and at:
http://reprap.org/bin/view/Main/ArduinoSend

Another way is to use an EMC2 or similar computer controlled milling machine, as described in the "ECM2 based repstrap" forum thread at:
http://forums.reprap.org/read.php?1,12143

using the M-Apps package, which is at:
http://forums.reprap.org/file.php?1,file=772

Another way is to use Zach's ReplicatorG at:
http://replicat.org/

There is also an older Processing script at:
http://reprap.svn.sourceforge.net/viewvc/reprap/trunk/users/hoeken/arduino/GCode_Host/

Yet another way is to use the reprap host, written in Java, to load and print gcode:
http://dev.www.reprap.org/bin/view/Main/DriverSoftware#Load_GCode

For jogging, the Metalab group wrote their own exerciser, also in Processing:
http://reprap.svn.sourceforge.net/viewvc/reprap/trunk/users/metalab/processing/GCode_Exerciser/

The Metalab group has descriptions of skeinforge in action and their adventures are described at:
http://reprap.soup.io/

There is a board about printing issues at:
http://www.bitsfrombytes.com/fora/user/index.php?board=5.0

You can buy the Rapman (an improved Darwin) from Bits from Bytes at:
http://www.bitsfrombytes.com/

You can buy the Makerbot from Makerbot Industries at:
http://www.makerbot.com/

===File Formats===
An explanation of the gcodes is at:
http://reprap.org/bin/view/Main/Arduino_GCode_Interpreter

and at:
http://reprap.org/bin/view/Main/MCodeReference

A gode example is at:
http://forums.reprap.org/file.php?12,file=565

The settings are saved as tab separated .csv files in the .skeinforge folder in your home directory.  The settings can be set in the tool dialogs.  The .csv files can also be edited with a text editor or a spreadsheet program set to separate tabs.

The Scalable Vector Graphics file produced by vectorwrite can be opened by an SVG viewer or an SVG capable browser like Mozilla:
http://www.mozilla.com/firefox/

A good triangle surface format is the GNU Triangulated Surface format, which is supported by Mesh Viewer and described at:
http://gts.sourceforge.net/reference/gts-surfaces.html#GTS-SURFACE-WRITE

You can export GTS files from Art of Illusion with the Export GNU Triangulated Surface.bsh script in the Art of Illusion Scripts folder.

STL is an inferior triangle surface format, described at:
http://en.wikipedia.org/wiki/STL_(file_format)

If you're using an STL file and you can't even carve it, try converting it to a GNU Triangulated Surface file in Art of Illusion.  If it still doesn't carve, then follow the advice in the troubleshooting section.

===Getting Skeinforge===
The latest version is at:
http://members.axion.net/~enrique/reprap_python_beanshell.zip

a sometimes out of date version is in the last reprap_python_beanshell.zip attachment in the last post of the Fabmetheus blog at:
http://fabmetheus.blogspot.com/

another sometimes out of date version is at:
https://reprap.svn.sourceforge.net/svnroot/reprap/trunk/reprap/miscellaneous/python-beanshell-scripts/

===Getting Started===
For skeinforge to run, install python 2.x on your machine, which is available from:
http://www.python.org/download/

To use the settings dialog you'll also need Tkinter, which probably came with the python installation.  If it did not, look for it at:
http://www.tcl.tk/software/tcltk/

If you want python and Tkinter together on MacOS, you can try:
http://www.astro.washington.edu/users/rowen/ROPackage/Overview.html

If you want python and Tkinter together on all platforms and don't mind filling out forms, you can try the ActivePython package from Active State at:
http://www.activestate.com/Products/activepython/feature_list.mhtml

The computation intensive python modules will use psyco if it is available and run about twice as fast.  Psyco is described at:
http://psyco.sourceforge.net/index.html

The psyco download page is:
http://psyco.sourceforge.net/download.html

Skeinforge imports Stereolithography (.stl) files or GNU Triangulated Surface (.gts) files.  If importing an STL file directly doesn't work, an indirect way to import an STL file is by turning it into a GTS file is by using the Export GNU Triangulated Surface script at:
http://members.axion.net/~enrique/Export%20GNU%20Triangulated%20Surface.bsh

The Export GNU Triangulated Surface script is also in the Art of Illusion folder, which is in the same folder as skeinforge.py.  To bring the script into Art of Illusion, drop it into the folder ArtOfIllusion/Scripts/Tools/.  Then import the STL file using the STL import plugin in the import submenu of the Art of Illusion file menu.  Then from the Scripts submenu in the Tools menu, choose 'Export GNU Triangulated Surface' and select the imported STL shape.  Click the 'Export Selected' checkbox and click OK. Once you've created the GTS file, you can turn it into gcode by typing in a shell in the same folder as skeinforge:
> python skeinforge.py

When the skeinforge dialog pops up, click 'Skeinforge', choose the file which you exported in 'Export GNU Triangulated Surface' and the gcode file will be saved with the suffix '_export.gcode'.

Or you can turn files into gcode by adding the file name, for example:
> python skeinforge.py Screw Holder Bottom.stl

===License===
GNU Affero General Public License
http://www.gnu.org/licenses/agpl.html

===Motto===
I may be slow, but I get there in the end.

===Troubleshooting===
If there's a bug, try downloading the very latest version because skeinforge is often updated without an announcement.  The very latest version is at:
http://members.axion.net/~enrique/reprap_python_beanshell.zip

If there is still a bug, then first prepare the following files:

1. stl file
2. pictures explaining the problem
3. your settings (pack the whole .skeinforge directory with all your settings) 
4. alterations folder, if you have any active alterations files

Then zip all the files.

Second, write a description of the error, send the description and the archive to the developer, enrique ( perez_enrique AT yahoo.com.removethispart ). After a bug fix is released, test the new version and report the results to enrique, whether the fix was successful or not.

If the dialog window is too big for the screen, on most Linux window managers you can move a window by holding down the Alt key and then drag the window with the left mouse button to get to the off screen widgets.

If you can't use the graphical interface, you can change the settings for skeinforge by using a text editor or spreadsheet to change the settings in the profiles folder in the .skeinforge folder in your home directory.

Comments and suggestions are welcome, however, I won't reply unless you are a contributor.  Likewise, I will only answer your questions if you contribute to skeinforge in some way.  Some ways of contributing to skeinforge are in the contributions thread at:
http://dev.forums.reprap.org/read.php?12,27562

You could also contribute articles to demozendium on any topic:
http://fabmetheus.crsndoo.com/wiki/index.php/Main_Page

If you contribute in a significant way to another open source project, I will consider that also.

When I answered everyone's questions, eventually I received more questions than I had time to answer, so now I only answer questions from contributors.

I reserve the right to make any correspondence public.  Do not send me any correspondence marked confidential.  If you do I will delete it.


==Examples==
The following examples forge the STL file Screw Holder.stl.  The examples are run in a terminal in the folder which contains Screw Holder.gts and skeinforge.py.

> python skeinforge.py
This brings up the dialog, after clicking 'Skeinforge', the following is printed:
The exported file is saved as Screw Holder_export.gcode

> python skeinforge.py Screw Holder.stl
The exported file is saved as Screw Holder_export.gcode

To run only fill for example, type in the craft_plugins folder which fill is in:
> python fill.py

"""

from __future__ import absolute_import
import __init__

from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import archive
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import settings
from optparse import OptionParser
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import os
import sys
import platform
import subprocess


# document raft, stretch, then carve, comb, fill, inset, oozebane, splodge, temperature, speed once they are updated
# wiki document help, description, polyfile
# subplugins like export static, maybe later mill cut and coil plugins, maybe later still export plugins & change file extension to output file extension  http://fabmetheus.crsndoo.com/wiki/index.php/Skeinforge
#
# backup demozendium links
# replace replace baseLayerThickness.. with baseLayerHeightMultiplier
# announce layer thickness with layer height
#
# unimportant
# minor outline problem when an end path goes through a path, like in the letter A
# view profile 1 mm thickness
# analyze doesn't save skeinlayer settings, remember xy in skeiniso
#
#
#
# question, should 'Infill Odd Layer Extra Rotation' be dropped
# consolidate Object First Layer Flow
#
# retraction step leave
# melt _extrusion
# think about http://code.google.com/p/skeinarchiver/ and/or undo
# add volume fraction to fill
# getStrokeRadius default to edgeWidth
# look at loop end removed bug in upper loop of layer 8 of Screw_Holder_alteration
# fix tower edge line start problem
# check globalExecutionOrder, ensure that bottom order is really high
# set temperature in temperature
# maybe rename geometry_plugins xml
# maybe add carve preview, opening it up in browser
# dwindle or dawdle or taper
# voronoi average location intersection looped inset intercircles
# skin layers without something over the infill
# check for last existing then remove unneeded fill code (getLastExistingFillLoops) from euclidean, add fill in penultimate loops, if there is no fill it should not use edge - skin should work
# delete commented addInfillPerimeter
# unpause slow flow rate instead of speeding feed rate
# maybe in svgReader if loop intersection with previous union else add
# add links download manual svg_writer, add left right arrow keys to layer
# delete location from wipe, in other words Arrival X instead of Location Arrival X, also convert Location Arrival to Arrival Location
# command
# manipulation derivations
# cutting ahmet
#
# When opening a file for craft I wondered if there is an option to set the file type to .stl as it currently defaults to .xml
# then add Retraction Scaling Exponent
# check inset loop for intersection with loopLayer.loops
# maybe make vectorwrite prominent, not skeiniso, probably not because it doesn't work on Mac
# close, getPillarByLoopLists, addConcave, polymorph original graph section, loop, add step object, add continuous object
# chamber: heated bed off at a layer http://blog.makerbot.com/2011/03/17/if-you-cant-stand-the-heat/
# profile copy / rename   /   delete, maybe move craft type to profile
# think about rectangular getVector3RemoveByPre..
# del previous, add begin & end if far  get actual path
# bridge infill modifiers only in the bridge infill loop
# linearbearingexample 15 x 1 x 2, linearbearingcage
# polling
# connectionfrom, to, connect, xaxis
# move replace from export to alterations
# lathe, transform normal in getRemaining, getConnection
# add overview link to crnsdoo index and svg page
# getConnection of some kind like getConnectionVertexes, getConnection
# incorporate actual thickness from feed rate and flow rate in statistics for dimension
# update stretch pictures By design, distance between parallel sides in hexagonal hole are 13mm, 7mm, 6.5mm, round hole diameter's are 8mm, 4mm and 3mm. http://fabmetheus.crsndoo.com/wiki/images/Stretch.png http://fabmetheus.crsndoo.com/wiki/images/thumb/NormalHole.png/180px-NormalHole.png http://fabmetheus.crsndoo.com/wiki/images/thumb/StretchDeformedHole.png/180px-StretchDeformedHole.png
# xml_creation
# 'fileName, text, repository' commandLineInterface
# delete: text = text.replace(('\nName                          %sValue\n' % globalSpreadsheetSeparator), ('\n_Name                          %sValue\n' % globalSpreadsheetSeparator))
# comment search from home panel when there is an input field
#
#
# multiply to table + boundary bedBound bedWidth bedHeight bedFile.csv
# getNormal, getIsFlat?
# info statistics, procedures, xml if any
# test solid arguments
# combine xmlelement with csvelement using example.csv & geometry.csv, csv _format, _column, _row, _text
# pixel, voxel, surfaxel/boxel, lattice, mesh
# probably not replace getOverlapRatio with getOverlap if getOverlapRatio is never small, always 0.0
# mesh. for cube, then cylinder, then sphere after lathe
# dimension extrude diameter, density
# superformula http://www.thingiverse.com/thing:12419
# maybe get rid of testLoops once they are no longer needed
# thermistor lookup table
# stretch maybe add back addAlong
# import, write, copy examples
# maybe remove default warnings from scale, rotate, translate, transform
# easy helix
# write tool; maybe write one deep
#
#
# tube
# rotor
# coin
# demozendium privacy policy, maybe thumbnail logo
# pymethe
# test translate
# full lathe
# pyramid
# round extrusion ?, fillet
# make html statistics, move statistics to folder
# manipulate solid, maybe manipulate around elements
# boolean loop corner outset
# mechaslab advanced drainage, shingles
# dovetail
# maybe not getNewObject, getNew, addToBoolean
# work out close and radius
# maybe have add function as well as append for list and string
# maybe move and give geometryOutput to cube, cylinder, sphere
#
# maybe move widen before bottom
# maybe add 1 to max layer input to iso in layer_template.svg
# maybe save all generated_files option
# table to dictionary
# remove cool set at end of layer
# add fan on when hot in chamber
# maybe measuring rod
# getLayerHeight from xml
# maybe center for xy plane
# remove comments from clip, bend
# winding into coiling, coil into wind & weave
# later, precision
# documentation
# http://wiki.makerbot.com/configuring-skeinforge
#
#
# remove index from CircleIntersection remove ahead or behind from CircleIntersection _speed
# probably not speed up CircleIntersection by performing isWithinCircles before creation _speed
# don't remove brackets in early craft tools _speed
# check bounding box when subtracting or intersecting boolean geometry
# get arounds in inset, the inside become extrude loops and the outside below loops _speed
#
#
# add hook _extrusion
# integral thin width _extrusion
# layer color, for multilayer start http://reprap.org/pub/Main/MultipleMaterialsFiles/legend.xml _extrusion
# maybe raft triple layer base, middle interface with hot loop or ties
# somehow, add pattern to outside, http://blog.makerbot.com/2010/09/03/lampshades/
# implement acceleration & collinear removal in penultimate viewers _extrusion
#
# rename skeinforge_profile.addListsToCraftTypeRepository to skeinforge_profile.addToCraftTypeRepository after skirt
# basic basedit tool
# arch, ceiling
# meta setting, rename setting _setting
# add polish, has edge, has cut first layer (False)
# probably not set addedLocation in distanceFeedRate after arc move
# maybe horizontal bridging and/or check to see if the ends are standing on anything
# thin self? check when removing intersecting paths in inset
# save all analyze viewers of the same name except itself, update help menu self.wikiManualPrimary.setUpdateFunction
# check alterations folder first, if there is something copy it to the home directory, if not check the home directory
# add links to demozendium in help
# maybe add hop only if long option
#
#
#
# help primary menu item refresh
# add plugin help menu, add craft below menu
# give option of saving when switching profiles
# xml & svg more forgiving, svg make defaults for layerHeight
# option of surrounding lines in display
# maybe add connecting line in display line
# maybe check inset loops to see if they are smaller, but this would be slow
# maybe status bar
# maybe measurement ruler mouse tool
# search rss from blogs, add search links for common materials, combine created on or progress bar with searchable help
# boundaries, center radius z bottom top, alterations file, circular or rectangular, polygon, put cool minimum radius orbits within boundaries, <bounds> bound.. </bounds>
# move & rotate model
# possible jitter bug http://cpwebste.blogspot.com/2010/04/hydras-first-print.html
# trial, meta in a grid settings
# maybe interpret svg_convex_mesh
#laminate tool head
#maybe use 5x5 radius search in circle node
#maybe add layer updates in behold, skeinlayer and maybe others
#lathe winding, extrusion and cutting; synonym for rotation or turning, loop angle
# maybe split into source code and documentation sections
# transform plugins, start with sarrus http://www.thingiverse.com/thing:1425
# maybe make setting backups
# move skeinforge_utilities to fabmetheus_utilities
# maybe lathe cutting
# maybe lathe extrusion
# maybe lathe milling
# maybe lathe winding & weaving
#
#
#
# pick and place
# search items, search links, choice entry field
# svg triangle mesh, svg polygon mesh
# simulate
#transform
# juricator
# probably not run along sparse infill to avoid stops
#custom inclined plane, inclined plane from model, screw, fillet travel as well maybe
# probably not stretch single isLoop
#maybe much afterwards make congajure multistep view
#maybe stripe although model colors alone can handle it
#stretch fiber around shape, maybe modify winding for asymmetric shapes
#multiple heads around edge
#maybe add rarely used tool option
#angle shape for overhang extrusions
#maybe m111? countdown
#first time tool tip
#individual tool tip to place in text
# maybe try to simplify raft layer start
# maybe make temp directory
# maybe carve aoi xml testing and check xml gcode
# maybe cross hatch support polishing???
# maybe print svg view from current layer or zero layer in single view
# maybe check if tower is picking the closest island
# maybe combine skein classes in fillet
# maybe isometric svg option

#Manual
#10,990
#11,1776,786
#12,3304,1528
#1,4960,1656
#2, 7077,2117
#3, 9598,2521
#4 12014,2305
#5 14319,2536
#6 16855,3226
#7 20081, 2189
#8 22270, 2625
#9 24895, 2967, 98
#10 27862, 3433, 110
#11 31295, 3327
#12 34622 
#85 jan7, 86jan11, 87 jan13, 88 jan15, 91 jan21, 92 jan23, 95 jan30, 98 feb6
#make one piece electromagnet spool
#stepper rotor with ceramic disk magnet in middle, electromagnet with long thin spool line?
#stepper motor
#make plastic coated thread in vat with pulley
#tensile stuart platform
#kayak
#gear vacuum pump
#gear turbine
#heat engine
#solar power
#sailboat
#yacht
#house
#condo with reflected gardens in between buildings
#medical equipment
#cell counter, etc..
#pipe clamp lathe
# square tube driller & cutter

# archihedrongagglevoteindexium
# outline images
# look from top of intersection circle plane to look for next, add a node; tree out until all are stepped on then connect, when more than three intersections are close
# when loading a file, we should have a preview of the part and orientation in space
# second (and most important in my opinion) would be the ability to rotate the part on X/Y/Z axis to chose it's orientation
# third, a routine to detect the largest face and orient the part accordingly. Mat http://reprap.kumy.net/
# concept, three perpendicular slices to get display spheres
# extend lines around short segment after cross hatched boolean
# concept, donation, postponement, rotate ad network, cached search options
# concept, local ad server, every time the program runs it changes the iamge which all the documentation points to from a pool of ads
# concept, join cross slices, go from vertex to two orthogonal edges, then from edges to each other, if not to a common point, then simplify polygons by removing points which do not change the area much
# concept, each node is fourfold, use sorted intersectionindexes to find close, connect each double sided edge, don't overlap more than two triangles on an edge
# concept, diamond cross section loops
# concept, in file, store polygon mesh and centers
# concept, display spheres or polygons would have original triangle for work plane
# .. then again no point with slices
# concept, filled slices, about 2 mm thick
# concept, rgb color triangle switch to get inside color, color golden ratio on 5:11 slope with a modulo 3 face
# concept, interlaced bricks at corners ( length proportional to corner angle )
# concept, new links to archi, import links to archi and adds skeinforge tool menu item, back on skeinforge named execute tool is added
# concept, trnsnt
# concept, indexium expand condense remove, single text, pymetheus
# concept, inscribed key silencer
# concept, spreadsheet to python and/or javascript
# concept, range voting for posters, informative, complainer, funny, insightful, rude, spammer, literacy,  troll?
# concept, intermittent cloud with multiple hash functions


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = """
Adrian Bowyer <http://forums.reprap.org/profile.php?12,13>
Brendan Erwin <http://forums.reprap.org/profile.php?12,217>
Greenarrow <http://forums.reprap.org/profile.php?12,81>
Ian England <http://forums.reprap.org/profile.php?12,192>
John Gilmore <http://forums.reprap.org/profile.php?12,364>
Jonwise <http://forums.reprap.org/profile.php?12,716>
Kyle Corbitt <http://forums.reprap.org/profile.php?12,90>
Michael Duffin <http://forums.reprap.org/profile.php?12,930>
Marius Kintel <http://reprap.soup.io/>
Nophead <http://www.blogger.com/profile/12801535866788103677>
PJR <http://forums.reprap.org/profile.php?12,757>
Reece.Arnott <http://forums.reprap.org/profile.php?12,152>
Wade <http://forums.reprap.org/profile.php?12,489>
Xsainnz <http://forums.reprap.org/profile.php?12,563>
Zach Hoeken <http://blog.zachhoeken.com/>

Organizations:
Art of Illusion <http://www.artofillusion.org/>"""
__date__ = '$Date: 2008/02/05 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def addToProfileMenu(profileSelection, profileType, repository):
	'Add a profile menu.'
	pluginFileNames = skeinforge_profile.getPluginFileNames()
	craftTypeName = skeinforge_profile.getCraftTypeName()
	pluginModule = skeinforge_profile.getCraftTypePluginModule()
	profilePluginSettings = settings.getReadRepository(pluginModule.getNewRepository())
	for pluginFileName in pluginFileNames:
		skeinforge_profile.ProfileTypeMenuRadio().getFromMenuButtonDisplay(profileType, pluginFileName, repository, craftTypeName == pluginFileName)
	for profileName in profilePluginSettings.profileList.value:
		skeinforge_profile.ProfileSelectionMenuRadio().getFromMenuButtonDisplay(profileSelection, profileName, repository, profileName == profilePluginSettings.profileListbox.value)

def getNewRepository():
	'Get new repository.'
	return SkeinforgeRepository()

def getPluginFileNames():
	'Get skeinforge plugin fileNames.'
	return archive.getPluginFileNamesFromDirectoryPath(archive.getSkeinforgePluginsPath())

def getRadioPluginsAddPluginGroupFrame(directoryPath, importantFileNames, names, repository):
	'Get the radio plugins and add the plugin frame.'
	repository.pluginGroupFrame = settings.PluginGroupFrame()
	radioPlugins = []
	for name in names:
		radioPlugin = settings.RadioPlugin().getFromRadio(name in importantFileNames, repository.pluginGroupFrame.latentStringVar, name, repository, name == importantFileNames[0])
		radioPlugin.updateFunction = repository.pluginGroupFrame.update
		radioPlugins.append( radioPlugin )
	defaultRadioButton = settings.getSelectedRadioPlugin(importantFileNames + [radioPlugins[0].name], radioPlugins)
	repository.pluginGroupFrame.getFromPath(defaultRadioButton, directoryPath, repository)
	return radioPlugins

def writeOutput(fileName):
	'Craft a file, display dialog.'
	repository = getNewRepository()
	repository.fileNameInput.value = fileName
	repository.execute()


class SkeinforgeRepository:
	'A class to handle the skeinforge settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge.html', self)
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for Skeinforge', self, '')
		self.profileType = settings.MenuButtonDisplay().getFromName('Profile Type: ', self )
		self.profileType.columnspan = 6
		self.profileSelection = settings.MenuButtonDisplay().getFromName('Profile Selection: ', self)
		self.profileSelection.columnspan = 6
		addToProfileMenu( self.profileSelection, self.profileType, self )
		settings.LabelDisplay().getFromName('', self)
		importantFileNames = ['craft', 'profile']
		getRadioPluginsAddPluginGroupFrame(archive.getSkeinforgePluginsPath(), importantFileNames, getPluginFileNames(), self)
		self.executeTitle = 'Skeinforge a file...'
	
	def getPyPyExe(self):
		if platform.system() == "Windows":
			pypyExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../pypy/pypy.exe"));
		else:
			pypyExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../pypy/bin/pypy"));
		if os.path.exists(pypyExe):
			return pypyExe
		pypyExe = "/bin/pypy";
		if os.path.exists(pypyExe):
			return pypyExe
		pypyExe = "/usr/bin/pypy";
		if os.path.exists(pypyExe):
			return pypyExe
		pypyExe = "/usr/local/bin/pypy";
		if os.path.exists(pypyExe):
			return pypyExe
		return False

	def execute(self):
		'Skeinforge button has been clicked.'
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode(self.fileNameInput.value, fabmetheus_interpret.getImportPluginFileNames(), self.fileNameInput.wasCancelled)
		pypyExe = self.getPyPyExe()
		for fileName in fileNames:
			if platform.python_implementation() == "PyPy":
				skeinforge_craft.writeOutput(fileName)
			elif pypyExe == False:
				print "************************************************"
				print "* Failed to find pypy, so slicing with python! *"
				print "************************************************"
				skeinforge_craft.writeOutput(fileName)
				print "************************************************"
				print "* Failed to find pypy, so sliced with python!  *"
				print "************************************************"
			else:
				subprocess.call([pypyExe, __file__, fileName])

	def save(self):
		'Profile has been saved and profile menu should be updated.'
		self.profileType.removeMenus()
		self.profileSelection.removeMenus()
		addToProfileMenu(self.profileSelection, self.profileType, self)
		self.profileType.addRadiosToDialog(self.repositoryDialog)
		self.profileSelection.addRadiosToDialog(self.repositoryDialog)


def main():
	'Display the skeinforge dialog.'
	parser = OptionParser()
	parser.add_option(
		'-p', '--prefdir', help='set path to preference directory', action='store', type='string', dest='preferencesDirectory')
	parser.add_option(
		'-s', '--start', help='set start file to use', action='store', type='string', dest='startFile')
	parser.add_option(
		'-e', '--end', help='set end file to use',	action='store', type='string', dest='endFile')
	parser.add_option(
		'-o', '--option', help='set an individual option in the format "module:preference=value"',
		action='append', type='string', dest='preferences')
	(options, args) = parser.parse_args()
	if options.preferencesDirectory:
		archive.globalTemporarySettingsPath = options.preferencesDirectory
	if options.preferences:
		for prefSpec in options.preferences:
			(moduleName, prefSpec) = prefSpec.split(':', 1)
			(prefName, valueName) = prefSpec.split('=', 1)
			settings.addPreferenceOverride(moduleName, prefName, valueName)
	sys.argv = [sys.argv[0]] + args
	if len( args ) > 0:
		writeOutput( ' '.join(args) )
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
