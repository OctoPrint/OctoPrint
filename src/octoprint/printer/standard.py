# coding=utf-8
"""
This module holds the standard implementation of the :class:`PrinterInterface` and it helpers.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import copy
import logging
import os
import threading
import time

from octoprint import util as util
from octoprint.events import eventManager, Events
from octoprint.filemanager import FileDestinations
from octoprint.plugin import plugin_manager, ProgressPlugin
from octoprint.printer import PrinterInterface, PrinterCallback, UnknownScript
from octoprint.printer.estimation import TimeEstimationHelper
from octoprint.settings import settings
from octoprint.util import comm as comm
from octoprint.util import InvariantContainer

from octoprint.comm.protocol import ProtocolListener, FileAwareProtocolListener, ProtocolState

from octoprint.job import LocalGcodeFilePrintjob, LocalGcodeStreamjob, SDFilePrintjob, PrintjobListener

from collections import namedtuple

JobData = namedtuple("JobData", ("job", "average_past_total", "analysis_total", "estimator"))

def _serial_factory(port=None, baudrate=None):
	import serial

	serial_factory_hooks = plugin_manager().get_hooks("octoprint.comm.transport.serial.factory")

	def default(_, port, baudrate, read_timeout):
		serial_obj = serial.Serial(str(port), baudrate, timeout=read_timeout, writeTimeout=10000, parity=serial.PARITY_ODD)
		serial_obj.close()
		serial_obj.parity = serial.PARITY_NONE
		serial_obj.open()
		return serial_obj

	serial_factories = serial_factory_hooks.items() + [("default", default)]
	for name, factory in serial_factories:
		try:
			serial_obj = factory(None, port, baudrate, settings().getFloat(["serial", "timeout", "connection"]))
		except:
			logging.getLogger(__name__).exception("Error while creating serial via factory {}".format(name))
			return None

		if serial_obj is not None:
			return serial_obj

	return None


class Printer(PrinterInterface, comm.MachineComPrintCallback, ProtocolListener, FileAwareProtocolListener, PrintjobListener):
	"""
	Default implementation of the :class:`PrinterInterface`. Manages the communication layer object and registers
	itself with it as a callback to react to changes on the communication layer.
	"""

	def __init__(self, fileManager, analysisQueue, printerProfileManager):
		from collections import deque

		self._logger = logging.getLogger(__name__)

		self._analysis_queue = analysisQueue
		self._file_manager = fileManager
		self._printer_profile_manager = printerProfileManager

		# state
		self._latest_temperatures = None
		self._temperature_history = TemperatureHistory(cutoff=settings().getInt(["temperature", "cutoff"]) * 60)
		self._temp_backlog = []

		self._latest_message = None
		self._messages = deque([], 300)
		self._message_backlog = []

		self._latest_log = None
		self._log = deque([], 300)
		self._log_backlog = []

		self._current_z = None

		self._progress = None
		self._print_time = None
		self._print_time_left = None

		# sd handling
		self._sdPrinting = False
		self._sdStreaming = False
		self._sd_filelist_available = threading.Event()
		self._streamingFinishedCallback = None

		self._sd_ready = False
		self._sd_files = []

		# comm
		self._comm = None

		self._protocol = None
		self._transport = None
		self._job = None

		# callbacks
		self._callbacks = []

		# progress plugins
		self._last_progress_report = None
		self._progress_plugins = plugin_manager().get_implementations(ProgressPlugin)

		self._state_monitor = StateMonitor(
			interval=0.5,
			on_update=self._send_current_data_callbacks,
			on_add_temperature=self.send_add_temperature_callbacks,
			on_add_log=self._send_add_log_callbacks,
			on_add_message=self._send_add_message_callbacks
		)
		self._state_monitor.reset(
			state={"text": self.get_state_string(), "flags": self._get_state_flags()},
			job_data={
				"file": {
					"name": None,
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
			current_z=None
		)

		eventManager().subscribe(Events.METADATA_ANALYSIS_FINISHED, self._on_event_MetadataAnalysisFinished)
		eventManager().subscribe(Events.METADATA_STATISTICS_UPDATED, self._on_event_MetadataStatisticsUpdated)

	#~~ handling of PrinterCallbacks

	def register_callback(self, callback):
		if not isinstance(callback, PrinterCallback):
			self._logger.warn("Registering an object as printer callback which doesn't implement the PrinterCallback interface")

		self._callbacks.append(callback)
		self._send_initial_state_update(callback)

	def unregister_callback(self, callback):
		if callback in self._callbacks:
			self._callbacks.remove(callback)

	def send_add_temperature_callbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_add_temperature(data)
			except: self._logger.exception("Exception while adding temperature data point")

	def _send_add_log_callbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_add_log(data)
			except: self._logger.exception("Exception while adding communication log entry")

	def _send_add_message_callbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_add_message(data)
			except: self._logger.exception("Exception while adding printer message")

	def _send_current_data_callbacks(self, data):
		for callback in self._callbacks:
			try: callback.on_printer_send_current_data(copy.deepcopy(data))
			except: self._logger.exception("Exception while pushing current data")

	#~~ callback from metadata analysis event

	def _on_event_MetadataAnalysisFinished(self, event, data):
		if self._job is not None:
			self._update_job()

	def _on_event_MetadataStatisticsUpdated(self, event, data):
		if self._job is not None:
			self._update_job()

	#~~ progress plugin reporting

	def _report_print_progress_to_plugins(self, progress):
		# TODO clean up
		if not progress or not self._job:
			return

		origin = self._get_origin_for_job()
		storage = "sdcard" if origin == FileDestinations.SDCARD else "local"
		filename = self._job.job.name

		def call_plugins(storage, filename, progress):
			for plugin in self._progress_plugins:
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

		if self._protocol is not None or self._transport is not None:
			self.disconnect()

		eventManager().fire(Events.CONNECTING)
		self._printer_profile_manager.select(profile)

		from octoprint.comm.transport.serialtransport import SerialTransport
		transport = SerialTransport(serial_factory=_serial_factory)

		from octoprint.comm.protocol.reprap import ReprapGcodeProtocol
		from octoprint.comm.protocol.reprap.flavors.marlin import BqMarlinFlavor
		protocol = ReprapGcodeProtocol(BqMarlinFlavor)
		protocol.register_listener(self)

		self._transport = transport
		self._protocol = protocol

		self._protocol.connect(self._transport, transport_kwargs=dict(port=port, baudrate=baudrate))

	def disconnect(self):
		"""
		 Closes the connection to the printer.
		"""
		eventManager().fire(Events.DISCONNECTING)
		self.cancel_print()

		if self._protocol is not None and self._protocol.state not in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR):
			self._protocol.disconnect()
			self._protocol.unregister_listener(self)
			self._protocol = None
			self._transport = None

		eventManager().fire(Events.DISCONNECTED)

	def get_transport(self):

		if self._comm is None:
			return None

		return self._comm.getTransport()
	getTransport = util.deprecated("getTransport has been renamed to get_transport", since="1.2.0-dev-590", includedoc="Replaced by :func:`get_transport`")

	def fake_ack(self):
		if self._protocol is None:
			return

		self._protocol.repair()

	def commands(self, commands):
		"""
		Sends one or more gcode commands to the printer.
		"""
		if self._protocol is None:
			return

		if not isinstance(commands, (list, tuple)):
			commands = [commands]

		self._protocol.send_commands(*commands)

	def script(self, name, context=None):
		if self._protocol is None:
			return

		if name is None or not name:
			raise ValueError("name must be set")

		# TODO
		#result = self._comm.sendGcodeScript(name, replacements=context)
		#if not result:
		#	raise UnknownScript(name)

	def jog(self, axis, amount):
		if not isinstance(axis, (str, unicode)):
			raise ValueError("axis must be a string: {axis}".format(axis=axis))

		axis = axis.lower()
		if not axis in PrinterInterface.valid_axes:
			raise ValueError("axis must be any of {axes}: {axis}".format(axes=", ".join(PrinterInterface.valid_axes), axis=axis))
		if not isinstance(amount, (int, long, float)):
			raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

		printer_profile = self._printer_profile_manager.get_current_or_default()
		movement_speed = printer_profile["axes"][axis]["speed"]

		kwargs = dict(feedrate=movement_speed,
		              relative=True)
		kwargs[axis] = amount
		self._protocol.move(**kwargs)

	def home(self, axes):
		if not isinstance(axes, (list, tuple)):
			if isinstance(axes, (str, unicode)):
				axes = [axes]
			else:
				raise ValueError("axes is neither a list nor a string: {axes}".format(axes=axes))

		validated_axes = filter(lambda x: x in PrinterInterface.valid_axes, map(lambda x: x.lower(), axes))
		if len(axes) != len(validated_axes):
			raise ValueError("axes contains invalid axes: {axes}".format(axes=axes))

		kwargs = dict((axes, True) for axes in validated_axes)
		self._protocol.home(**kwargs)

	def extrude(self, amount):
		if not isinstance(amount, (int, long, float)):
			raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

		printer_profile = self._printer_profile_manager.get_current_or_default()
		extrusion_speed = printer_profile["axes"]["e"]["speed"]
		self._protocol.move(e=amount, feedrate=extrusion_speed, relative=True)

	def change_tool(self, tool):
		if not PrinterInterface.valid_tool_regex.match(tool):
			raise ValueError("tool must match \"tool[0-9]+\": {tool}".format(tool=tool))

		tool_num = int(tool[len("tool"):])
		self._protocol.change_tool(tool_num)

	def set_temperature(self, heater, value):
		if not PrinterInterface.valid_heater_regex.match(heater):
			raise ValueError("heater must match \"tool[0-9]+\" or \"bed\": {heater}".format(type=heater))

		if not isinstance(value, (int, long, float)) or value < 0:
			raise ValueError("value must be a valid number >= 0: {value}".format(value=value))

		if heater.startswith("tool"):
			printer_profile = self._printer_profile_manager.get_current_or_default()
			extruder_count = printer_profile["extruder"]["count"]
			if extruder_count > 1:
				toolNum = int(heater[len("tool"):])
				self._protocol.set_extruder_temperature(value, tool=toolNum, wait=False)
			else:
				self._protocol.set_extruder_temperature(value, wait=False)

		elif heater == "bed":
			self._protocol.set_bed_temperature(value, wait=False)

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

		if self._protocol is None:
			return

		# TODO
		#self._comm.setTemperatureOffset(offsets)
		#self._stateMonitor.set_temp_offsets(offsets)

	def _convert_rate_value(self, factor, min=0, max=200):
		if not isinstance(factor, (int, float, long)):
			raise ValueError("factor is not a number")

		if isinstance(factor, float):
			factor = int(factor * 100.0)

		if factor < min or factor > max:
			raise ValueError("factor must be a value between %f and %f" % (min, max))

		return factor

	def feed_rate(self, factor):
		factor = self._convert_rate_value(factor, min=50, max=200)
		self._protocol.set_feedrate_multiplier(factor)

	def flow_rate(self, factor):
		factor = self._convert_rate_value(factor, min=75, max=125)
		self._protocol.set_extrusion_multiplier(factor)

	def select_job(self, job, start_printing=False, pos=None):
		self._update_job(job)
		self._reset_progress_data()

		if start_printing and self.is_ready():
			self.start_print(pos=pos)

	def unselect_job(self):
		self._update_job(job=None)
		self._reset_progress_data()

	# TODO add a since to the deprecation message as soon as the version this stuff will be included in is defined
	@util.deprecated("select_file has been deprecated, use select_job instead", includedoc="Replaced by :func:`select_job`")
	def select_file(self, path, sd, printAfterSelect=False, pos=None):
		if sd:
			job = SDFilePrintjob("/" + path)
		else:
			job = LocalGcodeFilePrintjob(os.path.join(settings().getBaseFolder("uploads"), path), name=path)

		self.select_job(job, start_printing=printAfterSelect, pos=pos)

	# TODO add a since to the deprecation message as soon as the version this stuff will be included in is defined
	unselect_file = util.deprecated("unselect_file has been deprecated, use unselect_job instead", includedoc="Replaced by :func:`unselect_job`")(unselect_job)

	def start_print(self, pos=None):
		"""
		 Starts the currently loaded print job.
		 Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
		"""
		if self._job is None or self._protocol is None or self._protocol.state not in (ProtocolState.CONNECTED,):
			return

		self._last_progress_report = None
		self._update_progress_data()
		self._setCurrentZ(None)

		self._protocol.process(self._job.job, position=pos)

	def toggle_pause_print(self):
		"""
		 Pause the current printjob.
		"""
		if self._protocol is None:
			return

		if self._protocol.state == ProtocolState.PAUSED:
			self._protocol.resume_processing()
		else:
			self._protocol.pause_processing()

	def cancel_print(self, error=False):
		"""
		 Cancel the current printjob.
		"""
		if self._protocol is None or not self._protocol.state in (ProtocolState.PRINTING, ProtocolState.PAUSED):
			return

		# reset progress, height, print time
		self._setCurrentZ(None)
		self._reset_progress_data()

		# mark print as failure
		if self._job is not None:
			origin = self._get_origin_for_job(self._job.job)
			self._file_manager.log_print(origin,
			                             self._job.job.name,
			                             time.time(),
			                             self._job.job.elapsed,
			                             False,
			                             self._printer_profile_manager.get_current_or_default()["id"])
			payload = {
				"file": self._job.job.name,
				"origin": origin
			}
			eventManager().fire(Events.PRINT_FAILED, payload)

		self._protocol.cancel_processing(error=error)

	def get_state_string(self, state=None):
		if self._protocol is None:
			return "Offline"
		else:
			if state is None:
				state = self._protocol.state

			if state == ProtocolState.DISCONNECTED:
				return "Offline"
			elif state == ProtocolState.CONNECTING:
				return "Connecting"
			elif state == ProtocolState.CONNECTED:
				return "Operational"
			elif state == ProtocolState.PRINTING:
				if self._job is None:
					return "Printing unknown job"
				if isinstance(self._job.job, SDFilePrintjob):
					return "Printing from SD"
				elif isinstance(self._job.job, LocalGcodeStreamjob):
					return "Sending file to SD"
				else:
					return "Printing"
			elif state == ProtocolState.PAUSED:
				return "Paused"
			elif state == ProtocolState.DISCONNECTED_WITH_ERROR:
				return "Error: {}".format(self._protocol.error)

		return "Unknown state ({})".format(self._protocol.state)

	def get_state_id(self, state=None):
		if self._comm is None:
			return "OFFLINE"
		else:
			if state is None:
				state = self._protocol.state

			if state == ProtocolState.DISCONNECTED:
				return "OFFLINE"
			elif state == ProtocolState.CONNECTING:
				return "CONNECTING"
			elif state == ProtocolState.CONNECTED:
				return "OPERATIONAL"
			elif state == ProtocolState.PRINTING:
				return "PRINTING"
			elif state == ProtocolState.PAUSED:
				return "PAUSED"
			elif state == ProtocolState.DISCONNECTED_WITH_ERROR:
				return "CLOSED_WITH_ERROR"

	def get_current_data(self):
		return self._state_monitor.get_current_data()

	def get_current_job(self):
		data = self._state_monitor.get_current_data()
		return data["job"]

	def get_current_temperatures(self):
		# TODO
		#if self._comm is not None:
		#	offsets = self._comm.getOffsets()
		#else:
		#	offsets = dict()
		offsets = dict()

		result = dict()
		for key, value in self._latest_temperatures.items():
			result[key] = dict(actual=value[0],
			                   target=value[1],
			                   offset=offsets.get(key, 0))
		return result

	def get_temperature_history(self):
		return self._temperature_history

	def get_current_connection(self):
		if self._transport is None:
			return "Closed", None, None, None

		port = None # TODO self._transport._serial.port
		baudrate = None # TODO self._transport._serial.baudrate
		printer_profile = self._printer_profile_manager.get_current_or_default()
		return self.get_state_string(), port, baudrate, printer_profile

	def is_connected(self):
		return self._protocol is not None and self._protocol.state in (ProtocolState.CONNECTED, ProtocolState.PRINTING, ProtocolState.PAUSED)

	def is_closed_or_error(self):
		return self._protocol is None or self._protocol.state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR)

	def is_operational(self):
		return not self.is_closed_or_error()

	def is_printing(self):
		return self._protocol is not None and self._protocol.state == ProtocolState.PRINTING

	def is_paused(self):
		return self._protocol is not None and self._protocol.state == ProtocolState.PAUSED

	def is_error(self):
		return self._protocol is not None and self._protocol.state == ProtocolState.DISCONNECTED_WITH_ERROR

	def is_ready(self):
		return self.is_operational() and not self._protocol.state in (ProtocolState.PRINTING, ProtocolState.PAUSED)

	def is_sd_ready(self):
		if not settings().getBoolean(["feature", "sdSupport"]) or self._protocol is None:
			return False
		else:
			return self._sd_ready

	#~~ sd file handling

	def get_sd_files(self):
		if not self.is_connected() or not self.is_sd_ready():
			return []
		return map(lambda x: (x[0][1:], x[1]), self._sd_files)

	def add_sd_file(self, filename, absolutePath, streamingFinishedCallback):
		# TODO

		#if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
		#	self._logger.error("No connection to printer or printer is busy")
		#	return

		#self._streamingFinishedCallback = streamingFinishedCallback

		#self.refresh_sd_files(blocking=True)
		#existingSdFiles = map(lambda x: x[0], self._comm.getSdFiles())

		#remoteName = util.get_dos_filename(filename, existing_filenames=existingSdFiles, extension="gco")
		#self._time_estimation_data = TimeEstimationHelper()
		#self._comm.startFileTransfer(absolutePath, filename, "/" + remoteName)

		#self._setJobData(filename, filesize, True)
		#self._setProgressData(0.0, 0, 0, None)
		#self._state_monitor.set_state({"text": self.get_state_string(), "flags": self._getStateFlags()})

		#return remoteName

		return "foo"

	def delete_sd_file(self, filename):
		if not self._protocol or not self.is_sd_ready():
			return
		self._protocol.delete_file("/" + filename)

	def init_sd_card(self):
		if not self._protocol or self.is_sd_ready():
			return
		self._protocol.init_file_storage()

	def release_sd_card(self):
		if not self._protocol or not self.is_sd_ready():
			return
		self._protocol.eject_file_storage()

	def refresh_sd_files(self, blocking=False):
		"""
		Refreshes the list of file stored on the SD card attached to printer (if available and printer communication
		available). Optional blocking parameter allows making the method block (max 10s) until the file list has been
		received. Defaults to an asynchronous operation.
		"""
		if self.is_connected() or not self.is_sd_ready():
			return
		self._sd_filelist_available.clear()
		self._protocol.list_files()
		if blocking:
			self._sd_filelist_available.wait(10000)

	#~~ state monitoring

	def _setCurrentZ(self, currentZ):
		self._current_z = currentZ
		self._state_monitor.set_current_z(self._current_z)

	def _set_state(self, state):
		self._state_monitor.set_state({"text": self.get_state_string(), "flags": self._get_state_flags()})

		payload = dict(
			state_id=self.get_state_id(state),
			state_string=self.get_state_string(state)
		)
		eventManager().fire(Events.PRINTER_STATE_CHANGED, payload)

	def _add_log(self, log):
		self._log.append(log)
		self._state_monitor.add_log(log)

	def _add_message(self, message):
		self._messages.append(message)
		self._state_monitor.add_message(message)

	def _estimate_total_for_job(self):
		if self._job is None or self._job.job is None or self._job.estimator is None or  self._job.job.estimate is None:
			return None

		self._job.estimator.update(self._job.job.estimate)

		result = None
		if self._job.estimator.is_stable():
			result = self._job.estimator.average_total_rolling

		return result

	def _reset_progress_data(self):
		self._state_monitor.set_progress(dict(completion=None,
		                                      filepos=0,
		                                      printTime=None,
		                                      printTimeLeft=None))

	def _set_completion_progress_data(self):
		self._progress = 1.0
		self._print_time = self._job.job.elapsed if self._job is not None else None
		self._print_time_left = 0

		pos = self._job.job.pos if self._job is not None else None

		self._state_monitor.set_progress(dict(completion=self._progress * 100 if self._progress is not None else None,
		                                      filepos=pos,
		                                      printTime=int(self._print_time) if self._print_time is not None else None,
		                                      printTimeLeft=int(self._print_time_left) if self._print_time_left is not None else None))

	def _update_progress_data(self):
		if self._job is None or not self._job.job.active:
			self._state_monitor.set_progress(dict(completion=None,
			                                      filepos=None,
			                                      printTime=None,
			                                      printTimeLeft=None))
			return

		estimated_total_print_time = self._estimate_total_for_job()
		total_print_time = estimated_total_print_time

		original_estimate = None
		if self._job.average_past_total:
			original_estimate = self._job.average_past_total
		elif self._job.analysis_total:
			original_estimate = self._job.analysis_total

		if original_estimate:
			if self._job.job.progress and self._job.job.elapsed:
				if estimated_total_print_time is None:
					total_print_time = original_estimate
				else:
					if self._job.job.progress < 0.5:
						sub_progress = self._job.job.progress * 2
					else:
						sub_progress = 1.0
					total_print_time = (1 - sub_progress) * original_estimate + sub_progress * estimated_total_print_time

		self._progress = self._job.job.progress
		self._print_time = self._job.job.elapsed
		self._print_time_left = total_print_time - self._job.job.elapsed if (total_print_time is not None and self._job.job.elapsed is not None) else None

		self._state_monitor.set_progress(dict(completion=self._progress * 100 if self._progress is not None else None,
		                                      filepos=self._job.job.pos,
		                                      printTime=int(self._print_time) if self._print_time is not None else None,
		                                      printTimeLeft=int(self._print_time_left) if self._print_time_left is not None else None))

		if self._job.job.progress:
			progress_int = int(self._job.job.progress * 100)
			if self._last_progress_report != progress_int:
				self._last_progress_report = progress_int
				self._report_print_progress_to_plugins(progress_int)


	def _add_temperature_data(self, temperatures):
		entry = dict(time=int(time.time()))
		entry.update(temperatures)
		self._temperature_history.append(entry)
		self._state_monitor.add_temperature(entry)

	def _update_job(self, job=None):
		if job is None and self._job is not None:
			job = self._job.job

		if job is None:
			job_data = dict(file=dict(name=None,
			                          origin=None,
			                          size=None,
			                          date=None),
			                estimatedPrintTime=None,
			                averagePrintTime=None,
			                lastPrintTime=None,
			                filament=None)
			self._state_monitor.set_job_data(job_data)
			self._job = None
			return

		rolling_window = None
		threshold = None
		countdown = None
		average_past_total = None
		analysis_total = None
		filament = None
		last_total = None
		date = None

		if isinstance(job, SDFilePrintjob):
			# we are interesting in a rolling window of roughly the last 15s, so the number of entries has to be derived
			# by that divided by the sd status polling interval
			rolling_window = 15 / job.status_interval

			# we are happy if the average of the estimates stays within 60s of the prior one
			threshold = 60

			# we are happy when one rolling window has been stable
			countdown = rolling_window

		elif isinstance(job, LocalGcodeFilePrintjob):
			# local file means we might have some information about the job stored in the file manager!
			try:
				file_data = self._file_manager.get_metadata(FileDestinations.LOCAL, job.path)
			except:
				pass
			else:
				if "analysis" in file_data:
					if "estimatedPrintTime" in file_data["analysis"]:
						analysis_total = file_data["analysis"]["estimatedPrintTime"]
					if "filament" in file_data["analysis"].keys():
						filament = file_data["analysis"]["filament"]

				if "statistics" in file_data:
					printer_profile = self._printer_profile_manager.get_current_or_default()["id"]
					if "averagePrintTime" in file_data["statistics"] and printer_profile in file_data["statistics"]["averagePrintTime"]:
						average_past_total = file_data["statistics"]["averagePrintTime"][printer_profile]
					if "lastPrintTime" in file_data["statistics"] and printer_profile in file_data["statistics"]["lastPrintTime"]:
						last_total = file_data["statistics"]["lastPrintTime"][printer_profile]

		# set the job data on the state monitor
		job_data = dict(file=dict(name=job.name,
		                          origin=self._get_origin_for_job(job),
		                          size=job.size,
		                          date=date),
		                estimatedPrintTime=analysis_total,
		                averagePrintTime=average_past_total,
		                lastPrintTime=last_total,
		                filament=filament)
		self._state_monitor.set_job_data(job_data)

		# set our internal job data
		estimation_helper = TimeEstimationHelper(rolling_window=rolling_window, threshold=threshold, countdown=countdown)
		self._job = JobData(job=job,
		                    average_past_total=average_past_total,
		                    analysis_total=analysis_total,
		                    estimator=estimation_helper)
		job.register_listener(self)

	def _send_initial_state_update(self, callback):
		try:
			data = self._state_monitor.get_current_data()
			data.update(dict(temps=list(self._temperature_history),
			                 logs=list(self._log),
			                 messages=list(self._messages)))
			callback.on_printer_send_initial_data(data)
		except Exception, err:
			import sys
			sys.stderr.write("ERROR: %s\n" % str(err))
			pass

	def _get_state_flags(self):
		return dict(operational=self.is_operational(),
		            printing=self.is_printing(),
		            closedOrError=self.is_closed_or_error(),
		            error=self.is_error(),
		            paused=self.is_paused(),
		            ready=self.is_ready(),
		            sdReady=self.is_sd_ready())

	def _get_origin_for_job(self, job=None):
		if job is None:
			if self._job is None:
				return None
			job = self._job.job

		return FileDestinations.SDCARD if isinstance(job, SDFilePrintjob) else FileDestinations.LOCAL

	#~~ octoprint.comm.protocol.ProtocolListener implementation

	def on_protocol_log(self, protocol, message):
		self._add_log(message)

	def on_protocol_state(self, protocol, old_state, new_state):
		self._logger.info("Protocol state changed from {} to {}".format(old_state, new_state))

		# forward relevant state changes to file manager
		if old_state == ProtocolState.PRINTING:
			if self._job is not None:
				if new_state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR):
					self._file_manager.log_print(self._get_origin_for_job(self._job.job),
					                             self._job.job.name,
					                             time.time(),
					                             self._job.job.elapsed,
					                             False,
					                             self._printer_profile_manager.get_current_or_default()["id"])
			self._analysis_queue.resume() # printing done, put those cpu cycles to good use

		elif new_state == ProtocolState.PRINTING:
			self._analysis_queue.pause() # do not analyse files while printing

		elif new_state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR) and old_state != ProtocolState.DISCONNECTING:
			self.disconnect()
			self._setCurrentZ(None)
			self._update_progress_data()
			self._update_job()
			self._printer_profile_manager.deselect()
			eventManager().fire(Events.DISCONNECTED)

		self._set_state(new_state)

	def on_protocol_temperature(self, protocol, temperatures):
		self._add_temperature_data(temperatures)

	#~~ octoprint.comm.protocol.FileAwareProtocolListener implementation

	def on_protocol_file_storage_available(self, protocol, available):
		self._sd_ready = available
		self._state_monitor.set_state({"text": self.get_state_string(), "flags": self._get_state_flags()})

	def on_protocol_file_list(self, protocol, files):
		self._sd_files = files
		eventManager().fire(Events.UPDATED_FILES, {"type": "gcode"})
		self._sd_filelist_available.set()

	#~~ octoprint.job.PrintjobListener

	def on_job_progress(self, job):
		self._update_progress_data()

	def on_job_done(self, job):
		if isinstance(self._job.job, LocalGcodeStreamjob):
			if self._streamingFinishedCallback is not None:
				# in case of SD files, both filename and absolutePath are the same, so we set the (remote) filename for
				# both parameters
				self._streamingFinishedCallback(self._job.job.name, self._job.job.name, FileDestinations.SDCARD)

			self._setCurrentZ(None)
			self._update_job()
			self._update_progress_data()
			self._state_monitor.set_state({"text": self.get_state_string(), "flags": self._get_state_flags()})
		else:
			self._file_manager.log_print(self._get_origin_for_job(),
			                             self._job.job.name,
			                             time.time(),
			                             self._job.job.elapsed,
			                             True,
			                             self._printer_profile_manager.get_current_or_default()["id"])
			self._set_completion_progress_data()
		self._state_monitor.set_state({"text": self.get_state_string(), "flags": self._get_state_flags()})

	#~~ comm.MachineComPrintCallback implementation

	def on_comm_z_change(self, newZ):
		# TODO
		pass

	def on_comm_force_disconnect(self):
		# TODO
		self.disconnect()

	def on_comm_record_fileposition(self, origin, name, pos):
		self._fileManager.save_recovery_data(origin, name, pos)

class StateMonitor(object):
	def __init__(self, interval=0.5, on_update=None, on_add_temperature=None, on_add_log=None, on_add_message=None):
		self._interval = interval
		self._update_callback = on_update
		self._on_add_temperature = on_add_temperature
		self._on_add_log = on_add_log
		self._on_add_message = on_add_message

		self._state = None
		self._job_data = None
		self._gcode_data = None
		self._sd_upload_data = None
		self._current_z = None
		self._progress = None

		self._offsets = {}

		self._change_event = threading.Event()
		self._state_lock = threading.Lock()

		self._last_update = time.time()
		self._worker = threading.Thread(target=self._work)
		self._worker.daemon = True
		self._worker.start()

	def reset(self, state=None, job_data=None, progress=None, current_z=None):
		self.set_state(state)
		self.set_job_data(job_data)
		self.set_progress(progress)
		self.set_current_z(current_z)

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

	def set_progress(self, progress):
		self._progress = progress
		self._change_event.set()

	def set_temp_offsets(self, offsets):
		self._offsets = offsets
		self._change_event.set()

	def _work(self):
		while True:
			self._change_event.wait()

			with self._state_lock:
				now = time.time()
				delta = now - self._last_update
				additional_wait_time = self._interval - delta
				if additional_wait_time > 0:
					time.sleep(additional_wait_time)

				data = self.get_current_data()
				self._update_callback(data)
				self._last_update = time.time()
				self._change_event.clear()

	def get_current_data(self):
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
