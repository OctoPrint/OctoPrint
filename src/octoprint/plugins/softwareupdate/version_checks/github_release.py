# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import requests
import logging

from ..exceptions import ConfigurationInvalid

RELEASE_URL = "https://api.github.com/repos/{user}/{repo}/releases"

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.github_release")

def _get_latest_release(user, repo, include_prerelease=False):
	r = requests.get(RELEASE_URL.format(user=user, repo=repo))

	from . import log_github_ratelimit
	log_github_ratelimit(logger, r)

	if not r.status_code == requests.codes.ok:
		return None, None

	releases = r.json()

	# filter out prereleases and drafts
	if include_prerelease:
		releases = filter(lambda rel: not rel["draft"], releases)
	else:
		releases = filter(lambda rel: not rel["prerelease"] and not rel["draft"], releases)

	if not releases:
		return None, None

	# sort by date
	comp = lambda a, b: cmp(a["published_at"], b["published_at"])
	releases = sorted(releases, cmp=comp)

	# latest release = last in list
	latest = releases[-1]

	return latest["name"], latest["tag_name"]


def _is_current(release_information, compare_type, custom=None):
	if release_information["remote"]["value"] is None:
		return True

	if not compare_type in ("semantic", "unequal", "custom") or compare_type == "custom" and custom is None:
		compare_type = "semantic"

	try:
		if compare_type == "semantic":
			import semantic_version

			local_version = semantic_version.Version(release_information["local"]["value"])
			remote_version = semantic_version.Version(release_information["remote"]["value"])

			return local_version >= remote_version

		elif compare_type == "custom":
			return custom(release_information["local"], release_information["remote"])

		else:
			return release_information["local"]["value"] == release_information["remote"]["value"]
	except:
		logger.exception("Could not check if version is current due to an error, assuming it is")
		return True


def get_latest(target, check, custom_compare=None):
	if not "user" in check or not "repo" in check:
		raise ConfigurationInvalid("github_release update configuration for %s needs user and repo set" % target)

	current = None
	if "current" in check:
		current = check["current"]

	remote_name, remote_tag = _get_latest_release(check["user"], check["repo"], include_prerelease=check["prerelease"] == True if "prerelease" in check else False)
	compare_type = check["release_compare"] if "release_compare" in check else "semantic"

	information =dict(
		local=dict(name=current, value=current),
		remote=dict(name=remote_name, value=remote_tag)
	)

	logger.debug("Target: %s, local: %s, remote: %s" % (target, current, remote_tag))

	return information, _is_current(information, compare_type, custom=custom_compare)
