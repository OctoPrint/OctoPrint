# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from octoprint.filemanager.destinations import FileDestinations
from octoprint.util import monotonic_time


class PrintingFileInformation(object):
	"""
	Encapsulates information regarding the current file being printed: file name, current position, total size and
	time the print started.
	Allows to reset the current file position to 0 and to calculate the current progress as a floating point
	value between 0 and 1.
	"""

	checksum = True

	def __init__(self, filename, user=None):
		self._logger = logging.getLogger(__name__)
		self._filename = filename
		self._user = user
		self._pos = 0
		self._size = None
		self._start_time = None
		self._done = False

	def getStartTime(self):
		return self._start_time

	def getFilename(self):
		return self._filename

	def getFilesize(self):
		return self._size

	def getFilepos(self):
		return self._pos

	def getFileLocation(self):
		return FileDestinations.LOCAL

	def getUser(self):
		return self._user

	def getProgress(self):
		"""
		The current progress of the file, calculated as relation between file position and absolute size. Returns -1
		if file size is None or < 1.
		"""
		if self._size is None or not self._size > 0:
			return -1
		return float(self._pos) / float(self._size)

	def reset(self):
		"""
		Resets the current file position to 0.
		"""
		self._pos = 0

	def start(self):
		"""
		Marks the print job as started and remembers the start time.
		"""
		self._start_time = monotonic_time()
		self._done = False

	def close(self):
		"""
		Closes the print job.
		"""
		pass

	@property
	def done(self):
		return self._done

	@done.setter
	def done(self, value):
		self._done = value
