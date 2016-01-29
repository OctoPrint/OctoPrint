# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


from octoprint.comm.protocol.gcode.util import strip_comment


def process_gcode_line(line, offsets=None, current_tool=None):
	line = strip_comment(line).strip()
	if not len(line):
		return None

	#if offsets is not None:
	#	line = apply_temperature_offsets(line, offsets, current_tool=current_tool)

	return line
