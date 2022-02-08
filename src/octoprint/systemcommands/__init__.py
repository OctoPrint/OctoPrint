"""
This module represents OctoPrint's system and server commands.
"""

__author__ = "Johan Verrept <johan@verrept.eu>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

from octoprint.settings import settings
from octoprint.util.commandline import CommandlineCaller, CommandlineError

# singleton
_instance = None


def system_command_manager():
    global _instance
    if _instance is None:
        _instance = SystemCommandManager()
    return _instance


class SystemCommandManager:

    SERVER_RESTART_COMMAND = "serverRestartCommand"
    SYSTEM_RESTART_COMMAND = "systemRestartCommand"
    SYSTEM_SHUTDOWN_COMMAND = "systemShutdownCommand"

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._caller = CommandlineCaller()

    def execute(self, command):
        if not command:
            return False

        try:
            # we run this with shell=True since we have to trust whatever
            # our admin configured as command and since we want to allow
            # shell-alike handling here...
            p = self._caller.non_blocking_call(command, shell=True)

            if p is None:
                raise CommandlineError(None, "", "")

            if p.returncode is not None:
                stdout = p.stdout.text if p is not None and p.stdout is not None else ""
                stderr = p.stderr.text if p is not None and p.stderr is not None else ""
                raise CommandlineError(p.returncode, stdout, stderr)
        except CommandlineError:
            raise
        except Exception:
            self._logger.exception(f"Error while executing command: {command}")
            raise CommandlineError(None, "", "")

        return True

    def get_command(self, cmd):
        return settings().get(["server", "commands", cmd])

    def has_command(self, cmd):
        return self.get_command(cmd) is not None

    def get_server_restart_command(self):
        return self.get_command(self.SERVER_RESTART_COMMAND)

    def get_system_restart_command(self):
        return self.get_command(self.SYSTEM_RESTART_COMMAND)

    def get_system_shutdown_command(self):
        return self.get_command(self.SYSTEM_SHUTDOWN_COMMAND)

    def has_server_restart_command(self):
        return self.get_server_restart_command() is not None

    def has_system_restart_command(self):
        return self.get_system_restart_command() is not None

    def has_system_shutdown_command(self):
        return self.get_system_shutdown_command() is not None

    def perform_server_restart(self):
        return self.execute(self.get_server_restart_command())

    def perform_system_restart(self):
        return self.execute(self.get_system_restart_command())

    def perform_system_shutdown(self):
        return self.execute(self.get_system_shutdown_command())
