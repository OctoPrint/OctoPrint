# coding=utf-8
"""
This module provides a bunch of utility methods and helpers for version handling.
"""
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import pkg_resources
import logging

from octoprint import __version__


def get_octoprint_version_string():
	return __version__


def get_octoprint_version(base=False):
	octoprint_version_string = get_octoprint_version_string()

	if "-" in octoprint_version_string:
		octoprint_version_string = octoprint_version_string[:octoprint_version_string.find("-")]

	octoprint_version = pkg_resources.parse_version(octoprint_version_string)

	# A leading v is common in github release tags and old setuptools doesn't remove it. While OctoPrint's
	# versions should never contain such a prefix, we'll make sure to have stuff behave the same
	# regardless of setuptools version anyhow.
	if octoprint_version and isinstance(octoprint_version, tuple) and octoprint_version[0].lower() == "*v":
		octoprint_version = octoprint_version[1:]

	if base:
		if isinstance(octoprint_version, tuple):
			# old setuptools
			base_version = []
			for part in octoprint_version:
				if part.startswith("*"):
					break
				base_version.append(part)
			base_version.append("*final")
			octoprint_version = tuple(base_version)
		else:
			# new setuptools
			octoprint_version = pkg_resources.parse_version(octoprint_version.base_version)
	return octoprint_version


def is_released_octoprint_version(version=None):
	"""
	>>> import pkg_resources
	>>> is_released_octoprint_version(version=pkg_resources.parse_version("1.3.6rc3"))
	True
	>>> is_released_octoprint_version(version=pkg_resources.parse_version("1.3.6rc3.dev2+g1234"))
	False
	>>> is_released_octoprint_version(version=pkg_resources.parse_version("1.3.6"))
	True
	>>> is_released_octoprint_version(version=pkg_resources.parse_version("1.3.6.post1+g1234"))
	True
	>>> is_released_octoprint_version(version=pkg_resources.parse_version("1.3.6.post1.dev0+g1234"))
	False
	>>> is_released_octoprint_version(version=pkg_resources.parse_version("1.3.7.dev123+g23545"))
	False
	"""

	if version is None:
		version = get_octoprint_version()

	if isinstance(version, tuple):
		# old setuptools
		return "*@" not in version
	else:
		# new setuptools
		return "dev" not in version.public


def is_stable_octoprint_version(version=None):
	"""
	>>> import pkg_resources
	>>> is_stable_octoprint_version(version=pkg_resources.parse_version("1.3.6rc3"))
	False
	>>> is_stable_octoprint_version(version=pkg_resources.parse_version("1.3.6rc3.dev2+g1234"))
	False
	>>> is_stable_octoprint_version(version=pkg_resources.parse_version("1.3.6"))
	True
	>>> is_stable_octoprint_version(version=pkg_resources.parse_version("1.3.6.post1+g1234"))
	True
	>>> is_stable_octoprint_version(version=pkg_resources.parse_version("1.3.6.post1.dev0+g1234"))
	False
	>>> is_stable_octoprint_version(version=pkg_resources.parse_version("1.3.7.dev123+g23545"))
	False
	"""

	if version is None:
		version = get_octoprint_version()

	if not is_released_octoprint_version(version=version):
		return False

	if isinstance(version, tuple):
		return "*a" not in version and "*b" not in version and "*c" not in version
	else:
		return not version.is_prerelease


def is_octoprint_compatible(*compatibility_entries, **kwargs):
	"""
	Tests if the current ``octoprint_version`` is compatible to any of the provided ``compatibility_entries``.

	Arguments:
		compatibility_entries (str): compatibility string(s) to test against, result will be `True` if any match
			is found
		octoprint_version (tuple or SetuptoolsVersion): optional OctoPrint version to match against, if not current
			base version will be determined via :func:`get_octoprint_version`.

	Returns:
		(bool) ``True`` if any of the provided compatibility entries matches or there are no entries, else ``False``
	"""

	logger = logging.getLogger(__name__)

	if not compatibility_entries:
		return True

	octoprint_version = kwargs.get("octoprint_version")
	if octoprint_version is None:
		octoprint_version = get_octoprint_version(base=True)

	for octo_compat in compatibility_entries:
		try:
			if not any(octo_compat.startswith(c) for c in ("<", "<=", "!=", "==", ">=", ">", "~=", "===")):
				octo_compat = ">={}".format(octo_compat)

			s = pkg_resources.Requirement.parse("OctoPrint" + octo_compat)
			if octoprint_version in s:
				break
		except:
			logger.exception("Something is wrong with this compatibility string for OctoPrint: {}".format(octo_compat))
	else:
		return False

	return True
