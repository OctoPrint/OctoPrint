# coding=utf-8
from __future__ import absolute_import

import logging.handlers
import os
import re
import time

class CleaningTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):

	def __init__(self, *args, **kwargs):
		logging.handlers.TimedRotatingFileHandler.__init__(self, *args, **kwargs)

		# clean up old files on handler start
		if self.backupCount > 0:
			for s in self.getFilesToDelete():
				os.remove(s)


class OctoPrintLogHandler(CleaningTimedRotatingFileHandler):
	rollover_callbacks = []

	@classmethod
	def registerRolloverCallback(cls, callback, *args, **kwargs):
		cls.rollover_callbacks.append((callback, args, kwargs))

	def doRollover(self):
		CleaningTimedRotatingFileHandler.doRollover(self)

		for rcb in self.rollover_callbacks:
			callback, args, kwargs = rcb
			callback(*args, **kwargs)


class SerialLogHandler(logging.handlers.RotatingFileHandler):

	_do_rollover = False
	_suffix_template = "%Y-%m-%d_%H-%M-%S"
	_file_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")

	@classmethod
	def on_open_connection(cls):
		cls._do_rollover = True

	def __init__(self, *args, **kwargs):
		logging.handlers.RotatingFileHandler.__init__(self, *args, **kwargs)
		self.cleanupFiles()

	def emit(self, record):
		logging.handlers.RotatingFileHandler.emit(self, record)

	def shouldRollover(self, record):
		return self.__class__._do_rollover

	def getFilesToDelete(self):
		"""
		Determine the files to delete when rolling over.
		"""
		dirName, baseName = os.path.split(self.baseFilename)
		fileNames = os.listdir(dirName)
		result = []
		prefix = baseName + "."
		plen = len(prefix)
		for fileName in fileNames:
			if fileName[:plen] == prefix:
				suffix = fileName[plen:]
				if self.__class__._file_pattern.match(suffix):
					result.append(os.path.join(dirName, fileName))
		result.sort()
		if len(result) < self.backupCount:
			result = []
		else:
			result = result[:len(result) - self.backupCount]
		return result

	def cleanupFiles(self):
		if self.backupCount > 0:
			for path in self.getFilesToDelete():
				os.remove(path)

	def doRollover(self):
		self.__class__._do_rollover = False

		if self.stream:
			self.stream.close()
			self.stream = None

		if os.path.exists(self.baseFilename):
			# figure out creation date/time to use for file suffix
			t = time.localtime(os.stat(self.baseFilename).st_mtime)
			dfn = self.baseFilename + "." + time.strftime(self.__class__._suffix_template, t)
			if os.path.exists(dfn):
				os.remove(dfn)
			os.rename(self.baseFilename, dfn)

		self.cleanupFiles()
		if not self.delay:
			self.stream = self._open()

class RecordingLogHandler(logging.Handler):
	def __init__(self, target=None, level=logging.NOTSET):
		logging.Handler.__init__(self, level=level)
		self._buffer = []
		self._target = target

	def emit(self, record):
		self._buffer.append(record)

	def setTarget(self, target):
		self._target = target

	def flush(self):
		if not self._target:
			return

		self.acquire()
		try:
			for record in self._buffer:
				self._target.handle(record)
			self._buffer = []
		finally:
			self.release()

	def close(self):
		self.flush()
		self.acquire()
		try:
			self._buffer = []
		finally:
			self.release()

	def __len__(self):
		return len(self._buffer)


class CombinedLogHandler(logging.Handler):
	def __init__(self, *handlers):
		logging.Handler.__init__(self)
		self._handlers = handlers

	def setHandlers(self, *handlers):
		self._handlers = handlers

	def handle(self, record):
		self.acquire()
		try:
			if self._handlers:
				for handler in self._handlers:
					handler.handle(record)
		finally:
			self.release()
