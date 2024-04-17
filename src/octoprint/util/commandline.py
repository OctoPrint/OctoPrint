__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import queue
import re
import time
import warnings
from typing import List, Optional, Tuple, Union

import sarge

from octoprint.util import to_bytes, to_unicode
from octoprint.util.platform import CLOSE_FDS

# These regexes are based on the colorama package
# Author: Jonathan Hartley
# License: BSD-3 (https://github.com/tartley/colorama/blob/master/LICENSE.txt)
# Website: https://github.com/tartley/colorama/
_ANSI_CSI_PATTERN = (
    "\001?\033\\[(\\??(?:\\d|;)*)([a-zA-Z])\002?"  # Control Sequence Introducer
)
_ANSI_OSC_PATTERN = "\001?\033\\]((?:.|;)*?)(\x07)\002?"  # Operating System Command
_ANSI_PATTERN = "|".join([_ANSI_CSI_PATTERN, _ANSI_OSC_PATTERN])

_ANSI_REGEX = re.compile(_ANSI_PATTERN)


def clean_ansi(line: Union[str, bytes]) -> Union[str, bytes]:
    """
    Removes ANSI control codes from ``line``.

    Note: This function also still supports an input of ``bytes``, leading to an
    ``output`` of ``bytes``. This if for reasons of backwards compatibility only,
    should no longer be used and considered to be deprecated and to be removed in
    a future version of OctoPrint. A warning will be logged.

    Parameters:
        line (str or bytes): the line to process

    Returns:
        (str or bytes) The line without any ANSI control codes

    .. versionchanged:: 1.8.0

       Usage as ``clean_ansi(line: bytes) -> bytes`` is now deprecated and will be removed
       in a future version of OctoPrint.
    """
    # TODO: bytes support is deprecated, remove in 2.0.0
    if isinstance(line, bytes):
        warnings.warn(
            "Calling clean_ansi with bytes is deprecated, call with str instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return to_bytes(_ANSI_REGEX.sub("", to_unicode(line)))
    return _ANSI_REGEX.sub("", line)


class CommandlineError(Exception):
    """
    Raised by :py:func:`~octoprint.util.commandline.CommandLineCaller.checked_call` on non zero return codes

    Arguments:
        returncode (int): the return code of the command
        stdout (str): the stdout output produced by the command
        stderr (str): the stderr output produced by the command
    """

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CommandlineCaller:
    """
    The CommandlineCaller is a utility class that allows running command line commands while logging their stdout
    and stderr via configurable callback functions.

    Callbacks are expected to have a signature matching

    .. code-block:: python

       def callback(*lines):
           do_something_with_the_passed_lines()

    The class utilizes sarge underneath.

    Example:

    .. code-block:: python

       from octoprint.util.commandline import CommandLineCaller, CommandLineError

       def log(prefix, *lines):
           for line in lines:
               print("{} {}".format(prefix, line))

       def log_stdout(*lines):
           log(">>>", *lines)

       def log_stderr(*lines):
           log("!!!", *lines)

       def log_call(*lines)
           log("---", *lines)

       caller = CommandLineCaller()
       caller.on_log_call = log_call
       caller.on_log_stdout = log_stdout
       caller.on_log_stderr = log_stderr

       try:
           caller.checked_call(["some", "command", "with", "parameters"])
       except CommandLineError as err:
           print("Command returned {}".format(err.returncode))
       else:
           print("Command finished successfully")
    """

    def __init__(self):
        self._logger = logging.getLogger(__name__)

        self.on_log_call = lambda *args, **kwargs: None
        """Callback for the called command line"""

        self.on_log_stdout = lambda *args, **kwargs: None
        """Callback for stdout output"""

        self.on_log_stderr = lambda *args, **kwargs: None
        """Callback for stderr output"""

    def checked_call(
        self, command: Union[str, List[str], Tuple[str]], **kwargs
    ) -> Tuple[int, List[str], List[str]]:
        """
        Calls a command and raises an error if it doesn't return with return code 0

        Args:
            command (list, tuple or str): command to call
            kwargs (dict): additional keyword arguments to pass to the sarge ``run`` call (note that ``_async``,
                           ``stdout`` and ``stderr`` will be overwritten)

        Returns:
            (tuple) a 3-tuple of return code, full stdout and full stderr output

        Raises:
            CommandlineError
        """
        returncode, stdout, stderr = self.call(command, **kwargs)

        if returncode != 0:
            raise CommandlineError(returncode, stdout, stderr)

        return returncode, stdout, stderr

    def call(
        self,
        command: Union[str, List[str], Tuple[str]],
        delimiter: bytes = b"\n",
        buffer_size: int = -1,
        logged: bool = True,
        output_timeout: float = 0.5,
        **kwargs,
    ) -> Tuple[Optional[int], List[str], List[str]]:
        """
        Calls a command

        Args:
            command (list, tuple or str): command to call
            kwargs (dict): additional keyword arguments to pass to the sarge ``run`` call (note that ``_async``,
                           ``stdout`` and ``stderr`` will be overwritten)

        Returns:
            (tuple) a 3-tuple of return code, full stdout and full stderr output
        """

        p = self.non_blocking_call(
            command, delimiter=delimiter, buffer_size=buffer_size, logged=logged, **kwargs
        )
        if p is None:
            return None, [], []

        all_stdout = []
        all_stderr = []

        def process_lines(lines, logger):
            if not lines:
                return []
            processed = self._preprocess_lines(
                *map(lambda x: to_unicode(x, errors="replace"), lines)
            )
            if logged:
                logger(*processed)
            return list(processed)

        def process_stdout(lines):
            return process_lines(lines, self._log_stdout)

        def process_stderr(lines):
            return process_lines(lines, self._log_stderr)

        try:
            # read lines from stdout and stderr until the process is finished
            while p.commands[0].poll() is None:
                # this won't be a busy loop, the readline calls will block up to the timeout
                all_stderr += process_stderr(p.stderr.readlines(timeout=output_timeout))
                all_stdout += process_stdout(p.stdout.readlines(timeout=output_timeout))

        finally:
            p.close()

        all_stderr += process_stderr(p.stderr.readlines())
        all_stdout += process_stdout(p.stdout.readlines())

        return p.returncode, all_stdout, all_stderr

    def non_blocking_call(
        self,
        command: Union[str, List, Tuple],
        delimiter: bytes = b"\n",
        buffer_size: int = -1,
        logged: bool = True,
        **kwargs,
    ) -> Optional[sarge.Pipeline]:
        if isinstance(command, (list, tuple)):
            joined_command = " ".join(command)
        else:
            joined_command = command
        self._logger.debug(f"Calling: {joined_command}")

        if logged:
            self.on_log_call(joined_command)

        kwargs.update(
            {
                "close_fds": CLOSE_FDS,
                "async_": True,
                "stdout": DelimiterCapture(delimiter=delimiter, buffer_size=buffer_size),
                "stderr": DelimiterCapture(delimiter=delimiter, buffer_size=buffer_size),
            }
        )

        p = sarge.run(command, **kwargs)
        while len(p.commands) == 0:
            # somewhat ugly... we can't use wait_events because
            # the events might not be all set if an exception
            # by sarge is triggered within the async process
            # thread
            time.sleep(0.01)

        # by now we should have a command, let's wait for its
        # process to have been prepared
        p.commands[0].process_ready.wait()

        if not p.commands[0].process:
            # the process might have been set to None in case of any exception
            self._logger.error(f"Error while trying to run command {joined_command}")
            return None

        return p

    def _log_stdout(self, *lines):
        self.on_log_stdout(*lines)

    def _log_stderr(self, *lines):
        self.on_log_stderr(*lines)

    def _preprocess_lines(self, *lines):
        return lines


class DelimiterCapture(sarge.Capture):
    def __init__(self, delimiter=b"\n", *args, **kwargs):
        self._delimiter = delimiter
        sarge.Capture.__init__(self, *args, **kwargs)

    def readline(self, size=-1, block=True, timeout=None):
        if not self.streams_open():
            block = False
            timeout = None
        else:
            timeout = timeout or self.timeout
        if self.current is None:
            try:
                self.current = self.buffer.get(block, timeout)
            except queue.Empty:
                self.current = b""
        while self._delimiter not in self.current:
            try:
                self.current += self.buffer.get(block, timeout)
            except queue.Empty:
                break
        if self._delimiter not in self.current:
            result = self.current
            self.current = None
        else:
            i = self.current.index(self._delimiter)
            if 0 < size < i:
                i = size - 1
            result = self.current[: i + 1]
            self.current = self.current[i + 1 :]
        return result
