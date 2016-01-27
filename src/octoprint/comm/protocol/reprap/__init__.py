# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import re

from octoprint.comm.protocol import Protocol, FileStreamingProtocolMixin, MotorControlProtocolMixin, FanControlProtocolMixin
from octoprint.comm.transport import LineAwareTransportWrapper, TransportListener, PushingTransportWrapper

from octoprint.util import to_unicode, dictview, CountedEvent

import Queue as queue
import threading


regex_float_pattern = "[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = "[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = "\d+"

regex_float = re.compile(regex_float_pattern)
"""Regex for a float value."""


class ReprapGcodeProtocol(Protocol, MotorControlProtocolMixin, FanControlProtocolMixin, FileStreamingProtocolMixin, TransportListener):

	def __init__(self, flavor):
		Protocol.__init__(self)
		self.flavor = flavor

		self._registered_messages = ["comm_ok", "comm_start", "comm_wait", "comm_resend"] \
		                            + [x for x in dir(self.flavor) if x.startswith("message_")]

		self._transport = None

		self._internal_state = dict(
			# sd status
			sd_available=False,
			sd_files=[],
			sd_files_temp=None
		)
		self._state_view = dictview(self._internal_state)

		self._command_queue = queue.Queue()
		self._clear_to_send = CountedEvent(max=10, name="comm.clear_to_send")
		self._send_queue = TypedQueue()

		self._current_linenumber = 1
		self._last_lines = []

		# mutexes
		self._line_mutex = threading.RLock()

		# sending thread
		self._send_queue_active = True
		self.sending_thread = threading.Thread(target=self._send_loop, name="comm.sending_thread")
		self.sending_thread.daemon = True
		self.sending_thread.start()

	def connect(self, transport):
		self._transport = transport

	def move(self, x=None, y=None, z=None, e=None, feedrate=None, relative=False):
		commands = [self.flavor.command_move(x=x, y=y, z=z, e=e, f=feedrate)]

		if relative:
			commands = [self.flavor.command_set_relative_positioning()] + commands + [self.flavor.command_set_absolute_positioning()]

		self._send(*commands)

	def home(self, x=False, y=False, z=False):
		self._send(self.flavor.command_home(x=x, y=y, z=z))

	def set_feedrate_multiplier(self, multiplier):
		self._send(self.flavor.command_set_feedrate_multiplier(multiplier))

	def set_extrusion_multiplier(self, multiplier):
		self._send(self.flavor.command.set_extrusion_multiplier(multiplier))

	##~~ MotorControlProtocolMixin

	def set_motors(self, enabled):
		self._send(self.flavor.command.set_motors(enabled))

	##~~ FanControlProtocolMixin

	def set_fan_speed(self, speed):
		self._send(self.flavor.command.set_fan_speed(speed))

	##~~ FileStreamingProtocolMixin

	def init_file_storage(self):
		self._send(self.flavor.command_sd_init())

	def list_files(self):
		self._send(self.flavor.command_sd_refresh())

	def start_file_print(self, name):
		self._send(self.flavor.command_sd_select_file(name),
		           self.flavor.command_sd_set_pos(0),
		           self.flavor.command_sd_start())

	def pause_file_print(self):
		self._send(self.flavor.command_sd_pause())

	def resume_file_print(self):
		self._send(self.flavor.command_sd_resume())

	def delete_file(self, name):
		self._send(self.flavor.command_sd_delete(name))

	def record_file(self, name, job):
		self._send(self.flavor.command_sd_begin_write(name))

	def stop_recording_file(self):
		self._send(self.flavor.command_sd_end_write())

	def on_transport_data_received(self, transport, data):
		if transport != self._transport:
			return
		self._receive(data)

	def _send(self, *commands):
		for command in commands:
			self._send_queue.put(str(command) + b"\n")

	def _receive(self, data):
		line = to_unicode(data, encoding="ascii", errors="replace").strip()
		lower_line = line.lower()

		for message in self._registered_messages:
			handler_method = getattr(self, "_on_{}".format(message), None)
			if not handler_method:
				continue

			if getattr(self.flavor, message)(line, lower_line, self._state_view):
				message_args = dict()

				parse_method = getattr(self.flavor, "parse_{}".format(message), None)
				if parse_method:
					message_args.update(parse_method(line, lower_line, self._state_view))

				if not handler_method(**message_args):
					break
		else:
			# unknown message
			pass

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
						checksum_enabled = self.flavor.always_send_checksum or (self.isPrinting() and not self.flavor.never_send_checksum)

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

	def _on_comm_ok(self):
		self._clear_to_send.set()

	def _on_comm_wait(self):
		print("!!! wait")

	def _on_comm_resend(self):
		print("!!! resend")

	def _on_comm_start(self):
		print("!!! start")

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

class GcodeCommand(object):

	known_float_attributes = ("x", "y", "z", "e", "s", "p", "r")
	known_int_attributes = ("f", "t", "n")
	known_attributes = known_float_attributes + known_int_attributes

	command_regex = re.compile("^\s*((?P<GM>[GM](?P<number>\d+))|(?P<T>T(?P<tool>\d+))|(?P<F>F(?P<feedrate>\d+)))")

	argument_pattern = "\s*([{float_args}]{float}|[{int_args}]{int})".format(float_args="".join(map(lambda x: x.upper(), known_float_attributes)),
	                                                                                                     int_args="".join(map(lambda x: x.upper(), known_int_attributes)),
	                                                                                                     float=regex_float_pattern,
	                                                                                                     int=regex_int_pattern)
	argument_regex = re.compile(argument_pattern)
	param_regex = re.compile("^[GMT]\d+\s+(.*?)$")

	@staticmethod
	def from_line(line):
		"""
		>>> gcode = GcodeCommand.from_line("M30 some_file.gco")
		>>> gcode.command
		'M30'
		>>> gcode.param
		'some_file.gco'
		>>> gcode = GcodeCommand.from_line("G28 X0 Y0")
		>>> gcode.command
		'G28'
		>>> gcode.x
		0.0
		>>> gcode.y
		0.0
		>>> gcode = GcodeCommand.from_line("M104 S220.0 T1")
		>>> gcode.command
		'M104'
		>>> gcode.s
		220.0
		>>> gcode.t
		1
		"""

		line = line.strip()
		command = ""
		args = {"original": line}
		match = GcodeCommand.command_regex.match(line)
		if match is None:
			args["unknown"] = True
		else:
			if match.group("GM"):
				command = match.group("GM")

				matched_args = GcodeCommand.argument_regex.findall(line)
				if not matched_args:
					param_match = GcodeCommand.param_regex.match(line)
					if param_match is not None:
						args["param"] = param_match.group(1)
				else:
					for arg in matched_args:
						key = arg[0].lower()
						if key in GcodeCommand.known_int_attributes:
							value = int(arg[1:])
						elif key in GcodeCommand.known_float_attributes:
							value = float(arg[1:])
						else:
							value = str(arg[1:])
						args[key] = value
			elif match.group("T"):
				command = "T"
				args["tool"] = match.group("tool")
			elif match.group("F"):
				command = "F"
				args["f"] = match.group("feedrate")

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

		self.progress = None
		self.callback = None

		self.unknown = False

		for key, value in kwargs.iteritems():
			if key in GcodeCommand.known_attributes + ("tool", "original", "param", "progress", "callback", "unknown"):
				self.__setattr__(key, value)

	def __repr__(self):
		return "GcodeCommand(\"{str}\",progress={progress})".format(str=str(self), progress=self.progress)

	def __str__(self):
		if self.original is not None:
			return self.original
		else:
			attr = []
			for key in GcodeCommand.known_attributes:
				value = self.__getattribute__(key)
				if value is not None:
					if key in GcodeCommand.known_int_attributes:
						attr.append("%s%d" % (key.upper(), value))
					elif key in GcodeCommand.known_float_attributes:
						attr.append("%s%f" % (key.upper(), value))
					else:
						attr.append("%s%r" % (key.upper(), value))
			attributeStr = " ".join(attr)
			return "%s%s%s" % (self.command.upper(), " " + attributeStr if attributeStr else "", " " + self.param if self.param else "")

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

	#if offsets is not None:
	#	line = apply_temperature_offsets(line, offsets, current_tool=current_tool)

	return line


"""
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
