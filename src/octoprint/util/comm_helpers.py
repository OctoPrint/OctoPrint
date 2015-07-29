# coding=utf-8
from __future__ import absolute_import
__author__ = "Gina Häußge <osd@foosel.net> based on work by David Braam"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import Queue as queue
import glob
import logging
import os
import re
import time

from octoprint.events import Events
from octoprint.filemanager.destinations import FileDestinations
from octoprint.settings import settings, default_settings

try:
	import _winreg
except:
	pass

def serialList():
	baselist=[]
	if os.name=="nt":
		try:
			key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
			i=0
			while(1):
				baselist+=[_winreg.EnumValue(key,i)[1]]
				i+=1
		except:
			pass
	baselist = baselist \
			   + glob.glob("/dev/ttyUSB*") \
			   + glob.glob("/dev/ttyACM*") \
			   + glob.glob("/dev/tty.usb*") \
			   + glob.glob("/dev/cu.*") \
			   + glob.glob("/dev/cuaU*") \
			   + glob.glob("/dev/rfcomm*")

	additionalPorts = settings().get(["serial", "additionalPorts"])
	for additional in additionalPorts:
		baselist += glob.glob(additional)

	prev = settings().get(["serial", "port"])
	if prev in baselist:
		baselist.remove(prev)
		baselist.insert(0, prev)
	if settings().getBoolean(["devel", "virtualPrinter", "enabled"]):
		baselist.append("VIRTUAL")
	return baselist

def baudrateList():
	ret = [250000, 230400, 115200, 57600, 38400, 19200, 9600]
	prev = settings().getInt(["serial", "baudrate"])
	if prev in ret:
		ret.remove(prev)
		ret.insert(0, prev)
	return ret

gcodeToEvent = {
	# pause for user input
	"M226": Events.WAITING,
	"M0": Events.WAITING,
	"M1": Events.WAITING,
	# dwell command
	"G4": Events.DWELL,

	# part cooler
	"M245": Events.COOLING,

	# part conveyor
	"M240": Events.CONVEYOR,

	# part ejector
	"M40": Events.EJECT,

	# user alert
	"M300": Events.ALERT,

	# home print head
	"G28": Events.HOME,

	# emergency stop
	"M112": Events.E_STOP,

	# motors on/off
	"M80": Events.POWER_ON,
	"M81": Events.POWER_OFF,
}

### MachineCom callback ################################################################################################

class MachineComPrintCallback(object):
	def on_comm_log(self, message):
		pass

	def on_comm_temperature_update(self, temp, bedTemp):
		pass

	def on_comm_state_change(self, state):
		pass

	def on_comm_message(self, message):
		pass

	def on_comm_progress(self):
		pass

	def on_comm_print_job_done(self):
		pass

	def on_comm_z_change(self, newZ):
		pass

	def on_comm_file_selected(self, filename, filesize, sd):
		pass

	def on_comm_sd_state_change(self, sdReady):
		pass

	def on_comm_sd_files(self, files):
		pass

	def on_comm_file_transfer_started(self, filename, filesize):
		pass

	def on_comm_file_transfer_done(self, filename):
		pass

	def on_comm_force_disconnect(self):
		pass

### Printing file information classes ##################################################################################

class PrintingFileInformation(object):
	"""
	Encapsulates information regarding the current file being printed: file name, current position, total size and
	time the print started.
	Allows to reset the current file position to 0 and to calculate the current progress as a floating point
	value between 0 and 1.
	"""

	def __init__(self, filename):
		self._logger = logging.getLogger(__name__)
		self._filename = filename
		self._pos = 0
		self._size = None
		self._start_time = None

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
		self._start_time = time.time()

	def close(self):
		"""
		Closes the print job.
		"""
		pass

class PrintingSdFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing print from SD.
	"""

	def __init__(self, filename, size):
		PrintingFileInformation.__init__(self, filename)
		self._size = size

	def setFilepos(self, pos):
		"""
		Sets the current file position.
		"""
		self._pos = pos

	def getFileLocation(self):
		return FileDestinations.SDCARD

class PrintingGcodeFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing direct print. Takes care of the needed file handle and ensures
	that the file is closed in case of an error.
	"""

	def __init__(self, filename, offsets_callback=None, current_tool_callback=None):
		PrintingFileInformation.__init__(self, filename)

		self._handle = None

		self._first_line = None

		self._offsets_callback = offsets_callback
		self._current_tool_callback = current_tool_callback

		if not os.path.exists(self._filename) or not os.path.isfile(self._filename):
			raise IOError("File %s does not exist" % self._filename)
		self._size = os.stat(self._filename).st_size
		self._pos = 0

	def start(self):
		"""
		Opens the file for reading and determines the file size.
		"""
		PrintingFileInformation.start(self)
		self._handle = open(self._filename, "r")

	def close(self):
		"""
		Closes the file if it's still open.
		"""
		PrintingFileInformation.close(self)
		if self._handle is not None:
			try:
				self._handle.close()
			except:
				pass
		self._handle = None

	def getNext(self):
		"""
		Retrieves the next line for printing.
		"""
		if self._handle is None:
			raise ValueError("File %s is not open for reading" % self._filename)

		try:
			offsets = self._offsets_callback() if self._offsets_callback is not None else None
			current_tool = self._current_tool_callback() if self._current_tool_callback is not None else None

			processed = None
			while processed is None:
				if self._handle is None:
					# file got closed just now
					return None
				line = self._handle.readline()
				if not line:
					self.close()
				processed = process_gcode_line(line, offsets=offsets, current_tool=current_tool)
			self._pos = self._handle.tell()

			return processed
		except Exception as e:
			self.close()
			self._logger.exception("Exception while processing line")
			raise e

