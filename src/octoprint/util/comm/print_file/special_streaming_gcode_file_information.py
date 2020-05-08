# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from .streaming_gcode_file_information import StreamingGcodeFileInformation


class SpecialStreamingGcodeFileInformation(StreamingGcodeFileInformation):
	"""
	For streaming files to the printer that aren't GCODE.

	Difference to regular StreamingGcodeFileInformation: no checksum requirement, only rudimentary line processing
	(stripping of whitespace from the end and ignoring of empty lines)
	"""

	checksum = False

	def _process(self, line, offsets, current_tool):
		line = line.rstrip()
		if not len(line):
			return None
		return line
