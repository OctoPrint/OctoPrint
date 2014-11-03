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
	def from_line(line):
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


class CommandQueueEntry(object):
	PRIORITY_RESEND = 1
	PRIORITY_HIGH = 2
	PRIORITY_NORMAL = 3

	def __init__(self, priority, command, line_number=None, command_type=None, prepared=None, progress=None):
		self.priority = priority
		self.command = command
		self.line_number = line_number
		self.command_type = command_type
		self.progress = progress
		self._prepared = prepared
		self._size = 0

	@property
	def prepared(self):
		return self._prepared

	@prepared.setter
	def prepared(self, prepared):
		self._prepared = prepared
		self._size = (len(prepared) + 1) if prepared is not None else 0

	@property
	def size(self):
		return self._size

	def __radd__(self, other):
		return other + self._size

	def __repr__(self):
		return "CommandQueueEntry({command},line_number={line_number},prepared={prepared})".format(command=self.command, line_number=self.line_number, prepared=self.prepared)


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
		if not isinstance(item, CommandQueueEntry):
			raise ValueError("queue can only take CommandQueueEntries, can't accept %r" % item)

		command_type = item.command_type
		if command_type is not None:
			if command_type not in self.lookup:
				self.lookup[command_type] = item
			else:
				raise TypeAlreadyInQueue()

		heappush(self.queue, (item.priority, next(self.counter), item))

	def _get(self, heappop=heapq.heappop):
		priority, counter, item = heappop(self.queue)
		if item.command_type in self.lookup:
			del self.lookup[item.command_type]
		return item

	def peek(self):
		if len(self.queue) == 0:
			return None
		priority, counter, item = self.queue[0]
		return item

	def __repr__(self):
		return repr(self.queue)

class TypeAlreadyInQueue(Exception):
	pass

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

		self._fileHandle = None
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
			self._startTime = time.time()
			return GcodeCommand.from_line("M110 N0")

		try:
			command = None
			while command is None:
				if self._filehandle is None:
					# file got closed just now
					return None
				line = self._filehandle.readline()
				if not line:
					self._filehandle.close()
					self._filehandle = None
				command = self._process_command(line)
			self._lineCount += 1
			self._filepos = self._filehandle.tell()

			return command
		except Exception as (e):
			if self._filehandle is not None:
				self._filehandle.close()
				self._filehandle = None
			raise e

	def _process_command(self, line):
		# remove all comments and trim the line
		if ";" in line:
			line = line[0:line.find(";")]
		line = line.strip()

		if len(line) > 0:
			# we still got something left => parse the command
			command = GcodeCommand.from_line(line)
			if command is None:
				return None

			if command.isSelectToolCommand():
				# track tool changes
				self._currentTool = command.tool

			elif command.isSetTemperatureCommand() and self._offsetCallback is not None:
				# if we have a temperature command and an offset callback, retrieve current offsets
				offsets = self._offsetCallback()

				# extruder temperature, determine which one and retrieve corresponding offset
				if command.command == "M104" or command.command == "M109":
					tool_num = self._currentTool
					if command.t is not None:
						tool_num = command.t

					key = "tool%d" % tool_num

				# bed temperature
				elif command.command == "M140" or command.command == "M190":
					key = "bed"

				# unknown, should never happen
				else:
					key = None

				if key is not None and key in offsets:
					offset = offsets[key]
					command.s = command.s + offset
					if command.original is not None:
						command.original = None

			# finally return the processed command
			return command
		else:
			# no command, return None
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

