# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import requests
import logging

from ..exceptions import ConfigurationInvalid

BRANCH_HEAD_URL = "https://api.github.com/repos/{user}/{repo}/git/refs/heads/{branch}"

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.github_commit")

def _get_latest_commit(user, repo, branch):
	r = requests.get(BRANCH_HEAD_URL.format(user=user, repo=repo, branch=branch))

	from . import log_github_ratelimit
	log_github_ratelimit(logger, r)

	if not r.status_code == requests.codes.ok:
		return None

	reference = r.json()
	if not "object" in reference or not "sha" in reference["object"]:
		return None

	return reference["object"]["sha"]


def get_latest(target, check):
	if "user" not in check or "repo" not in check:
		raise ConfigurationInvalid("Update configuration for %s of type github_commit needs all of user and repo" % target)

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

