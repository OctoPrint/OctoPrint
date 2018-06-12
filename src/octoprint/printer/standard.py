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
import string
import threading
import time

# noinspection PyCompatibility
from past.builtins import basestring

from frozendict import frozendict

from octoprint import util as util
from octoprint.events import eventManager, Events
from octoprint.filemanager import FileDestinations, NoSuchStorage, valid_file_type
from octoprint.plugin import plugin_manager, ProgressPlugin
from octoprint.printer import PrinterInterface, PrinterCallback, UnknownScript, InvalidFileLocation, InvalidFileType
from octoprint.printer.estimation import PrintTimeEstimator
from octoprint.settings import settings
from octoprint.util import InvariantContainer
from octoprint.util import to_unicode

from octoprint.comm.protocol import ProtocolListener, FileAwareProtocolListener, PositionAwareProtocolListener, ProtocolState
from octoprint.comm.job import StoragePrintjob, LocalGcodeFilePrintjob, LocalGcodeStreamjob, SDFilePrintjob
from octoprint.comm.protocol.reprap.scripts import GcodeScript

from collections import namedtuple

JobData = namedtuple("JobData", ("job",
                                 "average_past_total",
                                 "analysis_total",
                                 "estimator"))

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


class Printer(PrinterInterface,
              ProtocolListener,
              FileAwareProtocolListener,
              PositionAwareProtocolListener):
	"""
	Default implementation of the :class:`PrinterInterface`. Manages the communication layer object and registers
	itself with it as a callback to react to changes on the communication layer.
	"""

	def __init__(self, fileManager, analysisQueue, printerProfileManager):
		from collections import deque

		self._logger = logging.getLogger(__name__)

		self._dict = frozendict if settings().getBoolean(["devel", "useFrozenDictForPrinterState"]) else dict

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

		# sd handling
		self._sdPrinting = False
		self._sdStreaming = False
		self._sd_filelist_available = threading.Event()
		self._streamingFinishedCallback = None
		self._streamingFailedCallback = None

		self._sd_ready = False
		self._sd_files = []

		# job handling & estimation
		self._estimator_factory = PrintTimeEstimator
		analysis_queue_hooks = plugin_manager().get_hooks("octoprint.printer.estimation.factory")
		for name, hook in analysis_queue_hooks.items():
			try:
				estimator = hook()
				if estimator is not None:
					self._logger.info("Using print time estimator provided by {}".format(name))
					self._estimator_factory = estimator
			except:
				self._logger.exception("Error while processing analysis queues from {}".format(name))
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
			on_add_message=self._send_add_message_callbacks,
			on_get_progress=self._update_progress_data_callback
		)
		self._state_monitor.reset(
			state=self._dict(text=self.get_state_string(), flags=self._get_state_flags()),
			job_data=self._dict(file=self._dict(name=None,
			                                    path=None,
			                                    size=None,
			                                    origin=None,
			                                    date=None),
			                    estimatedPrintTime=None,
			                    lastPrintTime=None,
			                    filament=self._dict(length=None,
			                                        volume=None),
			                    user=None),
			progress=self._dict(completion=None,
			                    filepos=None,
			                    printTime=None,
			                    printTimeLeft=None,
			                    printTimeOrigin=None),
			current_z=None,
			offsets=self._dict()
		)

		eventManager().subscribe(Events.METADATA_ANALYSIS_FINISHED, self._on_event_MetadataAnalysisFinished)
		eventManager().subscribe(Events.METADATA_STATISTICS_UPDATED, self._on_event_MetadataStatisticsUpdated)

	def _create_estimator(self, job_type):
		return self._estimator_factory(job_type)

	#~~ handling of PrinterCallbacks

	def register_callback(self, callback, *args, **kwargs):
		if not isinstance(callback, PrinterCallback):
			self._logger.warn("Registering an object as printer callback which doesn't implement the PrinterCallback interface")
		self._callbacks.append(callback)

	def unregister_callback(self, callback, *args, **kwargs):
		try:
			self._callbacks.remove(callback)
		except ValueError:
			# not registered
			pass

	def send_initial_callback(self, callback):
		if callback in self._callbacks:
			self._send_initial_state_update(callback)

	def send_add_temperature_callbacks(self, data):
		for callback in self._callbacks:
			try:
				callback.on_printer_add_temperature(data)
			except:
				self._logger.exception(u"Exception while adding temperature data point to callback {}".format(callback))

	def _send_add_log_callbacks(self, data):
		for callback in self._callbacks:
			try:
				callback.on_printer_add_log(data)
			except:
				self._logger.exception(u"Exception while adding communication log entry to callback {}".format(callback))

	def _send_add_message_callbacks(self, data):
		for callback in self._callbacks:
			try:
				callback.on_printer_add_message(data)
			except:
				self._logger.exception(u"Exception while adding printer message to callback {}".format(callback))

	def _send_current_data_callbacks(self, data):
		for callback in self._callbacks:
			try:
				callback.on_printer_send_current_data(copy.deepcopy(data))
			except:
				self._logger.exception(u"Exception while pushing current data to callback {}".format(callback))

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

	def connect(self, **kwargs):
		"""
		 Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
		 will be attempted.
		"""

		if self._protocol is not None or self._transport is not None:
			self.disconnect()

		eventManager().fire(Events.CONNECTING)

		profile = kwargs.get("profile")
		if not profile:
			profile = self._printer_profile_manager.get_default()["id"]
		self._printer_profile_manager.select(profile)
		if not logging.getLogger("SERIAL").isEnabledFor(logging.DEBUG):
			# if serial.log is not enabled, log a line to explain that to reduce "serial.log is empty" in tickets...
			logging.getLogger("SERIAL").info("serial.log is currently not enabled, you can enable it via Settings > Serial Connection > Log communication to serial.log")

		selected_transport = kwargs.get("transport")
		if not selected_transport:
			port = kwargs.get("port")
			baudrate = kwargs.get("baudrate")

			if not port:
				port = "AUTO"
			if not baudrate:
				baudrate = 0

			selected_transport = "serial"
			transport_kwargs = dict(serial_factory=_serial_factory)
			transport_connect_kwargs = dict(port=port, baudrate=baudrate)
		else:
			transport_kwargs = kwargs.get("transport_kwargs", dict())
			transport_connect_kwargs = kwargs.get("transport_connect_kwargs", dict())

		from octoprint.logging.handlers import CommunicationLogHandler
		CommunicationLogHandler.on_open_connection(u"TRANSPORT")
		CommunicationLogHandler.on_open_connection(u"PROTOCOL")
		CommunicationLogHandler.on_open_connection(u"COMMDEBUG")

		from octoprint.comm.transport import lookup_transport
		transport_class = lookup_transport(selected_transport)
		if not transport_class:
			raise ValueError("Invalid transport: {}".format(selected_transport))
		transport = transport_class(**transport_kwargs)

		# TODO make this depend on the printer profile
		from octoprint.comm.protocol.reprap import ReprapGcodeProtocol
		protocol = ReprapGcodeProtocol(plugin_manager=plugin_manager())
		protocol.register_listener(self)

		self._transport = transport
		self._protocol = protocol

		self._protocol.connect(self._transport, transport_kwargs=transport_connect_kwargs)

	def disconnect(self, *args, **kwargs):
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

		self.unselect_job()
		eventManager().fire(Events.DISCONNECTED)

	def get_transport(self, *args, **kwargs):
		if self._protocol is None:
			return None
		return self._protocol.transport
	getTransport = util.deprecated("getTransport has been renamed to get_transport", since="1.2.0-dev-590", includedoc="Replaced by :func:`get_transport`")

	def job_on_hold(self, blocking=True, *args, **kwargs):
		if self._protocol is None:
			raise RuntimeError("No connection to the printer")
		return self._protocol.job_put_on_hold(blocking=blocking)

	def set_job_on_hold(self, value, blocking=True, *args, **kwargs):
		if self._protocol is None:
			raise RuntimeError("No connection to the printer")
		return self._protocol.set_job_on_hold(value, blocking=blocking)

	def fake_ack(self, *args, **kwargs):
		if self._protocol is None:
			return

		self._protocol.repair()

	def commands(self, commands, *args, **kwargs):
		"""
		Sends one or more gcode commands to the printer.
		"""
		if self._protocol is None:
			return

		if not isinstance(commands, (list, tuple)):
			commands = [commands]

		self._protocol.send_commands(*commands, **kwargs)

	def script(self, name, context=None, must_be_set=True, *args, **kwargs):
		if self._protocol is None:
			return

		if name is None or not name:
			raise ValueError("name must be set")

		if context is None:
			context = dict()

		def render(context):
			lines = settings().loadScript("gcode", name, context=context)
			if lines is None and must_be_set:
				raise UnknownScript(name)
			return lines
		script = GcodeScript(name, render, context=context)
		self._protocol.send_script(script)

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

		if speed is None:
			printer_profile = self._printer_profile_manager.get_current_or_default()
			speed = max(*map(lambda x: printer_profile["axes"][x]["speed"], axes))

		kwargs = dict(feedrate=speed,
		              relative=relative)
		kwargs.update(axes)
		self._protocol.move(**kwargs)

	def home(self, axes, *args, **kwargs):
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

	def extrude(self, amount, *args, **kwargs):
		if not isinstance(amount, (int, long, float)):
			raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

		printer_profile = self._printer_profile_manager.get_current_or_default()
		extrusion_speed = printer_profile["axes"]["e"]["speed"]
		self._protocol.move(e=amount, feedrate=extrusion_speed, relative=True)

	def change_tool(self, tool, *args, **kwargs):
		if not PrinterInterface.valid_tool_regex.match(tool):
			raise ValueError("tool must match \"tool[0-9]+\": {tool}".format(tool=tool))

		tool_num = int(tool[len("tool"):])
		self._protocol.change_tool(tool_num, tags=kwargs.get("tags", set()) | {"trigger:printer.change_tool"})

	def set_temperature(self, heater, value, *args, **kwargs):
		if not PrinterInterface.valid_heater_regex.match(heater):
			raise ValueError("heater must match \"tool[0-9]+\" or \"bed\": {heater}".format(heater=heater))

		if not isinstance(value, (int, long, float)) or value < 0:
			raise ValueError("value must be a valid number >= 0: {value}".format(value=value))

		if heater.startswith("tool"):
			printer_profile = self._printer_profile_manager.get_current_or_default()
			extruder_count = printer_profile["extruder"]["count"]
			shared_nozzle = printer_profile["extruder"]["sharedNozzle"]
			if extruder_count > 1 and not shared_nozzle:
				toolNum = int(heater[len("tool"):])
				self._protocol.set_extruder_temperature(value, tool=toolNum, wait=False)
			else:
				self._protocol.set_extruder_temperature(value, wait=False)

		elif heater == "bed":
			self._protocol.set_bed_temperature(value, wait=False)

	def set_temperature_offset(self, offsets=None, *args, **kwargs):
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
		#self._setOffsets(self._comm.getOffsets())

	def _convert_rate_value(self, factor, min=0, max=200):
		if not isinstance(factor, (int, float, long)):
			raise ValueError("factor is not a number")

		if isinstance(factor, float):
			factor = int(factor * 100.0)

		if factor < min or factor > max:
			raise ValueError("factor must be a value between {} and {}".format(min, max))

		return factor

	def feed_rate(self, factor, *args, **kwargs):
		factor = self._convert_rate_value(factor, min=50, max=200)
		self._protocol.set_feedrate_multiplier(factor,
		                                       tags=kwargs.get("tags", set()) | {"trigger:printer.feed_rate"})

	def flow_rate(self, factor, *args, **kwargs):
		factor = self._convert_rate_value(factor, min=75, max=125)
		self._protocol.set_extrusion_multiplier(factor,
		                                        tags=kwargs.get("tags", set()) | {"trigger:printer.flow_rate"})

	def select_job(self, job, start_printing=False, pos=None, *args, **kwargs):
		self._update_job(job)
		self._reset_progress_data()

		event_payload = job.event_payload()
		if event_payload:
			eventManager().fire(Events.FILE_SELECTED, event_payload)

		if start_printing and self.is_ready():
			self.start_print(pos=pos,
			                 tags=kwargs.get("tags", set()))

	def unselect_job(self):
		self._remove_job()
		self._reset_progress_data()

		eventManager().fire(Events.FILE_DESELECTED)

	@util.deprecated("select_file has been deprecated, use select_job instead",
	                 includedoc="Replaced by :func:`select_job`",
	                 since="1.4.0")
	def select_file(self, path, sd, printAfterSelect=False, pos=None, user=None):
		if sd:
			storage = "sdcard"
		else:
			storage = "local"

		job = self._file_manager.create_print_job(storage, path, user=user)
		self.select_job(job, start_printing=printAfterSelect, pos=pos)

	unselect_file = util.deprecated("unselect_file has been deprecated, use unselect_job instead",
	                                includedoc="Replaced by :func:`unselect_job`",
	                                since="1.4.0")(unselect_job)

	def start_print(self, pos=None, user=None, *args, **kwargs):
		"""
		 Starts the currently loaded print job.
		 Only starts if the printer is connected and operational, not currently printing and a printjob is loaded
		"""
		if self._job is None or self._protocol is None or self._protocol.state not in (ProtocolState.CONNECTED,):
			return

		self._file_manager.delete_recovery_data()

		self._last_progress_report = None
		self._update_progress_data()
		self._set_current_z(None)

		self._protocol.process(self._job.job,
		                       position=pos,
		                       tags=kwargs.get("tags", set()) | {"trigger:printer.start_print"})

	def pause_print(self, *args, **kwargs):
		"""
		Pause the current job.
		"""
		if self._protocol is None:
			return
		if self._protocol.state != ProtocolState.PROCESSING:
			return
		self._protocol.pause_processing()

	def resume_print(self, *args, **kwargs):
		"""
		Resume the current job.
		"""
		if self._protocol is None:
			return
		if self._protocol.state != ProtocolState.PAUSED:
			return
		self._protocol.resume_processing()

	def cancel_print(self, error=False, tags=None, *args, **kwargs):
		"""
		 Cancel the current job.
		"""
		if self._protocol is None or not self._protocol.state in (ProtocolState.PROCESSING, ProtocolState.PAUSED):
			return

		# reset progress, height, print time
		self._set_current_z(None)
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

	def log_lines(self, *lines):
		serial_logger = logging.getLogger("SERIAL")
		self.on_comm_log("\n".join(lines))
		for line in lines:
			serial_logger.debug(line)

	def get_state_string(self, state=None, *args, **kwargs):
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
			elif state == ProtocolState.PROCESSING:
				if self._job is None:
					return "Printing unknown job"
				if isinstance(self._job.job, SDFilePrintjob):
					return "Printing from SD"
				elif isinstance(self._job.job, LocalGcodeStreamjob):
					return "Sending file to SD"
				else:
					return "Printing"
			elif state == ProtocolState.PAUSING:
				return "Pausing"
			elif state == ProtocolState.RESUMING:
				return "Resuming"
			elif state == ProtocolState.CANCELLING:
				return "Cancelling"
			elif state == ProtocolState.FINISHING:
				return "Finishing"
			elif state == ProtocolState.PAUSED:
				return "Paused"
			elif state == ProtocolState.DISCONNECTED_WITH_ERROR:
				return "Error: {}".format(self._protocol.error)

		return "Unknown state ({})".format(self._protocol.state)

	def get_state_id(self, state=None, *args, **kwargs):
		if state is None:
			if self._protocol is None:
				return "OFFLINE"
			state = self._protocol.state

		if state == ProtocolState.DISCONNECTED:
			return "OFFLINE"
		elif state == ProtocolState.CONNECTING:
			return "CONNECTING"
		elif state == ProtocolState.CONNECTED:
			return "OPERATIONAL"
		elif state == ProtocolState.PROCESSING:
			return "PRINTING"
		elif state == ProtocolState.PAUSING:
			return "PAUSING"
		elif state == ProtocolState.PAUSED:
			return "PAUSED"
		elif state == ProtocolState.RESUMING:
			return "RESUMING"
		elif state == ProtocolState.FINISHING:
			return "FINISHING"
		elif state == ProtocolState.DISCONNECTED_WITH_ERROR:
			return "CLOSED_WITH_ERROR"

	def get_current_data(self, *args, **kwargs):
		return util.thaw_frozendict(self._state_monitor.get_current_data())

	def get_current_job(self):
		data = self._state_monitor.get_current_data()
		return util.thaw_frozendict(data["job"])

	def get_current_temperatures(self, *args, **kwargs):
		# TODO temperature offsets
		#if self._comm is not None:
		#	offsets = self._comm.getOffsets()
		#else:
		#	offsets = dict()
		offsets = dict()

		result = dict()
		if not len(self._temperature_history):
			return result

		latest_temperature = self._temperature_history[-1]
		for key, value in latest_temperature.items():
			if not key.startswith("tool") and not key == "bed":
				continue

			result[key] = dict(actual=value["actual"],
			                   target=value["target"],
			                   offset=offsets.get(key, 0))
		return result

	def get_temperature_history(self, *args, **kwargs):
		return self._temperature_history

	def get_current_connection(self, *args, **kwargs):
		if self._transport is None:
			return "Closed", None, None, None

		port = None # TODO self._transport._serial.port
		baudrate = None # TODO self._transport._serial.baudrate
		printer_profile = self._printer_profile_manager.get_current_or_default()
		return self.get_state_string(), port, baudrate, printer_profile

	def is_connected(self):
		return self._protocol is not None and self._protocol.state in (ProtocolState.CONNECTED, ProtocolState.PROCESSING, ProtocolState.PAUSED)

	def is_closed_or_error(self, *args, **kwargs):
		return self._protocol is None or self._protocol.state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR)

	def is_operational(self, *args, **kwargs):
		return not self.is_closed_or_error()

	def is_printing(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.PROCESSING

	def is_cancelling(self, *args, **kwargs):
		return self._comm is not None and self._comm.isCancelling()

	def is_pausing(self, *args, **kwargs):
		return self._comm is not None and self._comm.isPausing()

	def is_paused(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.PAUSED

	def is_resuming(self, *args, **kwargs):
		return self._comm is not None and self._comm.isResuming()

	def is_finishing(self, *args, **kwargs):
		return self._comm is not None and self._comm.isFinishing()

	def is_error(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.DISCONNECTED_WITH_ERROR

	def is_ready(self, *args, **kwargs):
		return self.is_operational() and not self._protocol.state in ProtocolState.PROCESSING_STATES

	def is_sd_ready(self, *args, **kwargs):
		if not settings().getBoolean(["feature", "sdSupport"]) or self._protocol is None:
			return False
		else:
			return self._sd_ready

	#~~ sd file handling

	def get_sd_files(self, *args, **kwargs):
		if not self.is_connected() or not self.is_sd_ready():
			return []
		return map(lambda x: (x[0][1:], x[1]), self._sd_files)

	def add_sd_file(self, filename, absolutePath, on_success=None, on_failure=None, *args, **kwargs):
		# TODO

		# if not self._comm or self._comm.isBusy() or not self._comm.isSdReady():
		# 	self._logger.error("No connection to printer or printer is busy")
		# 	return

		# self._streamingFinishedCallback = on_success
		# self._streamingFailedCallback = on_failure

		# self.refresh_sd_files(blocking=True)
		# existingSdFiles = map(lambda x: x[0], self._comm.getSdFiles())

		# if valid_file_type(filename, "gcode"):
		# 	remoteName = util.get_dos_filename(filename,
		# 	                                   existing_filenames=existingSdFiles,
		# 	                                   extension="gco",
		# 	                                   whitelisted_extensions=["gco", "g"])
		# else:
		# 	# probably something else added through a plugin, use it's basename as-is
		# 	remoteName = os.path.basename(filename)
		# self._create_estimator("stream")
		# self._comm.startFileTransfer(absolutePath, filename, "/" + remoteName,
		#                              special=not valid_file_type(filename, "gcode"),
		#                              tags=kwargs.get("tags", set()) | {"trigger:printer.add_sd_file"})

		# return remoteName

		return "foo"

	def delete_sd_file(self, filename, *args, **kwargs):
		if not self._protocol or not self.is_sd_ready():
			return
		self._protocol.delete_file("/" + filename, tags=kwargs.get("tags", set()) | {"trigger:printer.delete_sd_file"})

	def init_sd_card(self, *args, **kwargs):
		if not self._protocol or self.is_sd_ready():
			return
		self._protocol.init_file_storage(tags=kwargs.get("tags", set()) | {"trigger:printer.init_sd_card"})

	def release_sd_card(self, *args, **kwargs):
		if not self._protocol or not self.is_sd_ready():
			return
		self._protocol.eject_file_storage(tags=kwargs.get("tags", set()) | {"trigger:printer.release_sd_card"})

	def refresh_sd_files(self, blocking=False, *args, **kwargs):
		"""
		Refreshes the list of file stored on the SD card attached to printer (if available and printer communication
		available). Optional blocking parameter allows making the method block (max 10s) until the file list has been
		received. Defaults to an asynchronous operation.
		"""
		if self.is_connected() or not self.is_sd_ready():
			return
		self._sd_filelist_available.clear()
		self._protocol.list_files(tags=kwargs.get("tags", set()) | {"trigger:printer.refresh_sd_files"})
		if blocking:
			self._sd_filelist_available.wait(kwargs.get("timeout", 10000))

	#~~ state monitoring

	def _set_offsets(self, offsets):
		self._state_monitor.set_temp_offsets(offsets)

	def _set_current_z(self, currentZ):
		self._current_z = currentZ
		self._state_monitor.set_current_z(self._current_z)

	def _set_state(self, state, state_string=None):
		if state_string is None:
			state_string = self.get_state_string()

		self._state = state

		self._state_monitor.set_state(self._dict(text=state_string,
		                                         flags=self._get_state_flags()))

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
		if self._job is None or self._job.job is None or self._job.estimator is None:
			return None

		return self._job.estimator.estimate_total()

	def _reset_progress_data(self):
		self._state_monitor.set_progress(dict(completion=None,
		                                      filepos=0,
		                                      printTime=None,
		                                      printTimeLeft=None))

	def _set_completion_progress_data(self):
		progress = 1.0
		pos = self._job.job.size if self._job is not None else None
		print_time = int(self._job.job.elapsed) if self._job is not None else None
		print_time_left = 0

		self._update_progress_data(completion=progress,
		                           filepos=pos,
		                           print_time=print_time,
		                           print_time_left=print_time_left)

	def _update_progress_data(self, completion=None, filepos=None, print_time=None, print_time_left=None, print_time_left_origin=None):
		self._state_monitor.set_progress(self._dict(completion=completion,
		                                            filepos=filepos,
		                                            printTime=print_time,
		                                            printTimeLeft=print_time_left,
		                                            printTimeLeftOrigin=print_time_left_origin))

	def _update_progress_data_callback(self):
		if self._job is None or self._job.job is None:
			progress = None
			print_time = None
			cleaned_print_time = None
			pos = None
		else:
			progress = self._job.job.progress
			print_time = self._job.job.elapsed
			cleaned_print_time = self._job.job.clean_elapsed
			pos = self._job.job.pos

		print_time_left = print_time_left_origin = None

		if progress is not None:
			progress_int = int(self._job.job.progress * 100)
			if self._last_progress_report != progress_int:
				self._last_progress_report = progress_int
				self._report_print_progress_to_plugins(progress_int)

			if progress == 0:
				print_time_left = None
				print_time_left_origin = None
			elif progress == 1.0:
				print_time_left = 0
				print_time_left_origin = None
			else:
				original_estimate = None
				original_estimate_type = None

				if self._job.average_past_total is not None:
					original_estimate = self._job.average_past_total
					original_estimate_type = "average"
				elif self._job.analysis_total is not None:
					original_estimate = self._job.analysis_total
					original_estimate_type = "analysis"

				print_time_left, print_time_left_origin = self._job.estimator.estimate(progress,
				                                                                       print_time,
				                                                                       cleaned_print_time,
				                                                                       original_estimate,
				                                                                       original_estimate_type)

		return self._dict(completion=progress * 100 if progress is not None else None,
		                  filepos=pos,
		                  printTime=int(print_time) if print_time is not None else None,
		                  printTimeLeft=int(print_time_left) if print_time_left is not None else None,
		                  printTimeLeftOrigin=print_time_left_origin)

	def _add_temperature_data(self, temperatures):
		if temperatures is None:
			temperatures = dict()

		entry = dict(time=int(time.time()))
		for tool in temperatures:
			entry[tool] = dict(actual=temperatures[tool]["actual"],
			                   target=temperatures[tool]["target"])

		self._temperature_history.append(entry)
		self._state_monitor.add_temperature(entry)

	def _remove_job(self):
		job_data = self._dict(file=self._dict(name=None,
		                                      path=None,
		                                      display=None,
		                                      origin=None,
		                                      size=None,
		                                      date=None),
		                      estimatedPrintTime=None,
		                      averagePrintTime=None,
		                      lastPrintTime=None,
		                      filament=None,
		                      user=None)
		self._state_monitor.set_job_data(job_data)
		self._job = None

	def _update_job(self, job=None):
		if job is None and self._job is not None:
			job = self._job.job

		if job is None:
			# TODO fix this, this won't work for deselecting jobs
			self._remove_job()
			return

		average_past_total = None
		analysis_total = None
		filament = None
		last_total = None
		date = None

		display_name = job.name

		if isinstance(job, LocalGcodeFilePrintjob):
			# local file means we might have some information about the job stored in the file manager!
			try:
				file_data = self._file_manager.get_metadata(FileDestinations.LOCAL, job.path)
			except:
				pass
			else:
				if "display" in file_data:
					display_name = file_data["display"]

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
		job_data = self._dict(file=self._dict(name=job.name,
		                                      path=job.path_in_storage,
		                                      display=display_name,
		                                      origin=self._get_origin_for_job(job),
		                                      size=job.size,
		                                      date=date),
		                      estimatedPrintTime=analysis_total,
		                      averagePrintTime=average_past_total,
		                      lastPrintTime=last_total,
		                      filament=filament,
		                      user=job.user)
		self._state_monitor.set_job_data(job_data)

		# set our internal job data

		# TODO other way to determine job type?
		if isinstance(job, SDFilePrintjob):
			job_type = "sdcard"
		elif isinstance(job, LocalGcodeStreamjob):
			job_type = "stream"
		else:
			job_type = "local"

		self._job = JobData(job=job,
		                    average_past_total=average_past_total,
		                    analysis_total=analysis_total,
		                    estimator=self._create_estimator(job_type))
		job.register_listener(self)

	def _send_initial_state_update(self, callback):
		try:
			data = self._state_monitor.get_current_data()
			data.update(dict(temps=list(self._temperature_history),
			                 logs=list(self._log),
			                 messages=list(self._messages)))
			callback.on_printer_send_initial_data(data)
		except:
			self._logger.exception("Error while trying to send initial state update")

	def _get_state_flags(self):
		return self._dict(operational=self.is_operational(),
		                  printing=self.is_printing(),
		                  cancelling=self.is_cancelling(),
		                  pausing=self.is_pausing(),
		                  resuming=self.is_resuming(),
		                  finishing=self.is_finishing(),
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

		if not isinstance(job, StoragePrintjob):
			return None

		return job.storage

	#~~ octoprint.comm.protocol.ProtocolListener implementation

	def on_protocol_log(self, protocol, message, *args, **kwargs):
		if protocol != self._protocol:
			return

		self._add_log(message)

	def on_protocol_state(self, protocol, old_state, new_state, *args, **kwargs):
		if protocol != self._protocol:
			return

		self._logger.info("Protocol state changed from {} to {}".format(old_state, new_state))

		# forward relevant state changes to file manager
		if old_state == ProtocolState.PROCESSING:
			if self._job is not None:
				if new_state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR):
					self._file_manager.log_print(self._get_origin_for_job(self._job.job),
					                             self._job.job.name,
					                             time.time(),
					                             self._job.job.elapsed,
					                             False,
					                             self._printer_profile_manager.get_current_or_default()["id"])
			self._analysis_queue.resume() # printing done, put those cpu cycles to good use

		elif new_state == ProtocolState.PROCESSING:
			self._analysis_queue.pause() # do not analyse files while printing

		elif new_state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR) and old_state != ProtocolState.DISCONNECTING:
			self.disconnect()
			self._set_current_z(None)
			self._update_progress_data()
			self._set_offsets(None)
			self._addTemperatureData()
			self._update_job()
			self._printer_profile_manager.deselect()
			eventManager().fire(Events.DISCONNECTED)

		self._set_state(new_state)

	def on_protocol_temperature(self, protocol, temperatures, *args, **kwargs):
		if protocol != self._protocol:
			return

		self._add_temperature_data(temperatures)

	def on_protocol_reset(self, protocol, idle, *args, **kwargs):
		if protocol != self._protocol:
			return

		eventManager().fire(Events.PRINTER_RESET, payload=dict(idle=idle))

	#~~ octoprint.comm.protocol.FileAwareProtocolListener implementation

	def on_protocol_file_storage_available(self, protocol, available, *args, **kwargs):
		if protocol != self._protocol:
			return

		self._sd_ready = available
		self._state_monitor.set_state({"text": self.get_state_string(), "flags": self._get_state_flags()})

	def on_protocol_file_list(self, protocol, files, *args, **kwargs):
		if protocol != self._protocol:
			return

		self._sd_files = files
		eventManager().fire(Events.UPDATED_FILES, {"type": "gcode"})
		self._sd_filelist_available.set()

	#~~ octoprint.comm.protocol.PositionAwareProtocolListener implementation

	def on_protocol_position_z_update(self, protocol, z, *args, **kwargs):
		if protocol != self._protocol:
			return

		old_z = self._current_z
		if z != old_z:
			eventManager().fire(Events.Z_CHANGE, dict(new=z, old=old_z))

		self._set_current_z(z)

	def on_protocol_position_all_update(self, protocol, position, *args, **kwargs):
		payload = dict(reason=kwargs.get("reason", None))
		payload.update(position)
		eventManager().fire(Events.POSITION_UPDATE, payload)

	#~~ octoprint.comm.protocol.JobAwareProtocolListener implementation

	def on_protocol_job_processing(self, protocol, job, suppress_script=False):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		payload = job.event_payload()
		if payload:
			eventManager().fire(Events.PRINT_STARTED, payload)
			if not suppress_script:
				self.script("beforePrintStarted",
				            context=dict(event=payload),
				            must_be_set=False)

	def on_protocol_job_finishing(self, protocol, job, suppress_script=False, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if isinstance(self._job.job, LocalGcodeStreamjob):
			# streaming job

			if self._streamingFinishedCallback is not None:
				# in case of SD files, both filename and absolutePath are the same, so we set the (remote) filename for
				# both parameters
				self._streamingFinishedCallback(self._job.job.name, self._job.job.name, FileDestinations.SDCARD)

			self._set_current_z(None)
			self._update_job()
			self._update_progress_data()

		else:
			# all other job types

			payload = job.event_payload()
			if payload:
				payload["time"] = job.elapsed
				self._update_progress_data(completion=100,
				                           filepos=payload["size"],
				                           print_time=payload["time"],
				                           print_time_left=0)
				self._state_monitor.set_state(self._dict(text=self.get_state_string(),
				                                         flags=self._get_state_flags()))

				eventManager().fire(Events.PRINT_DONE, payload)
				if not suppress_script:
					self.script("afterPrintDone",
					            context=dict(event=payload),
					            must_be_set=False)

				def log_print():
					self._file_manager.log_print(payload["origin"],
					                             payload["path"],
					                             time.time(),
					                             payload["time"],
					                             True,
					                             self._printer_profile_manager.get_current_or_default()["id"])

				thread = threading.Thread(target=log_print)
				thread.daemon = True
				thread.start()


	def on_protocol_job_failed(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		payload = job.event_payload()
		if payload:
			eventManager().fire(Events.PRINT_FAILED, payload)

	def on_protocol_job_cancelling(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		firmware_error = kwargs.get("error", None)
		cancel_position = kwargs.get("position", None)
		suppress_scripts = kwargs.get("suppress_scripts", None)

		payload = job.event_payload()
		if payload:
			if firmware_error:
				payload["firmwareError"] = firmware_error
			if cancel_position:
				payload["position"] = cancel_position
			eventManager().fire(Events.PRINT_CANCELLING, payload)

			if not suppress_scripts:
				self.script("afterPrintCancelled",
				            context=dict(event=payload),
				            must_be_set=False)

	def on_protocol_job_cancelled(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		self._update_progress_data()

		cancel_position = kwargs.get("position", None)

		payload = job.event_payload()
		if payload:
			payload["time"] = job.elapsed
			if cancel_position:
				payload["position"] = cancel_position

			eventManager().fire(Events.PRINT_CANCELLED, payload)

			def finalize():
				self._file_manager.log_print(job.storage,
			                                 job.name,
			                                 time.time(),
			                                 payload["time"],
			                                 False,
			                                 self._printer_profile_manager.get_current_or_default()["id"])
				eventManager().fire(Events.PRINT_FAILED, payload)

			thread = threading.Thread(target=finalize)
			thread.daemon = True
			thread.start()

	def on_protocol_job_pausing(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		pause_position = kwargs.get("position", None)
		suppress_scripts = kwargs.get("suppress_scripts", None)

		payload = job.event_payload()
		if payload:
			if pause_position:
				payload["position"] = pause_position
			#eventManager().fire(Events.PRINT_PAUSED, payload)
			if not suppress_scripts:
				self.script("afterPrintPaused",
				            context=dict(event=payload),
				            must_be_set=False)

	def on_protocol_job_paused(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		pause_position = kwargs.get("position", None)

		payload = job.event_payload()
		if payload:
			if pause_position:
				payload["position"] = pause_position
			eventManager().fire(Events.PRINT_PAUSED, payload)

	def on_protocol_job_resuming(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		suppress_scripts = kwargs.get("suppress_scripts", False)

		payload = job.event_payload()
		if payload and not suppress_scripts:
			self.script("beforePrintResumed",
			            context=dict(event=payload),
			            must_be_set=False)

	def on_protocol_job_resumed(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		payload = job.event_payload()
		if payload:
			eventManager().fire(Events.PRINT_RESUMED, payload)

	# ~~ octoprint.comm.job.PrintjobListener implementation

	def on_job_progress(self, job):
		if self._job is None or job != self._job.job:
			return

		self._state_monitor.trigger_progress_update()

	#~~ comm.MachineComPrintCallback implementation

	def on_comm_force_disconnect(self):
		# TODO
		self.disconnect()

	def on_comm_record_fileposition(self, origin, name, pos):
		# TODO
		try:
			self._file_manager.save_recovery_data(origin, name, pos)
		except NoSuchStorage:
			pass
		except:
			self._logger.exception("Error while trying to persist print recovery data")

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

		return dict(state=self._state,
		            job=self._job_data,
		            currentZ=self._current_z,
		            progress=self._progress,
		            offsets=self._offsets)


class TemperatureHistory(InvariantContainer):
	def __init__(self, cutoff=30 * 60):

		def temperature_invariant(data):
			data.sort(key=lambda x: x["time"])
			now = int(time.time())
			return [item for item in data if item["time"] >= now - cutoff]

		InvariantContainer.__init__(self, guarantee_invariant=temperature_invariant)
