# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


def can_perform_update(target, check):
	return "python_updater" in check and check["python_updater"] is not None


def perform_update(target, check, target_version):
	return check["python_updater"].perform_update(target, check, target_version)