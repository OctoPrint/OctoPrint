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
	nothing = None, None, None
	r = requests.get(RELEASE_URL.format(user=user, repo=repo))

	from . import log_github_ratelimit
	log_github_ratelimit(logger, r)

	if not r.status_code == requests.codes.ok:
		return nothing

	releases = r.json()

	# sanitize
	required_fields = {"name", "tag_name", "html_url", "draft", "prerelease", "published_at"}
	releases = filter(lambda rel: set(rel.keys()) & required_fields == required_fields,
	                  releases)

	# filter out prereleases and drafts
	if include_prerelease:
		releases = filter(lambda rel: not rel["draft"], releases)
	else:
		releases = filter(lambda rel: not rel["prerelease"] and not rel["draft"],
		                  releases)

	if not releases:
		return nothing

	# sort by date
	comp = lambda a, b: cmp(a.get("published_at", None), b["published_at"])
	releases = sorted(releases, cmp=comp)

	# latest release = last in list
	latest = releases[-1]

	return latest["name"], latest["tag_name"], latest.get("html_url", None)


def _get_sanitized_version(version_string):
	if "-" in version_string:
		version_string = version_string[:version_string.find("-")]
	return version_string


def _get_comparable_version_pkg_resources(version_string, force_base=True):
	import pkg_resources

	version = pkg_resources.parse_version(version_string)

	if force_base:
		if isinstance(version, tuple):
			# old setuptools
			base_version = []
			for part in version:
				if part.startswith("*"):
					break
				base_version.append(part)
			version = tuple(base_version)
		else:
			# new setuptools
			version = pkg_resources.parse_version(version.base_version)

	return version


def _get_comparable_version_semantic(version_string, force_base=True):
	import semantic_version

	version = semantic_version.Version.coerce(version_string, partial=False)

	if force_base:
		version_string = "{}.{}.{}".format(version.major, version.minor, version.patch)
		version = semantic_version.Version.coerce(version_string, partial=False)

	return version


def _is_current(release_information, compare_type, custom=None, force_base=True):
	if release_information["remote"]["value"] is None:
		return True

	if not compare_type in ("python", "semantic", "unequal", "custom") or compare_type == "custom" and custom is None:
		compare_type = "python"

	sanitized_local = _get_sanitized_version(release_information["local"]["value"])
	sanitized_remote = _get_sanitized_version(release_information["remote"]["value"])

	try:
		if compare_type == "python":
			local_version = _get_comparable_version_pkg_resources(sanitized_local, force_base=force_base)
			remote_version = _get_comparable_version_pkg_resources(sanitized_remote, force_base=force_base)
			return local_version >= remote_version

		elif compare_type == "semantic":
			local_version = _get_comparable_version_semantic(sanitized_local, force_base=force_base)
			remote_version = _get_comparable_version_semantic(sanitized_remote, force_base=force_base)
			return local_version >= remote_version

		elif compare_type == "custom":
			return custom(sanitized_local, sanitized_remote)

		else:
			return sanitized_local == sanitized_remote
	except:
		logger.exception("Could not check if version is current due to an error, assuming it is")
		return True


def get_latest(target, check, custom_compare=None):
	if not "user" in check or not "repo" in check:
		raise ConfigurationInvalid("github_release update configuration for %s needs user and repo set" % target)

	current = check.get("current", None)
	include_prerelease = check.get("prerelease", False)
	force_base = check.get("force_base", True)

	remote_name, remote_tag, release_notes = _get_latest_release(check["user"],
	                                                             check["repo"],
	                                                             include_prerelease=include_prerelease)
	compare_type = check["release_compare"] if "release_compare" in check else "python"

	information =dict(
		local=dict(name=current, value=current),
		remote=dict(name=remote_name, value=remote_tag, release_notes=release_notes)
	)

	logger.debug("Target: %s, local: %s, remote: %s" % (target, current, remote_tag))

	return information, _is_current(information,
	                                compare_type,
	                                custom=custom_compare,
	                                force_base=force_base)
