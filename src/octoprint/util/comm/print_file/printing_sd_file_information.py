# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from octoprint.filemanager.destinations import FileDestinations

from .printing_file_information import PrintingFileInformation


class PrintingSdFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing print from SD.
	"""

	checksum = False

	def __init__(self, filename, size, user=None):
		PrintingFileInformation.__init__(self, filename, user=user)
		self._size = size

	def getFileLocation(self):
		return FileDestinations.SDCARD

	@property
	def size(self):
		return self._size

	@size.setter
	def size(self, value):
		self._size = value

	@property
	def pos(self):
		return self._pos

	@pos.setter
	def pos(self, value):
		self._pos = value
