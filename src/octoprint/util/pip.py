# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sarge
import sys
import logging

import pkg_resources

from .commandline import CommandlineCaller


class UnknownPip(Exception):
	pass

class PipCaller(CommandlineCaller):
	process_dependency_links = pkg_resources.parse_requirements("pip>=1.5")
	no_use_wheel = pkg_resources.parse_requirements("pip==1.5.0")
	broken = pkg_resources.parse_requirements("pip>=6.0.1,<=6.0.3")

	def __init__(self, configured=None):
		CommandlineCaller.__init__(self)
		self._logger = logging.getLogger(__name__)

		self.configured = configured
		self.refresh = False

		self._command = None
		self._version = None
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
	def use_sudo(self):
		return self._use_sudo

	@property
	def available(self):
		return self._command is not None

	def trigger_refresh(self):
		try:
			self._command, self._version, self._use_sudo = self._find_pip()
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

		arg_list = list(args)
		if "install" in arg_list:
			if not self.version in self.__class__.process_dependency_links and "--process-dependency-links" in arg_list:
				self._logger.debug("Found --process-dependency-links flag, version {} doesn't need that yet though, removing.".format(self.version))
				arg_list.remove("--process-dependency-links")
			if self.version in self.__class__.no_use_wheel and not "--no-use-wheel" in arg_list:
				self._logger.debug("Version {} needs --no-use-wheel to properly work.".format(self.version))
				arg_list.append("--no-use-wheel")

		command = [self._command] + list(args)
		if self._use_sudo:
			command = ["sudo"] + command
		return self.call(command)

	def _find_pip(self):
		pip_command = self.configured
		if pip_command is not None and pip_command.startswith("sudo "):
			pip_command = pip_command[len("sudo "):]
			pip_sudo = True
		else:
			pip_sudo = False
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

			try:
				pip_version = pkg_resources.parse_version(version_segment)
			except:
				self._logger.exception("Error while trying to parse version string from pip command")
				return None, None
			else:
				self._logger.info("Found pip at {}, version is {}".format(pip_command, version_segment))

			if pip_version in self.__class__.broken:
				self._logger.error("This version of pip is known to have errors that make it incompatible with how it needs to be used by OctoPrint. Please upgrade your pip version.")
				return None, None, False

		return pip_command, pip_version, pip_sudo
