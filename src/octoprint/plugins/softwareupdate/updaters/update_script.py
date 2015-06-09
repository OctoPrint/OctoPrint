# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import sys
import logging

from ..exceptions import ScriptError, ConfigurationInvalid, UpdateError
from ..util import execute


def can_perform_update(target, check):
	return "update_script" in check and ("checkout_folder" in check or "update_folder" in check)


def perform_update(target, check, target_version):
	logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.update_script")

	if not can_perform_update(target, check):
		raise ConfigurationInvalid("checkout_folder and update_folder are missing for update target %s, one is needed" % target)

	update_script = check["update_script"]
	folder = check["update_folder"] if "update_folder" in check else check["checkout_folder"]
	pre_update_script = check["pre_update_script"] if "pre_update_script" in check else None
	post_update_script = check["post_update_script"] if "post_update_script" in check else None

	update_stdout = ""
	update_stderr = ""

	### pre update

	if pre_update_script is not None:
		logger.debug("Target: %s, running pre-update script: %s" % (target, pre_update_script))
		try:
			returncode, stdout, stderr = execute(pre_update_script, cwd=folder)
			update_stdout += stdout
			update_stderr += stderr
		except ScriptError as e:
			logger.exception("Target: %s, error while executing pre update script, got returncode %r" % (target, e.returncode))
			logger.warn("Target: %s, pre-update stdout:\n%s" % (target, e.stdout))
			logger.warn("Target: %s, pre-update stderr:\n%s" % (target, e.stderr))

	### update

	try:
		update_command = update_script.format(python=sys.executable, folder=folder, target=target_version)

		logger.debug("Target %s, running update script: %s" % (target, update_command))
		returncode, stdout, stderr = execute(update_command, cwd=folder)
		update_stdout += stdout
		update_stderr += stderr
	except ScriptError as e:
		logger.exception("Target: %s, error while executing update script, got returncode %r" % (target, e.returncode))
		logger.warn("Target: %s, update stdout:\n%s" % (target, e.stdout))
		logger.warn("Target: %s, update stderr:\n%s" % (target, e.stderr))
		raise UpdateError("Error while executing update script for %s", (e.stdout, e.stderr))

	### post update

	if post_update_script is not None:
		logger.debug("Target: %s, running post-update script %s..." % (target, post_update_script))
		try:
			returncode, stdout, stderr = execute(post_update_script, cwd=folder)
			update_stdout += stdout
			update_stderr += stderr
		except ScriptError as e:
			logger.exception("Target: %s, error while executing post update script, got returncode %r" % (target, e.returncode))
			logger.warn("Target: %s, post-update stdout:\n%s" % (target, e.stdout))
			logger.warn("Target: %s, post-update stderr:\n%s" % (target, e.stderr))

	logger.debug("Target: %s, update stdout:\n%s" % (target, update_stdout))
	logger.debug("Target: %s, update stderr:\n%s" % (target, update_stderr))

	### result

	return update_stdout, update_stderr
