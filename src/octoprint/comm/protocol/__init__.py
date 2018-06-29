# coding=utf-8
from __future__ import absolute_import, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.transport import TransportListener, TransportState
from octoprint.plugin import plugin_manager
from octoprint.util import to_unicode, CountedEvent
from octoprint.util.listener import ListenerAware

import contextlib
import copy
import logging

_registry = dict()

def register_protocols():
	from .reprap import ReprapGcodeProtocol

	logger = logging.getLogger(__name__)

	# stock protocols
	register_protocol(ReprapGcodeProtocol)

	# more protocols provided by plugins
	hooks = plugin_manager().get_hooks(b"octoprint.comm.protocol.register")
	for name, hook in hooks.items():
		try:
			protocols = hook()
			for protocol in protocols:
				try:
					register_protocol(protocol)
				except:
					logger.exception("Error while registering protocol class {} for plugin {}".format(protocol, name))
		except:
			logger.exception("Error executing octoprint.comm.protocol.register hook for plugin {}".format(name))


def register_protocol(protocol_class):
	if not hasattr(protocol_class, "key"):
		raise ValueError("Protocol class {} is missing key".format(protocol_class))
	_registry[protocol_class.key] = protocol_class


def lookup_protocol(key):
	return _registry.get(key)


def all_protocols():
	return _registry.values()