class StreamingGcodeFileInformation(PrintingGcodeFileInformation):
	def __init__(self, path, localFilename, remoteFilename):
		PrintingGcodeFileInformation.__init__(self, path)
		self._localFilename = localFilename
		self._remoteFilename = remoteFilename

	def start(self):
		PrintingGcodeFileInformation.start(self)
		self._start_time = time.time()

	def getLocalFilename(self):
		return self._localFilename

	def getRemoteFilename(self):
		return self._remoteFilename


class TypedQueue(queue.Queue):

	def __init__(self, maxsize=0):
		queue.Queue.__init__(self, maxsize=maxsize)
		self._lookup = []

	def _put(self, item):
		if isinstance(item, tuple) and len(item) == 3:
			cmd, line, cmd_type = item
			if cmd_type is not None:
				if cmd_type in self._lookup:
					raise TypeAlreadyInQueue(cmd_type, "Type {cmd_type} is already in queue".format(**locals()))
				else:
					self._lookup.append(cmd_type)

		queue.Queue._put(self, item)

	def _get(self):
		item = queue.Queue._get(self)

		if isinstance(item, tuple) and len(item) == 3:
			cmd, line, cmd_type = item
			if cmd_type is not None and cmd_type in self._lookup:
				self._lookup.remove(cmd_type)

		return item


class TypeAlreadyInQueue(Exception):
	def __init__(self, t, *args, **kwargs):
		Exception.__init__(self, *args, **kwargs)
		self.type = t


def get_new_timeout(type):
	now = time.time()
	return now + get_interval(type)


def get_interval(type, default_value=0.0):
	if type not in default_settings["serial"]["timeout"]:
		return default_value
	else:
		value = settings().getFloat(["serial", "timeout", type])
		if not value:
			return default_value
		else:
			return value

_temp_command_regex = re.compile("^M(?P<command>104|109|140|190)(\s+T(?P<tool>\d+)|\s+S(?P<temperature>[-+]?\d*\.?\d*))+")

def apply_temperature_offsets(line, offsets, current_tool=None):
	if offsets is None:
		return line

	match = _temp_command_regex.match(line)
	if match is None:
		return line

	groups = match.groupdict()
	if not "temperature" in groups or groups["temperature"] is None:
		return line

	offset = 0
	if current_tool is not None and (groups["command"] == "104" or groups["command"] == "109"):
		# extruder temperature, determine which one and retrieve corresponding offset
		tool_num = current_tool
		if "tool" in groups and groups["tool"] is not None:
			tool_num = int(groups["tool"])

		tool_key = "tool%d" % tool_num
		offset = offsets[tool_key] if tool_key in offsets and offsets[tool_key] else 0

	elif groups["command"] == "140" or groups["command"] == "190":
		# bed temperature
		offset = offsets["bed"] if "bed" in offsets else 0

	if offset == 0:
		return line

	temperature = float(groups["temperature"])
	if temperature == 0:
		return line

	return line[:match.start("temperature")] + "%f" % (temperature + offset) + line[match.end("temperature"):]

def strip_comment(line):
	if not ";" in line:
		# shortcut
		return line

	escaped = False
	result = []
	for c in line:
		if c == ";" and not escaped:
			break
		result += c
		escaped = (c == "\\") and not escaped
	return "".join(result)

def process_gcode_line(line, offsets=None, current_tool=None):
	line = strip_comment(line).strip()
	if not len(line):
		return None

	if offsets is not None:
		line = apply_temperature_offsets(line, offsets, current_tool=current_tool)

	return line

def convert_pause_triggers(configured_triggers):
	triggers = {
		"enable": [],
		"disable": [],
		"toggle": []
	}
	for trigger in configured_triggers:
		if not "regex" in trigger or not "type" in trigger:
			continue

		try:
			regex = trigger["regex"]
			t = trigger["type"]
			if t in triggers:
				# make sure regex is valid
				re.compile(regex)
				# add to type list
				triggers[t].append(regex)
		except:
			# invalid regex or something like this, we'll just skip this entry
			pass

	result = dict()
	for t in triggers.keys():
		if len(triggers[t]) > 0:
			result[t] = re.compile("|".join(map(lambda pattern: "({pattern})".format(pattern=pattern), triggers[t])))
	return result


def convert_feedback_controls(configured_controls):
	def preprocess_feedback_control(control, result):
		if "key" in control and "regex" in control and "template" in control:
			# key is always the md5sum of the regex
			key = control["key"]

			if result[key]["pattern"] is None or result[key]["matcher"] is None:
				# regex has not been registered
				try:
					result[key]["matcher"] = re.compile(control["regex"])
					result[key]["pattern"] = control["regex"]
				except Exception as exc:
					logging.getLogger(__name__).warn("Invalid regex {regex} for custom control: {exc}".format(regex=control["regex"], exc=str(exc)))

			result[key]["templates"][control["template_key"]] = control["template"]

		elif "children" in control:
			for c in control["children"]:
				preprocess_feedback_control(c, result)

	def prepare_result_entry():
		return dict(pattern=None, matcher=None, templates=dict())

	from collections import defaultdict
	feedback_controls = defaultdict(prepare_result_entry)

	for control in configured_controls:
		preprocess_feedback_control(control, feedback_controls)

	feedback_pattern = []
	for match_key, entry in feedback_controls.items():
		if entry["matcher"] is None or entry["pattern"] is None:
			continue
		feedback_pattern.append("(?P<group{key}>{pattern})".format(key=match_key, pattern=entry["pattern"]))
	feedback_matcher = re.compile("|".join(feedback_pattern))

	return feedback_controls, feedback_matcher

