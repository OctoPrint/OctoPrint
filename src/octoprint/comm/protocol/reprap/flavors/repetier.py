__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

from octoprint.comm.protocol.reprap.flavors import StandardFlavor
from octoprint.comm.protocol.reprap.util import regex_positive_float_pattern


class RepetierFlavor(StandardFlavor):

    key = "repetier"
    name = "Repetier"

    send_checksum = "always"
    identical_resends_countdown = 5
    block_while_dwelling = True
    detect_external_heatups = False

    sd_always_available = True

    regex_tempextr = re.compile(
        r"targetextr(?P<toolnum>\d+):(?P<target>%s)" % regex_positive_float_pattern
    )
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
    def identifier(cls, firmware_name, firmware_info):
        return "repetier" in firmware_name.lower()

    def message_temperature(self, line, lower_line):
        return (
            super().message_temperature(line, lower_line)
            or "targetextr" in lower_line
            or "targetbed" in lower_line
        )

    def parse_message_temperature(self, line, lower_line):
        if "targetextr" in lower_line:
            match = self.regex_tempextr.match(lower_line)
            if match is not None:
                tool_num = int(match.group("toolnum"))
                target = float(match.group("target"))
                tool = "T{}".format(tool_num)
                temperatures = {}
                temperatures[tool] = (None, target)
                return {
                    "max_tool_num": max(
                        tool_num, self._protocol.flags.get("current_tool", 0)
                    ),
                    "temperatures": temperatures,
                    "heatup_detected": False,
                }
        elif "targetbed" in lower_line:
            match = self.regex_tempbed.match(lower_line)
            if match is not None:
                target = float(match.group("target"))
                temperatures = {"bed": (None, target)}
                return {
                    "max_tool_num": self._protocol.flags.get("current_tool", 0),
                    "temperatures": temperatures,
                    "heatup_detected": False,
                }
        else:
            # Repetier sends temperature output on it's own line, so we can't use the
            # "no ok in temperature output" metric to detected external heatups
            result = super().parse_message_temperature(line, lower_line)
            result["heatup_detected"] = False
            return result

    ##~~ Preprocessors, returning True stops further processing by the protocol

    def preprocess_comm_resend(self, linenumber):
        if (
            self._protocol.flags.get("resend_swallow_repetitions", False)
            and self._protocol.flags.get("resend_swallow_repetitions_counter", 0)
            and linenumber == self._protocol.flags["resend_requested"]
            and self._protocol.flags["resend_swallow_repetitions_counter"] > 0
        ):
            self.logger.debug(
                "Ignoring resend request for line {}, that is "
                "probably a repetition sent by the firmware to "
                "ensure it arrives, not a real request".format(linenumber)
            )
            self._protocol.flags["resend_swallow_repetitions_counter"] -= 1
            return True

        self._protocol.flags[
            "resend_swallow_repetitions_counter"
        ] = self.identical_resends_countdown
