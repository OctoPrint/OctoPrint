# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from ..exceptions import ConfigurationInvalid

def get_latest(target, check, full_data=False):
	if not "python_checker" in check:
		raise ConfigurationInvalid("Update configuration for %s of type commandline needs command defined" % target)

	return check["python_checker"].get_latest(target, check, full_data=full_data)
