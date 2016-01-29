# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import re

from octoprint.comm.protocol import Protocol, FileStreamingProtocolMixin, MotorControlProtocolMixin, FanControlProtocolMixin, ProtocolState
from octoprint.comm.transport import LineAwareTransportWrapper, TransportListener, PushingTransportWrapper

from octoprint.comm.protocol.util import TypedQueue, TypeAlreadyInQueue, GcodeCommand, process_gcode_line, strip_comment

from octoprint.job import LocalGcodeFilePrintjob, SDFilePrintjob, LocalGcodeStreamjob

from octoprint.util import to_unicode, protectedkeydict, CountedEvent

import Queue as queue
import threading

class ReprapGcodeProtocol(Protocol, MotorControlProtocolMixin, FanControlProtocolMixin, FileStreamingProtocolMixin, TransportListener):

	supported_jobs = [LocalGcodeFilePrintjob, LocalGcodeStreamjob, SDFilePrintjob]

	@staticmethod
	def get_attributes_starting_with(flavor, prefix):
		return [x for x in dir(flavor) if x.startswith(prefix)]

	def __init__(self, flavor):
		Protocol.__init__(self)
		self.flavor = flavor

		self._registered_messages = self.get_attributes_starting_with(self.flavor, "comm_") \
		                            + self.get_attributes_starting_with(self.flavor, "message_")
		self._error_messages = self.get_attributes_starting_with(self.flavor, "error_")

		self._transport = None

		self._internal_state = dict(
			# sd status
			sd_available=False,
			sd_files=[],
			sd_files_temp=None,

			# resend status
			resend_delta=None,
			resend_linenumber=None,
			resend_count=None,
		)
		self._protected_state = protectedkeydict(self._internal_state)

		self._command_queue = queue.Queue()
		self._clear_to_send = CountedEvent(max=10, name="comm.clear_to_send")
		self._send_queue = TypedQueue()

		self._current_linenumber = 1
		self._last_lines = []
		self._last_communication_error = None

		self._gcode_hooks = dict(queuing=dict(),
		                         queued=dict(),
		                         sending=dict(),
		                         sent=dict())

		# mutexes
		self._line_mutex = threading.RLock()
		self._send_queue_mutex = threading.RLock()

		# sending thread
		self._send_queue_active = True
		self.sending_thread = threading.Thread(target=self._send_loop, name="comm.sending_thread")
		self.sending_thread.daemon = True
		self.sending_thread.start()

		self._only_send_from_job = False
		self._trigger_events_while_sending = True

	def connect(self, transport):
		self._transport = transport

	def process(self, job, position=0):
		if isinstance(job, LocalGcodeStreamjob):
			self._only_send_from_job = True
			self._trigger_events_while_sending = False
		else:
			self._only_send_from_job = False
			self._trigger_events_while_sending = True

		Protocol.process(job, position=position)

	def move(self, x=None, y=None, z=None, e=None, feedrate=None, relative=False):
		commands = [self.flavor.command_move(x=x, y=y, z=z, e=e, f=feedrate)]

		if relative:
			commands = [self.flavor.command_set_relative_positioning()]\
			           + commands\
			           + [self.flavor.command_set_absolute_positioning()]

		self._send_commands(*commands)

	def home(self, x=False, y=False, z=False):
		self._send_commands(self.flavor.command_home(x=x, y=y, z=z))

	def set_feedrate_multiplier(self, multiplier):
		self._send_commands(self.flavor.command_set_feedrate_multiplier(multiplier))

	def set_extrusion_multiplier(self, multiplier):
		self._send_commands(self.flavor.command.set_extrusion_multiplier(multiplier))

	##~~ MotorControlProtocolMixin

	def set_motors(self, enabled):
		self._send_commands(self.flavor.command.set_motors(enabled))

	##~~ FanControlProtocolMixin

	def set_fan_speed(self, speed):
		self._send_commands(self.flavor.command.set_fan_speed(speed))

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

	##~~ Receiving

	def on_transport_data_received(self, transport, data):
		if transport != self._transport:
			return
		self._receive(data)

	def _receive(self, data):
		line = to_unicode(data, encoding="ascii", errors="replace").strip()
		lower_line = line.lower()

		for message in self._registered_messages:
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
			# unknown message
			pass

	def _on_comm_ok(self):
		self._clear_to_send.set()

		if not self.state in (ProtocolState.PRINTING, ProtocolState.CONNECTED, ProtocolState.PAUSED):
			return

		if self._internal_state["resend_delta"] is not None:
			self._send_next_from_resend()
		else:
			self._continue_sending()

	def _on_comm_wait(self):
		if self.state == ProtocolState.PRINTING:
			self._on_comm_ok()

	def _on_comm_resend(self, linenumber):
		if linenumber is None:
			return

		last_communication_error = self._last_communication_error
		self._last_communication_error = None

		resend_delta = self._current_linenumber - linenumber

		if last_communication_error is not None \
				and last_communication_error == "linenumber" \
				and linenumber == self._internal_state["resend_last_linenumber"] \
				and self._resend_delta is not None and self._internal_state["resend_count"] < self._internal_state["resend_delta"]:
			self._logger.debug("Ignoring resend request for line {}, that still originates from lines we sent before we got the first resend request".format(linenumber))
			self._internal_state["resend_count"] += 1
			return

		self._internal_state["resend_delta"] = resend_delta
		self._internal_state["resend_last_linenumber"] = linenumber
		self._internal_state["resend_count"] = 0

		if self._internal_state["resend_delta"] > len(self._last_lines) or len(self._last_lines) == 0 or self._internal_state["resend_delta"] < 0:
			# TODO error because printer requested lines we don't have
			pass


	def _on_comm_start(self):
		print("!!! start")
		self._clear_to_send.set()

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

	def on_error_communication(self, error_type):
		self._last_communication_error = error_type

	# TODO multiline error handling

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
		self.notify_listeners("on_protocol_sd_file_list", self._internal_state["sd_files"])

	def _on_message_sd_entry(self, name, size):
		self._internal_state["sd_files_temp"].append((name, size))

	def _on_message_sd_file_opened(self, name, size):
		pass

	def _on_message_sd_file_selected(self):
		pass

	def _on_message_sd_done_printing(self):
		pass

	def _on_message_sd_printing_byte(self, current, total):
		self.notify_listeners("on_protocol_sd_status", current, total)

	##~~ Sending

	def _continue_sending(self):
		if self.state == ProtocolState.PRINTING and self._job is not None:
			if not self._send_from_queue():
				self._send_next_from_job()
		elif self.state == ProtocolState.CONNECTED or self.state == ProtocolState.PAUSED:
			self._send_from_queue()

	def _send_next_from_resend(self):
		self._last_communication_error = None

		# Make sure we are only handling one sending job at a time
		with self._send_queue_mutex:
			resend_delta = self._internal_state["resend_delta"]
			command = self._last_lines[-resend_delta]
			linenumber = self._current_linenumber - resend_delta

			self._enqueue_for_sending(command, linenumber=linenumber)

			self._internal_state["resend_delta"] -= 1
			if self._internal_state["resend_delta"] <= 0:
				self._internal_state["resend_delta"] = None
				self._internal_state["resend_last_linenumber"] = None
				self._internal_state["resend_count"] = 0

	def _send_next_from_job(self):
		with self._send_queue_mutex:
			line = self._job.get_next()
			if line is not None:
				self._send_command(line)

				# TODO report progress

	def _send_from_queue(self):
		# We loop here to make sure that if we do NOT send the first command
		# from the queue, we'll send the second (if there is one). We do not
		# want to get stuck here by throwing away commands.
		while True:
			if self._command_queue.empty() or self._only_send_from_job:
				# no command queue or irrelevant command queue => return
				return False

			entry = self._command_queue.get()
			if isinstance(entry, tuple):
				if not len(entry) == 2:
					# something with that entry is broken, ignore it and fetch
					# the next one
					continue
				cmd, cmd_type = entry
			else:
				cmd = entry
				cmd_type = None

			if self._send_command(cmd, command_type=cmd_type):
				# we actually did add this cmd to the send queue, so let's
				# return, we are done here
				return True

	def _send_commands(self, *commands):
		for command in commands:
			self._send_command(command)

	def _send_command(self, command, command_type=None):
		if isinstance(command, GcodeCommand):
			gcode = command
			command = gcode.command
		else:
			gcode = None

		with self._send_queue_mutex:
			if self._trigger_events_while_sending:
				command, command_type, gcode = self._process_command_phase("queuing", command, command_type, gcode=gcode)

				if command is None:
					# command is no more, return
					return False

				# TODO gcode to event mapping
				#if gcode and gcode.command in gcode_to_event:
				#	# if this is a gcode bound to an event, trigger that now
				#	self._eventbus.fire(gcode_to_event[gcode.command])

			self._enqueue_for_sending(command, command_type=command_type)

			if self._trigger_events_while_sending:
				self._process_command_phase("queued", command, command_type, gcode=gcode)

			return True

	def _enqueue_for_sending(self, command, command_type=None, linenumber=None):
		"""
		Enqueues a command and optional command_type and linenumber in the send queue.

		Arguments:
		    command (unicode): The command to send
		    command_type (unicode): An optional command type. There can only be
		        one command of a specified command type in the queue at any
		        given time.
		    linenumber (int): An optional line number to use for sending the
		        command.
		"""

		try:
			self._send_queue.put((command, linenumber, command_type))
		except TypeAlreadyInQueue as e:
			self._logger.debug("Type already in queue: {}".format(e.type))

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
					command, linenumber, command_type = entry

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
						command_requiring_checksum = gcode is not None and gcode.command in self.flavor.checksum_requiring_commands
						command_allowing_checksum = gcode is not None or self.flavor.unknown_with_checksum
						checksum_enabled = self.flavor.always_send_checksum or (self.state == ProtocolState.PRINTING and not self.flavor.never_send_checksum)

						command_to_send = command.encode("ascii", errors="replace")
						if command_requiring_checksum or (command_allowing_checksum and checksum_enabled):
							self._do_increment_and_send_with_checksum(command_to_send)
						else:
							self._do_send_without_checksum(command_to_send)

					# trigger "sent" phase and use up one "ok"
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
		self._log("Closing down send loop")

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
			self._add_to_last_line(cmd)
			self._current_linenumber += 1
			self._do_send_with_checksum(cmd, linenumber)

	def _do_send_with_checksum(self, cmd, lineNumber):
		command_to_send = "N%d %s" % (lineNumber, cmd)
		checksum = reduce(lambda x,y:x^y, map(ord, command_to_send))
		command_to_send = "%s*%d" % (command_to_send, checksum)
		self._do_send_without_checksum(command_to_send)

	def _do_send_without_checksum(self, data):
		self._transport.write(data + b"\n")

	def _add_to_last_line(self, command):
		self._last_lines.append(command)


if __name__ == "__main__":
	from octoprint.comm.transport.serialtransport import VirtualSerialTransport
	from octoprint.comm.protocol.reprap.virtual import VirtualPrinter
	from octoprint.comm.protocol.reprap.flavors import ReprapGcodeFlavor

	def virtual_serial_factory():
		return VirtualPrinter(virtual_sd="C:/Users/gina/AppData/Roaming/OctoPrint/virtualSd")

	class CustomProtocolListener(object):

		def on_protocol_sd_file_list(self, files):
			print("Received files from printer:")
			for f in files:
				print("\t{} (Size {} bytes)".format(*f))

	transport = PushingTransportWrapper(
			LineAwareTransportWrapper(
					VirtualSerialTransport(virtual_serial_factory=virtual_serial_factory)
			)
	)
	protocol = ReprapGcodeProtocol(ReprapGcodeFlavor)
	transport.register_listener(protocol)
	protocol.register_listener(CustomProtocolListener())

	transport.connect()
	protocol.connect(transport)
"""

if __name__ == "__main__":
	gcode = GcodeCommand.from_line("M104 S220.4 T2")
"""
