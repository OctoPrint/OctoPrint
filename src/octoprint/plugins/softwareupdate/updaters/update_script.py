# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import sys
import logging

from ..exceptions import ConfigurationInvalid, UpdateError

from octoprint.util.commandline import CommandlineCaller, CommandlineError


def _get_caller(log_cb=None):
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

	caller = CommandlineCaller()
	if log_cb is not None:
		caller.on_log_call = _log_call
		caller.on_log_stdout = _log_stdout
		caller.on_log_stderr = _log_stderr
	return caller


def can_perform_update(target, check):
	import os
	script_configured = bool("update_script" in check and check["update_script"])

	folder = None
	if "update_folder" in check:
		folder = check["update_folder"]
	elif "checkout_folder" in check:
		folder = check["checkout_folder"]
	folder_configured = bool(folder and os.path.isdir(folder))

	return script_configured and folder_configured


def perform_update(target, check, target_version, log_cb=None):
	logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.update_script")

	if not can_perform_update(target, check):
		raise ConfigurationInvalid("checkout_folder and update_folder are missing for update target %s, one is needed" % target)

	update_script = check["update_script"]
	folder = check["update_folder"] if "update_folder" in check else check["checkout_folder"]
	pre_update_script = check["pre_update_script"] if "pre_update_script" in check else None
	post_update_script = check["post_update_script"] if "post_update_script" in check else None

	caller = _get_caller(log_cb=log_cb)

	### pre update

	if pre_update_script is not None:
		logger.debug("Target: %s, running pre-update script: %s" % (target, pre_update_script))
		try:
			caller.checked_call(pre_update_script, cwd=folder)
		except CommandlineError as e:
			logger.exception("Target: %s, error while executing pre update script, got returncode %r" % (target, e.returncode))

	### update

	try:
		update_command = update_script.format(python=sys.executable, folder=folder, target=target_version)
		logger.debug("Target %s, running update script: %s" % (target, update_command))

		caller.checked_call(update_command, cwd=folder)
	except CommandlineError as e:
		logger.exception("Target: %s, error while executing update script, got returncode %r" % (target, e.returncode))
		raise UpdateError("Error while executing update script for %s", (e.stdout, e.stderr))

	### post update

	if post_update_script is not None:
		logger.debug("Target: %s, running post-update script %s..." % (target, post_update_script))
		try:
			caller.checked_call(post_update_script, cwd=folder)
		except CommandlineError as e:
			logger.exception("Target: %s, error while executing post update script, got returncode %r" % (target, e.returncode))

	return "ok"
