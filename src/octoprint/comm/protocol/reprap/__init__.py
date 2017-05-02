# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, division

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol import Protocol, ThreeDPrinterProtocolMixin, FileStreamingProtocolMixin, \
	MotorControlProtocolMixin, FanControlProtocolMixin, ProtocolState
from octoprint.comm.transport import Transport, LineAwareTransportWrapper, \
	PushingTransportWrapper, PushingTransportWrapperListener

from octoprint.comm.protocol.gcode.util import TypedQueue, TypeAlreadyInQueue, \
	GcodeCommand, regexes_parameters

from octoprint.job import LocalGcodeFilePrintjob, SDFilePrintjob, \
	LocalGcodeStreamjob

from octoprint.util import to_unicode, protectedkeydict, CountedEvent

try:
	import queue
except ImportError:
	import Queue as queue

import collections
import threading
import time


class ReprapGcodeProtocol(Protocol, ThreeDPrinterProtocolMixin, MotorControlProtocolMixin,
                          FanControlProtocolMixin, FileStreamingProtocolMixin,
                          PushingTransportWrapperListener):

	supported_jobs = [LocalGcodeFilePrintjob,
	                  LocalGcodeStreamjob,
	                  SDFilePrintjob]

	@staticmethod
	def get_attributes_starting_with(flavor, prefix):
		return [x for x in dir(flavor) if x.startswith(prefix)]

	def __init__(self, flavor, connection_timeout=30.0, communication_timeout=5.0,
	             temperature_interval_idle=5.0, temperature_interval_printing=5.0):
		super(ReprapGcodeProtocol, self).__init__()

		self.flavor = flavor
		self.timeouts = dict(
			connection=connection_timeout,
			communication=communication_timeout
		)
		self.interval = dict(
			temperature_idle=temperature_interval_idle,
			temperature_printing=temperature_interval_printing
		)

		comm_attrs = self.get_attributes_starting_with(self.flavor, "comm_")
		message_attrs = self.get_attributes_starting_with(self.flavor, "message_")
		error_attrs = self.get_attributes_starting_with(self.flavor, "error_")

		self._registered_messages = comm_attrs + message_attrs
		self._error_messages = error_attrs

		self._transport = None

		self._internal_state = dict(
			# temperature and heating related
			temperatures=dict(),
			heating_start=None,
			heating_lost=0,
			heating=False,

			# current stuff
			current_tool=0,
			former_tool=0,
			current_z=None,

			# sd status
			sd_available=False,
			sd_files=[],
			sd_files_temp=None,

			# resend status
			resend_active=False,
			resend_delta=None,
			resend_linenumber=None,
			resend_count=None,

			# protocol status
			long_running_command=False,

			# misc
			only_from_job=False,
			trigger_events=True,
			ignore_ok=0,

			# timeout
			timeout = None,
			timeout_consecutive=0,
		)
		self._protected_state = protectedkeydict(self._internal_state)

		self._command_queue = queue.Queue()
		self._clear_to_send = CountedEvent(max=10, name="comm.clear_to_send")
		self._send_queue = TypedQueue()

		self._current_linenumber = 1
		self._last_lines = collections.deque(iterable=[], maxlen=50)
		self._last_communication_error = None

		self._gcode_hooks = dict(queuing=dict(),
		                         queued=dict(),
		                         sending=dict(),
		                         sent=dict())

		# temperature polling
		self._temperature_poller = None

		# mutexes
		self._line_mutex = threading.RLock()
		self._send_queue_mutex = threading.RLock()

		# sending thread
		self._send_queue_active = False
		self._sending_thread = None

	@property
	def _active(self):
		return self._transport is not None and self._transport.active and self._send_queue_active

	def connect(self, transport, transport_args=None, transport_kwargs=None):
		if not isinstance(transport, Transport):
			raise ValueError("transport must be a Transport subclass but is a {} instead".format(type(transport)))

		self._internal_state["timeout"] = self._get_timeout("connection")

		transport = PushingTransportWrapper(LineAwareTransportWrapper(transport), timeout=5.0)

		self._send_queue_active = True
		self._sending_thread = threading.Thread(target=self._send_loop, name="comm.sending_thread")
		self._sending_thread.daemon = True
		self._sending_thread.start()

		super(ReprapGcodeProtocol, self).connect(transport,
		                                         transport_args=transport_args,
		                                         transport_kwargs=transport_kwargs)


	def disconnect(self, error=False):
		# TODO either clear send queue, or wait until everything has been sent...
		self._send_queue_active = False
		self._sending_thread = None

		if self._temperature_poller:
			self._temperature_poller.cancel()
			self._temperature_poller = None

		super(ReprapGcodeProtocol, self).disconnect()

	def process(self, job, position=0):
		if isinstance(job, LocalGcodeStreamjob):
			self._internal_state["only_from_job"] = True
			self._internal_state["trigger_events"] = False
		else:
			self._internal_state["only_from_job"] = False
			self._internal_state["trigger_events"] = True

		super(ReprapGcodeProtocol, self).process(job, position=position)

	def move(self, x=None, y=None, z=None, e=None, feedrate=None, relative=False):
		commands = [self.flavor.command_move(x=x, y=y, z=z, e=e, f=feedrate)]

		if relative:
			commands = [self.flavor.command_set_relative_positioning()]\
			           + commands\
			           + [self.flavor.command_set_absolute_positioning()]

		self._send_commands(*commands)

	def home(self, x=False, y=False, z=False):
		self._send_commands(self.flavor.command_home(x=x, y=y, z=z))

	def change_tool(self, tool):
		self._send_commands(self.flavor.command_set_tool(tool))

	def set_feedrate_multiplier(self, multiplier):
		self._send_commands(self.flavor.command_set_feedrate_multiplier(multiplier))

	def set_extrusion_multiplier(self, multiplier):
		self._send_commands(self.flavor.command_set_extrusion_multiplier(multiplier))

	def set_extruder_temperature(self, temperature, tool=None, wait=False):
		self._send_commands(self.flavor.command_set_extruder_temp(temperature, tool, wait=wait))

	def set_bed_temperature(self, temperature, wait=False):
		self._send_commands(self.flavor.command_set_bed_temp(temperature, wait=wait))

	##~~ MotorControlProtocolMixin

	def set_motor_state(self, enabled):
		self._send_commands(self.flavor.command.set_motor_state(enabled))

	##~~ FanControlProtocolMixin

	def set_fan_speed(self, speed):
		self._send_commands(self.flavor.command.command_set_fan_speed(speed))

	##~~ FileStreamingProtocolMixin

	def init_file_storage(self):
		self._send_commands(self.flavor.command_sd_init())

	def list_files(self):
		self._send_commands(self.flavor.command_sd_refresh())

	def start_file_print(self, name, position=0):
		self._send_commands(self.flavor.command_sd_select_file(name),
		                    self.flavor.command_sd_set_pos(position),
		                    self.flavor.command_sd_start())

	def pause_file_print(self):
		self._send_commands(self.flavor.command_sd_pause())

	def resume_file_print(self):
		self._send_commands(self.flavor.command_sd_resume())

	def delete_file(self, name):
		self._send_commands(self.flavor.command_sd_delete(name))

	def record_file(self, name, job):
		self._send_commands(self.flavor.command_sd_begin_write(name))

	def stop_recording_file(self):
		self._send_commands(self.flavor.command_sd_end_write())

	def get_file_print_status(self):
		self._send_commands(self.flavor.command_sd_status())

	def can_send(self):
		return not self._internal_state["long_running_command"] and not self._internal_state["heating"]

	def send_commands(self, *commands, **kwargs):
		command_type = kwargs.get("command_type")
		if self.state == ProtocolState.PRINTING and not self._job.runs_parallel:
			if len(commands) > 1:
				command_type = None
			for command in commands:
				self._command_queue.put((command, command_type))
		elif self._is_operational():
			self._send_commands(*commands, command_type=command_type)

	##~~ State handling

	def _is_operational(self):
		return self.state not in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR)

	def _is_busy(self):
		return self.state in (ProtocolState.PRINTING, ProtocolState.PAUSED)

	def _on_state_connecting(self, old_state):
		if old_state is not ProtocolState.DISCONNECTED:
			return

		hello = self.flavor.command_hello()
		if hello:
			self._send_command(hello)
			self._clear_to_send.set()

	def _on_state_connected(self, old_state):
		if old_state == ProtocolState.CONNECTING:
			self._internal_state["timeout"] = self._get_timeout("communication")

			self._send_command(self.flavor.command_set_line(0))
			self._clear_to_send.set()

			def poll_temperature_interval():
				return self.interval["temperature_printing"] if self.state == ProtocolState.PRINTING else self.interval["temperature_idle"]

			def poll_temperature():
				if self._is_operational() and not self._internal_state["only_from_job"] and self.can_send():
					self._send_command(self.flavor.command_get_temp(), command_type="temperature_poll")

			from octoprint.util import RepeatedTimer
			self._temperature_poller = RepeatedTimer(poll_temperature_interval,
			                                         poll_temperature,
			                                         run_first=True)
			self._temperature_poller.start()

	def _on_state_disconnected(self, old_state):
		self._handle_disconnected(old_state, False)

	def _on_state_disconnected_with_error(self, old_state):
		self._handle_disconnected(old_state, True)

	def _handle_disconnected(self, old_state, error):
		if self._temperature_poller is not None:
			self._temperature_poller.cancel()
			self._temperature_poller = None

	##~~ Receiving

	def on_transport_data_pushed(self, transport, data):
		if transport != self._transport:
			return
		self._receive(data)

	def _receive(self, data):
		if data is None:
			# EOF
			# TODO handle EOF
			pass

		def convert_line(line):
			if line is None:
				return None, None
			stripped_line = line.strip().strip("\0")
			return stripped_line, stripped_line.lower()

		orig_line = to_unicode(data, encoding="ascii", errors="replace").strip()
		line, lower_line = convert_line(orig_line)

		if len(line):
			# TODO handle dwelling
			pass

		any_processed = False

		for message in self._registered_messages: # flavor.comm_* + flavor.message_*
			handler_method = getattr(self, "_on_{}".format(message), None)
			if not handler_method:
				# no handler, nothing to do
				continue

			# match line against flavor specific matcher
			matches = getattr(self.flavor, message)(line, lower_line, self._protected_state)
			continue_further = False
			if isinstance(matches, tuple) and len(matches) == 2:
				matches, continue_further = matches

			if matches:
				if not any_processed:
					self._on_comm_any()
					any_processed = True

				message_args = dict()

				parse_method = getattr(self.flavor, "parse_{}".format(message), None)
				if parse_method:
					# flavor specific parser? run it
					parse_result = parse_method(line, lower_line, self._protected_state)
					if parse_result is None:
						if continue_further:
							continue
						else:
							break

					# add parser result to kwargs
					message_args.update(parse_result)

				# before handler: flavor.before_comm_* or flavor.before_message_*
				before_handler = getattr(self.flavor, "before_{}".format(message), None)
				if before_handler:
					before_handler(**message_args)

				# run handler
				result = handler_method(**message_args)

				# after handler: flavor.after_comm_* or flavor.after_message_*
				after_handler = getattr(self.flavor, "after_{}".format(message), None)
				if after_handler:
					after_handler(result, **message_args)

				if not result:
					# nothing returned? handled -> only continue further if instructed
					if continue_further:
						continue
					else:
						break
		else:
			# unknown message
			pass

	def _on_comm_any(self):
		if self.state == ProtocolState.CONNECTING:
			hello = self.flavor.command_hello()
			if hello:
				self._send_command(hello)
				self._clear_to_send.set()

	def _on_comm_timeout(self):
		if self.state not in (ProtocolState.PRINTING,
		                      ProtocolState.PAUSED,
		                      ProtocolState.CONNECTED):
			return

		general_message = "Configure long running commands or increase communication timeout if that happens regularly on specific commands or long moves."

		# figure out which consecutive timeout maximum we have to use
		if self._internal_state["long_running_command"]:
			consecutive_max = 5 # TODO take from config
		elif self.state in (ProtocolState.PRINTING,):
			consecutive_max = 10 # TODO take from config
		else:
			consecutive_max = 15 # TODO take from config

		# now increment the timeout counter
		self._internal_state["timeout_consecutive"] += 1
		self._logger.debug("Now at {} consecutive timeouts".format(self._internal_state["timeout_consecutive"]))

		if 0 < consecutive_max < self._internal_state["timeout_consecutive"]:
			# too many consecutive timeouts, we give up
			# TODO implement
			pass

		elif self._internal_state["resend_active"]:
			message = "Communication timeout during an active resend, resending same line again to trigger response from printer."
			self._logger.info(message)
			self.notify_listeners("on_protocol_log", self, message + " " + general_message)
			if self._send_same_from_resend():
				self._clear_to_send.set()

		elif self._internal_state["heating"]:
			# blocking heatup active, consider that finished
			message = "Timeout while in an active heatup, considering heatup to be over"
			self._logger.info(message)
			self._finish_heatup()

		elif self._internal_state["long_running_command"]:
			# long running command active, ignore timeout
			self._logger.debug("Ran into a communication timeout, but a command known to be a long runner is currently active")

		elif self.state in (ProtocolState.PRINTING, ProtocolState.PAUSED):
			# printing, try to tickle the printer
			message = "Communication timeout while printing, trying to trigger response from printer."
			self._logger.info(message)
			self.notify_listeners("on_protocol_log_message", self, message + " " + general_message)
			if self._send_command("M105", command_type="temperature"):
				self._clear_to_send.set()

		elif self._clear_to_send.blocked():
			# timeout while idle and no oks left, let's try to tickle the printer
			message = "Communication timeout while idle, trying to trigger response from printer."
			self._logger.info(message)
			self.notify_listeners("on_protocol_log_message", self, message + " " + general_message)
			self._clear_to_send.set()

		return self.state != ProtocolState.PRINTING

	def _on_comm_ok(self):
		if self._internal_state["ignore_ok"] > 0:
			self._internal_state["ignore_ok"] -= 1
			if self._internal_state["ignore_ok"] < 0:
				self._internal_state["ignore_ok"] = 0
			self._logger.debug("Ignoring this ok, ignore counter is now {}".format(self._internal_state["ignore_ok"]))
			return

		if self.state == ProtocolState.CONNECTING:
			self.state = ProtocolState.CONNECTED
			return

		self._clear_to_send.set()

		# reset long running commands, persisted current tools and heatup counters on ok

		self._internal_state["long_running_command"] = False

		if self._internal_state["former_tool"]:
			self._internal_state["current_tool"] = self._internal_state["former_tool"]
			self._internal_state["former_tool"] = None

		self._finish_heatup()

		if not self.state in (ProtocolState.PRINTING, ProtocolState.CONNECTED, ProtocolState.PAUSED):
			return

		# process ongoing resend requests and queues if we are operational

		if self._internal_state["resend_delta"] is not None:
			self._send_next_from_resend()
		else:
			self._internal_state["resend_active"] = False
			self._continue_sending()

	def _on_comm_ignore_ok(self):
		self._internal_state["ignore_ok"] += 1
		self._logger.info("Ignoring next ok, counter is now at {}".format(self._internal_state["ignore_ok"]))

	def _on_comm_wait(self):
		if self.state == ProtocolState.PRINTING:
			self._on_comm_ok()

	def _on_comm_resend(self, linenumber):
		if linenumber is None:
			return False

		if self._internal_state["resend_delta"] is None and linenumber == self._current_linenumber:
			# We don't expect to have an active resend request and the printer is requesting a resend of
			# a line we haven't yet sent.
			#
			# This means the printer got a line from us with N = self._current_linenumber - 1 but had already
			# acknowledged that. This can happen if the last line was resent due to a timeout during an active
			# (prior) resend request.
			#
			# We will ignore this resend request and just continue normally.
			self._logger.debug("Ignoring resend request for line {} == current line, we haven't sent that yet so the printer got N-1 twice from us, probably due to a timeout".format(linenumber))
			return False

		last_communication_error = self._last_communication_error
		self._last_communication_error = None

		resend_delta = self._current_linenumber - linenumber

		if last_communication_error is not None \
				and last_communication_error == "linenumber" \
				and linenumber == self._internal_state["resend_linenumber"] \
				and self._internal_state["resend_delta"] is not None and self._internal_state["resend_count"] < self._internal_state["resend_delta"]:
			self._logger.debug("Ignoring resend request for line {}, that still originates from lines we sent before we got the first resend request".format(linenumber))
			self._internal_state["resend_count"] += 1
			return True

		self._internal_state["resend_active"] = True
		self._internal_state["resend_delta"] = resend_delta
		self._internal_state["resend_linenumber"] = linenumber
		self._internal_state["resend_count"] = 0

		if resend_delta > len(self._last_lines) or len(self._last_lines) == 0 or resend_delta < 0:
			self._logger.error("Printer requested to resend a line further back than we have")
			if self._is_busy():
				# TODO set error state & log
				self.cancel_processing(error=True)
			else:
				self._internal_state["resend_delta"] = None

		# TODO log resend (with rate limiting)

		return True

	def _on_comm_start(self):
		if self.state == ProtocolState.CONNECTING:
			self.state = ProtocolState.CONNECTED

	def _on_comm_error(self, line, lower_line):
		for message in self._error_messages:
			handler_method = getattr(self, "_on_{}".format(message), None)
			if not handler_method:
				continue

			if getattr(self.flavor, message)(line, lower_line, self._protected_state):
				message_args = dict()

				parse_method = getattr(self.flavor, "parse_{}".format(message), None)
				if parse_method:
					parse_result = parse_method(line, lower_line, self._protected_state)
					if parse_result is None:
						break

					message_args.update(parse_result)

				if not handler_method(**message_args):
					break
		else:
			# unknown error message
			pass

	def _on_error_communication(self, error_type):
		self._last_communication_error = error_type

	# TODO multiline error handling

	def _on_message_temperature(self, max_tool_num, temperatures, heatup_detected):
		if heatup_detected:
			self._logger.debug("Externally triggered heatup detected")
			self._internal_state["heating"] = True
			self._internal_state["heatup_start"] = time.time()

		potential_tools = dict(("T{}".format(x), "tool{}".format(x)) for x in range(max_tool_num + 1))
		potential_tools.update(dict(B="bed"))

		for tool_rep, tool in potential_tools.items():
			if not tool_rep in temperatures:
				continue
			actual, target = temperatures[tool_rep]
			self._set_temperature(tool, actual, target)

		self.notify_listeners("on_protocol_temperature", self, self._internal_state["temperatures"])

	def _on_message_sd_init_ok(self):
		self._internal_state["sd_available"] = True
		self.list_files()

	def _on_message_sd_init_fail(self):
		self._internal_state["sd_available"] = False

	def _on_message_sd_begin_file_list(self):
		self._internal_state["sd_files_temp"] = []

	def _on_message_sd_end_file_list(self):
		self._internal_state["sd_files"] = self._internal_state["sd_files_temp"]
		self._internal_state["sd_files_temp"] = None
		self.notify_listeners("on_protocol_sd_file_list", self, self._internal_state["sd_files"])

	def _on_message_sd_entry(self, name, size):
		self._internal_state["sd_files_temp"].append((name, size))

	def _on_message_sd_file_opened(self, name, size):
		self.notify_listeners("on_protocol_file_print_started", self, name, size)

	def _on_message_sd_done_printing(self):
		self.notify_listeners("on_protocol_file_print_done", self)

	def _on_message_sd_printing_byte(self, current, total):
		self.notify_listeners("on_protocol_sd_status", self, current, total)

	def _finish_heatup(self):
		if self._internal_state["heating_start"]:
			self._internal_state["heating_lost"] = self._internal_state["heating_lost"] + (time.time() - self._internal_state["heating_start"])
			self._internal_state["heating_start"] = None
			self._internal_state["heating"] = False

	##~~ Sending

	def _continue_sending(self):
		while self._active:
			if self.state in (ProtocolState.CONNECTED, ProtocolState.PAUSED):
				return self._send_from_queue()

			elif self.state in (ProtocolState.PRINTING,):
				# we are printing, we really want to send either something from the command
				# queue or the next line from our file, so we only return here if we actually DO
				# send something
				if self._send_from_queue():
					# we found something in the queue to send
					return True

				elif self._send_next_from_job():
					# we sent the next line from the file
					return True

				self._logger.debug("No command sent on ok while printing, doing another iteration")

	def _send_same_from_resend(self):
		return self._send_next_from_resend(again=True)

	def _send_next_from_resend(self, again=False):
		self._last_communication_error = None

		# Make sure we are only handling one sending job at a time
		with self._send_queue_mutex:
			if again:
				# If we are about to send the last line from the active resend request
				# again, we first need to increment resend delta. It might already
				# be set to None if the last resend line was already sent, so
				# if that's the case we set it to 0. It will then be incremented,
				# the last line will be sent again, and then the delta will be
				# decremented and set to None again, completing the cycle.
				if self._internal_state["resend_delta"] is None:
					self._internal_state["resend_delta"] = 0
				self._internal_state["resend_delta"] += 1

			resend_delta = self._internal_state["resend_delta"]

			command = self._last_lines[-resend_delta]
			linenumber = self._current_linenumber - resend_delta

			result = self._enqueue_for_sending(command, linenumber=linenumber)

			self._internal_state["resend_delta"] -= 1
			if self._internal_state["resend_delta"] <= 0:
				self._internal_state["resend_active"] = False
				self._internal_state["resend_delta"] = None
				self._internal_state["resend_linenumber"] = None
				self._internal_state["resend_count"] = 0

			return result

	def _send_next_from_job(self):
		with self._send_queue_mutex:
			while self._active:
				# we loop until we've actually enqueued a line for sending
				if self.state != ProtocolState.PRINTING:
					# we are no longer printing, return False
					return False

				line = self._job.get_next()
				if line is None:
					# end of job, return False
					return False

				if self._send_command(line):
					return True

				self._logger.debug("Command \"{}\" from job not enqueued, doing another iteration".format(line))

	def _send_from_queue(self):
		# We loop here to make sure that if we do NOT send the first command
		# from the queue, we'll send the second (if there is one). We do not
		# want to get stuck here by throwing away commands.
		while True:
			if self._internal_state["only_from_job"]:
				# irrelevant command queue => return
				return False

			try:
				entry = self._command_queue.get(block=False)
			except queue.Empty:
				# nothing in command queue
				return False

			try:
				if isinstance(entry, tuple):
					if not len(entry) == 3:
						# something with that entry is broken, ignore it and fetch
						# the next one
						continue
					cmd, cmd_type, callback = entry
				else:
					cmd = entry
					cmd_type = None
					callback = None

				if self._send_command(cmd, command_type=cmd_type, on_sent=callback):
					# we actually did add this cmd to the send queue, so let's
					# return, we are done here
					return True
			finally:
				self._command_queue.task_done()

	def _send_commands(self, *commands, **kwargs):
		# TODO return True or False depending on whether something/all? was sent
		command_type = kwargs.get("command_type", None)
		for command in commands:
			if len(commands) > 1:
				command_type = None
			self._send_command(command, command_type=command_type)

	def _send_command(self, command, command_type=None, on_sent=None):
		if isinstance(command, GcodeCommand):
			gcode = command
			command = str(gcode)
		else:
			gcode = None

		with self._send_queue_mutex:
			if self._internal_state["trigger_events"]:
				command, command_type, gcode = self._process_command_phase("queuing", command, command_type, gcode=gcode)

				if command is None:
					# command is no more, return
					return False

				# TODO gcode to event mapping
				#if gcode and gcode.command in gcode_to_event:
				#	# if this is a gcode bound to an event, trigger that now
				#	self._eventbus.fire(gcode_to_event[gcode.command])

			if self._enqueue_for_sending(command, command_type=command_type, on_sent=on_sent):
				if self._internal_state["trigger_events"]:
					self._process_command_phase("queued", command, command_type, gcode=gcode)
				return True
			else:
				return False

	def _enqueue_for_sending(self, command, linenumber=None, command_type=None, on_sent=None):
		"""
		Enqueues a command and optional command_type and linenumber in the send queue.

		Arguments:
		    command (unicode): The command to send
		    linenumber (int): An optional line number to use for sending the
		        command.
		    command_type (unicode): An optional command type. There can only be
		        one command of a specified command type in the queue at any
		        given time.
		"""

		try:
			self._send_queue.put((command, linenumber, command_type, on_sent), item_type=command_type)
			return True
		except TypeAlreadyInQueue as e:
			self._logger.debug("Type already in queue: {}".format(e.type))
			return False

	def _send_loop(self):
		"""
		The send loop is reponsible of sending commands in ``self._send_queue`` over the line, if it is cleared for
		sending (through received ``ok`` responses from the printer's firmware.
		"""

		self._clear_to_send.wait()

		while self._send_queue_active:
			try:
				# wait until we have something in the queue
				entry = self._send_queue.get()

				try:
					# make sure we are still active
					if not self._send_queue_active:
						break

					# fetch command and optional linenumber from queue
					command, linenumber, command_type, on_sent = entry

					# some firmwares (e.g. Smoothie) might support additional in-band communication that will not
					# stick to the acknowledgement behaviour of GCODE, so we check here if we have a GCODE command
					# at hand here and only clear our clear_to_send flag later if that's the case
					gcode = GcodeCommand.from_line(command)

					if linenumber is not None:
						# line number predetermined - this only happens for resends, so we'll use the number and
						# send directly without any processing (since that already took place on the first sending!)
						self._do_send_with_checksum(command, linenumber)

					else:
						# trigger "sending" phase
						command, _, gcode = self._process_command_phase("sending", command, command_type, gcode=gcode)

						if command is None:
							# No, we are not going to send this, that was a last-minute bail.
							# However, since we already are in the send queue, our _monitor
							# loop won't be triggered with the reply from this unsent command
							# now, so we try to tickle the processing of any active
							# command queues manually
							self._continue_sending()

							# and now let's fetch the next item from the queue
							continue

						if command.strip() == "":
							self._logger.info("Refusing to send an empty line to the printer")

							# same here, tickle the queues manually
							self._continue_sending()

							# and fetch the next item
							continue

						# now comes the part where we increase line numbers and send stuff - no turning back now
						if not self._transport.message_integrity:
							# transport does not have message integrity, let's see if we'll send a checksum
							command_requiring_checksum = gcode is not None and gcode.command in self.flavor.checksum_requiring_commands
							command_allowing_checksum = gcode is not None or self.flavor.unknown_with_checksum
							checksum_enabled = self.flavor.always_send_checksum or (self.state == ProtocolState.PRINTING and not self.flavor.never_send_checksum)

							send_with_checksum = command_requiring_checksum or (command_allowing_checksum and checksum_enabled)

						else:
							# transport has message integrity, no checksum
							send_with_checksum = False

						command_to_send = command.encode("ascii", errors="replace")
						if send_with_checksum:
							self._do_increment_and_send_with_checksum(command_to_send)
						else:
							self._do_send_without_checksum(command_to_send)

					# trigger "sent" phase and use up one "ok"
					if on_sent is not None and callable(on_sent):
						# we have a sent callback for this specific command, let's execute it now
						on_sent()
					self._process_command_phase("sent", command, command_type, gcode=gcode)

					# we only need to use up a clear if the command we just sent was either a gcode command or if we also
					# require ack's for unknown commands
					use_up_clear = self.flavor.unknown_requires_ack
					if gcode is not None and not gcode.unknown:
						use_up_clear = True

					if use_up_clear:
						# if we need to use up a clear, do that now
						self._clear_to_send.clear()
					else:
						# Otherwise we need to tickle the read queue - there might not be a reply
						# to this command, so our _monitor loop will stay waiting until timeout. We
						# definitely do not want that, so we tickle the queue manually here
						self._continue_sending()

				finally:
					# no matter _how_ we exit this block, we signal that we
					# are done processing the last fetched queue entry
					self._send_queue.task_done()

				# now we just wait for the next clear and then start again
				self._clear_to_send.wait()
			except:
				self._logger.exception("Caught an exception in the send loop")
		self.notify_listeners("on_protocol_log", self, "Closing down send loop")

	def _process_command_phase(self, phase, command, command_type=None, gcode=None):
		if phase not in ("queuing", "queued", "sending", "sent"):
			return command, command_type, gcode

		if gcode is None:
			gcode = GcodeCommand.from_line(command)

		# send it through the phase specific handlers provided by plugins
		for name, hook in self._gcode_hooks[phase].items():
			try:
				hook_result = hook(self, phase, command, command_type, gcode.command)
			except:
				self._logger.exception("Error while processing hook {name} for phase {phase} and command {command}:".format(**locals()))
			else:
				command, command_type, gcode = self._handle_command_handler_result(command, command_type, gcode.command, hook_result)
				if command is None:
					# hook handler return None as command, so we'll stop here and return a full out None result
					return None, None, None

		# if it's a gcode command send it through the specific handler if it exists
		if gcode is not None:
			gcode_handler = "_gcode_" + gcode.command + "_" + phase
			if hasattr(self, gcode_handler):
				handler_result = getattr(self, gcode_handler)(command, cmd_type=command_type)
				command, command_type, gcode = self._handle_command_handler_result(command, command_type, gcode, handler_result)

		# send it through the phase specific command handler if it exists
		command_phase_handler = "_command_phase_" + phase
		if hasattr(self, command_phase_handler):
			handler_result = getattr(self, command_phase_handler)(command, cmd_type=command_type, gcode=gcode)
			command, command_type, gcode = self._handle_command_handler_result(command, command_type, gcode, handler_result)

		# finally return whatever we resulted on
		return command, command_type, gcode

	def _handle_command_handler_result(self, command, command_type, gcode, handler_result):
		original_tuple = (command, command_type, gcode)

		if handler_result is None:
			# handler didn't return anything, we'll just continue
			return original_tuple

		if isinstance(handler_result, basestring):
			# handler did return just a string, we'll turn that into a 1-tuple now
			handler_result = (handler_result,)
		elif not isinstance(handler_result, (tuple, list)):
			# handler didn't return an expected result format, we'll just ignore it and continue
			return original_tuple

		hook_result_length = len(handler_result)
		if hook_result_length == 1:
			# handler returned just the command
			command, = handler_result
		elif hook_result_length == 2:
			# handler returned command and command_type
			command, command_type = handler_result
		else:
			# handler returned a tuple of an unexpected length
			return original_tuple

		gcode = GcodeCommand.from_line(command)
		return command, command_type, gcode

	##~~ actual sending via serial

	def _do_increment_and_send_with_checksum(self, cmd):
		with self._line_mutex:
			linenumber = self._current_linenumber
			self._add_to_last_lines(cmd)
			self._current_linenumber += 1
			self._do_send_with_checksum(cmd, linenumber)

	def _do_send_with_checksum(self, cmd, lineNumber):
		command_to_send = b"N%d %s" % (lineNumber, cmd)
		checksum = 0
		for c in command_to_send:
			checksum ^= ord(c)
		command_to_send = b"%s*%d" % (command_to_send, checksum)
		self._do_send_without_checksum(command_to_send)

	def _do_send_without_checksum(self, data):
		self._transport.write(data + b"\n")

	def _add_to_last_lines(self, command):
		self._last_lines.append(command)

	##~~ command handlers

	def _gcode_T_sent(self, cmd, cmd_type=None):
		tool_match = regexes_parameters["intT"].search(cmd)
		if tool_match:
			self._internal_state["current_tool"] = int(tool_match.group("value"))

	def _gcode_G0_sent(self, cmd, cmd_type=None):
		if "Z" in cmd:
			match = regexes_parameters["floatZ"].search(cmd)
			if match:
				try:
					z = float(match.group("value"))
					if self._internal_state["current_z"] != z:
						self._internal_state["current_z"] = z
						# TODO self._callback.on_comm_z_change(z)
				except ValueError:
					pass
	_gcode_G1_sent = _gcode_G0_sent

	def _gcode_M0_queuing(self, cmd, cmd_type=None):
		self.pause_file_print()
		return None, # Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
	_gcode_M1_queuing = _gcode_M0_queuing

	def _gcode_M25_queuing(self, cmd, cmd_type=None):
		# M25 while not printing from SD will be handled as pause. This way it can be used as another marker
		# for GCODE induced pausing. Send it to the printer anyway though.
		if self.state == ProtocolState.PRINTING and not isinstance(self._job, SDFilePrintjob):
			self.pause_file_print()

	def _gcode_M140_queuing(self, cmd, cmd_type=None):
		# TODO heated bed handling needs heated bed flag from printer profile
		#if not self._printerProfileManager.get_current_or_default()["heatedBed"]:
		#	self._log("Warn: Not sending \"{}\", printer profile has no heated bed".format(cmd))
		#	return None, # Don't send bed commands if we don't have a heated bed
		pass
	_gcode_M190_queuing = _gcode_M140_queuing

	def _gcode_M104_sent(self, cmd, cmd_type=None, wait=False, support_r=False):
		tool_num = self._internal_state["current_tool"]
		tool_match = regexes_parameters["intT"].search(cmd)

		if tool_match:
			tool_num = int(tool_match.group("value"))

			if wait:
				self._internal_state["former_tool"] = self._internal_state["current_tool"]
				self._internal_state["current_tool"] = tool_num

		match = regexes_parameters["floatS"].search(cmd)
		if not match and support_r:
			match = regexes_parameters["floatR"].search(cmd)

		if match:
			tool = "tool{}".format(tool_num)
			try:
				target = float(match.group("value"))
				self._set_temperature(tool, None, target)
				self.notify_listeners("on_protocol_temperature", self, self._internal_state["temperatures"])
			except ValueError:
				pass

	def _gcode_M140_sent(self, cmd, cmd_type=None, wait=False, support_r=False):
		match = regexes_parameters["floatS"].search(cmd)
		if not match and support_r:
			match = regexes_parameters["floatR"].search(cmd)

		if match:
			try:
				target = float(match.group("value"))
				self._set_temperature("bed", None, target)
				self.notify_listeners("on_protocol_temperature", self, self._internal_state["temperatures"])
			except ValueError:
				pass

	def _gcode_M109_sent(self, cmd, cmd_type=None):
		self._internal_state["heatup_start"] = time.time()
		self._internal_state["long_running_command"] = True
		self._internal_state["heating"] = True
		self._gcode_M104_sent(cmd, cmd_type, wait=True, support_r=True)

	def _gcode_M190_sent(self, cmd, cmd_type=None):
		self._internal_state["heatup_start"] = time.time()
		self._internal_state["long_running_command"] = True
		self._internal_state["heating"] = True
		self._gcode_M140_sent(cmd, cmd_type, wait=True, support_r=True)

	def _gcode_M116_sent(self, cmd, cmd_type=None):
		self._internal_state["heatup_start"] = time.time()
		self._internal_state["long_running_command"] = True
		self._internal_state["heating"] = True

	def _gcode_M110_sending(self, cmd, cmd_type=None):
		new_line_number = None
		match = regexes_parameters["intN"].search(cmd)
		if match:
			try:
				new_line_number = int(match.group("value"))
			except:
				pass
		else:
			new_line_number = 0

		with self._line_mutex:
			# send M110 command with new line number
			self._current_linenumber = new_line_number

			# after a reset of the line number we have no way to determine what line exactly the printer now wants
			self._last_lines.clear()
		self._internal_state["resend_delta"] = None

	def _gcode_M112_queuing(self, cmd, cmd_type=None):
		# emergency stop, jump the queue with the M112
		self._do_send_with_checksum(str(self.flavor.command_emergency_stop()))
		self._do_increment_and_send_with_checksum(str(self.flavor.command_emergency_stop()))

		# No idea if the printer is still listening or if M112 won. Just in case
		# we'll now try to also manually make sure all heaters are shut off - better
		# safe than sorry. We do this ignoring the queue since at this point it
		# is irrelevant whether the printer has sent enough ack's or not, we
		# are going to shutdown the connection in a second anyhow.
		# TODO needs printer profile
		"""
		for tool in range(self._printerProfileManager.get_current_or_default()["extruder"]["count"]):
			self._do_increment_and_send_with_checksum(self.flavor.set_extruder_temp(s=0, t=tool))
		if self._printerProfileManager.get_current_or_default()["heatedBed"]:
			self._do_increment_and_send_with_checksum(str(self.flavor.set_bed_temp(s=0)))
		"""

		# close to reset host state
		# TODO needs error and event handling
		"""
		self._errorValue = "Closing serial port due to emergency stop M112."
		self._log(self._errorValue)
		self.close(is_error=True)

		# fire the M112 event since we sent it and we're going to prevent the caller from seeing it
		gcode = "M112"
		if gcode in gcodeToEvent:
			eventManager().fire(gcodeToEvent[gcode])
		"""

		# return None 1-tuple to eat the one that is queuing because we don't want to send it twice
		# I hope it got it the first time because as far as I can tell, there is no way to know
		return None,

	def _gcode_G4_sent(self, cmd, cmd_type=None):
		# we are intending to dwell for a period of time, increase the timeout to match
		p_match = regexes_parameters["floatP"].search(cmd)
		s_match = regexes_parameters["floatS"].search(cmd)

		_timeout = 0
		if p_match:
			_timeout = float(p_match.group("value")) / 1000.0
		elif s_match:
			_timeout = float(s_match.group("value"))

		self._internal_state["timeout"] = self._get_timeout("communication") + _timeout

	##~~ command phase handlers

	def _command_phase_sending(self, cmd, cmd_type=None, gcode=None):
		if gcode is not None and gcode.command in self.flavor.long_running_commands:
			self._internal_state["long_running_command"] = True

	##~~ helpers

	def _set_temperature(self, tool, actual, target):
		temperatures = self._internal_state["temperatures"]
		if actual is None and tool in temperatures:
			actual, _ = temperatures[tool]
		if target is None and tool in temperatures:
			_, target = temperatures[tool]
		temperatures[tool] = (actual, target)

	def _get_timeout(self, timeout_type):
		if timeout_type in self.timeouts:
			return time.time() + self.timeouts[timeout_type]
		else:
			return time.time()


