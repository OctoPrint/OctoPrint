# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

def normalize(path, expand_user=True, expand_vars=True, real=True, **kwargs):
	import os

	if path is None:
		return None

	if expand_user:
		path = os.path.expanduser(path)
	if expand_vars:
		path = os.path.expandvars(path)
	path = os.path.abspath(path)
	if real:
		path = os.path.realpath(path)
	return path
