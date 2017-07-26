# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import requests
import logging

BRANCH_HEAD_URL = "https://api.github.com/repos/{user}/{repo}/git/refs/heads/{branch}"

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.github_commit")

def _get_latest_commit(user, repo, branch):
	from ..exceptions import NetworkError

	try:
		r = requests.get(BRANCH_HEAD_URL.format(user=user, repo=repo, branch=branch), timeout=(3.05, 30))
	except requests.ConnectionError as exc:
		raise NetworkError(cause=exc)

	from . import log_github_ratelimit
	log_github_ratelimit(logger, r)

	if not r.status_code == requests.codes.ok:
		return None

	reference = r.json()
	if not "object" in reference or not "sha" in reference["object"]:
		return None

	return reference["object"]["sha"]


def get_latest(target, check, online=True):
	from ..exceptions import ConfigurationInvalid

	user = check.get("user")
	repo = check.get("repo")

	if user is None or repo is None:
		raise ConfigurationInvalid("Update configuration for {} of type github_commit needs user and repo set and not None".format(target))

	branch = "master"
	if "branch" in check and check["branch"] is not None:
		branch = check["branch"]

	current = check.get("current")

	information = dict(local=dict(name="Commit {commit}".format(commit=current if current is not None else "?"), value=current),
	                   remote=dict(name="?", value="?"),
	                   needs_online=not check.get("offline", False))
	if not online and information["needs_online"]:
		return information, True

	remote_commit = _get_latest_commit(check["user"], check["repo"], branch)
	remote_name = "Commit {commit}".format(commit=remote_commit) if remote_commit is not None else "-"

	information["remote"] = dict(name=remote_name, value=remote_commit)
	is_current = (current is not None and current == remote_commit) or remote_commit is None

	logger.debug("Target: %s, local: %s, remote: %s" % (target, current, remote_commit))

	return information, is_current