if __name__ == "__main__":
	from octoprint.comm.transport.serialtransport import VirtualSerialTransport
	from octoprint.comm.protocol.reprap.virtual import VirtualPrinter
	from octoprint.comm.protocol.reprap.flavors import ReprapGcodeFlavor
	from octoprint.comm.protocol import ProtocolListener, FileAwareProtocolListener
	from octoprint.job import PrintjobListener

	import os

	virtual_sd = "C:/Users/gina/AppData/Roaming/OctoPrint/virtualSd"
	filename = "50mm-t~5.gco"

	def virtual_serial_factory():
		return VirtualPrinter(virtual_sd=virtual_sd)

	class CustomProtocolListener(ProtocolListener, FileAwareProtocolListener, PrintjobListener):

		def __init__(self, protocol):
			super(CustomProtocolListener, self).__init__()
			self._job = None
			self._queue = []
			self._protocol = protocol

		def add_job(self, job):
			self._queue.append(job)

		def get_next_job(self):
			return self._queue.pop(0) if self._queue else None

		def start_next_job(self):
			job = self.get_next_job()
			if job is None:
				return

			self._job = job
			self._job.register_listener(self)
			self._protocol.process(self._job)

		def on_protocol_state(self, protocol, old_state, new_state):
			if protocol != self._protocol:
				return
			print("State changed from {} to {}".format(old_state, new_state))

		def on_protocol_temperature(self, protocol, temperatures):
			if protocol != self._protocol:
				return
			print("Temperature update: {!r}".format(temperatures))

		def on_protocol_sd_file_list(self, protocol, files):
			if protocol != self._protocol:
				return
			print("Received files from printer:")
			for f in files:
				print("\t{} (Size {} bytes)".format(*f))

			self.start_next_job()

		def on_protocol_log(self, protocol, data):
			if protocol != self._protocol:
				return
			print(data)

		def on_job_progress(self, job, progress, elapsed, estimated):
			if job != self._job:
				return
			print("Job progress: {}% (Time: {} min / {} min)".format(int(progress * 100) if progress is not None else "0",
			                                                       "{}:{}".format(int(elapsed / 60), int(elapsed % 60)) if elapsed is not None else "?",
			                                                       "{}:{}".format(int(estimated / 60), int(estimated % 60)) if estimated is not None else "?"))

		def on_job_done(self, job):
			self.start_next_job()

	transport = VirtualSerialTransport(virtual_serial_factory=virtual_serial_factory)
	protocol = ReprapGcodeProtocol(ReprapGcodeFlavor)

	protocol_listener = CustomProtocolListener(protocol)
	protocol_listener.add_job(LocalGcodeFilePrintjob(os.path.join(virtual_sd, filename)))
	protocol_listener.add_job(SDFilePrintjob(filename))
	protocol.register_listener(protocol_listener)

	transport.connect()
	protocol.connect(transport)
"""

if __name__ == "__main__":
	gcode = GcodeCommand.from_line("M104 S220.4 T2")
"""
