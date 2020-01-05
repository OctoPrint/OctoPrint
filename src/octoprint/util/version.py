# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

"""
This module provides a bunch of utility methods and helpers for version handling.
"""

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import pkg_resources
import logging

from octoprint import __version__


def get_octoprint_version_string():
	return __version__


def get_octoprint_version(base=False):
	octoprint_version_string = get_octoprint_version_string()
	return get_comparable_version(octoprint_version_string, base=base)


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
		except Exception:
			logger.exception("Something is wrong with this compatibility string for OctoPrint: {}".format(octo_compat))
	else:
		return False

	return True


def get_python_version_string():
	from platform import python_version
	version_string = python_version()

	# Debian has the python version set to 2.7.15+ which is not PEP440 compliant (bug 914072)
	if version_string.endswith("+"):
		version_string = version_string[:-1]

	return version_string


def get_python_version():
	return get_comparable_version(get_python_version_string())


def is_python_compatible(compat, **kwargs):
	if not compat:
		return True

	python_version = kwargs.get("python_version")
	if python_version is None:
		python_version = get_python_version_string()

	s = pkg_resources.Requirement.parse("Python" + compat)
	return python_version in s


def get_comparable_version(version_string, base=False):
	if "-" in version_string:
		version_string = version_string[:version_string.find("-")]

	# Debian has the python version set to 2.7.15+ which is not PEP440 compliant (bug 914072)
	if version_string.endswith("+"):
		version_string = version_string[:-1]

	version = pkg_resources.parse_version(version_string)

	# A leading v is common in github release tags and old setuptools doesn't remove it.
	if version and isinstance(version, tuple) and version[0].lower() == "*v":
		version = version[1:]

	if base:
		if isinstance(version, tuple):
			# old setuptools
			base_version = []
			for part in version:
				if part.startswith("*"):
					break
				base_version.append(part)
			base_version.append("*final")
			version = tuple(base_version)
		else:
			# new setuptools
			version = pkg_resources.parse_version(version.base_version)
	return version


def is_prerelease(version_string):
	version = get_comparable_version(version_string)

	if isinstance(version, tuple):
		# old setuptools
		return any(map(lambda x: x in version, ("*a", "*b", "*c", "*rc")))
	else:
		# new setuptools
		return version.is_prerelease
