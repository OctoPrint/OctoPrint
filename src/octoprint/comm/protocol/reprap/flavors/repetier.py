# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


from octoprint.comm.protocol.reprap.flavors import ReprapGcodeFlavor

from octoprint.comm.protocol.gcode.util import regex_positive_float_pattern

import re

class RepetierFlavor(ReprapGcodeFlavor):

	key = "repetier"

	always_send_checksum = True

	identical_resends_countdown = 5

	regex_tempextr = re.compile("targetextr(?P<toolnum>\d+):(?P<target>%s)" % regex_positive_float_pattern)
	"""Regex for matching target temp reporting from Repetier.

	Groups will be as follows:

	  * ``toolnum``: number of the extruder to which the target temperature
	    report belongs (int)
	  * ``target``: new target temperature (float)
	"""

	regex_tempbed = re.compile("targetbed:(?P<target>%s)" % regex_positive_float_pattern)
	"""Regex for matching target temp reporting from Repetier for beds.

	Groups will be as follows:

	  * ``target``: new target temperature (float)
	"""

	@classmethod
	def message_temperature(cls, line, lower_line, state):
		return ReprapGcodeFlavor.message_temperature(line, lower_line, state) or "targetextr" in lower_line or "targetbed" in lower_line

	@classmethod
	def parse_message_temperature(cls, line, lower_line, state):
		if "targetextr" in lower_line:
			match = cls.regex_tempextr.match(lower_line)
			if match is not None:
				tool_num = int(match.group("toolnum"))
				target = float(match.group("target"))
				tool = "T{}".format(tool_num)
				temperatures = dict()
				temperatures[tool] = (None, target)
				return dict(max_tool_num=max(tool_num, state.get("current_tool", 0)),
				            temperatures=temperatures,
				            detected_heatup=False)
		elif "targetbed" in lower_line:
			match = cls.regex_tempbed.match(lower_line)
			if match is not None:
				target = float(match.group("target"))
				temperatures = dict(bed=(None, target))
				return dict(max_tool_num=state.get("current_tool", 0),
				            temperatures=temperatures,
				            detected_heatup=False)
		else:
			# Repetier sends temperature output on it's own line, so we can't use the
			# "no ok in temperature output" metric to detected external heatups
			result = ReprapGcodeFlavor.parse_message_temperature(line, lower_line, state)
			result["heating"] = False
			return result


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


