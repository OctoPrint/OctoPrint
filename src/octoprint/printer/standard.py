# coding=utf-8
"""
This module holds the standard implementation of the :class:`PrinterInterface` and it helpers.
"""

from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import copy
import logging
import os
import threading
import time

from past.builtins import basestring

from octoprint import util as util
from octoprint.events import eventManager, Events
from octoprint.filemanager import FileDestinations, NoSuchStorage, valid_file_type
from octoprint.plugin import plugin_manager, ProgressPlugin
from octoprint.printer import PrinterInterface, PrinterCallback, UnknownScript, InvalidFileLocation, InvalidFileType
from octoprint.printer.estimation import TimeEstimationHelper
from octoprint.settings import settings
from octoprint.util import comm as comm
from octoprint.util import InvariantContainer
from octoprint.util import to_unicode


class Printer(PrinterInterface, comm.MachineComPrintCallback):
	"""
	Default implementation of the :class:`PrinterInterface`. Manages the communication layer object and registers
	itself with it as a callback to react to changes on the communication layer.
	"""

	def __init__(self, fileManager, analysisQueue, printerProfileManager):
		from collections import deque

		self._logger = logging.getLogger(__name__)

		self._analysisQueue = analysisQueue
		self._fileManager = fileManager
		self._printerProfileManager = printerProfileManager

		# state
		# TODO do we really need to hold the temperature here?
		self._temp = None
		self._bedTemp = None
		self._targetTemp = None
		self._targetBedTemp = None
		self._temps = TemperatureHistory(cutoff=settings().getInt(["temperature", "cutoff"])*60)
		self._tempBacklog = []

		self._messages = deque([], 300)
		self._messageBacklog = []

		self._log = deque([], 300)
		self._logBacklog = []

		self._state = None

		self._currentZ = None

		self._printAfterSelect = False
		self._posAfterSelect = None

		# sd handling
		self._sdPrinting = False
		self._sdStreaming = False
		self._sdFilelistAvailable = threading.Event()
		self._streamingFinishedCallback = None
		self._streamingFailedCallback = None

		self._selectedFileMutex = threading.RLock()
		self._selectedFile = None
		self._timeEstimationData = None
		self._timeEstimationStatsWeighingUntil = settings().getFloat(["estimation", "printTime", "statsWeighingUntil"])
		self._timeEstimationValidityRange = settings().getFloat(["estimation", "printTime", "validityRange"])
		self._timeEstimationForceDumbFromPercent = settings().getFloat(["estimation", "printTime", "forceDumbFromPercent"])
		self._timeEstimationForceDumbAfterMin = settings().getFloat(["estimation", "printTime", "forceDumbAfterMin"])

		# comm
		self._comm = None

		# callbacks
		self._callbacks = []

		# progress plugins
		self._lastProgressReport = None
		self._progressPlugins = plugin_manager().get_implementations(ProgressPlugin)

		self._stateMonitor = StateMonitor(
			interval=0.5,
			on_update=self._sendCurrentDataCallbacks,
			on_add_temperature=self._sendAddTemperatureCallbacks,
			on_add_log=self._sendAddLogCallbacks,
			on_add_message=self._sendAddMessageCallbacks,
			on_get_progress=self._updateProgressDataCallback
		)
		self._stateMonitor.reset(
			state={"text": self.get_state_string(), "flags": self._getStateFlags()},
			job_data={
				"file": {
					"name": None,
					"path": None,
					"size": None,
					"origin": None,
					"date": None
				},
				"estimatedPrintTime": None,
				"lastPrintTime": None,
				"filament": {
					"length": None,
					"volume": None
				}
			},
			progress={"completion": None, "filepos": None, "printTime": None, "printTimeLeft": None},
			current_z=None,
			offsets=dict()
		)

		eventManager().subscribe(Events.METADATA_ANALYSIS_FINISHED, self._on_event_MetadataAnalysisFinished)
		eventManager().subscribe(Events.METADATA_STATISTICS_UPDATED, self._on_event_MetadataStatisticsUpdated)

	#~~ handling of PrinterCallbacks

	def register_callback(self, callback):
		if not isinstance(callback, PrinterCallback):
			self._logger.warn("Registering an object as printer callback which doesn't implement the PrinterCallback interface")

		self._callbacks.append(callback)
		self._sendInitialStateUpdate(callback)

	def unregister_callback(self, callback):
		if callback in self._callbacks:
			self._callbacks.remove(callback)

	def _sendAddTemperatureCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_add_temperature(data)
			except: self._logger.exception("Exception while adding temperature data point")

	def _sendAddLogCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_add_log(data)
			except: self._logger.exception("Exception while adding communication log entry")

	def _sendAddMessageCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_add_message(data)
			except: self._logger.exception("Exception while adding printer message")

	def _sendCurrentDataCallbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_send_current_data(copy.deepcopy(data))
			except: self._logger.exception("Exception while pushing current data")

	#~~ callback from metadata analysis event

	def _on_event_MetadataAnalysisFinished(self, event, data):
		with self._selectedFileMutex:
			if self._selectedFile:
				self._setJobData(self._selectedFile["filename"],
								 self._selectedFile["filesize"],
								 self._selectedFile["sd"])

	def _on_event_MetadataStatisticsUpdated(self, event, data):
		with self._selectedFileMutex:
			if self._selectedFile:
				self._setJobData(self._selectedFile["filename"],
				                 self._selectedFile["filesize"],
				                 self._selectedFile["sd"])

	#~~ progress plugin reporting

	def _reportPrintProgressToPlugins(self, progress):
		with self._selectedFileMutex:
			if progress is None or not self._selectedFile or not "sd" in self._selectedFile or not "filename" in self._selectedFile:
				return

			storage = "sdcard" if self._selectedFile["sd"] else "local"
			filename = self._selectedFile["filename"]

		def call_plugins(storage, filename, progress):
			for plugin in self._progressPlugins:
				try:
					plugin.on_print_progress(storage, filename, progress)
				except:
					self._logger.exception("Exception while sending print progress to plugin %s" % plugin._identifier)

		thread = threading.Thread(target=call_plugins, args=(storage, filename, progress))
		thread.daemon = False
		thread.start()

	#~~ PrinterInterface implementation

	def connect(self, port=None, baudrate=None, profile=None):
		"""
		 Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
		 will be attempted.
		"""
		if self._comm is not None:
			self.disconnect()

		eventManager().fire(Events.CONNECTING)
		self._printerProfileManager.select(profile)

		from octoprint.logging.handlers import SerialLogHandler
		SerialLogHandler.on_open_connection()
		if not logging.getLogger("SERIAL").isEnabledFor(logging.DEBUG):
			# if serial.log is not enabled, log a line to explain that to reduce "serial.log is empty" in tickets...
			logging.getLogger("SERIAL").info("serial.log is currently not enabled, you can enable it via Settings > Serial Connection > Log communication to serial.log")

		self._comm = comm.MachineCom(port, baudrate, callbackObject=self, printerProfileManager=self._printerProfileManager)

	def disconnect(self):
		"""
		 Closes the connection to the printer.
		"""
		eventManager().fire(Events.DISCONNECTING)
		if self._comm is not None:
			self._comm.close()
		else:
			eventManager().fire(Events.DISCONNECTED)

	def get_transport(self):

		if self._comm is None:
			return None

		return self._comm.getTransport()
	getTransport = util.deprecated("getTransport has been renamed to get_transport", since="1.2.0-dev-590", includedoc="Replaced by :func:`get_transport`")

	def fake_ack(self):
		if self._comm is None:
			return

		self._comm.fakeOk()

	def commands(self, commands):
		"""
		Sends one or more gcode commands to the printer.
		"""
		if self._comm is None:
			return

		if not isinstance(commands, (list, tuple)):
			commands = [commands]

		for command in commands:
			self._comm.sendCommand(command)

	def script(self, name, context=None, must_be_set=True):
		if self._comm is None:
			return

		if name is None or not name:
			raise ValueError("name must be set")

		result = self._comm.sendGcodeScript(name, replacements=context)
		if not result and must_be_set:
			raise UnknownScript(name)

	def jog(self, axes, relative=True, speed=None, *args, **kwargs):
		if isinstance(axes, basestring):
			# legacy parameter format, there should be an amount as first anonymous positional arguments too
			axis = axes

			if not len(args) >= 1:
				raise ValueError("amount not set")
			amount = args[0]
			if not isinstance(amount, (int, long, float)):
				raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

			axes = dict()
			axes[axis] = amount

		if not axes:
			raise ValueError("At least one axis to jog must be provided")

		for axis in axes:
			if not axis in PrinterInterface.valid_axes:
				raise ValueError("Invalid axis {}, valid axes are {}".format(axis, ", ".join(PrinterInterface.valid_axes)))

		command = "G1 {}".format(" ".join(["{}{}".format(axis.upper(), amount) for axis, amount in axes.items()]))

		if speed is None:
			printer_profile = self._printerProfileManager.get_current_or_default()
			speed = min([printer_profile["axes"][axis]["speed"] for axis in axes])

		if speed and not isinstance(speed, bool):
			command += " F{}".format(speed)

		if relative:
			commands = ["G91", command, "G90"]
		else:
			commands = ["G90", command]

		self.commands(commands)

	def home(self, axes):
		if not isinstance(axes, (list, tuple)):
			if isinstance(axes, (str, unicode)):
				axes = [axes]
			else:
				raise ValueError("axes is neither a list nor a string: {axes}".format(axes=axes))

		validated_axes = filter(lambda x: x in PrinterInterface.valid_axes, map(lambda x: x.lower(), axes))
		if len(axes) != len(validated_axes):
			raise ValueError("axes contains invalid axes: {axes}".format(axes=axes))

		self.commands(["G91", "G28 %s" % " ".join(map(lambda x: "%s0" % x.upper(), validated_axes)), "G90"])

	def extrude(self, amount):
		if not isinstance(amount, (int, long, float)):
			raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

		printer_profile = self._printerProfileManager.get_current_or_default()
		extrusion_speed = printer_profile["axes"]["e"]["speed"]
		self.commands(["G91", "G1 E%s F%d" % (amount, extrusion_speed), "G90"])

	def change_tool(self, tool):
		if not PrinterInterface.valid_tool_regex.match(tool):
			raise ValueError("tool must match \"tool[0-9]+\": {tool}".format(tool=tool))

		tool_num = int(tool[len("tool"):])
		self.commands("T%d" % tool_num)

	def set_temperature(self, heater, value):
		if not PrinterInterface.valid_heater_regex.match(heater):
			raise ValueError("heater must match \"tool[0-9]+\" or \"bed\": {heater}".format(heater=heater))

		if not isinstance(value, (int, long, float)) or value < 0:
			raise ValueError("value must be a valid number >= 0: {value}".format(value=value))

		if heater.startswith("tool"):
			printer_profile = self._printerProfileManager.get_current_or_default()
			extruder_count = printer_profile["extruder"]["count"]
			shared_nozzle = printer_profile["extruder"]["sharedNozzle"]
			if extruder_count > 1 and not shared_nozzle:
				toolNum = int(heater[len("tool"):])
				self.commands("M104 T{} S{}".format(toolNum, value))
			else:
				self.commands("M104 S{}".format(value))

		elif heater == "bed":
			self.commands("M140 S{}".format(value))

	def set_temperature_offset(self, offsets=None):
		if offsets is None:
			offsets = dict()

		if not isinstance(offsets, dict):
			raise ValueError("offsets must be a dict")

		validated_keys = filter(lambda x: PrinterInterface.valid_heater_regex.match(x), offsets.keys())
		validated_values = filter(lambda x: isinstance(x, (int, long, float)), offsets.values())

		if len(validated_keys) != len(offsets):
			raise ValueError("offsets contains invalid keys: {offsets}".format(offsets=offsets))
		if len(validated_values) != len(offsets):
			raise ValueError("offsets contains invalid values: {offsets}".format(offsets=offsets))

		if self._comm is None:
			return

		self._comm.setTemperatureOffset(offsets)
		self._setOffsets(self._comm.getOffsets())

	def _convert_rate_value(self, factor, min=0, max=200):
		if not isinstance(factor, (int, float, long)):
			raise ValueError("factor is not a number")

		if isinstance(factor, float):
			factor = int(factor * 100.0)

		if factor < min or factor > max:
			raise ValueError("factor must be a value between {} and {}".format(min, max))

		return factor

	def feed_rate(self, factor):
		factor = self._convert_rate_value(factor, min=50, max=200)
		self.commands("M220 S%d" % factor)

	def flow_rate(self, factor):
		factor = self._convert_rate_value(factor, min=75, max=125)
		self.commands("M221 S%d" % factor)

	def select_file(self, path, sd, printAfterSelect=False, pos=None):
		if self._comm is None or (self._comm.isBusy() or self._comm.isStreaming()):
			self._logger.info("Cannot load file: printer not connected or currently busy")
			return

		self._validateJob(path, sd)

		recovery_data = self._fileManager.get_recovery_data()
		if recovery_data:
			# clean up recovery data if we just selected a different file than is logged in that
			expected_origin = FileDestinations.SDCARD if sd else FileDestinations.LOCAL
			actual_origin = recovery_data.get("origin", None)
			actual_path = recovery_data.get("path", None)

			if actual_origin is None or actual_path is None or actual_origin != expected_origin or actual_path != path:
				self._fileManager.delete_recovery_data()

		self._printAfterSelect = printAfterSelect
		self._posAfterSelect = pos
		self._comm.selectFile("/" + path if sd else path, sd)
		self._updateProgressData()
		self._setCurrentZ(None)

	def unselect_file(self):
		if self._comm is not None and (self._comm.isBusy() or self._comm.isStreaming()):
			return

		self._comm.unselectFile()
		self._updateProgressData()
		self._setCurrentZ(None)

	def get_file_position(self):
		if self._comm is None:
			return None

		with self._selectedFileMutex:
			if self._selectedFile is None:
				return None

		return self._comm.getFilePosition()

	def start_print(self, pos=None):
		"""
		 Starts the currently loaded print job.
		 Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
		"""
		if self._comm is None or not self._comm.isOperational() or self._comm.isPrinting():
			return
		with self._selectedFileMutex:
			if self._selectedFile is None:
				return

		# we are happy if the average of the estimates stays within 60s of the prior one
		threshold = settings().getFloat(["estimation", "printTime", "stableThreshold"])
		rolling_window = None
		countdown = None

		with self._selectedFileMutex:
			if self._selectedFile["sd"]:
				# we are interesting in a rolling window of roughly the last 15s, so the number of entries has to be derived
				# by that divided by the sd status polling interval
				rolling_window = 15 / settings().get(["serial", "timeout", "sdStatus"])

				# we are happy when one rolling window has been stable
				countdown = rolling_window
		self._timeEstimationData = TimeEstimationHelper(rolling_window=rolling_window,
		                                                threshold=threshold,
		                                                countdown=countdown)

		self._fileManager.delete_recovery_data()

		self._lastProgressReport = None
		self._updateProgressData()
		self._setCurrentZ(None)
		self._comm.startPrint(pos=pos)

	def pause_print(self):
		"""
		Pause the current printjob.
		"""
		if self._comm is None:
			return

		if self._comm.isPaused():
			return

		self._comm.setPause(True)

	def resume_print(self):
		"""
		Resume the current printjob.
		"""
		if self._comm is None:
			return

		if not self._comm.isPaused():
			return

		self._comm.setPause(False)

	def cancel_print(self):
		"""
		 Cancel the current printjob.
		"""
		if self._comm is None:
			return

		# tell comm layer to cancel - will also trigger our cancelled handler
		# for further processing
		self._comm.cancelPrint()

	def get_state_string(self, state=None):
		if self._comm is None:
			return "Offline"
		else:
			return self._comm.getStateString(state=state)

	def get_state_id(self, state=None):
		if self._comm is None:
			return "OFFLINE"
		else:
			return self._comm.getStateId(state=state)

	def get_current_data(self):
		return self._stateMonitor.get_current_data()

	def get_current_job(self):
		currentData = self._stateMonitor.get_current_data()
		return currentData["job"]

	def get_current_temperatures(self):
		if self._comm is not None:
			offsets = self._comm.getOffsets()
		else:
			offsets = dict()

		result = {}
		if self._temp is not None:
			for tool in self._temp.keys():
				result["tool%d" % tool] = {
					"actual": self._temp[tool][0],
					"target": self._temp[tool][1],
					"offset": offsets[tool] if tool in offsets and offsets[tool] is not None else 0
				}
		if self._bedTemp is not None:
			result["bed"] = {
				"actual": self._bedTemp[0],
				"target": self._bedTemp[1],
				"offset": offsets["bed"] if "bed" in offsets and offsets["bed"] is not None else 0
			}

		return result

	def get_temperature_history(self):
		return self._temps

	def get_current_connection(self):
		if self._comm is None:
			return "Closed", None, None, None

		port, baudrate = self._comm.getConnection()
		printer_profile = self._printerProfileManager.get_current_or_default()
		return self._comm.getStateString(), port, baudrate, printer_profile

	def is_closed_or_error(self):
		return self._comm is None or self._comm.isClosedOrError()

	def is_operational(self):
		return self._comm is not None and self._comm.isOperational()

	def is_printing(self):
		return self._comm is not None and self._comm.isPrinting()

	def is_paused(self):
		return self._comm is not None and self._comm.isPaused()

	def is_error(self):
		return self._comm is not None and self._comm.isError()

	def is_ready(self):
		return self.is_operational() and not self.is_printing() and not self._comm.isStreaming()

	def is_sd_ready(self):
		if not settings().getBoolean(["feature", "sdSupport"]) or self._comm is None:
			return False
		else:
			return self._comm.isSdReady()

	#~~ sd file handling

	def get_sd_files(self):
		if self._comm is None or not self._comm.isSdReady():
			return []
		return map(lambda x: (x[0][1:], x[1]), self._comm.getSdFiles())

	def add_sd_file(self, filename, absolutePath, on_success=None, on_failure=None):
		if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
			self._logger.error("No connection to printer or printer is busy")
			return

		self._streamingFinishedCallback = on_success
		self._streamingFailedCallback = on_failure

		self.refresh_sd_files(blocking=True)
		existingSdFiles = map(lambda x: x[0], self._comm.getSdFiles())

		if valid_file_type(filename, "gcode"):
			remoteName = util.get_dos_filename(filename,
			                                   existing_filenames=existingSdFiles,
			                                   extension="gco",
			                                   whitelisted_extensions=["gco", "g"])
		else:
			# probably something else added through a plugin, use it's basename as-is
			remoteName = os.path.basename(filename)
		self._timeEstimationData = TimeEstimationHelper()
		self._comm.startFileTransfer(absolutePath, filename, "/" + remoteName, special=not valid_file_type(filename, "gcode"))

		return remoteName

	def delete_sd_file(self, filename):
		if not self._comm or not self._comm.isSdReady():
			return
		self._comm.deleteSdFile("/" + filename)

	def init_sd_card(self):
		if not self._comm or self._comm.isSdReady():
			return
		self._comm.initSdCard()

	def release_sd_card(self):
		if not self._comm or not self._comm.isSdReady():
			return
		self._comm.releaseSdCard()

	def refresh_sd_files(self, blocking=False):
		"""
		Refreshes the list of file stored on the SD card attached to printer (if available and printer communication
		available). Optional blocking parameter allows making the method block (max 10s) until the file list has been
		received (and can be accessed via self._comm.getSdFiles()). Defaults to an asynchronous operation.
		"""
		if not self._comm or not self._comm.isSdReady():
			return
		self._sdFilelistAvailable.clear()
		self._comm.refreshSdFiles()
		if blocking:
			self._sdFilelistAvailable.wait(10000)

	#~~ state monitoring

	def _setOffsets(self, offsets):
		self._stateMonitor.set_temp_offsets(offsets)

	def _setCurrentZ(self, currentZ):
		self._currentZ = currentZ
		self._stateMonitor.set_current_z(self._currentZ)

	def _setState(self, state, state_string=None):
		if state_string is None:
			state_string = self.get_state_string()

		self._state = state
		self._stateMonitor.set_state({"text": state_string, "flags": self._getStateFlags()})

		payload = dict(
			state_id=self.get_state_id(self._state),
			state_string=self.get_state_string(self._state)
		)
		eventManager().fire(Events.PRINTER_STATE_CHANGED, payload)

	def _addLog(self, log):
		self._log.append(log)
		self._stateMonitor.add_log(log)

	def _addMessage(self, message):
		self._messages.append(message)
		self._stateMonitor.add_message(message)

	def _estimateTotalPrintTime(self, progress, printTime):
		if not progress or not printTime or not self._timeEstimationData:
			return None

		else:
			newEstimate = printTime / progress
			self._timeEstimationData.update(newEstimate)

			result = None
			if self._timeEstimationData.is_stable():
				result = self._timeEstimationData.average_total_rolling

			return result

	def _updateProgressData(self, completion=None, filepos=None, printTime=None, printTimeLeft=None):
		self._stateMonitor.set_progress(dict(completion=int(completion * 100) if completion is not None else None,
		                                     filepos=filepos,
		                                     printTime=int(printTime) if printTime is not None else None,
		                                     printTimeLeft=int(printTimeLeft) if printTimeLeft is not None else None))

	def _updateProgressDataCallback(self):
		if self._comm is None:
			progress = None
			filepos = None
			printTime = None
			cleanedPrintTime = None
		else:
			progress = self._comm.getPrintProgress()
			filepos = self._comm.getPrintFilepos()
			printTime = self._comm.getPrintTime()
			cleanedPrintTime = self._comm.getCleanedPrintTime()

		statisticalTotalPrintTime = None
		statisticalTotalPrintTimeType = None
		with self._selectedFileMutex:
			if self._selectedFile and "estimatedPrintTime" in self._selectedFile \
					and self._selectedFile["estimatedPrintTime"]:
				statisticalTotalPrintTime = self._selectedFile["estimatedPrintTime"]
				statisticalTotalPrintTimeType = self._selectedFile.get("estimatedPrintTimeType", None)

		printTimeLeft, printTimeLeftOrigin = self._estimatePrintTimeLeft(progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)

		if progress is not None:
			progress_int = int(progress * 100)
			if self._lastProgressReport != progress_int:
				self._lastProgressReport = progress_int
				self._reportPrintProgressToPlugins(progress_int)

		return dict(completion=progress * 100 if progress is not None else None,
		            filepos=filepos,
		            printTime=int(printTime) if printTime is not None else None,
		            printTimeLeft=int(printTimeLeft) if printTimeLeft is not None else None,
		            printTimeLeftOrigin=printTimeLeftOrigin)

	def _estimatePrintTimeLeft(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
		"""
		Tries to estimate the print time left for the print job

		This is somewhat horrible since accurate print time estimation is pretty much impossible to
		achieve, considering that we basically have only two data points (current progress in file and
		time needed for that so far - former prints or a file analysis might not have happened or simply
		be completely impossible e.g. if the file is stored on the printer's SD card) and
		hence can only do a linear estimation of a completely non-linear process. That's a recipe
		for inaccurate predictions right there. Yay.

		Anyhow, here's how this implementation works. This method gets the current progress in the
		printed file (percentage based on bytes read vs total bytes), the print time that elapsed,
		the same print time with the heat up times subtracted (if possible) and if available also
		some statistical total print time (former prints or a result from the GCODE analysis).

		  1. First get an "intelligent" estimate based on the :class:`~octoprint.printer.estimation.TimeEstimationHelper`.
		     That thing tries to detect if the estimation based on our progress and time needed for that becomes
		     stable over time through a rolling window and only returns a result once that appears to be the
		     case.
		  2. If we have any statistical data (former prints or a result from the GCODE analysis)
		     but no intelligent estimate yet, we'll use that for the next step. Otherwise, up to a certain percentage
		     in the print we do a percentage based weighing of the statistical data and the intelligent
		     estimate - the closer to the beginning of the print, the more precedence for the statistical
		     data, the closer to the cut off point, the more precendence for the intelligent estimate. This
		     is our preliminary total print time.
		  3. If the total print time is set, we do a sanity check for it. Based on the total print time
		     estimate and the time we already spent printing, we calculate at what percentage we SHOULD be
		     and compare that to the percentage at which we actually ARE. If it's too far off, our total
		     can't be trusted and we fall back on the dumb estimate. Same if the time we spent printing is
		     already higher than our total estimate.
		  4. If we do NOT have a total print time estimate yet but we've been printing for longer than
		     a configured amount of minutes or are further in the file than a configured percentage, we
		     also use the dumb estimate for now.

		Yes, all this still produces horribly inaccurate results. But we have to do this live during the print and
		hence can't produce to much computational overhead, we do not have any insight into the firmware implementation
		with regards to planner setup and acceleration settings, we might not even have access to the printed file's
		contents and such we need to find something that works "mostly" all of the time without costing too many
		resources. Feel free to propose a better solution within the above limitations (and I mean that, this solution
		here makes me unhappy).

		Args:
		    progress (float or None): Current percentage in the printed file
		    printTime (float or None): Print time elapsed so far
		    cleanedPrintTime (float or None): Print time elapsed minus the time needed for getting up to temperature
		        (if detectable).
		    statisticalTotalPrintTime (float or None): Total print time of past prints against same printer profile,
		        or estimated total print time from GCODE analysis.
		    statisticalTotalPrintTimeType (str or None): Type of statistical print time, either "average" (total time
		        of former prints) or "analysis"

		Returns:
		    (2-tuple) estimated print time left or None if not proper estimate could be made at all, origin of estimation
		"""

		if progress is None or progress == 0 or printTime is None or cleanedPrintTime is None:
			return None, None

		dumbTotalPrintTime = printTime / progress
		estimatedTotalPrintTime = self._estimateTotalPrintTime(progress, cleanedPrintTime)
		totalPrintTime = estimatedTotalPrintTime

		printTimeLeftOrigin = "estimate"
		if statisticalTotalPrintTime is not None:
			if estimatedTotalPrintTime is None:
				# no estimate yet, we'll use the statistical total
				totalPrintTime = statisticalTotalPrintTime
				printTimeLeftOrigin = statisticalTotalPrintTimeType

			else:
				if progress < self._timeEstimationStatsWeighingUntil:
					# still inside weighing range, use part stats, part current estimate
					sub_progress = progress * (1 / self._timeEstimationStatsWeighingUntil)
					if sub_progress > 1.0:
						sub_progress = 1.0
					printTimeLeftOrigin = "mixed-" + statisticalTotalPrintTimeType
				else:
					# use only the current estimate
					sub_progress = 1.0
					printTimeLeftOrigin = "estimate"

				# combine
				totalPrintTime = (1.0 - sub_progress) * statisticalTotalPrintTime \
				                 + sub_progress * estimatedTotalPrintTime

		printTimeLeft = None
		if totalPrintTime is not None:
			# sanity check current total print time estimate
			assumed_progress = cleanedPrintTime / totalPrintTime
			min_progress = progress - self._timeEstimationValidityRange
			max_progress = progress + self._timeEstimationValidityRange

			if min_progress <= assumed_progress <= max_progress and totalPrintTime > cleanedPrintTime:
				# appears sane, we'll use it
				printTimeLeft = totalPrintTime - cleanedPrintTime

			else:
				# too far from the actual progress or negative,
				# we use the dumb print time instead
				printTimeLeft = dumbTotalPrintTime - cleanedPrintTime
				printTimeLeftOrigin = "linear"

		else:
			printTimeLeftOrigin = "linear"
			if progress > self._timeEstimationForceDumbFromPercent or \
					cleanedPrintTime >= self._timeEstimationForceDumbAfterMin * 60:
				# more than x% or y min printed and still no real estimate, ok, we'll use the dumb variant :/
				printTimeLeft = dumbTotalPrintTime - cleanedPrintTime

		if printTimeLeft is not None and printTimeLeft < 0:
			# shouldn't actually happen, but let's make sure
			printTimeLeft = None

		return printTimeLeft, printTimeLeftOrigin

	def _addTemperatureData(self, tools=None, bed=None):
		if tools is None:
			tools = dict()

		currentTimeUtc = int(time.time())

		data = {
			"time": currentTimeUtc
		}
		for tool in tools.keys():
			data["tool%d" % tool] = {
				"actual": tools[tool][0],
				"target": tools[tool][1]
			}
		if bed is not None and isinstance(bed, tuple):
			data["bed"] = {
				"actual": bed[0],
				"target": bed[1]
			}

		self._temps.append(data)

		self._temp = tools
		self._bedTemp = bed

		self._stateMonitor.add_temperature(data)

	def _validateJob(self, filename, sd):
		if not valid_file_type(filename, type="machinecode"):
			raise InvalidFileType("{} is not a machinecode file, cannot print".format(filename))

		if sd:
			return

		path_on_disk = self._fileManager.path_on_disk(FileDestinations.LOCAL, filename)
		if os.path.isabs(filename) and not filename == path_on_disk:
			raise InvalidFileLocation("{} is not located within local storage, cannot select for printing".format(filename))
		if not os.path.isfile(path_on_disk):
			raise InvalidFileLocation("{} does not exist in local storage, cannot select for printing".format(filename))

	def _setJobData(self, filename, filesize, sd):
		with self._selectedFileMutex:
			if filename is not None:
				if sd:
					name_in_storage = filename
					if name_in_storage.startswith("/"):
						name_in_storage = name_in_storage[1:]
					path_in_storage = name_in_storage
					path_on_disk = None
				else:
					path_in_storage = self._fileManager.path_in_storage(FileDestinations.LOCAL, filename)
					path_on_disk = self._fileManager.path_on_disk(FileDestinations.LOCAL, filename)
					_, name_in_storage = self._fileManager.split_path(FileDestinations.LOCAL, path_in_storage)
				self._selectedFile = {
					"filename": path_in_storage,
					"filesize": filesize,
					"sd": sd,
					"estimatedPrintTime": None
				}
			else:
				self._selectedFile = None
				self._stateMonitor.set_job_data({
					"file": {
						"name": None,
						"path": None,
						"display": None,
						"origin": None,
						"size": None,
						"date": None
					},
					"estimatedPrintTime": None,
					"averagePrintTime": None,
					"lastPrintTime": None,
					"filament": None,
				})
				return

			estimatedPrintTime = None
			lastPrintTime = None
			averagePrintTime = None
			date = None
			filament = None
			display_name = name_in_storage
			if path_on_disk:
				# Use a string for mtime because it could be float and the
				# javascript needs to exact match
				if not sd:
					date = int(os.stat(path_on_disk).st_mtime)

				try:
					fileData = self._fileManager.get_metadata(FileDestinations.SDCARD if sd else FileDestinations.LOCAL, path_on_disk)
				except:
					fileData = None
				if fileData is not None:
					if "display" in fileData:
						display_name = fileData["display"]
					if "analysis" in fileData:
						if estimatedPrintTime is None and "estimatedPrintTime" in fileData["analysis"]:
							estimatedPrintTime = fileData["analysis"]["estimatedPrintTime"]
						if "filament" in fileData["analysis"].keys():
							filament = fileData["analysis"]["filament"]
					if "statistics" in fileData:
						printer_profile = self._printerProfileManager.get_current_or_default()["id"]
						if "averagePrintTime" in fileData["statistics"] and printer_profile in fileData["statistics"]["averagePrintTime"]:
							averagePrintTime = fileData["statistics"]["averagePrintTime"][printer_profile]
						if "lastPrintTime" in fileData["statistics"] and printer_profile in fileData["statistics"]["lastPrintTime"]:
							lastPrintTime = fileData["statistics"]["lastPrintTime"][printer_profile]

					if averagePrintTime is not None:
						self._selectedFile["estimatedPrintTime"] = averagePrintTime
						self._selectedFile["estimatedPrintTimeType"] = "average"
					elif estimatedPrintTime is not None:
						# TODO apply factor which first needs to be tracked!
						self._selectedFile["estimatedPrintTime"] = estimatedPrintTime
						self._selectedFile["estimatedPrintTimeType"] = "analysis"

			self._stateMonitor.set_job_data({
				"file": {
					"name": name_in_storage,
					"path": path_in_storage,
					"display": display_name,
					"origin": FileDestinations.SDCARD if sd else FileDestinations.LOCAL,
					"size": filesize,
					"date": date
				},
				"estimatedPrintTime": estimatedPrintTime,
				"averagePrintTime": averagePrintTime,
				"lastPrintTime": lastPrintTime,
				"filament": filament,
			})

	def _sendInitialStateUpdate(self, callback):
		try:
			data = self._stateMonitor.get_current_data()
			data.update({
				"temps": list(self._temps),
				"logs": list(self._log),
				"messages": list(self._messages)
			})
			callback.on_printer_send_initial_data(data)
		except:
			self._logger.exception("Error while trying to send initial state update")

	def _getStateFlags(self):
		return {
			"operational": self.is_operational(),
			"printing": self.is_printing(),
			"closedOrError": self.is_closed_or_error(),
			"error": self.is_error(),
			"paused": self.is_paused(),
			"ready": self.is_ready(),
			"sdReady": self.is_sd_ready()
		}

	#~~ comm.MachineComPrintCallback implementation

	def on_comm_log(self, message):
		"""
		 Callback method for the comm object, called upon log output.
		"""
		self._addLog(to_unicode(message, "utf-8", errors="replace"))

	def on_comm_temperature_update(self, temp, bedTemp):
		self._addTemperatureData(tools=copy.deepcopy(temp), bed=copy.deepcopy(bedTemp))

	def on_comm_position_update(self, position, reason=None):
		payload = dict(reason=reason)
		payload.update(position)
		eventManager().fire(Events.POSITION_UPDATE, payload)

	def on_comm_state_change(self, state):
		"""
		 Callback method for the comm object, called if the connection state changes.
		"""
		oldState = self._state

		state_string = None
		if self._comm is not None:
			state_string = self._comm.getStateString()

		# forward relevant state changes to gcode manager
		if oldState == comm.MachineCom.STATE_PRINTING:
			with self._selectedFileMutex:
				if self._selectedFile is not None:
					if state == comm.MachineCom.STATE_CLOSED or state == comm.MachineCom.STATE_ERROR or state == comm.MachineCom.STATE_CLOSED_WITH_ERROR:
						def log_print():
							self._fileManager.log_print(FileDestinations.SDCARD if self._selectedFile["sd"] else FileDestinations.LOCAL,
							                            self._selectedFile["filename"],
							                            time.time(),
							                            self._comm.getPrintTime(),
							                            False,
							                            self._printerProfileManager.get_current_or_default()["id"])

						thread = threading.Thread(target=log_print)
						thread.daemon = True
						thread.start()
			self._analysisQueue.resume() # printing done, put those cpu cycles to good use
		elif state == comm.MachineCom.STATE_PRINTING:
			self._analysisQueue.pause() # do not analyse files while printing

		if state == comm.MachineCom.STATE_CLOSED or state == comm.MachineCom.STATE_CLOSED_WITH_ERROR:
			if self._comm is not None:
				self._comm = None

			self._updateProgressData()
			self._setCurrentZ(None)
			self._setJobData(None, None, None)
			self._setOffsets(None)
			self._addTemperatureData()
			self._printerProfileManager.deselect()
			eventManager().fire(Events.DISCONNECTED)

		self._setState(state, state_string=state_string)

	def on_comm_message(self, message):
		"""
		 Callback method for the comm object, called upon message exchanges via serial.
		 Stores the message in the message buffer, truncates buffer to the last 300 lines.
		"""
		self._addMessage(to_unicode(message, "utf-8", errors="replace"))

	def on_comm_progress(self):
		"""
		 Callback method for the comm object, called upon any change in progress of the printjob.
		 Triggers storage of new values for printTime, printTimeLeft and the current progress.
		"""

		self._stateMonitor.trigger_progress_update()

	def on_comm_z_change(self, newZ):
		"""
		 Callback method for the comm object, called upon change of the z-layer.
		"""
		oldZ = self._currentZ
		if newZ != oldZ:
			# we have to react to all z-changes, even those that might "go backward" due to a slicer's retraction or
			# anti-backlash-routines. Event subscribes should individually take care to filter out "wrong" z-changes
			eventManager().fire(Events.Z_CHANGE, {"new": newZ, "old": oldZ})

		self._setCurrentZ(newZ)

	def on_comm_sd_state_change(self, sdReady):
		self._stateMonitor.set_state({"text": self.get_state_string(), "flags": self._getStateFlags()})

	def on_comm_sd_files(self, files):
		eventManager().fire(Events.UPDATED_FILES, {"type": "gcode"})
		self._sdFilelistAvailable.set()

	def on_comm_file_selected(self, full_path, size, sd):
		if full_path is not None:
			payload = self._payload_for_print_job_event(location=FileDestinations.SDCARD if sd else FileDestinations.LOCAL,
			                                            print_job_file=full_path)
			eventManager().fire(Events.FILE_SELECTED, payload)
		else:
			eventManager().fire(Events.FILE_DESELECTED)

		self._setJobData(full_path, size, sd)
		self._stateMonitor.set_state({"text": self.get_state_string(), "flags": self._getStateFlags()})

		if self._printAfterSelect:
			self._printAfterSelect = False
			self.start_print(pos=self._posAfterSelect)

	def on_comm_print_job_started(self):
		payload = self._payload_for_print_job_event()
		if payload:
			eventManager().fire(Events.PRINT_STARTED, payload)
			self.script("beforePrintStarted",
			            context=dict(event=payload),
			            must_be_set=False)

	def on_comm_print_job_done(self):
		self._fileManager.delete_recovery_data()

		payload = self._payload_for_print_job_event()
		if payload:
			payload["time"] = self._comm.getPrintTime()
			self._updateProgressData(completion=1.0,
			                         filepos=payload["size"],
			                         printTime=payload["time"],
			                         printTimeLeft=0)
			self._stateMonitor.set_state({"text": self.get_state_string(), "flags": self._getStateFlags()})

			eventManager().fire(Events.PRINT_DONE, payload)
			self.script("afterPrintDone",
			            context=dict(event=payload),
			            must_be_set=False)

			def log_print():
				self._fileManager.log_print(payload["origin"],
				                            payload["path"],
				                            time.time(),
				                            payload["time"],
				                            True,
				                            self._printerProfileManager.get_current_or_default()["id"])

			thread = threading.Thread(target=log_print)
			thread.daemon = True
			thread.start()

		else:
			self._updateProgressData()
			self._stateMonitor.set_state({"text": self.get_state_string(), "flags": self._getStateFlags()})


	def on_comm_print_job_failed(self):
		payload = self._payload_for_print_job_event()
		eventManager().fire(Events.PRINT_FAILED, payload)

	def on_comm_print_job_cancelled(self):
		self._setCurrentZ(None)
		self._updateProgressData()

		payload = self._payload_for_print_job_event(position=self._comm.cancel_position.as_dict() if self._comm and self._comm.cancel_position else None)
		if payload:
			payload["time"] = self._comm.getPrintTime()

			eventManager().fire(Events.PRINT_CANCELLED, payload)
			self.script("afterPrintCancelled",
			            context=dict(event=payload),
			            must_be_set=False)

			def finalize():
				self._fileManager.log_print(payload["origin"],
				                            payload["path"],
				                            time.time(),
				                            payload["time"],
				                            False,
				                            self._printerProfileManager.get_current_or_default()["id"])
				eventManager().fire(Events.PRINT_FAILED, payload)

			thread = threading.Thread(target=finalize)
			thread.daemon = True
			thread.start()

	def on_comm_print_job_paused(self):
		payload = self._payload_for_print_job_event(position=self._comm.pause_position.as_dict() if self._comm and self._comm.pause_position else None)
		if payload:
			eventManager().fire(Events.PRINT_PAUSED, payload)
			self.script("afterPrintPaused",
			            context=dict(event=payload),
			            must_be_set=False)

	def on_comm_print_job_resumed(self):
		payload = self._payload_for_print_job_event()
		if payload:
			eventManager().fire(Events.PRINT_RESUMED, payload)
			self.script("beforePrintResumed",
			            context=dict(event=payload),
			            must_be_set=False)

	def on_comm_file_transfer_started(self, filename, filesize):
		self._sdStreaming = True

		self._setJobData(filename, filesize, True)
		self._updateProgressData(completion=0.0, filepos=0, printTime=0)
		self._stateMonitor.set_state({"text": self.get_state_string(), "flags": self._getStateFlags()})

	def on_comm_file_transfer_done(self, filename, failed=False):
		self._sdStreaming = False

		# in case of SD files, both filename and absolutePath are the same, so we set the (remote) filename for
		# both parameters
		if failed:
			if self._streamingFailedCallback is not None:
				self._streamingFailedCallback(filename, filename, FileDestinations.SDCARD)
		else:
			if self._streamingFinishedCallback is not None:
				self._streamingFinishedCallback(filename, filename, FileDestinations.SDCARD)

		self._setCurrentZ(None)
		self._setJobData(None, None, None)
		self._updateProgressData()
		self._stateMonitor.set_state({"text": self.get_state_string(), "flags": self._getStateFlags()})

	def on_comm_file_transfer_failed(self, filename):
		self.on_comm_file_transfer_done(filename, failed=True)

	def on_comm_force_disconnect(self):
		self.disconnect()

	def on_comm_record_fileposition(self, origin, name, pos):
		try:
			self._fileManager.save_recovery_data(origin, name, pos)
		except NoSuchStorage:
			pass
		except:
			self._logger.exception("Error while trying to persist print recovery data")

	def _payload_for_print_job_event(self, location=None, print_job_file=None, print_job_size=None, position=None):
		if print_job_file is None:
			with self._selectedFileMutex:
				selected_file = self._selectedFile
				if not selected_file:
					return dict()

				print_job_file = selected_file.get("filename", None)
				print_job_size = selected_file.get("filesize", None)
				location = FileDestinations.SDCARD if selected_file.get("sd", False) else FileDestinations.LOCAL

		if not print_job_file or not location:
			return dict()

		if location == FileDestinations.SDCARD:
			full_path = print_job_file
			if full_path.startswith("/"):
				full_path = full_path[1:]
			name = path = full_path
			origin = FileDestinations.SDCARD

		else:
			full_path = self._fileManager.path_on_disk(FileDestinations.LOCAL, print_job_file)
			path = self._fileManager.path_in_storage(FileDestinations.LOCAL, print_job_file)
			_, name = self._fileManager.split_path(FileDestinations.LOCAL, path)
			origin = FileDestinations.LOCAL

		result= dict(name=name,
		             path=path,
		             origin=origin,
		             size=print_job_size,

		             # TODO deprecated, remove in 1.4.0
		             file=full_path,
		             filename=name)

		if position is not None:
			result["position"] = position

		return result


class StateMonitor(object):
	def __init__(self, interval=0.5, on_update=None, on_add_temperature=None, on_add_log=None, on_add_message=None, on_get_progress=None):
		self._interval = interval
		self._update_callback = on_update
		self._on_add_temperature = on_add_temperature
		self._on_add_log = on_add_log
		self._on_add_message = on_add_message
		self._on_get_progress = on_get_progress

		self._state = None
		self._job_data = None
		self._current_z = None
		self._offsets = dict()
		self._progress = None

		self._progress_dirty = False

		self._change_event = threading.Event()
		self._state_lock = threading.Lock()
		self._progress_lock = threading.Lock()

		self._last_update = time.time()
		self._worker = threading.Thread(target=self._work)
		self._worker.daemon = True
		self._worker.start()

	def _get_current_progress(self):
		if callable(self._on_get_progress):
			return self._on_get_progress()
		return self._progress

	def reset(self, state=None, job_data=None, progress=None, current_z=None, offsets=None):
		self.set_state(state)
		self.set_job_data(job_data)
		self.set_progress(progress)
		self.set_current_z(current_z)
		self.set_temp_offsets(offsets)

	def add_temperature(self, temperature):
		self._on_add_temperature(temperature)
		self._change_event.set()

	def add_log(self, log):
		self._on_add_log(log)
		self._change_event.set()

	def add_message(self, message):
		self._on_add_message(message)
		self._change_event.set()

	def set_current_z(self, current_z):
		self._current_z = current_z
		self._change_event.set()

	def set_state(self, state):
		with self._state_lock:
			self._state = state
			self._change_event.set()

	def set_job_data(self, job_data):
		self._job_data = job_data
		self._change_event.set()

	def trigger_progress_update(self):
		with self._progress_lock:
			self._progress_dirty = True
			self._change_event.set()

	def set_progress(self, progress):
		with self._progress_lock:
			self._progress_dirty = False
			self._progress = progress
			self._change_event.set()

	def set_temp_offsets(self, offsets):
		if offsets is None:
			offsets = dict()
		self._offsets = offsets
		self._change_event.set()

	def _work(self):
		while True:
			self._change_event.wait()

			now = time.time()
			delta = now - self._last_update
			additional_wait_time = self._interval - delta
			if additional_wait_time > 0:
				time.sleep(additional_wait_time)

			with self._state_lock:
				data = self.get_current_data()
				self._update_callback(data)
				self._last_update = time.time()
				self._change_event.clear()

	def get_current_data(self):
		with self._progress_lock:
			if self._progress_dirty:
				self._progress = self._get_current_progress()
				self._progress_dirty = False

		return {
			"state": self._state,
			"job": self._job_data,
			"currentZ": self._current_z,
			"progress": self._progress,
			"offsets": self._offsets
		}


class TemperatureHistory(InvariantContainer):
	def __init__(self, cutoff=30 * 60):

		def temperature_invariant(data):
			data.sort(key=lambda x: x["time"])
			now = int(time.time())
			return [item for item in data if item["time"] >= now - cutoff]

		InvariantContainer.__init__(self, guarantee_invariant=temperature_invariant)
