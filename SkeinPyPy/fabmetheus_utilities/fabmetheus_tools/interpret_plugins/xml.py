"""
This page is in the table of contents.
The xml.py script is an import translator plugin to get a carving from an xml file.

An import plugin is a script in the interpret_plugins folder which has the function getCarving.  It is meant to be run from the interpret tool.  To ensure that the plugin works on platforms which do not handle file capitalization properly, give the plugin a lower case name.

The getCarving function takes the file name of an xml file and returns the carving.

An example of an xml boolean geometry format file follows below.

<?xml version='1.0' ?>
<fabmetheus version="2010-03-29">
	<difference id="cube_cylinder_difference">
		<matrix m14="-10.0" m24="20.0" m34="5.0" />
		<cube id="Cube 5" halfx="5.0" halfy="5.0" halfz="5.0">
		</cube>
		<cylinder id="Cylinder 5" height="10.0" radiusx="5.0" radiusy="5.0" topOverBottom="1.0">
			<matrix m14="5.0" m24="-5.0" />
		</cylinder>
	</difference>
</fabmetheus>

In the 'fabmetheus' format, all class names are lower case.  The defined geometric objects are cube, cylinder, difference, group, sphere, trianglemesh and union.  The id attribute is not necessary.  The default matrix is a four by four identity matrix.  The attributes of the cube, cylinder and sphere default to one.  The attributes of the vertexes in the triangle mesh default to zero.  The boolean solids are difference, intersection and union.  The difference solid is the first solid minus the remaining solids.  The combined_shape.xml example in the xml_models folder in the models folder is pasted below.

<?xml version='1.0' ?>
<fabmetheus version="2010-03-29">
	<difference id="cube_cylinder_difference">
		<matrix m14="-10.0" m24="20.0" m34="5.0" />
		<cube id="Cube 5" halfx="5.0" halfy="5.0" halfz="5.0">
		</cube>
		<cylinder id="Cylinder 5" height="10.0" radiusx="5.0" radiusy="5.0" topOverBottom="1.0">
			<matrix m14="5.0" m24="-5.0" />
		</cylinder>
	</difference>
	<intersection id="cube_cylinder_intersection">
		<matrix m14="-10.0" m34="5.0" />
		<cube id="Cube 5" halfx="5.0" halfy="5.0" halfz="5.0">
		</cube>
		<cylinder id="Cylinder 5" height="10.0" radiusx="5.0" radiusy="5.0" topOverBottom="1.0">
			<matrix m14="5.0" m24="-5.0" />
		</cylinder>
	</intersection>
	<union id="cube_cylinder_union">
		<matrix m14="-10.0" m24="-20.0" m34="5.0" />
		<cube id="Cube 5" halfx="5.0" halfy="5.0" halfz="5.0">
		</cube>
		<cylinder id="Cylinder 5" height="10.0" radiusx="5.0" radiusy="5.0" topOverBottom="1.0">
			<matrix m14="5.0" m24="-5.0" />
		</cylinder>
	</union>
	<group id="sphere_tetrahedron_group">
		<matrix m14="10.0" m24="-20.0" m34="5.0" />
		<sphere id="Group Sphere 5" radiusx="5.0" radiusy="5.0" radiusz="5.0">
		</sphere>
		<trianglemesh id="Group Tetrahedron 5">
			<matrix m14="15.0" />
			<vertex x="-5.0" y="-5.0" z="-5.0" />
			<vertex x="5.0" y="-5.0" z="-5.0" />
			<vertex y="5.0" z="-5.0" />
			<vertex z="5.0" />
			<face vertex0="0" vertex1="2" vertex2="1" />
			<face vertex0="3" vertex1="1" vertex2="2" />
			<face vertex0="3" vertex1="2" vertex2="0" />
			<face vertex0="3" vertex1="0" vertex2="1" />
		</trianglemesh>
	</group>
	<sphere id="Sphere 5" radiusx="5.0" radiusy="5.0" radiusz="5.0">
		<matrix m14="10.0" m34="5.0" />
	</sphere>
	<trianglemesh id="Tetrahedron 5">
		<matrix m14="10.0" m24="20.0" m34="5.0" />
		<vertex x="-5.0" y="-5.0" z="-5.0" />
		<vertex x="5.0" y="-5.0" z="-5.0" />
		<vertex y="5.0" z="-5.0" />
		<vertex z="5.0" />
		<face vertex0="0" vertex1="2" vertex2="1" />
		<face vertex0="3" vertex1="1" vertex2="2" />
		<face vertex0="3" vertex1="2" vertex2="0" />
		<face vertex0="3" vertex1="0" vertex2="1" />
	</trianglemesh>
</fabmetheus>

The 'fabmetheus' xml format is the preferred skeinforge format.  When the Interpret button in the Interpret tool in Analyze is clicked, any xml format for which there is a plugin will be converted to the 'fabmetheus' format.

There is a plugin for the 'Art of Illusion' xml format.  An xml file can be exported from Art of Illusion by going to the "File" menu, then going into the "Export" menu item, then picking the XML choice.  This will bring up the XML file chooser window, choose a place to save the file then click "OK".  Leave the "compressFile" checkbox unchecked.  All the objects from the scene will be exported, the artofillusion plugin will ignore the light and camera.  If you want to fabricate more than one object at a time, you can have multiple objects in the Art of Illusion scene and they will all be carved, then fabricated together.

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities.xml_simple_reader import DocumentNode
from fabmetheus_utilities import archive
from fabmetheus_utilities import gcodec
import os
import sys

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__credits__ = 'Nophead <http://hydraraptor.blogspot.com/>\nArt of Illusion <http://www.artofillusion.org/>'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCarving(fileName=''):
	"Get the carving for the xml file."
	xmlText = archive.getFileText(fileName)
	if xmlText == '':
		return None
	xmlParser = DocumentNode(fileName, xmlText)
	lowerLocalName = xmlParser.getDocumentElement().getNodeName().lower()
	pluginModule = archive.getModuleWithDirectoryPath( getPluginsDirectoryPath(), lowerLocalName )
	if pluginModule == None:
		return None
	return pluginModule.getCarvingFromParser( xmlParser )

def getPluginsDirectoryPath():
	"Get the plugins directory path."
	return archive.getInterpretPluginsPath('xml_plugins')

def main():
	"Display the inset dialog."
	if len(sys.argv) > 1:
		getCarving(' '.join(sys.argv[1 :]))

if __name__ == "__main__":
	main()
