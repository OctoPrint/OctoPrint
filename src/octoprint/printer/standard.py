# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

"""
This module holds the standard implementation of the :class:`PrinterInterface` and it helpers.
"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import copy
import logging
import os
import string
import threading
import time
import re

# noinspection PyCompatibility
from past.builtins import basestring, long

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
from octoprint.util import monotonic_time
from octoprint.util import dict_merge

from octoprint.comm.protocol import ProtocolListener, FileAwareProtocolListener, PositionAwareProtocolListener, ProtocolState
from octoprint.comm.job import StoragePrintjob, LocalGcodeFilePrintjob, LocalGcodeStreamjob, SDFilePrintjob, CopyJobMixin
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
		except Exception:
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

	def __init__(self, fileManager, analysisQueue, connectionProfileManager, printerProfileManager):
		from collections import deque

		self._logger = logging.getLogger(__name__)
		self._logger_job = logging.getLogger("{}.job".format(__name__))

		self._dict = frozendict if settings().getBoolean(["devel", "useFrozenDictForPrinterState"]) else dict

		self._analysis_queue = analysisQueue
		self._file_manager = fileManager
		self._connection_profile_manager = connectionProfileManager
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
		self._sd_printing = False
		self._sd_streaming = False
		self._sd_filelist_available = threading.Event()
		self._on_streaming_done = None
		self._on_streaming_failed = None

		self._sd_ready = False
		self._sd_files = []

		# feedback controls
		self._feedback_controls = None
		self._feedback_matcher = None
		self._feedback_errors = []

		# job handling & estimation
		self._estimator_factory = PrintTimeEstimator
		analysis_queue_hooks = plugin_manager().get_hooks("octoprint.printer.estimation.factory")
		for name, hook in analysis_queue_hooks.items():
			try:
				estimator = hook()
				if estimator is not None:
					self._logger.info("Using print time estimator provided by {}".format(name))
					self._estimator_factory = estimator
			except Exception:
				self._logger.exception("Error while processing analysis queues from {}".format(name),
				                       extra=dict(plugin=name))

		#hook card upload
		self.sd_card_upload_hooks = plugin_manager().get_hooks("octoprint.printer.sdcardupload")

		# comm
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

	#~~ handling of PrinterCallbacks

	def register_callback(self, callback, *args, **kwargs):
		if not isinstance(callback, PrinterCallback):
			self._logger.warning("Registering an object as printer callback which doesn't implement the PrinterCallback interface")
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
			except Exception:
				self._logger.exception("Exception while adding temperature data point to callback {}".format(callback))

	def _send_add_log_callbacks(self, data):
		for callback in self._callbacks:
			try:
				callback.on_printer_add_log(data)
			except Exception:
				self._logger.exception("Exception while adding communication log entry to callback {}".format(callback))

	def _send_add_message_callbacks(self, data):
		for callback in self._callbacks:
			try:
				callback.on_printer_add_message(data)
			except Exception:
				self._logger.exception("Exception while adding printer message to callback {}".format(callback))

	def _send_current_data_callbacks(self, data):
		for callback in self._callbacks:
			try:
				callback.on_printer_send_current_data(copy.deepcopy(data))
			except Exception:
				self._logger.exception("Exception while pushing current data to callback {}".format(callback))

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
				except Exception:
					self._logger.exception("Exception while sending print progress to plugin %s" % plugin._identifier,
					                       extra=dict(plugin=plugin._identifier))

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

		## prepare feedback controls
		self._feedback_controls, self._feedback_matcher = convert_feedback_controls(settings().get(["controls"]))

		eventManager().fire(Events.CONNECTING)

		##~~ Logging

		from octoprint.logging.handlers import CommunicationLogHandler
		CommunicationLogHandler.on_open_connection(u"CONNECTION")
		CommunicationLogHandler.on_open_connection(u"COMMDEBUG")

		if not logging.getLogger("CONNECTION").isEnabledFor(logging.DEBUG):
			# is protocol.log is not enabled, log a line to explain to reduce "connection.log is empty" in tickets...
			logging.getLogger("CONNECTION").info("connection.log is currently not enabled, you can enable it via Settings > Connection > Log communication to connection.log")

		connection_id = kwargs.get("connection")
		connection = None
		if connection_id is not None:
			connection = self._connection_profile_manager.get(connection_id)

		if connection is not None:
			# we have a connection profile
			self._connection_profile_manager.select(connection.id)

			##~~ Printer profile
			profile_id = kwargs.get("profile", connection.printer_profile)
			self._printer_profile_manager.select(profile_id)
			profile = self._printer_profile_manager.get_current_or_default()

			##~~ Transport

			selected_transport = kwargs.get("transport", connection.transport)
			transport_connect_kwargs = connection.transport_parameters
			transport_connect_kwargs = dict_merge(transport_connect_kwargs, kwargs.get("transport_options", dict()))

			transport_kwargs = dict()
			transport_kwargs.update(dict(settings=settings(),
			                             plugin_manager=plugin_manager(),
			                             event_bus=eventManager(),
			                             printer_profile=profile))

			##~~ Protocol

			selected_protocol = kwargs.get("protocol", connection.protocol)
			protocol_kwargs = dict_merge(connection.protocol_parameters, kwargs.get("protocol_options", dict()))
			protocol_kwargs.update(dict(settings=settings(),
			                            plugin_manager=plugin_manager(),
			                            event_bus=eventManager(),
			                            printer_profile=profile))

		else:
			self._connection_profile_manager.deselect()

			##~~ Printer profile

			profile_id = kwargs.get("profile")
			if not profile_id:
				profile_id = self._printer_profile_manager.get_default()["id"]

			self._printer_profile_manager.select(profile_id)
			profile = self._printer_profile_manager.get_current_or_default()

			##~~ Transport

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
				transport_connect_kwargs = kwargs.get("transport_options", dict())

			transport_kwargs.update(dict(settings=settings(),
			                             plugin_manager=plugin_manager(),
			                             event_bus=eventManager(),
			                             printer_profile=profile))

			##~~ Protocol

			# TODO make this depend on the printer profile
			selected_protocol = kwargs.get("protocol")
			if not selected_protocol:
				selected_protocol = "reprap"
				protocol_kwargs = dict()
			else:
				protocol_kwargs = kwargs.get("protocol_options", dict())

			protocol_kwargs.update(dict(settings=settings(),
			                            plugin_manager=plugin_manager(),
			                            event_bus=eventManager(),
			                            printer_profile=profile))

		##~~ Lookup and create transport instances

		from octoprint.comm.transport import lookup_transport
		transport_class = lookup_transport(selected_transport)
		if not transport_class:
			raise ValueError("Invalid transport: {}".format(selected_transport))

		transport = transport_class(**transport_kwargs)
		self._transport = transport

		##~~ Lookup and create protocol instance

		from octoprint.comm.protocol import lookup_protocol
		protocol_class = lookup_protocol(selected_protocol)
		if not protocol_class:
			raise ValueError("Invalid protocol: {}".format(selected_protocol))

		protocol = protocol_class(**protocol_kwargs)
		self._protocol = protocol

		##~~ Register everything and connect

		self._protocol.register_listener(self)
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

	def script(self, name, context=None, must_be_set=True, part_of_job=False, *args, **kwargs):
		if self._protocol is None:
			return

		if name is None or not name:
			raise ValueError("name must be set")

		if context is None:
			context = dict()

		try:
			self._protocol.send_script(name,
			                           part_of_job=part_of_job,
			                           context=context,
			                           tags=kwargs.get("tags", set()) | {"trigger:printer.script"})
		except UnknownScript:
			if must_be_set:
				raise

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
		              relative=relative,
		              tags=kwargs.get("tags", set()) | {"trigger:printer.jog"})
		kwargs.update(axes)
		self._protocol.move(**kwargs)

	def home(self, axes, *args, **kwargs):
		if not isinstance(axes, (list, tuple)):
			if isinstance(axes, basestring):
				axes = [axes]
			else:
				raise ValueError("axes is neither a list nor a string: {axes}".format(axes=axes))

		validated_axes = list(filter(lambda x: x in PrinterInterface.valid_axes, map(lambda x: x.lower(), axes)))
		if len(axes) != len(validated_axes):
			raise ValueError("axes contains invalid axes: {axes}".format(axes=axes))

		kwargs = dict((axes, True) for axes in validated_axes)
		self._protocol.home(**kwargs)

	def extrude(self, amount, speed=None, *args, **kwargs):
		if not isinstance(amount, (int, long, float)):
			raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

		printer_profile = self._printer_profile_manager.get_current_or_default()

		# Use specified speed (if any)
		max_e_speed = printer_profile["axes"]["e"]["speed"]

		if speed is None:
			# No speed was specified so default to value configured in printer profile
			extrusion_speed = max_e_speed
		else:
			# Make sure that specified value is not greater than maximum as defined in printer profile
			extrusion_speed = min([speed, max_e_speed])

		self._protocol.move(e=amount,
		                    feedrate=extrusion_speed,
		                    relative=True,
		                    tags=kwargs.get("tags", set()) | {"trigger:printer.extrude"})

	def change_tool(self, tool, *args, **kwargs):
		if not PrinterInterface.valid_tool_regex.match(tool):
			raise ValueError("tool must match \"tool[0-9]+\": {tool}".format(tool=tool))

		tool_num = int(tool[len("tool"):])
		self._protocol.change_tool(tool_num, tags=kwargs.get("tags", set()) | {"trigger:printer.change_tool"})

	def set_temperature(self, heater, value, *args, **kwargs):
		if not PrinterInterface.valid_heater_regex.match(heater):
			raise ValueError("heater must match \"tool[0-9]+\", \"bed\" or \"chamber\": {heater}".format(heater=heater))

		if not isinstance(value, (int, long, float)) or value < 0:
			raise ValueError("value must be a valid number >= 0: {value}".format(value=value))

		tags = kwargs.get("tags", set()) | {"trigger:printer.set_temperature"}
		self._protocol.set_temperature(heater, value, wait=False, tags=tags)

	def set_temperature_offset(self, offsets=None, *args, **kwargs):
		if offsets is None:
			offsets = dict()

		if not isinstance(offsets, dict):
			raise ValueError("offsets must be a dict")

		validated_keys = list(filter(lambda x: PrinterInterface.valid_heater_regex.match(x), offsets.keys()))
		validated_values = list(filter(lambda x: isinstance(x, (int, long, float)), offsets.values()))

		if len(validated_keys) != len(offsets):
			raise ValueError("offsets contains invalid keys: {offsets}".format(offsets=offsets))
		if len(validated_values) != len(offsets):
			raise ValueError("offsets contains invalid values: {offsets}".format(offsets=offsets))

		if self._protocol is None:
			return

		for heater, offset in offsets.items():
			self._protocol.set_temperature_offset(heater, offset)
		self._set_offsets(self._protocol.get_temperature_offsets())

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

		payload = job.event_payload()
		if payload:
			eventManager().fire(Events.FILE_SELECTED, payload)

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
	def select_file(self, path, sd, printAfterSelect=False, pos=None, user=None, **kwargs):
		if sd:
			storage = "sdcard"
		else:
			storage = "local"

		job = self._file_manager.create_print_job(storage, path, user=user)
		self.select_job(job, start_printing=printAfterSelect, pos=pos, **kwargs)

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
		                       position=0 if pos is None else pos,
		                       user=user,
		                       tags=kwargs.get("tags", set()) | {"trigger:printer.start_print"})

	def pause_print(self, user=None, *args, **kwargs):
		"""
		Pause the current job.
		"""
		if self._protocol is None:
			return
		if self._protocol.state != ProtocolState.PROCESSING:
			return
		self._protocol.pause_processing(user=user,
		                                tags=kwargs.get("tags", set()) | {"trigger:printer.pause_print"})

	def resume_print(self, user=None, *args, **kwargs):
		"""
		Resume the current job.
		"""
		if self._protocol is None:
			return
		if self._protocol.state != ProtocolState.PAUSED:
			return
		self._protocol.resume_processing(user=user,
		                                 tags=kwargs.get("tags", set()) | {"trigger:printer.resume_print"})

	def cancel_print(self, error=False, user=None, tags=None, *args, **kwargs):
		"""
		 Cancel the current job.
		"""
		if self._protocol is None or not self._protocol.state in (ProtocolState.PROCESSING, ProtocolState.PAUSED):
			return

		self._protocol.cancel_processing(error=error,
		                                 user=user,
		                                 tags=kwargs.get("tags", set()) | {"trigger:printer.cancel_print"})

	def log_lines(self, *lines):
		serial_logger = logging.getLogger("SERIAL")
		for line in lines:
			self.on_protocol_log(self._protocol, line)
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
			elif state in (ProtocolState.DISCONNECTING, ProtocolState.DISCONNECTING_WITH_ERROR):
				return "Disconnecting"
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
		if self._protocol is not None:
			offsets = self._protocol.get_temperature_offsets()
		else:
			offsets = dict()

		result = dict()
		if not len(self._temperature_history):
			return result

		latest_temperature = self._temperature_history[-1]
		for key, value in latest_temperature.items():
			if key == "time":
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

	def get_current_connection_parameters(self, *args, **kwargs):
		if self._transport is None or self._protocol is None:
			return dict(state="Closed",
			            connection=None,
			            protocol=None,
			            protocol_args=dict(),
			            transport=None,
			            transport_args=dict(),
			            printer_profile=None)

		printer_profile = self._printer_profile_manager.get_current_or_default()
		connection_profile = self._connection_profile_manager.get_current_or_default()
		return dict(state=self.get_state_string(),
		            connection=connection_profile.id if connection_profile is not None else None,
		            protocol=self._protocol.key,
		            protocol_args=self._protocol.args(),
		            transport=self._transport.key,
		            transport_args=self._transport.args(),
		            printer_profile=printer_profile["id"] if printer_profile is not None and "id" in printer_profile else "_default")

	def is_connected(self):
		return self._protocol is not None and self._protocol.state in (ProtocolState.CONNECTED, ProtocolState.PROCESSING, ProtocolState.PAUSED)

	def is_closed_or_error(self, *args, **kwargs):
		return self._protocol is None or self._protocol.state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR)

	def is_operational(self, *args, **kwargs):
		return not self.is_closed_or_error()

	def is_printing(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.PROCESSING

	def is_cancelling(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.CANCELLING

	def is_pausing(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.PAUSING

	def is_paused(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.PAUSED

	def is_resuming(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.RESUMING

	def is_finishing(self, *args, **kwargs):
		return self._protocol is not None and self._protocol.state == ProtocolState.FINISHING

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
		return list(map(lambda x: (x[0][1:], x[2]), self._sd_files))

	def add_sd_file(self, filename, path, on_success=None, on_failure=None, *args, **kwargs):
		if not self._protocol or self._protocol.state in ProtocolState.PROCESSING_STATES or not self.is_sd_ready():
			self._logger.error("No connection to printer, printer busy or missing SD support")
			return

		self._on_streaming_done = on_success
		self._on_streaming_failed = on_failure

		def sd_upload_started(local_filename, remote_filename):
			eventManager().fire(Events.TRANSFER_STARTED, dict(local=local_filename,
			                                                  remote=remote_filename))

		def sd_upload_succeeded(local_filename, remote_filename, elapsed):
			payload = dict(local=local_filename,
			               remote=remote_filename,
			               time=elapsed)
			eventManager().fire(Events.TRANSFER_DONE, payload)
			if callable(self._on_streaming_done):
				self._on_streaming_done(remote_filename, remote_filename, FileDestinations.SDCARD)

		def sd_upload_failed(local_filename, remote_filename, elapsed):
			payload = dict(local=local_filename,
			               remote=remote_filename,
			               time=elapsed)
			eventManager().fire(Events.TRANSFER_FAILED, payload)
			if callable(self._on_streaming_failed):
				self._on_streaming_failed(remote_filename, remote_filename, FileDestinations.SDCARD)

		for name, hook in self.sd_card_upload_hooks.items():
			# first sd card upload plugin that feels responsible gets the job
			try:
				result = hook(self, filename, path, sd_upload_started, sd_upload_succeeded, sd_upload_failed,
				              *args, **kwargs)
				if result is not None:
					return result
			except Exception:
				self._logger.exception("There was an error running the sd upload "
				                       "hook provided by plugin {}".format(name),
				                       extra=dict(plugin=name))

		else:
			# no plugin feels responsible, use the default implementation
			return self._add_sd_file(filename, path, user=kwargs.get("user"), tags=kwargs.get("tags"))

	def _get_free_remote_name(self, filename):
		files = self.refresh_sd_files(blocking=True)
		existingSdFiles = list(map(lambda x: x[0], files))

		if valid_file_type(filename, "gcode"):
			# figure out remote filename
			remote_name = util.get_dos_filename(filename,
			                                    existing_filenames=existingSdFiles,
			                                    extension="gco",
			                                    whitelisted_extensions=["gco", "g"])
		else:
			# probably something else added through a plugin, use it's basename as-is
			remote_name = os.path.basename(filename)

		return remote_name

	def _add_sd_file(self, filename, path, user=None, tags=None, **kwargs):
		remote_name = self._get_free_remote_name(filename)

		job = LocalGcodeStreamjob.from_job(self._file_manager.create_print_job("local", path,
		                                                                       user=user),
		                                   "/" + remote_name)
		self._sd_streaming = True
		self._update_job(job)
		self._reset_progress_data()
		self._protocol.process(job)

		return remote_name

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
		if not self.is_connected() or not self.is_sd_ready():
			return []
		self._sd_filelist_available.clear()
		self._protocol.list_files(tags=kwargs.get("tags", set()) | {"trigger:printer.refresh_sd_files"})
		if blocking:
			self._sd_filelist_available.wait(kwargs.get("timeout", 10000))
			return self._sd_files

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
		elif self._job.job.last_result.success:
			progress = self._job.job.last_result.progress
			print_time = self._job.job.last_result.elapsed
			cleaned_print_time = self._job.job.last_result.clean_elapsed
			pos = self._job.job.last_result.pos
		else:
			progress = self._job.job.progress
			print_time = self._job.job.elapsed
			cleaned_print_time = self._job.job.clean_elapsed
			pos = self._job.job.pos

		print_time_left = print_time_left_origin = None
		if progress is not None:
			progress_int = int(progress * 100)
			if self._last_progress_report != progress_int:
				self._last_progress_report = progress_int
				self._report_print_progress_to_plugins(progress_int)

			if progress == 0:
				print_time_left = None
				print_time_left_origin = None
			elif progress == 1.0:
				print_time_left = 0
				print_time_left_origin = None
			elif self._job.estimator is not None:
				original_estimate = None
				original_estimate_type = None

				try:
					print_time_left, print_time_left_origin = self._job.estimator.estimate(progress,
					                                                                       print_time,
					                                                                       cleaned_print_time,
					                                                                       original_estimate,
					                                                                       original_estimate_type)
				except Exception:
					self._logger.exception("Error while estimating print time via {}".format(self._job.estimator))

		return self._dict(completion=progress * 100 if progress is not None else None,
		                  filepos=pos,
		                  printTime=int(print_time) if print_time is not None else None,
		                  printTimeLeft=int(print_time_left) if print_time_left is not None else None,
		                  printTimeLeftOrigin=print_time_left_origin)

	def _add_temperature_data(self, temperatures=None):
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

	def _update_job(self, job=None, user=None):
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

		if isinstance(job, LocalGcodeFilePrintjob) and not isinstance(job, CopyJobMixin):
			# local file means we might have some information about the job stored in the file manager!
			try:
				file_data = self._file_manager.get_metadata(FileDestinations.LOCAL, job.path)
			except Exception:
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
		if isinstance(job, SDFilePrintjob):
			job_type = "sdcard"
		elif isinstance(job, LocalGcodeStreamjob):
			job_type = "stream"
		else:
			job_type = "local"

		self._job = JobData(job=job,
		                    average_past_total=average_past_total,
		                    analysis_total=analysis_total,
		                    estimator=self._estimator_factory(job_type))
		job.register_listener(self)

	def _update_job_user(self, user):
		# TODO need multithread protection?
		self._job.user = user
		job_data = self.get_current_job()
		self._state_monitor.set_job_data(self._dict(file=job_data["file"],
		                                            estimatedPrintTime=job_data["estimatedPrintTime"],
		                                            averagePrintTime=job_data["averagePrintTime"],
		                                            lastPrintTime=job_data["lastPrintTime"],
		                                            filament=job_data["filament"],
		                                            user=user))

	def _send_initial_state_update(self, callback):
		try:
			data = self._state_monitor.get_current_data()
			data.update(dict(temps=list(self._temperature_history),
			                 logs=list(self._log),
			                 messages=list(self._messages)))
			callback.on_printer_send_initial_data(data)
		except Exception:
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

	def on_protocol_log_received(self, protocol, message, *args, **kwargs):
		if protocol != self._protocol:
			return

		# process feedback controls
		if self._feedback_controls and not "_all" in self._feedback_errors:
			try:
				self._process_registered_message(message)
			except Exception:
				# something went wrong while feedback matching
				self._logger.exception("Error while trying to apply feedback control matching, disabling it")
				self._feedback_errors.append("_all")

	def on_protocol_state(self, protocol, old_state, new_state, *args, **kwargs):
		if protocol != self._protocol:
			return

		self._logger.info("Protocol state changed from {} to {}".format(old_state, new_state))

		# forward relevant state changes to file manager
		if old_state == ProtocolState.PROCESSING:
			if self._job is not None:
				if new_state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR):
					payload = self._job.job.event_payload()
					if payload:
						payload["reason"] = "error"
						payload["error"] = protocol.get_error_string() # TODO

					def finalize():
						self._file_manager.log_print(self._get_origin_for_job(self._job.job),
						                             self._job.job.name,
						                             time.time(),
						                             payload["time"],
						                             False,
						                             self._printer_profile_manager.get_current_or_default()["id"])
						eventManager().fire(Events.PRINT_FAILED, payload)

					thread = threading.Thread(target=finalize)
					thread.daemon = True
					thread.start()
			self._analysis_queue.resume() # printing done, put those cpu cycles to good use

		elif new_state == ProtocolState.PROCESSING:
			self._analysis_queue.pause() # do not analyse files while printing

		elif new_state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR) and old_state != ProtocolState.DISCONNECTING:
			self.disconnect()
			self._set_current_z(None)
			self._update_progress_data()
			self._set_offsets(None)
			self._add_temperature_data()
			self._update_job()
			self._connection_profile_manager.deselect()
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
		eventManager().fire(Events.UPDATED_FILES, {"type": "printables"})
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

	def on_protocol_job_started(self, protocol, job, suppress_script=False, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "processing"):
			return

		payload = job.event_payload()
		if payload:
			payload["user"] = kwargs.get("user")
			eventManager().fire(Events.PRINT_STARTED, payload)
			self._logger_job.info("Print job started - origin: {}, path: {}, owner: {}, user: {}".format(payload.get("origin"),
			                                                                                             payload.get("path"),
			                                                                                             payload.get("owner"),
			                                                                                             payload.get("user")))

			if not suppress_script:
				self.script("beforePrintStarted",
				            context=dict(event=payload),
				            part_of_job=True,
				            must_be_set=False)

	def on_protocol_job_finishing(self, protocol, job, suppress_script=False, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "finishing"):
			return

		payload = job.event_payload()
		if payload:
			if "time" not in payload and job.last_result.available:
				elapsed = job.last_result.elapsed
				if elapsed is not None:
					payload["time"] = elapsed

			self._update_progress_data(completion=100,
			                           filepos=payload.get("size"),
			                           print_time=payload.get("time"),
			                           print_time_left=0)
			self._state_monitor.set_state(self._dict(text=self.get_state_string(),
			                                         flags=self._get_state_flags()))

			if not suppress_script:
				self.script("afterPrintDone",
				            context=dict(event=payload),
				            part_of_job=True,
				            must_be_set=False)

	def on_protocol_job_done(self, protocol, job, suppress_scripts=False, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "done"):
			return

		payload = job.event_payload(incl_last=True)
		if payload.get("time") is not None:
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

		eventManager().fire(Events.PRINT_DONE, payload)
		self._logger_job.info("Print job done - origin: {}, path: {}, owner: {}".format(payload.get("origin"),
		                                                                                payload.get("path"),
		                                                                                payload.get("owner")))


	def on_protocol_job_failed(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "failed"):
			return

		payload = job.event_payload(incl_last=True)
		if payload:
			eventManager().fire(Events.PRINT_FAILED, payload)

	def on_protocol_job_cancelling(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "cancelling"):
			return

		firmware_error = kwargs.get("error", None)

		payload = job.event_payload()
		if payload:
			payload["user"] = kwargs.get("user")
			if firmware_error:
				payload["firmwareError"] = firmware_error
			eventManager().fire(Events.PRINT_CANCELLING, payload)

	def on_protocol_job_cancelled(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "cancelled"):
			return

		self._update_progress_data()

		cancel_position = kwargs.get("position", None)
		suppress_script = kwargs.get("suppress_script", None)

		payload = job.event_payload(incl_last=True)
		if payload:
			payload["user"] = kwargs.get("user")
			if cancel_position:
				payload["position"] = cancel_position

			if not suppress_script:
				self.script("afterPrintCancelled",
				            context=dict(event=payload),
				            part_of_job=True,
				            must_be_set=False)

			eventManager().fire(Events.PRINT_CANCELLED, payload)
			self._logger_job.info("Print job cancelled - origin: {}, path: {}, owner: {}, user: {}".format(payload.get("origin"),
			                                                                                               payload.get("path"),
			                                                                                               payload.get("owner"),
			                                                                                               payload.get("user")))

			payload["reason"] = "cancelled"

			def finalize():
				if payload.get("time") is not None:
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

	def on_protocol_job_paused(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "paused"):
			return

		pause_position = kwargs.get("position", None)
		suppress_script = kwargs.get("suppress_script", None)

		payload = job.event_payload()
		if payload:
			payload["user"] = kwargs.get("user")
			if pause_position:
				payload["position"] = pause_position

			if not suppress_script:
				self.script("afterPrintPaused",
				            context=dict(event=payload),
				            part_of_job=True,
				            must_be_set=False)

			eventManager().fire(Events.PRINT_PAUSED, payload)

			self._logger_job.info("Print job paused - origin: {}, path: {}, owner: {}, user: {}".format(payload.get("origin"),
			                                                                                            payload.get("path"),
			                                                                                            payload.get("owner"),
			                                                                                            payload.get("user")))

	def on_protocol_job_resumed(self, protocol, job, *args, **kwargs):
		if protocol != self._protocol:
			return

		if self._job is None or job != self._job.job:
			return

		if self._job_event_handled(protocol, job, "resumed"):
			return

		suppress_script = kwargs.get("suppress_script", False)

		payload = job.event_payload()
		if payload:
			payload["user"] = kwargs.get("user")

			if not suppress_script:
				self.script("beforePrintResumed",
				            context=dict(event=payload),
				            must_be_set=False)

			eventManager().fire(Events.PRINT_RESUMED, payload)
			self._logger_job.info("Print job resumed - origin: {}, path: {}, owner: {}, user: {}".format(payload.get("origin"),
			                                                                                             payload.get("path"),
			                                                                                             payload.get("owner"),
			                                                                                             payload.get("user")))

	def _job_event_handled(self, protocol, job, event_type):
		if not isinstance(job, LocalGcodeStreamjob):
			return False

		if event_type == "processing":
			eventManager().fire(Events.TRANSFER_STARTED, {"local": job.name, "remote": job.remote})

		elif event_type in ("done", "cancelled"):
			self._sd_streaming = False
			self._set_current_z(None)
			self._remove_job()
			self._reset_progress_data()
			self._state_monitor.set_state(self._dict(text=self.get_state_string(), flags=self._get_state_flags()))

			if event_type == "done" and self._on_streaming_done is not None:
				self._on_streaming_done(job.name, job.name, FileDestinations.SDCARD)
				eventManager().fire(Events.TRANSFER_DONE, {"local": job.name, "remote": job.remote, "time": job.last_elapsed})
			elif event_type == "cancelled" and self._on_streaming_failed is not None:
				self._on_streaming_failed(job.name, job.name, FileDestinations.SDCARD)
				eventManager().fire(Events.TRANSFER_FAILED, {"local": job.name, "remote": job.remote})

		return True

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
		except Exception:
			self._logger.exception("Error while trying to persist print recovery data")

	#~~ feedback controls

	def _process_registered_message(self, line):
		if not self._feedback_controls or not self._feedback_matcher:
			return

		feedback_match = self._feedback_matcher.search(line)
		if feedback_match is None:
			return

		for match_key in feedback_match.groupdict():
			try:
				feedback_key = match_key[len("group"):]
				if not feedback_key in self._feedback_controls or feedback_key in self._feedback_errors or feedback_match.group(match_key) is None:
					continue
				matched_part = feedback_match.group(match_key)

				if self._feedback_controls[feedback_key]["matcher"] is None:
					continue

				match = self._feedback_controls[feedback_key]["matcher"].search(matched_part)
				if match is None:
					continue

				outputs = dict()
				for template_key, template in self._feedback_controls[feedback_key]["templates"].items():
					try:
						output = template.format(*match.groups())
					except KeyError:
						output = template.format(**match.groupdict())
					except Exception:
						if self._logger.isEnabledFor(logging.DEBUG):
							self._logger.exception("Could not process template {}: {}".format(template_key, template))
						output = None

					if output is not None:
						outputs[template_key] = output

				eventManager().fire(Events.REGISTERED_MESSAGE_RECEIVED, dict(key=feedback_key, matched=matched_part, outputs=outputs))

			except Exception:
				self._logger.exception("Error while trying to match feedback control output, disabling key {}".format(match_key))
				self._feedback_errors.append(match_key)

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

		self._last_update = monotonic_time()
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
			self._change_event.set()

	def set_progress(self, progress):
		with self._progress_lock:
			self._progress = progress
			self._change_event.set()

	def set_temp_offsets(self, offsets):
		if offsets is None:
			offsets = dict()
		self._offsets = offsets
		self._change_event.set()

	def _work(self):
		try:
			while True:
				self._change_event.wait()

				now = monotonic_time()
				delta = now - self._last_update
				additional_wait_time = self._interval - delta
				if additional_wait_time > 0:
					time.sleep(additional_wait_time)

				with self._state_lock:
					data = self.get_current_data()
					self._update_callback(data)
					self._last_update = monotonic_time()
					self._change_event.clear()
		except Exception:
			logging.getLogger(__name__).exception("Looks like something crashed inside the state update worker. Please report this on the OctoPrint issue tracker (make sure to include logs!)")

	def get_current_data(self):
		with self._progress_lock:
			self._progress = self._get_current_progress()

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


def convert_feedback_controls(configured_controls):
	if not configured_controls:
		return dict(), None

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
