# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import threading

from octoprint.util import bom_aware_open, monotonic_time

from .printing_file_information import PrintingFileInformation
from octoprint.util.gcode import process_gcode_line


class PrintingGcodeFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing direct print. Takes care of the needed file handle and ensures
	that the file is closed in case of an error.
	"""

	def __init__(self,
				 filename,
				 offsets_callback=None,
				 current_tool_callback=None,
				 user=None):
		PrintingFileInformation.__init__(self, filename, user=user)

		self._handle = None
		self._handle_mutex = threading.RLock()

		self._offsets_callback = offsets_callback
		self._current_tool_callback = current_tool_callback

		if not os.path.exists(self._filename) or not os.path.isfile(
			self._filename):
			raise IOError("File %s does not exist" % self._filename)
		self._size = os.stat(self._filename).st_size
		self._pos = 0
		self._read_lines = 0

	def seek(self, offset):
		with self._handle_mutex:
			if self._handle is None:
				return

			self._handle.seek(offset)
			self._pos = self._handle.tell()
			self._read_lines = 0

	def start(self):
		"""
		Opens the file for reading and determines the file size.
		"""
		PrintingFileInformation.start(self)
		with self._handle_mutex:
			self._handle = bom_aware_open(self._filename,
										  encoding="utf-8",
										  errors="replace")
			self._pos = self._handle.tell()
			if self._handle.encoding.endswith("-sig"):
				# Apparently we found an utf-8 bom in the file.
				# We need to add its length to our pos because it will
				# be stripped transparently and we'll have no chance
				# catching that.
				import codecs
				self._pos += len(codecs.BOM_UTF8)
			self._read_lines = 0

	def close(self):
		"""
		Closes the file if it's still open.
		"""
		PrintingFileInformation.close(self)
		with self._handle_mutex:
			if self._handle is not None:
				try:
					self._handle.close()
				except Exception:
					pass
			self._handle = None

	def getNext(self):
		"""
		Retrieves the next line for printing.
		"""
		with self._handle_mutex:
			if self._handle is None:
				self._logger.warning("File {} is not open for reading".format(
					self._filename))
				return None, None, None

			try:
				offsets = self._offsets_callback(
				) if self._offsets_callback is not None else None
				current_tool = self._current_tool_callback(
				) if self._current_tool_callback is not None else None

				processed = None
				while processed is None:
					if self._handle is None:
						# file got closed just now
						self._pos = self._size
						self._done = True
						self._report_stats()
						return None, None, None

					# we need to manually keep track of our pos here since
					# codecs' readline will make our handle's tell not
					# return the actual number of bytes read, but also the
					# already buffered bytes (for detecting the newlines)
					line = self._handle.readline()
					self._pos += len(line.encode("utf-8"))

					if not line:
						self.close()
					processed = self._process(line, offsets, current_tool)
				self._read_lines += 1
				return processed, self._pos, self._read_lines
			except Exception as e:
				self.close()
				self._logger.exception("Exception while processing line")
				raise e

	def _process(self, line, offsets, current_tool):
		return process_gcode_line(line,
								  offsets=offsets,
								  current_tool=current_tool)

	def _report_stats(self):
		duration = monotonic_time() - self._start_time
		self._logger.info("Finished in {:.3f} s.".format(duration))
		pass
