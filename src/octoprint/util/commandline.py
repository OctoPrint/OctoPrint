# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sarge
import logging


class CommandlineError(Exception):
	def __init__(self, returncode, stdout, stderr):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr


class CommandlineCaller(object):

	def __init__(self):
		self._logger = logging.getLogger(__name__)

		self.on_log_call = lambda *args, **kwargs: None
		self.on_log_stdout = lambda *args, **kwargs: None
		self.on_log_stderr = lambda *args, **kwargs: None

	def checked_call(self, command, **kwargs):
		returncode, stdout, stderr = self.call(command, **kwargs)

		if returncode != 0:
			raise CommandlineError(returncode, stdout, stderr)

		return returncode, stdout, stderr

	def call(self, command, **kwargs):
		if isinstance(command, (list, tuple)):
			joined_command = " ".join(command)
		else:
			joined_command = command
		self._logger.debug(u"Calling: {}".format(joined_command))
		self.on_log_call(joined_command)

		kwargs.update(dict(async=True, stdout=sarge.Capture(), stderr=sarge.Capture()))

		p = sarge.run(command, **kwargs)
		p.wait_events()

		all_stdout = []
		all_stderr = []
		try:
			while p.returncode is None:
				line = p.stderr.readline(timeout=0.5)
				if line:
					self._log_stderr(line)
					all_stderr.append(line)

				line = p.stdout.readline(timeout=0.5)
				if line:
					self._log_stdout(line)
					all_stdout.append(line)

				p.commands[0].poll()

		finally:
			p.close()

		stderr = p.stderr.text
		if stderr:
			split_lines = stderr.split("\n")
			self._log_stderr(*split_lines)
			all_stderr += split_lines

		stdout = p.stdout.text
		if stdout:
			split_lines = stdout.split("\n")
			self._log_stdout(*split_lines)
			all_stdout += split_lines

		return p.returncode, all_stdout, all_stderr

	def _log_stdout(self, *lines):
		self.on_log_stdout(*lines)

	def _log_stderr(self, *lines):
		self.on_log_stderr(*lines)
