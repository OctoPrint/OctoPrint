# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import sarge
import sys
import logging
import site
import threading

import pkg_resources

from .commandline import CommandlineCaller, clean_ansi
from octoprint.util import to_unicode

_cache = dict(version=dict(), setup=dict())
_cache_mutex = threading.RLock()

class UnknownPip(Exception):
	pass

class PipCaller(CommandlineCaller):
	process_dependency_links = pkg_resources.Requirement.parse("pip>=1.5")
	no_use_wheel = pkg_resources.Requirement.parse("pip==1.5.0")
	broken = pkg_resources.Requirement.parse("pip>=6.0.1,<=6.0.3")

	@classmethod
	def clean_install_command(cls, args, pip_version, virtual_env, use_user, force_user):
		logger = logging.getLogger(__name__)
		args = list(args)

		# strip --process-dependency-links for versions that don't support it
		if not pip_version in cls.process_dependency_links and "--process-dependency-links" in args:
			logger.debug(
				"Found --process-dependency-links flag, version {} doesn't need that yet though, removing.".format(
					pip_version))
			args.remove("--process-dependency-links")

		# add --no-use-wheel for versions that otherwise break
		if pip_version in cls.no_use_wheel and not "--no-use-wheel" in args:
			logger.debug("Version {} needs --no-use-wheel to properly work.".format(pip_version))
			args.append("--no-use-wheel")

		# remove --user if it's present and a virtual env is detected
		if "--user" in args:
			if virtual_env or not site.ENABLE_USER_SITE:
				logger.debug("Virtual environment detected, removing --user flag.")
				args.remove("--user")
		# otherwise add it if necessary
		elif not virtual_env and site.ENABLE_USER_SITE and (use_user or force_user):
			logger.debug("pip needs --user flag for installations.")
			args.append("--user")

		return args

	def __init__(self, configured=None, ignore_cache=False, force_sudo=False,
	             force_user=False):
		CommandlineCaller.__init__(self)
		self._logger = logging.getLogger(__name__)

		self.configured = configured
		self.refresh = False
		self.ignore_cache = ignore_cache

		self.force_sudo = force_sudo
		self.force_user = force_user

		self._command = None
		self._version = None
		self._version_string = None
		self._use_sudo = False
		self._use_user = False
		self._virtual_env = False
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
	def virtual_env(self):
		return self._virtual_env

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

	def execute(self, *args, **kwargs):
		if self.refresh:
			self.trigger_refresh()

		if self._command is None:
			raise UnknownPip()

		arg_list = list(args)

		if "install" in arg_list:
			arg_list = self.clean_install_command(arg_list, self.version, self._virtual_env, self.use_user,
			                                      self.force_user)

		# add args to command
		if isinstance(self._command, list):
			command = self._command + list(arg_list)
		else:
			command = [self._command] + list(arg_list)

		# add sudo if necessary
		if self._use_sudo or self.force_sudo:
			command = ["sudo"] + command

		return self.call(command, **kwargs)

	def _setup_pip(self):
		pip_command, pip_sudo = self._get_pip_command()
		if pip_command is None:
			return

		# Determine the pip version

		self._logger.debug("Going to figure out pip's version")

		pip_version, version_segment = self._get_pip_version(pip_command)
		if pip_version is None:
			return

		if pip_version in self.__class__.broken:
			self._logger.error("This version of pip is known to have bugs that make it incompatible with how it needs to be used by OctoPrint. Please upgrade your pip version.")
			return

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

		ok, pip_user, pip_virtual_env, pip_install_dir = self._check_pip_setup(pip_command)
		if not ok:
			self._logger.error("Cannot use pip")
			return

		self._command = pip_command
		self._version = pip_version
		self._version_string = version_segment
		self._use_sudo = pip_sudo
		self._use_user = pip_user
		self._virtual_env = pip_virtual_env
		self._install_dir = pip_install_dir

	def _get_pip_command(self):
		pip_command = self.configured

		if pip_command is not None and pip_command.startswith("sudo "):
			pip_command = pip_command[len("sudo "):]
			pip_sudo = True
		else:
			pip_sudo = False

		if pip_command is None:
			pip_command = self.autodetect_pip()

		return pip_command, pip_sudo

	@classmethod
	def autodetect_pip(cls):
		commands = [[sys.executable, "-m", "pip"],
		            [sys.executable, "-c", "import sys; sys.argv = ['pip'] + sys.argv[1:]; import pip; pip.main()"]]

		for command in commands:
			p = sarge.run(command + ["--version"], stdout=sarge.Capture(), stderr=sarge.Capture())
			if p.returncode == 0:
				logging.getLogger(__name__).info("Using \"{}\" as command to invoke pip".format(" ".join(command)))
				return command

		return None

	@classmethod
	def to_sarge_command(cls, pip_command, *args):
		if isinstance(pip_command, list):
			sarge_command = pip_command
		else:
			sarge_command = [pip_command]
		return sarge_command + list(args)

	def _get_pip_version(self, pip_command):
		# Debugging this with PyCharm/IntelliJ with Python plugin and no output is being
		# generated? PyCharm bug. Disable "Attach to subprocess automatically when debugging"
		# in IDE Settings or patch pydevd.py
		# -> https://youtrack.jetbrains.com/issue/PY-18365#comment=27-1290453

		pip_command_str = pip_command
		if isinstance(pip_command_str, list):
			pip_command_str = " ".join(pip_command_str)

		with _cache_mutex:
			if not self.ignore_cache and pip_command_str in _cache["version"]:
				self._logger.debug("Using cached pip version information for {}".format(pip_command_str))
				return _cache["version"][pip_command_str]

			sarge_command = self.to_sarge_command(pip_command, "--version")
			p = sarge.run(sarge_command, stdout=sarge.Capture(), stderr=sarge.Capture())

			if p.returncode != 0:
				self._logger.warn("Error while trying to run pip --version: {}".format(p.stderr.text))
				return None, None

			output = PipCaller._preprocess(p.stdout.text)
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

			self._logger.info("Version of pip is {}".format(version_segment))

			result = pip_version, version_segment
			_cache["version"][pip_command_str] = result
			return result

	def _check_pip_setup(self, pip_command):
		pip_command_str = pip_command
		if isinstance(pip_command_str, list):
			pip_command_str = " ".join(pip_command_str)

		with _cache_mutex:
			if not self.ignore_cache and pip_command_str in _cache["setup"]:
				self._logger.debug("Using cached pip setup information for {}".format(pip_command_str))
				return _cache["setup"][pip_command_str]

			# This is horribly ugly and I'm sorry...
			#
			# While we can figure out the install directory, if that's writable and if a virtual environment
			# is active for pip that belongs to our sys.executable python instance by just checking some
			# variables, we can't for stuff like third party software we allow to update via the software
			# update plugin.
			#
			# What we do instead for these situations is try to install (and of course uninstall) the
			# testballoon dummy package, which collects that information for us. For pip <= 7 we could
			# have the testballoon provide us with the info needed through stdout, if pip was called
			# with --verbose anything printed to stdout within setup.py would be output. Pip 8 managed
			# to break this mechanism. Any (!) output within setup.py appears to be suppressed now, and
			# no combination of --log and multiple --verbose or -v arguments could get it to bring the
			# output back.
			#
			# So here's what we do now instead. Our sarge call sets an environment variable
			# "TESTBALLOON_OUTPUT" that points to a temporary file. If the testballoon sees that
			# variable set, it opens the file and writes to it the output it so far printed on stdout.
			# We then open the file and read in the data that way.
			#
			# Yeah, I'm not happy with that either. But as long as there's no way to otherwise figure
			# out for a generic pip command whether OctoPrint can even install anything with that
			# and if so how, well, that's how we'll have to do things.

			import os
			testballoon = os.path.join(os.path.realpath(os.path.dirname(__file__)), "piptestballoon")

			from octoprint.util import temppath
			with temppath() as testballoon_output_file:
				sarge_command = self.to_sarge_command(pip_command, "install", ".")
				try:
					# our testballoon is no real package, so this command will fail - that's ok though,
					# we only need the output produced within the pip environment
					sarge.run(sarge_command,
					          stdout=sarge.Capture(),
					          stderr=sarge.Capture(),
					          cwd=testballoon,
					          env=dict(TESTBALLOON_OUTPUT=testballoon_output_file))
				except:
					self._logger.exception("Error while trying to install testballoon to figure out pip setup")
					return False, False, False, None

				data = dict()
				with open(testballoon_output_file) as f:
					for line in f:
						key, value = line.split("=", 2)
						data[key] = value

			install_dir_str = data.get("PIP_INSTALL_DIR", None)
			virtual_env_str = data.get("PIP_VIRTUAL_ENV", None)
			writable_str = data.get("PIP_WRITABLE", None)

			if install_dir_str is not None and virtual_env_str is not None and writable_str is not None:
				install_dir = install_dir_str.strip()
				virtual_env = virtual_env_str.strip() == "True"
				writable = writable_str.strip() == "True"

				can_use_user_flag = not virtual_env and site.ENABLE_USER_SITE

				ok = writable or can_use_user_flag
				user_flag = not writable and can_use_user_flag

				self._logger.info("pip installs to {}, --user flag needed => {}, "
				                  "virtual env => {}".format(install_dir,
				                                             "yes" if user_flag else "no",
				                                             "yes" if virtual_env else "no"))

				# ok, enable user flag, virtual env yes/no, installation dir
				result = ok, user_flag, virtual_env, install_dir
				_cache["setup"][pip_command_str] = result
				return result
			else:
				self._logger.debug("Could not detect desired output from testballoon install, got this instead: {!r}".format(data))
				return False, False, False, None

	def _preprocess_lines(self, *lines):
		return map(self._preprocess, lines)

	@staticmethod
	def _preprocess(text):
		"""
		Strips ANSI and VT100 cursor control characters from line and makes sure it's a unicode.

		Parameters:
		    text (str or unicode): The text to process

		Returns:
		    (unicode) The processed text as a unicode, stripped of ANSI and VT100 cursor show/hide codes

		Example::

		    >>> text = b'some text with some\x1b[?25h ANSI codes for \x1b[31mred words\x1b[39m and\x1b[?25l also some cursor control codes'
		    >>> PipCaller._preprocess(text)
		    u'some text with some ANSI codes for red words and also some cursor control codes'
		"""
		return to_unicode(clean_ansi(text))

class LocalPipCaller(PipCaller):
	"""
	The LocalPipCaller always uses the pip instance associated with
	sys.executable.
	"""

	def _get_pip_command(self):
		return self.autodetect_pip(), False

	def _check_pip_setup(self, pip_command):
		import sys
		import os
		from distutils.sysconfig import get_python_lib

		virtual_env = hasattr(sys, "real_prefix")
		install_dir = get_python_lib()
		writable = os.access(install_dir, os.W_OK)

		can_use_user_flag = not virtual_env and site.ENABLE_USER_SITE

		return writable or can_use_user_flag, \
		       not writable and can_use_user_flag, \
		       virtual_env, \
		       install_dir
