# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import pkg_resources

from octoprint.util.pip import PipCaller, UnknownPip
from .. import exceptions

logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.pip")
console_logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.pip.console")

_ALREADY_INSTALLED = "Requirement already satisfied (use --upgrade to upgrade)"

_pip_callers = dict()
_pip_version_dependency_links = pkg_resources.parse_version("1.5")

def can_perform_update(target, check, online=True):
	pip_caller = _get_pip_caller(command=check["pip_command"] if "pip_command" in check else None)
	return "pip" in check and pip_caller is not None and pip_caller.available and (online or check.get("offline", False))

def _get_pip_caller(command=None):
	key = command
	if command is None:
		key = "__default"

	if not key in _pip_callers:
		try:
			_pip_callers[key] = PipCaller(configured=command)
		except UnknownPip:
			_pip_callers[key] = None

	return _pip_callers[key]

def perform_update(target, check, target_version, log_cb=None, online=True, force=False):
	pip_command = None
	if "pip_command" in check:
		pip_command = check["pip_command"]

	if not online and not check.get("offline", False):
		raise exceptions.CannotUpdateOffline()

	pip_caller = _get_pip_caller(command=pip_command)
	if pip_caller is None:
		raise exceptions.UpdateError("Can't run pip", None)

	def _log_call(*lines):
		_log(lines, prefix=" ", stream="call")

	def _log_stdout(*lines):
		_log(lines, prefix=">", stream="stdout")

	def _log_stderr(*lines):
		_log(lines, prefix="!", stream="stderr")

	def _log(lines, prefix=None, stream=None):
		if log_cb is None:
			return
		log_cb(lines, prefix=prefix, stream=stream)

	if log_cb is not None:
		pip_caller.on_log_call = _log_call
		pip_caller.on_log_stdout = _log_stdout
		pip_caller.on_log_stderr = _log_stderr

	install_arg = check["pip"].format(target_version=target_version, target=target_version)

	logger.debug(u"Target: %s, executing pip install %s" % (target, install_arg))
	pip_args = ["install", install_arg]

	if "dependency_links" in check and check["dependency_links"]:
		pip_args += ["--process-dependency-links"]

	returncode, stdout, stderr = pip_caller.execute(*pip_args)
	if returncode != 0:
		raise exceptions.UpdateError("Error while executing pip install", (stdout, stderr))
	
	if not force and any(map(lambda x: x.strip().startswith(_ALREADY_INSTALLED) and (install_arg in x or install_arg in x.lower()), stdout)):
		logger.debug(u"Looks like we were already installed in this version. Forcing a reinstall.")
		force = True

	if force:
		logger.debug(u"Target: %s, executing pip install %s --ignore-reinstalled --force-reinstall --no-deps" % (target, install_arg))
		pip_args += ["--ignore-installed", "--force-reinstall", "--no-deps"]
	
		returncode, stdout, stderr = pip_caller.execute(*pip_args)
		if returncode != 0:
			raise exceptions.UpdateError("Error while executing pip install --force-reinstall", (stdout, stderr))

	return "ok"
