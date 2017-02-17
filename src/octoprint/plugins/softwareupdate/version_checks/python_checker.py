# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from ..exceptions import ConfigurationInvalid

def get_latest(target, check, full_data=False):
	python_checker = check.get("python_checker")
	if python_checker is None or not hasattr(python_checker, "get_latest"):
		raise ConfigurationInvalid("Update configuration for {} of type python_checker needs python_checker defined and have an attribute \"get_latest\"".format(target))

	return check["python_checker"].get_latest(target, check, full_data=full_data)
