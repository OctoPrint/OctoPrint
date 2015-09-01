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
from octoprint.plugin import plugin_manager, MachineComPlugin
from octoprint.settings import settings, default_settings

try:
	import _winreg
except:
	pass

_logger = logging.getLogger(__name__)

# a bunch of regexes we'll need for the communication parsing...

regex_float_pattern = "[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = "[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = "\d+"

regex_command = re.compile("^\s*((?P<commandGM>[GM]\d+)|(?P<commandT>T)\d+)")
"""Regex for a GCODE command."""

regex_float = re.compile(regex_float_pattern)
"""Regex for a float value."""

regexes_parameters = dict(
	floatP=re.compile("(^|[^A-Za-z])[Pp](?P<value>%s)" % regex_float_pattern),
	floatS=re.compile("(^|[^A-Za-z])[Ss](?P<value>%s)" % regex_float_pattern),
	floatZ=re.compile("(^|[^A-Za-z])[Zz](?P<value>%s)" % regex_float_pattern),
	intN=re.compile("(^|[^A-Za-z])[Nn](?P<value>%s)" % regex_int_pattern),
	intT=re.compile("(^|[^A-Za-z])[Tt](?P<value>%s)" % regex_int_pattern)
)
"""Regexes for parsing various GCODE command parameters."""

regex_minMaxError = re.compile("Error:[0-9]\n")
"""Regex matching first line of min/max errors from the firmware."""

regex_sdPrintingByte = re.compile("(?P<current>[0-9]*)/(?P<total>[0-9]*)")
"""Regex matching SD printing status reports.

Groups will be as follows:

  * ``current``: current byte position in file being printed
  * ``total``: total size of file being printed
"""

regex_sdFileOpened = re.compile("File opened:\s*(?P<name>.*?)\s+Size:\s*(?P<size>%s)" % regex_int_pattern)
"""Regex matching "File opened" messages from the firmware.

Groups will be as follows:

  * ``name``: name of the file reported as having been opened (str)
  * ``size``: size of the file in bytes (int)
"""

regex_temp = re.compile("(?P<tool>B|T(?P<toolnum>\d*)):\s*(?P<actual>%s)(\s*\/?\s*(?P<target>%s))?" % (regex_positive_float_pattern, regex_positive_float_pattern))
"""Regex matching temperature entries in line.

Groups will be as follows:

  * ``tool``: whole tool designator, incl. optional ``toolnum`` (str)
  * ``toolnum``: tool number, if provided (int)
  * ``actual``: actual temperature (float)
  * ``target``: target temperature, if provided (float)
"""

regex_repetierTempExtr = re.compile("TargetExtr(?P<toolnum>\d+):(?P<target>%s)" % regex_positive_float_pattern)
"""Regex for matching target temp reporting from Repetier.

Groups will be as follows:

  * ``toolnum``: number of the extruder to which the target temperature
    report belongs (int)
  * ``target``: new target temperature (float)
"""

regex_repetierTempBed = re.compile("TargetBed:(?P<target>%s)" % regex_positive_float_pattern)
"""Regex for matching target temp reporting from Repetier for beds.

Groups will be as follows:

  * ``target``: new target temperature (float)
"""

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
	additionalBaudrates = settings().get(["serial", "additionalBaudrates"])
	for additional in additionalBaudrates:
		try:
			ret.append(int(additional))
		except:
			_logger.warn("{} is not a valid additional baudrate, ignoring it".format(additional))

	ret.sort(reverse=True)

	prev = settings().getInt(["serial", "baudrate"])
	if prev in ret:
		ret.remove(prev)
		ret.insert(0, prev)
	return ret

def commList():
    comm_implementations = plugin_manager().get_implementations(MachineComPlugin)
    return [{ "identifier": c._identifier, "name": c._plugin_name } for c in comm_implementations]

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

	def on_comm_set_job_data(self, name, size, print_time):
		pass

	def on_comm_set_progress_data(self, completion, filepos, print_time, print_time_left):
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

def canonicalize_temperatures(parsed, current):
	"""
	Canonicalizes the temperatures provided in parsed.

	Will make sure that returned result only contains extruder keys
	like Tn, so always qualified with a tool number.

	The algorithm for cleaning up the parsed keys is the following:

	  * If ``T`` is not included with the reported extruders, return
	  * If more than just ``T`` is reported:
	    * If both ``T`` and ``T0`` are reported set ``Tc`` to ``T``, remove
	      ``T`` from the result.
	    * Else set ``T0`` to ``T`` and delete ``T`` (Smoothie extra).
	  * If only ``T`` is reported, set ``Tc`` to ``T`` and delete ``T``
	  * return

	Arguments:
	    parsed (dict): the parsed temperatures (mapping tool => (actual, target))
	      to canonicalize
	    current (int): the current active extruder
	Returns:
	    dict: the canonicalized version of ``parsed``
	"""

	reported_extruders = filter(lambda x: x.startswith("T"), parsed.keys())
	if not "T" in reported_extruders:
		# Our reported_extruders are either empty or consist purely
		# of Tn keys, no need for any action
		return parsed

	current_tool_key = "T%d" % current
	result = dict(parsed)

	if len(reported_extruders) > 1:
		if "T0" in reported_extruders:
			# Both T and T0 are present, so T contains the current
			# extruder's temperature, e.g. for current_tool == 1:
			#
			#     T:<T1> T0:<T0> T2:<T2> ... B:<B>
			#
			# becomes
			#
			#     T0:<T1> T1:<T1> T2:<T2> ... B:<B>
			#
			# Same goes if Tc is already present, it will be overwritten:
			#
			#     T:<T1> T0:<T0> T1:<T1> T2:<T2> ... B:<B>
			#
			# becomes
			#
			#     T0:<T0> T1:<T1> T2:<T2> ... B:<B>
			result[current_tool_key] = result["T"]
			del result["T"]
		else:
			# So T is there, but T0 isn't. That looks like Smoothieware which
			# always reports the first extruder T0 as T:
			#
			#     T:<T0> T1:<T1> T2:<T2> ... B:<B>
			#
			# becomes
			#
			#     T0:<T0> T1:<T1> T2:<T2> ... B:<B>
			result["T0"] = result["T"]
			del result["T"]

	else:
		# We only have T. That can mean two things:
		#
		#   * we only have one extruder at all, or
		#   * we are currently parsing a response to M109/M190, which on
		#     some firmwares doesn't report the full M105 output while
		#     waiting for the target temperature to be reached but only
		#     reports the current tool and bed
		#
		# In both cases it is however safe to just move our T over
		# to T<current> in the parsed data, current should always stay
		# 0 for single extruder printers. E.g. for current_tool == 1:
		#
		#     T:<T1>
		#
		# becomes
		#
		#     T1:<T1>

		result[current_tool_key] = result["T"]
		del result["T"]

	return result

def parse_temperature_line(line, current):
	"""
	Parses the provided temperature line.

	The result will be a dictionary mapping from the extruder or bed key to
	a tuple with current and target temperature. The result will be canonicalized
	with :func:`canonicalize_temperatures` before returning.

	Arguments:
	    line (str): the temperature line to parse
	    current (int): the current active extruder

	Returns:
	    tuple: a 2-tuple with the maximum tool number and a dict mapping from
	      key to (actual, target) tuples, with key either matching ``Tn`` for ``n >= 0`` or ``B``
	"""

	result = {}
	maxToolNum = 0
	for match in re.finditer(regex_temp, line):
		values = match.groupdict()
		tool = values["tool"]
		toolnum = values.get("toolnum", None)
		toolNumber = int(toolnum) if toolnum is not None and len(toolnum) else None
		if toolNumber > maxToolNum:
			maxToolNum = toolNumber

		try:
			actual = float(match.group(3))
			target = None
			if match.group(4) and match.group(5):
				target = float(match.group(5))

			result[tool] = (actual, target)
		except ValueError:
			# catch conversion issues, we'll rather just not get the temperature update instead of killing the connection
			pass

	return max(maxToolNum, current), canonicalize_temperatures(result, current)

def gcode_command_for_cmd(cmd):
	"""
	Tries to parse the provided ``cmd`` and extract the GCODE command identifier from it (e.g. "G0" for "G0 X10.0").

	Arguments:
	    cmd (str): The command to try to parse.

	Returns:
	    str or None: The GCODE command identifier if it could be parsed, or None if not.
	"""
	if not cmd:
		return None

	gcode = regex_command.search(cmd)
	if not gcode:
		return None

	values = gcode.groupdict()
	if "commandGM" in values and values["commandGM"]:
		return values["commandGM"]
	elif "commandT" in values and values["commandT"]:
		return values["commandT"]
	else:
		# this should never happen
		return None

