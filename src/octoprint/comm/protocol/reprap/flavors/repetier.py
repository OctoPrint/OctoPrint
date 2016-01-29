# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


from octoprint.comm.protocol.reprap.flavors import ReprapGcodeFlavor

import logging

class RepetierFlavor(ReprapGcodeFlavor):

	key = "repetier"

	always_send_checksum = True

	logger = logging.getLogger(__name__)

	identical_resends_countdown = 5

	##~~ Preprocessors, returning True stops further processing by the protocol

	@classmethod
	def preprocess_comm_resend(cls, linenumber, state):
		if state.get("resend_swallow_repetitions", False) \
				and state.get("resend_swallow_repetitions_counter", 0) \
				and linenumber == state["resend_last_linenumber"] \
				and state["resend_swallow_repetitions_counter"] > 0:
			cls.logger.debug("Ignoring resend request for line {}, that is "
			                 "probably a repetition sent by the firmware to "
			                 "ensure it arrives, not a real request"
			                 .format(linenumber))
			state["resend_swallow_repetitions_counter"] -= 1
			return True

		state["resend_swallow_repetitions_counter"] = cls.identical_resends_countdown


