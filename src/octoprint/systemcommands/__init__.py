"""
This module represents OctoPrint's system and server commands.
"""

__author__ = "Johan Verrept <johan@verrept.eu>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

import sarge

from octoprint.settings import settings
from octoprint.util.platform import CLOSE_FDS

# singleton
_instance = None


def systemcommands(init=False):
    global _instance
    if _instance is not None:
        if init:
            raise ValueError("SystemCommands is already initialized")
    else:
        if init:
            _instance = SystemCommands()

    return _instance


class SystemCommands:

    SERVER_RESTART_COMMAND = "serverRestartCommand"
    SYSTEM_RESTART_COMMAND = "systemRestartCommand"
    SYSTEM_SHUTDOWN_COMMAND = "systemShutdownCommand"

    def __call(self, command):
        if not command:
            return

        try:
            sarge.run(
                command,
                close_fds=CLOSE_FDS,
                stdout=sarge.Capture(),
                stderr=sarge.Capture(),
                shell=True,
            )
        except Exception:
            logging.getLogger(__name__).exception("Error while executing system command")

    def __getcmd(self, cmd):
        return settings().get(["server", "commands", cmd])

    def server_restart(self):
        self.__call(self.__getcmd(self.SERVER_RESTART_COMMAND))

    def system_restart(self):
        self.__call(self.__getcmd(self.SYSTEM_RESTART_COMMAND))

    def system_shutdown(self):
        self.__call(self.__getcmd(self.SYSTEM_SHUTDOWN_COMMAND))
