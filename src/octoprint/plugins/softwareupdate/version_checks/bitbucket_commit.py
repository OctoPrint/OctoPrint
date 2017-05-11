# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import requests
import logging

from ..exceptions import ConfigurationInvalid

BRANCH_HEAD_URL = "https://api.bitbucket.org/2.0/repositories/{user}/{repo}/commit/{branch}"

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.bitbucket_commit")

def _get_latest_commit(user, repo, branch):
	r = requests.get(BRANCH_HEAD_URL.format(user=user, repo=repo, branch=branch))

	if not r.status_code == requests.codes.ok:
		return None

	reference = r.json()
	if not "hash" in reference:
		return None

	return reference["hash"]


def get_latest(target, check):
	if "user" not in check or "repo" not in check:
		raise ConfigurationInvalid("Update configuration for %s of type bitbucket_commit needs all of user and repo" % target)

	branch = "master"
	if "branch" in check:
		branch = check["branch"]

	current = None
	if "current" in check:
		current = check["current"]

	remote_commit = _get_latest_commit(check["user"], check["repo"], branch)

	information = dict(
		local=dict(name="Commit {commit}".format(commit=current if current is not None else "unknown"), value=current),
		remote=dict(name="Commit {commit}".format(commit=remote_commit if remote_commit is not None else "unknown"), value=remote_commit)
	)
	is_current = (current is not None and current == remote_commit) or remote_commit is None

	logger.debug("Target: %s, local: %s, remote: %s" % (target, current, remote_commit))

	return information, is_current

