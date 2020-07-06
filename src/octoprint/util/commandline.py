# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sarge
import logging
import re
import time

from . import to_unicode, to_native_str
from .platform import get_os

from past.builtins import unicode

from octoprint.util.platform import CLOSE_FDS

try:
	import queue
except ImportError:  # pragma: no cover
	import Queue as queue

# These regexes are based on the colorama package
# Author: Jonathan Hartley
# License: BSD-3 (https://github.com/tartley/colorama/blob/master/LICENSE.txt)
# Website: https://github.com/tartley/colorama/
_ANSI_CSI_PATTERN = b"\001?\033\[(\??(?:\d|;)*)([a-zA-Z])\002?"  # Control Sequence Introducer
_ANSI_OSC_PATTERN = b"\001?\033\]((?:.|;)*?)(\x07)\002?"         # Operating System Command
_ANSI_REGEX = re.compile(b"|".join([_ANSI_CSI_PATTERN,
                                    _ANSI_OSC_PATTERN]))


def clean_ansi(line):
	"""
	Removes ANSI control codes from ``line``.

	Parameters:
	    line (bytes or unicode): the line to process

	Returns:
	    (bytes or unicode) The line without any ANSI control codes

	Example::

	    >>> text = b"Some text with some \x1b[31mred words\x1b[39m in it"
	    >>> clean_ansi(text) # doctest: +ALLOW_BYTES
	    'Some text with some red words in it'
	    >>> text = b"We \x1b[?25lhide the cursor here and then \x1b[?25hshow it again here"
	    >>> clean_ansi(text) # doctest: +ALLOW_BYTES
	    'We hide the cursor here and then show it again here'
	"""
	if isinstance(line, unicode):
		return _ANSI_REGEX.sub(b"", line.encode("latin1")).decode("latin1")
	return _ANSI_REGEX.sub(b"", line)


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


class CommandlineCaller(object):
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

	def checked_call(self, command, **kwargs):
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

	def call(self, command, **kwargs):
		"""
		Calls a command

		Args:
		    command (list, tuple or str): command to call
		    kwargs (dict): additional keyword arguments to pass to the sarge ``run`` call (note that ``_async``,
		                   ``stdout`` and ``stderr`` will be overwritten)

		Returns:
		    (tuple) a 3-tuple of return code, full stdout and full stderr output
		"""

		if isinstance(command, (list, tuple)):
			joined_command = " ".join(command)
		else:
			joined_command = command
		self._logger.debug("Calling: {}".format(joined_command))
		self.on_log_call(joined_command)

		# if we are running under windows, make sure there are no unicode strings in the env
		if get_os() == "windows" and "env" in kwargs:
			kwargs["env"] = dict((k, to_native_str(v)) for k, v in kwargs["env"].items())

		delimiter = kwargs.get("delimiter", b'\n')
		try:
			kwargs.pop("delimiter")
		except KeyError:
			pass

		buffer_size = kwargs.get("buffer_size", -1)
		try:
			kwargs.pop("buffer_size")
		except KeyError:
			pass

		kwargs.update(dict(close_fds=CLOSE_FDS,
		                   async_=True,
		                   stdout=DelimiterCapture(delimiter=delimiter, buffer_size=buffer_size),
		                   stderr=DelimiterCapture(delimiter=delimiter, buffer_size=buffer_size)))

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
			self._logger.error("Error while trying to run command {}".format(joined_command))
			return None, [], []

		all_stdout = []
		all_stderr = []

		def process_lines(lines, logger):
			if not lines:
				return []
			l = self._preprocess_lines(*map(lambda x: to_unicode(x, errors="replace"), lines))
			logger(*l)
			return list(l)

		def process_stdout(lines):
			return process_lines(lines, self._log_stdout)

		def process_stderr(lines):
			return process_lines(lines, self._log_stderr)

		try:
			while p.returncode is None:
				all_stderr += process_stderr(p.stderr.readlines(timeout=0.5))
				all_stdout += process_stdout(p.stdout.readlines(timeout=0.5))
				p.commands[0].poll()

		finally:
			p.close()

		all_stderr += process_stderr(p.stderr.readlines())
		all_stdout += process_stdout(p.stdout.readlines())

		return p.returncode, all_stdout, all_stderr

	def _log_stdout(self, *lines):
		self.on_log_stdout(*lines)

	def _log_stderr(self, *lines):
		self.on_log_stderr(*lines)

	def _preprocess_lines(self, *lines):
		return lines


class DelimiterCapture(sarge.Capture):
	def __init__(self, delimiter=b'\n', *args, **kwargs):
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
				self.current = b''
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
			result = self.current[:i + 1]
			self.current = self.current[i + 1:]
		return result
