"""
This page is in the table of contents.
Extrusion is a script to set the extrusion profile for the skeinforge chain.

The displayed craft sequence is the sequence in which the tools craft the model and export the output.

On the extrusion dialog, clicking the 'Add Profile' button will duplicate the selected profile and give it the name in the input field.  For example, if ABS is selected and the name ABS_black is in the input field, clicking the 'Add Profile' button will duplicate ABS and save it as ABS_black.  The 'Delete Profile' button deletes the selected profile.

The profile selection is the setting.  If you hit 'Save and Close' the selection will be saved, if you hit 'Cancel' the selection will not be saved.  However; adding and deleting a profile is a permanent action, for example 'Cancel' will not bring back any deleted profiles.

To change the extrusion profile, in a shell in the profile_plugins folder type:
> python extrusion.py

"""


from __future__ import absolute_import
import __init__
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile
import sys


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getCraftSequence():
	'Get the extrusion craft sequence.'
	return 'carve scale bottom preface widen inset fill multiply speed temperature raft skirt chamber tower jitter clip smooth stretch skin comb cool hop wipe oozebane dwindle splodge home lash fillet limit unpause dimension alteration export'.split()

def getNewRepository():
	'Get new repository.'
	return ExtrusionRepository()


class ExtrusionRepository:
	'A class to handle the export settings.'
	def __init__(self):
		'Set the default settings, execute title & settings fileName.'
		skeinforge_profile.addListsSetCraftProfile( getCraftSequence(), 'ABS', self, 'skeinforge_application.skeinforge_plugins.profile_plugins.extrusion.html')


def main():
	'Display the export dialog.'
	if len(sys.argv) > 1:
		writeOutput(' '.join(sys.argv[1 :]))
	else:
		settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == '__main__':
	main()
