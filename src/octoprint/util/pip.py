# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sarge
import sys
import logging
import re

import pkg_resources

from .commandline import CommandlineCaller

_cache = dict(version=dict(), setup=dict())

class UnknownPip(Exception):
	pass

class PipCaller(CommandlineCaller):
	process_dependency_links = pkg_resources.parse_requirements("pip>=1.5")
	no_use_wheel = pkg_resources.parse_requirements("pip==1.5.0")
	broken = pkg_resources.parse_requirements("pip>=6.0.1,<=6.0.3")

	def __init__(self, configured=None, ignore_cache=False):
		CommandlineCaller.__init__(self)
		self._logger = logging.getLogger(__name__)

		self.configured = configured
		self.refresh = False
		self.ignore_cache = ignore_cache

		self._command = None
		self._version = None
		self._version_string = None
		self._use_sudo = False
		self._use_user = False
		self._install_dir = None

		self.trigger_refresh()

		self.on_log_call = lambda *args, **kwargs: None
		self.on_log_stdout = lambda *args, **kwargs: None
		self.on_log_stderr = lambda *args, **kwargs: None

	def _reset(self):
		self._command = None
		self._version = None
		self._version_string = None
		self._use_sudo = False
		self._use_user = False
		self._install_dir = None

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
	def install_dir(self):
		return self._install_dir

	@property
	def use_sudo(self):
		return self._use_sudo

	@property
	def use_user(self):
		return self._use_user

	@property
	def available(self):
		return self._command is not None

	def trigger_refresh(self):
		self._reset()
		try:
			self._setup_pip()
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
			if self.use_user:
				arg_list.append("--user")

		command = [self._command] + list(args)
		if self._use_sudo:
			command = ["sudo"] + command
		return self.call(command)

	def _setup_pip(self):
		pip_command = self.configured

		if pip_command is not None and pip_command.startswith("sudo "):
			pip_command = pip_command[len("sudo "):]
			pip_sudo = True
		else:
			pip_sudo = False

		if pip_command is None:
			pip_command = self._autodetect_pip()

		if pip_command is None:
			return

		# Determine the pip version

		self._logger.debug("Found pip at {}, going to figure out its version".format(pip_command))

		pip_version, version_segment = self._get_pip_version(pip_command)
		if pip_version is None:
			return

		if pip_version in self.__class__.broken:
			self._logger.error("This version of pip is known to have errors that make it incompatible with how it needs to be used by OctoPrint. Please upgrade your pip version.")
			return

		self._logger.info("Version of pip at {} is {}".format(pip_command, version_segment))

		# Now figure out if pip belongs to a virtual environment and if the
		# default installation directory is writable.
		#
		# The idea is the following: If OctoPrint is installed globally,
		# the site-packages folder is probably not writable by our user.
		# However, the user site-packages folder as usable by providing the
		# --user parameter during install is. This we may not use though if
		# the provided pip belongs to a virtual env (since that hiccups hard).
		#
		# So we figure out the installation directory, check if it's writable
		# and if not if pip belongs to a virtual environment. Only if the
		# installation directory is NOT writable by us but we also don't run
		# in a virtual environment may we proceed with the --user parameter.

		ok, pip_user, pip_install_dir = self._check_pip_setup(pip_command)
		if not ok:
			self._logger.error("Pip install directory {} is not writable and is part of a virtual environment, can't use this constellation".format(pip_install_dir))
			return

		self._logger.info("pip at {} installs to {}, --user flag needed => {}".format(pip_command, pip_install_dir, "yes" if pip_user else "no"))

		self._command = pip_command
		self._version = pip_version
		self._version_string = version_segment
		self._use_sudo = pip_sudo
		self._use_user = pip_user
		self._install_dir = pip_install_dir

	def _autodetect_pip(self):
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

		return pip_command

	def _get_pip_version(self, pip_command):
		if not self.ignore_cache and pip_command in _cache["version"]:
			self._logger.debug("Using cached pip version information for {}".format(pip_command))
			return _cache["version"][pip_command]

		sarge_command = [pip_command, "--version"]
		p = sarge.run(sarge_command, stdout=sarge.Capture(), stderr=sarge.Capture())

		if p.returncode != 0:
			self._logger.warn("Error while trying to run pip --version: {}".format(p.stderr.text))
			return None, None

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

		result = pip_version, version_segment
		_cache["version"][pip_command] = result
		return result

	pip_install_dir_regex = re.compile("^\s*!!! PIP_INSTALL_DIR=(.*)\s*$", re.MULTILINE)
	pip_virtual_env_regex = re.compile("^\s*!!! PIP_VIRTUAL_ENV=(True|False)\s*$", re.MULTILINE)
	pip_writable_regex = re.compile("^\s*!!! PIP_WRITABLE=(True|False)\s*$", re.MULTILINE)

	def _check_pip_setup(self, pip_command):
		if not self.ignore_cache and pip_command in _cache["setup"]:
			self._logger.debug("Using cached pip setup information for {}".format(pip_command))
			return _cache["setup"][pip_command]

		import os
		testballoon = os.path.join(os.path.realpath(os.path.dirname(__file__)), "piptestballoon")

		sarge_command = [pip_command, "install", ".", "--verbose"]
		try:
			p = sarge.run(sarge_command,
			              stdout=sarge.Capture(),
			              stderr=sarge.Capture(),
			              cwd=testballoon)

			output = p.stdout.text
			self._logger.debug("Got output from {}: {}".format(" ".join(sarge_command), output))

			install_dir_match = self.__class__.pip_install_dir_regex.search(output)
			virtual_env_match = self.__class__.pip_virtual_env_regex.search(output)
			writable_match = self.__class__.pip_writable_regex.search(output)

			if install_dir_match and virtual_env_match and writable_match:
				install_dir = install_dir_match.group(1)
				virtual_env = virtual_env_match.group(1) == "True"
				writable = writable_match.group(1) == "True"

				result = writable or not virtual_env, not writable and not virtual_env, install_dir
				_cache["setup"][pip_command] = result
				return result

		finally:
			sarge_command = [pip_command, "uninstall", "-y", "OctoPrint-PipTestBalloon"]
			sarge.run(sarge_command, stdout=sarge.Capture(), stderr=sarge.Capture())

