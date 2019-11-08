# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import pkg_resources
import requests

from octoprint.util import to_native_str
from octoprint.util.version import is_python_compatible, get_comparable_version, is_prerelease

INFO_URL = "https://pypi.org/pypi/{package}/json"

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.pypi_release")

def _filter_out_latest(releases, include_prerelease=False, python_version=None):
	"""
	Filters out the newest of all matching releases.

	Tests:

	    >>> requires_py2 = ">=2.7.9,<3"
	    >>> requires_py23 = ">=2.7.9, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, <4"
	    >>> requires_py3 = ">=3.6, <4"
	    >>> releases = {"1.3.12": [dict(requires_python=requires_py2, upload_time_iso_8601="2019-10-22T10:06:03.190293Z")], "1.4.0rc1": [dict(requires_python=requires_py23, upload_time_iso_8601="2019-11-22T10:06:03.190293Z")], "2.0.0rc1": [dict(requires_python=requires_py3, upload_time_iso_8601="2020-10-22T10:06:03.190293Z")]}
	    >>> to_native_str(_filter_out_latest(releases, python_version="2.7.9"))
	    '1.3.12'
	    >>> to_native_str(_filter_out_latest(releases, include_prerelease=True, python_version="2.7.9"))
	    '1.4.0rc1'
	    >>> to_native_str(_filter_out_latest(releases, include_prerelease=True, python_version="3.6.0"))
	    '2.0.0rc1'
	    >>> to_native_str(_filter_out_latest(releases, python_version="3.6.0"))
	"""
	releases = [dict(version=k, data=v[0]) for k, v in releases.items()]

	# filter out prereleases and versions incompatible to our python
	filter_function = lambda release: not is_prerelease(release["version"]) and is_python_compatible(release["data"].get("requires_python", ""), python_version=python_version)
	if include_prerelease:
		filter_function = lambda release: is_python_compatible(release["data"].get("requires_python", ""), python_version=python_version)

	releases = list(filter(filter_function, releases))
	if not releases:
		return None

	# sort by upload date
	releases = sorted(releases, key=lambda release: release["data"].get("upload_time_iso_8601", ""))

	# latest release = last in list
	latest = releases[-1]

	return latest["version"]

def _get_latest_release(package, include_prerelease):
	from ..exceptions import NetworkError

	try:
		r = requests.get(INFO_URL.format(package=package), timeout=(3.05, 30))
	except requests.ConnectionError as exc:
		raise NetworkError(cause=exc)

	if not r.status_code == requests.codes.ok:
		return None

	data = r.json()
	if not "info" in data or not "version" in data["info"]:
		return None

	requires_python = data["info"].get("requires_python")
	if requires_python and not is_python_compatible(requires_python):
		return None

	return _filter_out_latest(data["releases"],
	                          include_prerelease=include_prerelease)

def _is_current(release_information):
	if release_information["remote"]["value"] is None:
		return True

	local_version = get_comparable_version(release_information["local"]["value"])
	remote_version = get_comparable_version(release_information["remote"]["value"])

	return remote_version <= local_version

def get_latest(target, check, online=True):
	from ..exceptions import CannotUpdateOffline

	if not online and not check.get("offline", False):
		raise CannotUpdateOffline()

	package = check.get("package")

	distribution = pkg_resources.get_distribution(package)
	if distribution:
		local_version = distribution.version
	else:
		local_version = None

	remote_version = _get_latest_release(package,
	                                     include_prerelease=check.get("prerelease", False))

	information = dict(local=dict(name=local_version, value=local_version),
	                   remote=dict(name=remote_version, value=remote_version))

	logger.debug("Target: {}, local: {}, remote: {}".format(target, information["local"]["name"], information["remote"]["name"]))

	return information, _is_current(information)
