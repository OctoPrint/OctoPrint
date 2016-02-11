# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


class ListenerAware(object):

	def __init__(self):
		self._listeners = set()

	def register_listener(self, listener):
		self._listeners.add(listener)

	def unregister_listener(self, listener):
		try:
			self._listeners.remove(listener)
		except KeyError:
			pass

	def notify_listeners(self, name, *args, **kwargs):
		from logging import getLogger
		logger = getLogger(__name__)

		for listener in self._listeners.copy():
			method = getattr(listener, name, None)
			if not method:
				continue

			try:
				method(*args, **kwargs)
			except:
				logger.exception("Exception while calling {} on protocol listener {}".format(
					"{}(...)".format(name),
					listener
				))
