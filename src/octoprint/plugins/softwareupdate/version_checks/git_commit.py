# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import errno
import subprocess
import sys
import logging

from ..exceptions import ConfigurationInvalid

def _get_git_executables():
	GITS = ["git"]
	if sys.platform == "win32":
		GITS = ["git.cmd", "git.exe"]
	return GITS


def _git(args, cwd, hide_stderr=False):
	commands = _get_git_executables()

	for c in commands:
		try:
			p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
			                     stderr=(subprocess.PIPE if hide_stderr
			                             else None))
			break
		except EnvironmentError:
			e = sys.exc_info()[1]
			if e.errno == errno.ENOENT:
				continue
			return None, None
	else:
		return None, None

	stdout = p.communicate()[0].strip()
	if sys.version >= '3':
		stdout = stdout.decode()

	if p.returncode != 0:
		return p.returncode, None

	return p.returncode, stdout


def get_latest(target, check):
	if not "checkout_folder" in check:
		raise ConfigurationInvalid("Update configuration for %s needs checkout_folder" % target)

	checkout_folder = check["checkout_folder"]

	returncode, _ = _git(["fetch"], checkout_folder)
	if returncode != 0:
		return None, True

	returncode, local_commit = _git(["rev-parse", "@{0}"], checkout_folder)
	if returncode != 0:
		return None, True

	returncode, remote_commit = _git(["rev-parse", "@{u}"], checkout_folder)
	if returncode != 0:
		return None, True

	returncode, base = _git(["merge-base", "@{0}", "@{u}"], checkout_folder)
	if returncode != 0:
		return None, True

	if local_commit == remote_commit or remote_commit == base:
		information = dict(
			local=dict(name="Commit %s" % local_commit, value=local_commit),
			remote=dict(name="Commit %s" % local_commit, value=local_commit)
		)
		is_current = True
	else:
		information = dict(
			local=dict(name="Commit %s" % local_commit, value=local_commit),
			remote=dict(name="Commit %s" % remote_commit, value=remote_commit)
		)
		is_current = local_commit == remote_commit

	logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.git_commit")
	logger.debug("Target: %s, local: %s, remote: %s" % (target, local_commit, remote_commit))

	return information, is_current