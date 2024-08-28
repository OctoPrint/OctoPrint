"""
This module provides a bunch of utility methods and helpers for version handling.
"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

import logging

from packaging.version import parse as parse_version

from octoprint import __version__

try:
    import importlib.metadata as meta
except ImportError:  # Python 3.7
    import importlib_metadata as meta


def get_package_version(package):
    return meta.version(package)


def safe_get_package_version(package, default=None):
    try:
        return get_package_version(package)
    except meta.PackageNotFoundError:
        return default


def is_version_compatible(version, specifier):
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    if not isinstance(version, Version):
        version = Version(version)

    if not isinstance(specifier, SpecifierSet):
        specifier = SpecifierSet(specifier)

    return version in specifier


def get_octoprint_version_string():
    return __version__


def get_octoprint_version(cut=None, **kwargs):
    octoprint_version_string = normalize_version(get_octoprint_version_string())
    return get_comparable_version(octoprint_version_string, cut=cut, **kwargs)


def is_released_octoprint_version(version=None):
    if version is None:
        version = get_octoprint_version()
    return is_release(version)


def is_stable_octoprint_version(version=None):
    if version is None:
        version = get_octoprint_version()
    return is_stable(version)


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
            if not any(
                octo_compat.startswith(c)
                for c in ("<", "<=", "!=", "==", ">=", ">", "~=", "===")
            ):
                octo_compat = f">={octo_compat}"

            if is_version_compatible(octoprint_version, octo_compat):
                break
        except Exception:
            logger.exception(
                "Something is wrong with this compatibility string for OctoPrint: {}".format(
                    octo_compat
                )
            )
    else:
        return False

    return True


def get_python_version_string():
    from platform import python_version

    version_string = normalize_version(python_version())

    return version_string


def get_python_version():
    return get_comparable_version(get_python_version_string())


def is_python_compatible(compat, **kwargs):
    if not compat:
        return True

    python_version = kwargs.get("python_version")
    if python_version is None:
        python_version = get_python_version_string()

    return is_version_compatible(python_version, compat)


def get_comparable_version(version_string, cut=None, **kwargs):
    """
    Args:
        version_string: The version string for which to create a comparable version instance
        cut: optional, how many version digits to remove (e.g., cut=1 will turn 1.2.3 into 1.2).
             Defaults to ``None``, meaning no further action. Settings this to 0 will remove
             anything up to the last digit, e.g. dev or rc information.

    Returns:
        A comparable version
    """

    if "base" in kwargs and kwargs.get("base", False) and cut is None:
        cut = 0
    if cut is not None and (cut < 0 or not isinstance(cut, int)):
        raise ValueError("level must be a positive integer")

    version_string = normalize_version(version_string)
    version = parse_version(version_string)

    if cut is not None:
        version = parse_version(version.base_version)
        if cut is not None:
            parts = version.base_version.split(".")
            if 0 < cut < len(parts):
                reduced = parts[:-cut]
                version = parse_version(".".join(str(x) for x in reduced))

    return version


def is_stable(version):
    """
    >>> is_stable("1.3.6rc3")
    False
    >>> is_stable("1.3.6rc3.dev2+g1234")
    False
    >>> is_stable("1.3.6")
    True
    >>> is_stable("1.3.6.post1+g1234")
    True
    >>> is_stable("1.3.6.post1.dev0+g1234")
    False
    >>> is_stable("1.3.7.dev123+g23545")
    False
    """

    if isinstance(version, str):
        version = get_comparable_version(version)

    if not is_release(version):
        return False

    return not version.is_prerelease


def is_release(version):
    """
    >>> is_release("1.3.6rc3")
    True
    >>> is_release("1.3.6rc3.dev2+g1234")
    False
    >>> is_release("1.3.6")
    True
    >>> is_release("1.3.6.post1+g1234")
    True
    >>> is_release("1.3.6.post1.dev0+g1234")
    False
    >>> is_release("1.3.7.dev123+g23545")
    False
    """

    if isinstance(version, str):
        version = get_comparable_version(version)
    return "dev" not in version.public


def is_prerelease(version):
    if isinstance(version, str):
        version = get_comparable_version(version)
    return version.is_prerelease


def normalize_version(version):
    # Debian has the python version set to 2.7.15+ which is not PEP440 compliant (bug 914072)
    if version.endswith("+"):
        version = version[:-1]

    if version[0].lower() == "v":
        version = version[1:]

    return version.strip()
