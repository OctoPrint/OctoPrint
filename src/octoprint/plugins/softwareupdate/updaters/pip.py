# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import sarge
import sys

logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.pip")
console_logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.pip.console")

def can_perform_update(target, check):
	return "pip" in check

def perform_update(target, check, target_version):
	pip_command = None
	if "pip_command" in check:
		pip_command = check["pip_command"]

	install_arg = check["pip"].format(target_version=target_version)

	logger.debug("Target: %s, executing pip install %s" % (target, install_arg))
	pip_args = ["install", check["pip"].format(target_version=target_version, target=target_version)]

	if "dependency_links" in check and check["dependency_links"]:
		pip_args += ["--process-dependency-links"]

	_call_pip(pip_args, pip_command=pip_command)

	logger.debug("Target. %s, executing pip install %s --ignore-reinstalled --force-reinstall --no-deps" % (target, install_arg))
	pip_args += ["--ignore-installed", "--force-reinstall", "--no-deps"]
	_call_pip(pip_args, pip_command=pip_command)

	return "ok"

def _call_pip(args, pip_command=None):
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
			raise RuntimeError(u"No pip path configured and {pip_command} does not exist or is not executable, can't install".format(**locals()))

	command = [pip_command] + args

	logger.debug(u"Calling: {}".format(" ".join(command)))

	p = sarge.run(" ".join(command), shell=True, async=True, stdout=sarge.Capture(), stderr=sarge.Capture())
	p.wait_events()

	all_stdout = []
	all_stderr = []
	try:
		while p.returncode is None:
			line = p.stderr.readline(timeout=0.5)
			if line:
				_log_stderr(line)
				all_stderr.append(line)

			line = p.stdout.readline(timeout=0.5)
			if line:
				_log_stdout(line)
				all_stdout.append(line)

			p.commands[0].poll()

	finally:
		p.close()

	stderr = p.stderr.text
	if stderr:
		split_lines = stderr.split("\n")
		_log_stderr(*split_lines)
		all_stderr += split_lines

	stdout = p.stdout.text
	if stdout:
		split_lines = stdout.split("\n")
		_log_stdout(*split_lines)
		all_stdout += split_lines

	return p.returncode, all_stdout, all_stderr

def _log_stdout(*lines):
	_log(lines, prefix=">", stream="stdout")

def _log_stderr(*lines):
	_log(lines, prefix="!", stream="stderr")

def _log(lines, prefix=None, stream=None, strip=True):
	if strip:
		lines = map(lambda x: x.strip(), lines)
	for line in lines:
		console_logger.debug(u"{prefix} {line}".format(**locals()))

