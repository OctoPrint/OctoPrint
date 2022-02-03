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


def systemcommands():
    global _instance
    if _instance is None:
        _instance = SystemCommands()
    return _instance


class SystemCommands:

    SERVER_RESTART_COMMAND = "serverRestartCommand"
    SYSTEM_RESTART_COMMAND = "systemRestartCommand"
    SYSTEM_SHUTDOWN_COMMAND = "systemShutdownCommand"

    def _execute(self, cmd):
        command = settings().get(["server", "commands", cmd])

        if not command:
            return False

        try:
            sarge.run(
                command,
                close_fds=CLOSE_FDS,
                shell=True,
                async_=True,
            )

            return True
        except Exception:
            logging.getLogger(__name__).exception("Error while executing system command")

        return False

    def server_restart(self):
        return self._execute(self.SERVER_RESTART_COMMAND)

    def system_restart(self):
        return self._execute(self.SYSTEM_RESTART_COMMAND)

    def system_shutdown(self):
        return self._execute(self.SYSTEM_SHUTDOWN_COMMAND)
