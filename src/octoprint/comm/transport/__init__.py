# coding=utf-8
from __future__ import absolute_import, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

from .types import get_param_dict

class Transport(object):

	name = None
	url_scheme = None
	message_integrity = False

	@classmethod
	def get_connection_options(cls):
		return []

	def __init__(self):
		self._listeners = set()

	def connect(self, params, options=None):
		if options is None:
			options = self.get_connection_options()

		param_dict = get_param_dict(params, options)
		self.create_connection(**param_dict)

	def create_connection(self, *args, **kwargs):
		pass

	def send(self, message):
		pass

	def register_listener(self, transport_listener):
		self._listeners.add(transport_listener)

	def unregister_listener(self, transport_listener):
		try:
			self._listeners.remove(transport_listener)
		except KeyError:
			# not registered, ah well, we'll ignore that
			pass

class TransportListener(object):

	def on_transport_message_received(self, message):
		pass

