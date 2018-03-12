# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

def get_latest(target, check, online=True):
	local_version = check.get("local_version", "1.0.0")
	remote_version = check.get("remote_version", "1.0.1")

	information = dict(local=dict(name=local_version, value=local_version),
	                   remote=dict(name=remote_version, value=remote_version))

	return information, False
