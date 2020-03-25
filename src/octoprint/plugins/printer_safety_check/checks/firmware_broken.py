# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_babel import gettext
from . import Check, Severity

class FirmwareBrokenChecks(object):
	@classmethod
	def as_dict(cls):
		return dict(checks=(CbdCheck(),),
		            message=gettext("Your printer's firmware is known to have a broken implementation of the "
		                            "communication protocol. This will cause print failures. You'll need to "
		                            "take additional steps for OctoPrint to work with it."),
		            severity=Severity.INFO)


class CbdCheck(Check):
	name = "cbd"
	url = "https://faq.octoprint.org/warning-firmware-broken-cbd"

	CRITICAL_FRAGMENT = "CBD make it".lower()

	def __init__(self):
		Check.__init__(self)
		self._fragment_matches = None

	def received(self, line):
		if not line:
			return

		lower_line = line.lower()
		if self.CRITICAL_FRAGMENT in lower_line:
			self._fragment_matches = True

		self._evaluate()

	def _evaluate(self):
		if self._fragment_matches is None:
			return
		self._triggered = self._fragment_matches
		self._active = False

	def reset(self):
		Check.reset(self)
		self._fragment_matches = None

class ZwlfCheck(CbdCheck):
	name = "zwlf"
	CRITICAL_FRAGMENT = "ZWLF make it".lower()