class Protocol(ListenerAware, TransportListener):

	name = None
	key = None

	supported_jobs = []

	@classmethod
	def get_connection_options(cls):
		return []

	def __init__(self, *args, **kwargs):
		super(Protocol, self).__init__()

		self._logger = logging.getLogger(__name__)
		self._protocol_logger = logging.getLogger("PROTOCOL")
		self._state = ProtocolState.DISCONNECTED

		self._job = None
		self._transport = None

		self._job_on_hold = CountedEvent()

		self._args = dict()

	def args(self):
		return copy.deepcopy(self._args)

	def set_current_args(self, **value):
		self._args = copy.deepcopy(value)

	@contextlib.contextmanager
	def job_put_on_hold(self, blocking=True):
		if not self._job_on_hold.acquire(blocking=blocking):
			raise RuntimeError("Could not acquire job_on_hold lock")

		self._job_on_hold.set()
		try:
			yield
		finally:
			self._job_on_hold.clear()
			if self._job_on_hold.counter == 0:
				self._job_on_hold_cleared()
			self._job_on_hold.release()

	@property
	def job_on_hold(self):
		return self._job_on_hold.counter > 0

	def set_job_on_hold(self, value, blocking=True):
		if not self._job_on_hold.acquire(blocking=blocking):
			return False

		try:
			if value:
				self._job_on_hold.set()
			else:
				self._job_on_hold.clear()
				if self._job_on_hold.counter == 0:
					self._job_on_hold_cleared()
		finally:
			self._job_on_hold.release()

		return True

	@property
	def transport(self):
		return self._transport

	@property
	def state(self):
		return self._state

	@state.setter
	def state(self, new_state):
		old_state = self._state
		if old_state == new_state:
			return

		self._state = new_state

		name = "_on_state_{}".format(new_state)
		method = getattr(self, name, None)
		if method is not None:
			method(old_state)

		self.process_protocol_log("--- Protocol state changed from '{}' to '{}'".format(old_state, new_state))
		self.notify_listeners("on_protocol_state", self, old_state, new_state)

	def connect(self, transport, transport_args=None, transport_kwargs=None):
		if self.state not in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR):
			raise ProtocolAlreadyConnectedError("Already connected, disconnect first")

		self.process_protocol_log("--- Protocol {} connecting via transport {}...".format(self,
		                                                                                  transport))

		if transport_args is None:
			transport_args = []
		if transport_kwargs is None:
			transport_kwargs = dict()

		self._transport = transport
		self._transport.register_listener(self)

		if self._transport.state == TransportState.DISCONNECTED:
			self._transport.connect(*transport_args, **transport_kwargs)
		self.state = ProtocolState.CONNECTING

	def disconnect(self, error=False):
		if self.state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR, ProtocolState.DISCONNECTING):
			raise ProtocolNotConnectedError("Already disconnecting or disconnected")

		self.state = ProtocolState.DISCONNECTING

		self.process_protocol_log("--- Protocol {} disconnecting from transport {}...".format(self,
		                                                                                      self._transport))

		self._transport.unregister_listener(self)
		if self._transport.state == TransportState.CONNECTED:
			self._transport.disconnect()

		if error:
			self.state = ProtocolState.DISCONNECTED_WITH_ERROR
		else:
			self.state = ProtocolState.DISCONNECTED

	def process(self, job, position=0, tags=None):
		if not job.can_process(self):
			raise ValueError("Job {} cannot be processed with protocol {}".format(job, self))
		self._job = job
		self._job.register_listener(self)
		self._job.process(self, position=position, tags=tags)

	def pause_processing(self, tags=None):
		if self._job is None or self.state != ProtocolState.PROCESSING:
			return
		self.state = ProtocolState.PAUSING
		self._job.pause()

	def resume_processing(self, tags=None):
		if self._job is None or self.state != ProtocolState.PAUSED:
			return
		self.state = ProtocolState.RESUMING
		self._job.resume()

	def cancel_processing(self, error=False, tags=None):
		if self._job is not None and self.state in (ProtocolState.PROCESSING, ProtocolState.PAUSED):
			self.state = ProtocolState.CANCELLING
			self.notify_listeners("on_protocol_job_cancelling", self, self._job)
			self._job.cancel(error=error)

	def can_send(self):
		return True

	def send_commands(self, command_type=None, *commands):
		pass

	def send_script(self, script, context=None):
		pass

	def repair(self):
		pass

	def on_job_started(self, job):
		self.notify_listeners("on_protocol_job_started", self, job)
		self.state = ProtocolState.PROCESSING

	def on_job_paused(self, job, *args, **kwargs):
		self.notify_listeners("on_protocol_job_paused", self, job)
		self.state = ProtocolState.PAUSED

	def on_job_resumed(self, job):
		self.notify_listeners("on_protocol_job_resumed", self, job)
		self.state = ProtocolState.PROCESSING

	def on_job_done(self, job):
		self.notify_listeners("on_protocol_job_done", self, job)
		self._job_processed(job)

	def on_job_cancelled(self, job):
		self.notify_listeners("on_protocol_job_cancelled", self, job)
		self._job_processed(job)

	def on_job_failed(self, job):
		self.notify_listeners("on_protocol_job_failed", self, job)
		self._job_processed(job)

	def _job_processed(self, job):
		self._job.unregister_listener(self)
		self.state = ProtocolState.CONNECTED

	def on_transport_disconnected(self, transport, error=None):
		self.disconnect(error=error is not None)

	def on_transport_log_received_data(self, transport, data):
		message = "<<< {}".format(to_unicode(data, errors="replace").strip())
		self.process_protocol_log(message)

	def on_transport_log_sent_data(self, transport, data):
		message = ">>> {}".format(to_unicode(data, errors="replace").strip())
		self.process_protocol_log(message)

	def on_transport_log_message(self, transport, data):
		message = "--- {}".format(to_unicode(data, errors="replace").strip())
		self.process_protocol_log(message)

	def process_protocol_log(self, message):
		self._protocol_logger.info(message)
		self.notify_listeners("on_protocol_log", self, message)

	def _job_on_hold_cleared(self):
		pass


	def __str__(self):
		return self.__class__.__name__

class ProtocolState(object):
	CONNECTING = "connecting"
	CONNECTED = "connected"
	DISCONNECTING = "disconnecting"
	DISCONNECTED = "disconnected"
	PROCESSING = "processing"
	FINISHING = "finishing"
	CANCELLING = "cancelling"
	PAUSING = "pausing"
	RESUMING = "resuming"
	PAUSED = "paused"
	ERROR = "error"
	DISCONNECTED_WITH_ERROR = "disconnected_with_error"

	PROCESSING_STATES = (PROCESSING, CANCELLING, PAUSING, RESUMING, FINISHING)
	OPERATIONAL_STATES = (CONNECTED, PAUSED) + PROCESSING_STATES

