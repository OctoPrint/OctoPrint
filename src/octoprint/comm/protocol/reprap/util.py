# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import Queue
import re
import heapq
import os
import time
import itertools

from octoprint.comm.protocol import PrintingFileInformation


class GcodeCommand(object):

	KNOWN_FLOAT_ATTRIBUTES = ("x", "y", "z", "e", "s", "p", "r")
	KNOWN_INT_ATTRIBUTES = ("f", "t", "n")
	KNOWN_ATTRIBUTES = KNOWN_FLOAT_ATTRIBUTES + KNOWN_INT_ATTRIBUTES

	COMMAND_REGEX = re.compile("^([GMT])(\d+)")
	ARGUMENT_REGEX = re.compile("\s+([%s][-+]?\d*\.?\d+|[%s][-+]?\d+)" % ("".join(map(lambda x: x.upper(), KNOWN_FLOAT_ATTRIBUTES)), "".join(map(lambda x: x.upper(), KNOWN_INT_ATTRIBUTES))))
	PARAM_REGEX = re.compile("^[GMT]\d+\s+(.*?)$")

	@staticmethod
	def fromLine(line):
		line = line.strip()
		match = GcodeCommand.COMMAND_REGEX.match(line)
		if match is None:
			return None

		commandType = match.group(1)
		commandNumber = int(match.group(2))
		command = "%s%d" % (commandType, commandNumber)
		args = {"original": line}

		if commandType == "T":
			args["tool"] = commandNumber
		else:
			matchedArgs = GcodeCommand.ARGUMENT_REGEX.findall(line)
			if len(matchedArgs) == 0:
				paramMatch = GcodeCommand.PARAM_REGEX.match(line)
				if paramMatch is not None:
					args["param"] = paramMatch.group(1)
			else:
				for arg in matchedArgs:
					key = arg[0].lower()
					if key in GcodeCommand.KNOWN_INT_ATTRIBUTES:
						value = int(arg[1:])
					elif key in GcodeCommand.KNOWN_FLOAT_ATTRIBUTES:
						value = float(arg[1:])
					else:
						value = str(arg[1:])
					args[key] = value

		return GcodeCommand(command, **args)

	def __init__(self, command, **kwargs):
		self.command = command
		self.x = None
		self.y = None
		self.z = None
		self.e = None
		self.s = None
		self.p = None
		self.r = None
		self.f = None
		self.t = None
		self.n = None

		self.tool = None
		self.original = None
		self.param = None

		for key, value in kwargs.iteritems():
			if key in GcodeCommand.KNOWN_ATTRIBUTES + ("tool", "original", "param"):
				self.__setattr__(key, value)

	def isGetTemperatureCommand(self):
		return self.command == "M105"

	def isSetTemperatureCommand(self):
		return self.command in ("M104", "M140", "M109", "M190")

	def isSelectToolCommand(self):
		return self.command.startswith("T")

	def __str__(self):
		if self.original is not None:
			return self.original
		else:
			attr = []
			for key in GcodeCommand.KNOWN_ATTRIBUTES:
				value = self.__getattribute__(key)
				if value is not None:
					if key in GcodeCommand.KNOWN_INT_ATTRIBUTES:
						attr.append("%s%d" % (key.upper(), value))
					elif key in GcodeCommand.KNOWN_FLOAT_ATTRIBUTES:
						attr.append("%s%f" % (key.upper(), value))
					else:
						attr.append("%s%r" % (key.upper(), value))
			attributeStr = " ".join(attr)
			return "%s%s%s" % (self.command.upper(), " " + attributeStr if attributeStr else "", " " + self.param if self.param else "")


class CommandQueue(Queue.Queue):
	'''Variant of Queue that retrieves open entries in priority order (lowest first, followed by addition order).

	Entries need to be of the form (priority, command). An optional third argument commandType may be given:
	(priority, command, commandType), the queue will ensure that only one command of a given commandType will ever
	be in the queue.
	'''

	def _init(self, maxsize):
		self.queue = []
		self.lookup = {}
		self.counter = itertools.count()

	def _qsize(self, len=len):
		return len(self.queue)

	def _put(self, item, heappush=heapq.heappush):
		if len(item) == 3:
			priority, command, commandType = item
		else:
			priority, command = item
			commandType = None

		if commandType is not None:
			if commandType not in self.lookup:
				self.lookup[commandType] = item
			else:
				return

		heappush(self.queue, (priority, next(self.counter), command, commandType))

	def _get(self, heappop=heapq.heappop):
		priority, count, command, commandType = heappop(self.queue)
		if commandType in self.lookup:
			del self.lookup[commandType]
		return priority, command, commandType


class PrintingGcodeFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing direct print. Takes care of the needed file handle and ensures
	that the file is closed in case of an error.
	"""

	def __init__(self, filename, offsetCallback):
		PrintingFileInformation.__init__(self, filename)
		self._lineCount = None
		self._firstLine = None
		self._currentTool = 0

		self._offsetCallback = offsetCallback
		self._tempCommandPattern = re.compile("M(104|109|140|190)")
		self._tempCommandTemperaturePattern = re.compile("S([-+]?/d*/.?/d+)")
		self._tempCommandToolPattern = re.compile("T(/d+)")
		self._toolCommandPattern = re.compile("^T(/d+)")

		if not os.path.exists(self._filename) or not os.path.isfile(self._filename):
			raise IOError("File %s does not exist" % self._filename)
		self._filesize = os.stat(self._filename).st_size

	def start(self):
		"""
		Opens the file for reading and determines the file size. Start time won't be recorded until 100 lines in
		"""
		self._filehandle = open(self._filename, "r")
		self._lineCount = None
		self._startTime = None

	def getNext(self):
		"""
		Retrieves the next line for printing.
		"""
		if self._filehandle is None:
			raise ValueError("File %s is not open for reading" % self._filename)

		if self._lineCount is None:
			self._lineCount = 0
			return "M110 N0"

		try:
			processedLine = None
			while processedLine is None:
				if self._filehandle is None:
					# file got closed just now
					return None
				line = self._filehandle.readline()
				if not line:
					self._filehandle.close()
					self._filehandle = None
				processedLine = self._processLine(line)
			self._lineCount += 1
			self._filepos = self._filehandle.tell()

			if self._lineCount >= 100 and self._startTime is None:
				self._startTime = time.time()

			return processedLine
		except Exception as (e):
			if self._filehandle is not None:
				self._filehandle.close()
				self._filehandle = None
			raise e

	def _processLine(self, line):
		if ";" in line:
			line = line[0:line.find(";")]
		line = line.strip()
		if len(line) > 0:
			toolMatch = self._toolCommandPattern.match(line)
			if toolMatch is not None:
				# track tool changes
				self._currentTool = int(toolMatch.group(1))
			else:
				## apply offsets
				if self._offsetCallback is not None:
					tempMatch = self._tempCommandPattern.match(line)
					if tempMatch is not None:
						# if we have a temperature command, retrieve current offsets
						tempOffset, bedTempOffset = self._offsetCallback()
						if tempMatch.group(1) == "104" or tempMatch.group(1) == "109":
							# extruder temperature, determine which one and retrieve corresponding offset
							toolNum = self._currentTool

							toolNumMatch = self._tempCommandToolPattern.search(line)
							if toolNumMatch is not None:
								try:
									toolNum = int(toolNumMatch.group(1))
								except ValueError:
									pass

							offset = tempOffset[toolNum] if toolNum in tempOffset.keys() and tempOffset[toolNum] is not None else 0
						elif tempMatch.group(1) == "140" or tempMatch.group(1) == "190":
							# bed temperature
							offset = bedTempOffset
						else:
							# unknown, should never happen
							offset = 0

						if not offset == 0:
							# if we have an offset != 0, we need to get the temperature to be set and apply the offset to it
							tempValueMatch = self._tempCommandTemperaturePattern.search(line)
							if tempValueMatch is not None:
								try:
									temp = float(tempValueMatch.group(1))
									if temp > 0:
										newTemp = temp + offset
										line = line.replace("S" + tempValueMatch.group(1), "S%f" % newTemp)
								except ValueError:
									pass
			return line
		else:
			return None


class StreamingGcodeFileInformation(PrintingGcodeFileInformation):
	def __init__(self, path, localFilename, remoteFilename):
		PrintingGcodeFileInformation.__init__(self, path, None)
		self._localFilename = localFilename
		self._remoteFilename = remoteFilename

	def start(self):
		PrintingGcodeFileInformation.start(self)
		self._startTime = time.time()

	def getLocalFilename(self):
		return self._localFilename

	def getRemoteFilename(self):
		return self._remoteFilename

