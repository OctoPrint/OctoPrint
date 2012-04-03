"""
This page is in the table of contents.
Description is a script to store a description of the profile.

==Settings==
===Description Text===
Default is 'Write your profile description here.'

The suggested format is a description, followed by a link to a profile post or web page.

==Example==
Example of using description follows below.

> python description.py
This brings up the description dialog.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile


__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getNewRepository():
	'Get new repository.'
	return DescriptionRepository()


class DescriptionRepository:
	"A class to handle the description settings."
	def __init__(self):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository('skeinforge_application.skeinforge_plugins.meta_plugins.description.html', self)
		description = 'Write your description of the profile here.\n\nSuggested format is a description, followed by a link to the profile post or web page.'
		self.descriptionText = settings.TextSetting().getFromValue('Description Text:', self, description)


def main():
	"Display the file or directory dialog."
	settings.startMainLoopFromConstructor(getNewRepository())

if __name__ == "__main__":
	main()