class ProtocolAlreadyConnectedError(Exception):
	pass

class ProtocolNotConnectedError(Exception):
	pass

class ThreeAxisProtocolMixin(object):
	def move(self, x=None, y=None, z=None, feedrate=None, relative=False):
		pass

	def home(self, x=False, y=False, z=False):
		pass


class MultiToolProtocolMixin(object):

	def change_tool(self, tool):
		pass


class ThreeDPrinterProtocolMixin(ThreeAxisProtocolMixin, MultiToolProtocolMixin):
	def move(self, x=None, y=None, z=None, e=None, feedrate=None, relative=False):
		pass

	def set_feedrate_multiplier(self, multiplier):
		pass

	def set_extrusion_multiplier(self, multiplier):
		pass

	def set_extruder_temperature(self, temperature, tool=None, wait=False):
		pass

	def set_bed_temperature(self, temperature, wait=False):
		pass


class FanControlProtocolMixin(object):

	def set_fan_speed(self, speed):
		pass

	def get_fan_speed(self, speed):
		pass


class MotorControlProtocolMixin(object):

	def enable_motors(self):
		self.set_motor_state(True)

	def disable_motors(self):
		self.set_motor_state(False)

	def set_motor_state(self, enabled):
		pass

	def get_motor_state(self):
		pass


class PowerControlProtocolMixin(object):

	def enable_power(self):
		self.set_power_state(True)

	def disable_power(self):
		self.set_power_state(False)

	def set_power_state(self, enabled):
		pass

	def get_power_state(self):
		return None


class FileAwareProtocolMixin(object):

	def init_file_storage(self):
		pass

	def eject_file_storage(self):
		pass

	def list_files(self):
		pass

	def start_file_print(self, name, position=0, tags=None):
		pass

	def pause_file_print(self):
		pass

	def resume_file_print(self):
		pass

	def get_file_print_status(self):
		pass

	def start_file_print_status_monitor(self):
		pass

	def stop_file_print_status_monitor(self):
		pass


class FileManagementProtocolMixin(FileAwareProtocolMixin):

	def delete_file(self, name):
		pass


class FileStreamingProtocolMixin(FileManagementProtocolMixin):

	def record_file(self, name):
		pass

	def stop_recording_file(self):
		pass


class ProtocolListener(object):

	def on_protocol_state(self, protocol, old_state, new_state, *args, **kwargs):
		pass

	def on_protocol_temperature(self, protocol, temperatures, *args, **kwargs):
		pass

	def on_protocol_log(self, protocol, message, *args, **kwargs):
		pass

	def on_protocol_reset(self, protocol, idle, *args, **kwargs):
		pass

	def on_protocol_job_started(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_pausing(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_paused(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_resuming(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_resumed(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_cancelling(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_cancelled(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_finishing(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_done(self, protocol, job, *args, **kwargs):
		pass

	def on_protocol_job_failed(self, protocol, job, *args, **kwargs):
		pass


class FileAwareProtocolListener(object):

	def on_protocol_file_storage_available(self, protocol, available, *args, **kwargs):
		pass

	def on_protocol_file_list(self, protocol, files, *args, **kwargs):
		pass

	def on_protocol_file_status(self, protocol, pos, total, *args, **kwargs):
		pass

	def on_protocol_file_print_started(self, protocol, name, long_name, size, *args, **kwargs):
		pass

	def on_protocol_file_print_done(self, protocol, *args, **kwargs):
		pass


class PositionAwareProtocolListener(object):

	def on_protocol_position_all_update(self, protocol, position, *args, **kwargs):
		pass

	def on_protocol_position_z_update(self, protocol, z, *args, **kwargs):
		pass


class FirmwareDataAwareProtocolListener(object):

	def on_protocol_firmware_info(self, protocol, info, *args, **kwargs):
		pass

	def on_protocol_firmware_capability(self, protocol, capability, enabled, capabilities, *args, **kwargs):
		pass
