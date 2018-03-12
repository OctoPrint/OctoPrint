# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

def get_latest(target, check, online=True):
	current_version = check.get("current_version", "1.0.0")

	information = dict(local=dict(name=current_version, value=current_version),
	                   remote=dict(name=current_version, value=current_version))

	return information, True
