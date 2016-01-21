# coding=utf-8
from __future__ import absolute_import, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging


class Protocol(object):

	def __init__(self):
		self._logger = logging.getLogger(__name__)
		self._listeners = []

	def register_listener(self, listener):
		self._listeners.append(listener)

	def unregister_listener(self, listener):
		self._listeners.remove(listener)

	def connect(self, transport):
		pass

	def disconnect(self):
		pass

	def process(self, job):
		pass

	def move(self, x=None, y=None, z=None, e=None, feedrate=None, relative=False):
		pass

	def home(self, x=False, y=False, z=False):
		pass

	def set_feedrate_multiplier(self, multiplier):
		pass

	def set_extrusion_multiplier(self, multiplier):
		pass

	def notify_listeners(self, name, *args, **kwargs):
		for listener in self._listeners:
			method = getattr(listener, name, None)
			if not method:
				continue

			try:
				method(*args, **kwargs)
			except:
				self._logger.exception("Exception while calling {} on protocol listener {}".format(
						"{}({})".format(name, ", ".join(list(args) + ["{}={}".format(key, value)
						                                              for key, value in kwargs.items()]))
				))


class FanControlProtocolMixin(object):

	def set_fan_speed(self, speed):
		pass


class MotorControlProtocolMixin(object):

	def enable_motors(self):
		self.set_motors(True)

	def disable_motors(self):
		self.set_motors(False)

	def set_motors(self, enabled):
		pass


class PowerControlProtocolMixin(object):

	def enable_power(self):
		self.set_power(True)

	def disable_power(self):
		self.set_power(False)

	def set_power(self, enabled):
		pass


class FileAwareProtocolMixin(object):

	def init_file_storage(self):
		pass

	def list_files(self):
		pass

	def start_file_print(self, name):
		pass

	def pause_file_print(self):
		pass

	def resume_file_print(self):
		pass


class FileManagementProtocolMixin(FileAwareProtocolMixin):

	def delete_file(self, name):
		pass


class FileStreamingProtocolMixin(FileManagementProtocolMixin):

	def record_file(self, name, job):
		pass

	def stop_recording_file(self):
		pass


class ProtocolListener(object):

	def on_protocol_connection_state(self, state):
		pass

	def on_protocol_temperature(self, temperatures):
		pass


class FileAwareProtocolListener(object):

	def on_protocol_sd_file_list(self, files):
		pass

	def on_protocol_sd_status(self, name, pos, total):
		pass
