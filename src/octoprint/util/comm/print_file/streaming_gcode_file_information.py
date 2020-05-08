# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from src.octoprint.util.gcode import process_gcode_line

from octoprint.util import monotonic_time

from .printing_gcode_file_information import PrintingGcodeFileInformation

class StreamingGcodeFileInformation(PrintingGcodeFileInformation):
	def __init__(self, path, localFilename, remoteFilename, user=None):
		PrintingGcodeFileInformation.__init__(self, path, user=user)
		self._localFilename = localFilename
		self._remoteFilename = remoteFilename

	def start(self):
		PrintingGcodeFileInformation.start(self)
		self._start_time = monotonic_time()

	def getLocalFilename(self):
		return self._localFilename

	def getRemoteFilename(self):
		return self._remoteFilename

	def _process(self, line, offsets, current_tool):
		return process_gcode_line(line)

	def _report_stats(self):
		duration = monotonic_time() - self._start_time
		read_lines = self._read_lines
		if duration > 0 and read_lines > 0:
			stats = dict(lines=read_lines,
						 rate=float(read_lines) / duration,
						 time_per_line=duration * 1000.0 / float(read_lines),
						 duration=duration)
			self._logger.info(
				"Finished in {duration:.3f} s. Approx. transfer rate of {rate:.3f} lines/s or {time_per_line:.3f} ms per line"
					.format(**stats))
