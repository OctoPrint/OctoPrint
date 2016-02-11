# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sarge
import sys
import logging
import re


from octoprint.util import to_unicode


# These regexes are based on the colorama package
# Author: Jonathan Hartley
# License: BSD-3 (https://github.com/tartley/colorama/blob/master/LICENSE.txt)
# Website: https://github.com/tartley/colorama/
_ANSI_CSI_PATTERN = "\001?\033\[(\??(?:\d|;)*)([a-zA-Z])\002?"  # Control Sequence Introducer
_ANSI_OSC_PATTERN = "\001?\033\]((?:.|;)*?)(\x07)\002?"         # Operating System Command
_ANSI_REGEX = re.compile("|".join([_ANSI_CSI_PATTERN,
                                   _ANSI_OSC_PATTERN]))


def _clean_ansi(text):
	"""
	>>> text = "Successfully \x1b[?25linstalled a package"
	>>> _clean_ansi(text)
	'Successfully installed a package'
	>>> text = "Successfully installed\x1b[?25h a package"
	>>> _clean_ansi(text)
	'Successfully installed a package'
	>>> text = "Successfully installed a \x1b[31mpackage\x1b[39m"
	>>> _clean_ansi(text)
	'Successfully installed a package'
	"""
	return _ANSI_REGEX.sub("", text)


class UnknownPip(Exception):
	pass

class PipCaller(object):
	def __init__(self, configured=None):
		self._logger = logging.getLogger(__name__)

		self.configured = configured
		self.refresh = False

		self._command = None
		self._version = None
		self._version_string = None
		self._use_sudo = False

		self.trigger_refresh()

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
	def version_string(self):
		return self._version_string

	@property
	def use_sudo(self):
		return self._use_sudo

	@property
	def available(self):
		return self._command is not None

	def trigger_refresh(self):
		try:
			self._command, self._version, self._version_string, self._use_sudo = self._find_pip()
		except:
			self._logger.exception("Error while discovering pip command")
			self._command = None
			self._version = None
		self.refresh = False

	def execute(self, *args):
		if self.refresh:
			self.trigger_refresh()

		if self._command is None:
			raise UnknownPip()

		command = [self._command] + list(args)
		if self._use_sudo:
			command = ["sudo"] + command

		joined_command = " ".join(command)
		self._logger.debug(u"Calling: {}".format(joined_command))
		self.on_log_call(joined_command)

		p = sarge.run(command, async=True, stdout=sarge.Capture(), stderr=sarge.Capture())
		p.wait_events()

		all_stdout = []
		all_stderr = []
		try:
			while p.returncode is None:
				lines = p.stderr.readlines(timeout=0.5)
				if lines:
					lines = self._convert_lines(lines)
					self._log_stderr(*lines)
					all_stderr += lines

				lines = p.stdout.readlines(timeout=0.5)
				if lines:
					lines = self._convert_lines(lines)
					self._log_stdout(*lines)
					all_stdout += lines

				p.commands[0].poll()

		finally:
			p.close()

		lines = p.stderr.readlines()
		if lines:
			lines = map(self._convert_line, lines)
			self._log_stderr(*lines)
			all_stderr += lines

		lines = p.stdout.readlines()
		if lines:
			lines = map(self._convert_line, lines)
			self._log_stdout(*lines)
			all_stdout += lines

		return p.returncode, all_stdout, all_stderr


	def _find_pip(self):
		pip_command = self.configured

		if pip_command is not None and pip_command.startswith("sudo "):
			pip_command = pip_command[len("sudo "):]
			pip_sudo = True
		else:
			pip_sudo = False

		pip_version = None
		version_segment = None

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

			sarge_command = [pip_command, "--version"]
			if pip_sudo:
				sarge_command = ["sudo"] + sarge_command
			p = sarge.run(sarge_command, stdout=sarge.Capture(), stderr=sarge.Capture())

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

		return pip_command, pip_version, version_segment, pip_sudo

	def _log_stdout(self, *lines):
		self.on_log_stdout(*lines)

	def _log_stderr(self, *lines):
		self.on_log_stderr(*lines)

	@staticmethod
	def _convert_lines(lines):
		return map(PipCaller._convert_line, lines)

	@staticmethod
	def _convert_line(line):
		return to_unicode(_clean_ansi(line), errors="replace")
