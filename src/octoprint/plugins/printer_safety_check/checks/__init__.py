# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


class Check(object):
	name = None

	def __init__(self):
		self._active = True
		self._triggered = False

	def received(self, line):
		"""Called when receiving a new line from the printer"""
		pass

	def m115(self, name, data):
		"""Called when receiving the response to an M115 from the printer"""
		pass

	def cap(self, cap, enabled):
		"""Called when receiving a capability report line"""
		pass

	@property
	def active(self):
		"""Whether this check is still active"""
		return self._active

	@property
	def triggered(self):
		"""Whether the check has been triggered"""
		return self._triggered

	def reset(self):
		self._active = True
		self._triggered = False


class AuthorCheck(Check):
	authors = ()

	AUTHOR = "| Author: ".lower()

	def received(self, line):
		if not line:
			return

		lower_line = line.lower()
		if self.AUTHOR in lower_line:
			self._triggered = any(map(lambda x: x in lower_line, self.authors))
			self._active = False

