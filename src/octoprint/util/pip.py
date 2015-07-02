# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sarge
import sys
import logging


from octoprint.util import to_unicode


class UnknownPip(Exception):
	pass

class PipCaller(object):
	def __init__(self, configured=None):
		self._logger = logging.getLogger(__name__)

		self._configured = configured

		self._command = None
		self._version = None

		self._command, self._version = self._find_pip()

		self.refresh = False
		self.on_log_call = lambda *args, **kwargs: None
		self.on_log_stdout = lambda *args, **kwargs: None
		self.on_log_stderr = lambda *args, **kwargs: None

	def __le__(self, other):
		return self.version is not None and self.version <= other

	def __lt__(self, other):
		return self.version is not None and self.version < other

	def __ge__(self, other):
		return self.version is not None and self.version >= other

	def __gt__(self, other):
		return self.version is not None and self.version > other

	@property
	def command(self):
		return self._command

	@property
	def version(self):
		return self._version

	@property
	def available(self):
		return self._command is not None

	def execute(self, *args):
		if self.refresh:
			self._command, self._version = self._find_pip()
			self.refresh = False

		if self._command is None:
			raise UnknownPip()

		command = [self._command] + list(args)

		joined_command = " ".join(command)
		self._logger.debug(u"Calling: {}".format(joined_command))
		self.on_log_call(joined_command)

		p = sarge.run(command, async=True, stdout=sarge.Capture(), stderr=sarge.Capture())
		p.wait_events()

		all_stdout = []
		all_stderr = []
		try:
			while p.returncode is None:
				line = p.stderr.readline(timeout=0.5)
				if line:
					line = to_unicode(line, errors="replace")
					self._log_stderr(line)
					all_stderr.append(line)

				line = p.stdout.readline(timeout=0.5)
				if line:
					line = to_unicode(line, errors="replace")
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


	def _find_pip(self):
		pip_command = self._configured
		pip_version = None

		if pip_command is None:
			import os
			python_command = sys.executable
			binary_dir = os.path.dirname(python_command)

			pip_command = os.path.join(binary_dir, "pip")
			if sys.platform == "win32":
				# Windows is a bit special... first of all the file will be called pip.exe, not just pip, and secondly
				# for a non-virtualenv install (e.g. global install) the pip binary will not be located in the
				# same folder as python.exe, but in a subfolder Scripts, e.g.
				#
				# C:\Python2.7\
				#  |- python.exe
				#  `- Scripts
				#      `- pip.exe

				# virtual env?
				pip_command = os.path.join(binary_dir, "pip.exe")

				if not os.path.isfile(pip_command):
					# nope, let's try the Scripts folder then
					scripts_dir = os.path.join(binary_dir, "Scripts")
					if os.path.isdir(scripts_dir):
						pip_command = os.path.join(scripts_dir, "pip.exe")

			if not os.path.isfile(pip_command) or not os.access(pip_command, os.X_OK):
				pip_command = None

		if pip_command is not None:
			self._logger.debug("Found pip at {}, going to figure out its version".format(pip_command))
			p = sarge.run([pip_command, "--version"], stdout=sarge.Capture(), stderr=sarge.Capture())

			if p.returncode != 0:
				self._logger.warn("Error while trying to run pip --version: {}".format(p.stderr.text))
				pip_command = None

			output = p.stdout.text
			# output should look something like this:
			#
			#     pip <version> from <path> (<python version>)
			#
			# we'll just split on whitespace and then try to use the second entry

			if not output.startswith("pip"):
				self._logger.warn("pip command returned unparseable output, can't determine version: {}".format(output))

			split_output = map(lambda x: x.strip(), output.split())
			if len(split_output) < 2:
				self._logger.warn("pip command returned unparseable output, can't determine version: {}".format(output))

			version_segment = split_output[1]

			from pkg_resources import parse_version
			try:
				pip_version = parse_version(version_segment)
			except:
				self._logger.exception("Error while trying to parse version string from pip command")
			else:
				self._logger.info("Found pip at {}, version is {}".format(pip_command, version_segment))

		return pip_command, pip_version

	def _log_stdout(self, *lines):
		self.on_log_stdout(*lines)

	def _log_stderr(self, *lines):
		self.on_log_stderr(*lines)
