# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import pkg_resources

from octoprint.util.pip import PipCaller, UnknownPip

logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.pip")
console_logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.pip.console")

_pip_callers = dict()
_pip_version_dependency_links = pkg_resources.parse_version("1.5")

def can_perform_update(target, check):
	pip_caller = _get_pip_caller(command=check["pip_command"] if "pip_command" in check else None)
	return "pip" in check and pip_caller is not None and pip_caller.available

def _get_pip_caller(command=None):
	key = command
	if command is None:
		key = "__default"

	if not key in _pip_callers:
		try:
			_pip_callers[key] = PipCaller(configured=command)
			_pip_callers[key].on_log_call = _log_call
			_pip_callers[key].on_log_stdout = _log_stdout
			_pip_callers[key].on_log_stderr = _log_stderr
		except UnknownPip:
			_pip_callers[key] = None

	return _pip_callers[key]

def perform_update(target, check, target_version):
	pip_command = None
	if "pip_command" in check:
		pip_command = check["pip_command"]

	pip_caller = _get_pip_caller(command=pip_command)
	if pip_caller is None:
		raise RuntimeError("Can't run pip")

	install_arg = check["pip"].format(target_version=target_version)

	logger.debug(u"Target: %s, executing pip install %s" % (target, install_arg))
	pip_args = ["install", check["pip"].format(target_version=target_version, target=target_version)]

	if "dependency_links" in check and check["dependency_links"] and pip_caller >= _pip_version_dependency_links:
		pip_args += ["--process-dependency-links"]

	pip_caller.execute(*pip_args)

	logger.debug(u"Target: %s, executing pip install %s --ignore-reinstalled --force-reinstall --no-deps" % (target, install_arg))
	pip_args += ["--ignore-installed", "--force-reinstall", "--no-deps"]

	pip_caller.execute(*pip_args)

	return "ok"

def _log_call(*lines):
	_log(lines, prefix=u" ")

def _log_stdout(*lines):
	_log(lines, prefix=u">")

def _log_stderr(*lines):
	_log(lines, prefix=u"!")

def _log(lines, prefix=None):
	lines = map(lambda x: x.strip(), lines)
	for line in lines:
		console_logger.debug(u"{prefix} {line}".format(**locals()))

