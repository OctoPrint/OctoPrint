# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

import re

from octoprint.comm.protocol.reprap import RepRapProtocol


class RepetierTextualProtocol(RepRapProtocol):

	__protocolinfo__ = ("repetier", "RepRap (Repetier Flavor)", False)

	MESSAGE_TARGET_TEMPERATURE = staticmethod(lambda line: "TargetExtr" in line or "TargetBed" in line)

	REGEX_POSITIVE_FLOAT = "[+]?[0-9]*\.?[0-9]+"
	REGEX_TARGET_EXTRUDER_TEMPERATURE = re.compile("TargetExtr([0-9]+):(%s)" % REGEX_POSITIVE_FLOAT)
	REGEX_TARGET_BED_TEMPERATURE = re.compile("TargetBed:(%s)" % REGEX_POSITIVE_FLOAT)

	def __init__(self, transport_factory, protocol_listener=None):
		RepRapProtocol.__init__(self, transport_factory, protocol_listener)
		self._sd_available = True

	def _reset(self):
		self._sd_available = True

	def _evaluate_firmware_specific_messages(self, source, message):
		if RepetierTextualProtocol.MESSAGE_TARGET_TEMPERATURE(message):
			match_extr = RepetierTextualProtocol.REGEX_TARGET_EXTRUDER_TEMPERATURE.match(message)
			match_bed = RepetierTextualProtocol.REGEX_TARGET_BED_TEMPERATURE.match(message)

			current_temperatures = self.get_current_temperatures()
			key = None
			target = None
			try:
				if match_extr is not None:
					tool_num = int(match_extr.group(1))
					key = "tool%d" % tool_num
					target = float(match_extr.group(2))
				elif match_bed is not None:
					key = "bed"
					target = float(match_bed.group(1))
			except ValueError:
				pass

			if key is None:
				return False

			if key in current_temperatures and current_temperatures[key] is not None and isinstance(current_temperatures[key], tuple):
				(actual, old_target) = current_temperatures[key]
				current_temperatures[key] = (actual, target)
			else:
				current_temperatures[key] = (None, target)
			self._updateTemperature(current_temperatures)

		return True

	def _useChecksum(self):
		return True