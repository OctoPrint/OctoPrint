"""
This module provides a bunch of utility methods and helpers for version handling.

Comparable versions are provided as ``packaging.version.Version`` instances,
see `the packaging docs <https://packaging.pypa.io/en/stable/version.html#packaging.version.Version>`_
for details.

See the `documentation on version specifiers <https://packaging.python.org/en/latest/specifications/version-specifiers/>`_
for supported specifier formats.

The `packaging library <https://packaging.pypa.io>`_ is heavily used.
"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

import importlib.metadata as meta
import logging
from typing import Optional, Union

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from packaging.version import parse as parse_version

from octoprint import __version__


def get_package_version(package: str) -> str:
    """Returns the version of the provided package, throws an error if it cannot be found"""
    return meta.version(package)


def safe_get_package_version(package: str, default: Optional[str] = None) -> str:
    """Returns the version of the provided package, returns the configured ``default`` if it cannot be found"""
    try:
        return get_package_version(package)
    except meta.PackageNotFoundError:
        return default


def parse_specifier(specifier: str) -> SpecifierSet:
    """Parses the supplied ``specifier``"""
    return SpecifierSet(specifier)


def is_version_compatible(
    version: Union[str, Version], specifier: Union[str, SpecifierSet]
):
    """Checks whether the provided ``version`` is compatible to the supplied version ``specifier``"""
    if not isinstance(version, Version):
        version = parse_version(version)

    if not isinstance(specifier, SpecifierSet):
        specifier = parse_specifier(specifier)

    return version in specifier


def get_octoprint_version_string() -> str:
    """Returns the current OctoPrint version as a string"""
    return __version__


def get_octoprint_version(cut: int = None, **kwargs) -> Version:
    """Returns the current OctoPrint version in a comparable format"""
    octoprint_version_string = normalize_version(get_octoprint_version_string())
    return get_comparable_version(octoprint_version_string, cut=cut, **kwargs)


def is_released_octoprint_version(version: Optional[Union[str, Version]] = None) -> bool:
    """Returns whether the current OctoPrint version is a released version"""
    if version is None:
        version = get_octoprint_version()
    return is_release(version)


def is_stable_octoprint_version(version: Optional[Union[str, Version]] = None) -> bool:
    """Returns whether the current OctoPrint version is a stable version"""
    if version is None:
        version = get_octoprint_version()
    return is_stable(version)


def is_octoprint_compatible(
    *compatibility_entries: str,
    octoprint_version: Optional[Union[str, Version]] = None,
    **kwargs,
) -> bool:
    """
    Tests if the current ``octoprint_version`` is compatible to any of the provided ``compatibility_entries``.

    Arguments:
            compatibility_entries: compatibility string(s) to test against, result will be `True` if any match
                    is found
            octoprint_version: optional OctoPrint version to match against, if not current
                    base version will be determined via :func:`get_octoprint_version`.

    Examples:

        >>> is_octoprint_compatible(">=2")
        True
        >>> is_octoprint_compatible("<2")
        False
        >>> is_octoprint_compatible("==1.2.3", octoprint_version="1.2.3")
        True
        >>> is_octoprint_compatible("!=1.2.3", octoprint_version="1.2.3")
        False

    Returns:
            (bool) ``True`` if any of the provided compatibility entries matches or there are no entries, else ``False``
    """

    logger = logging.getLogger(__name__)

    if not compatibility_entries:
        return True

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


def get_python_version_string() -> str:
    """Returns the current python version as a normalized version string"""
    from platform import python_version

    version_string = normalize_version(python_version())

    return version_string


def get_python_version() -> Version:
    """Returns the current python version in a comparable format"""
    return get_comparable_version(get_python_version_string())


def is_python_compatible(
    compat: Union[str, Version], python_version: Optional[Union[str, Version]] = None
) -> bool:
    """
    Tests if the current python version is compatible to the provided ``compat``.

    Arguments:
        compat: compatibility string to test against
        python_version: the python version to test, if unset the current runtime will be used

    Returns:
        (bool) ``True`` the provided compatibility entry matches, else ``False``
    """
    if not compat:
        return True

    if python_version is None:
        python_version = get_python_version_string()

    return is_version_compatible(python_version, compat)


def get_comparable_version(
    version_string: str, cut: Optional[int] = None, base: Optional[bool] = None
) -> Version:
    """
    Args:
        version_string: The version string for which to create a comparable version instance
        cut: optional, how many version digits to remove (e.g., cut=1 will turn 1.2.3 into 1.2).
             Defaults to ``None``, meaning no further action. Settings this to 0 will remove
             anything up to the last digit, e.g. dev or rc information.
        base: optional, will be ignored if ``cut`` is set; if set to ``True`` will set ``cut`` to ``0``

    Examples:

        >>> str(get_comparable_version("1.2.3"))
        '1.2.3'
        >>> str(get_comparable_version("1.2.3", cut=1))
        '1.2'
        >>> str(get_comparable_version("1.2.3rc2", base=True))
        '1.2.3'
        >>> str(get_comparable_version("1.2.3rc2", cut=0))
        '1.2.3'
        >>> str(get_comparable_version("1.2.3rc2", base=False))
        '1.2.3rc2'
        >>> str(get_comparable_version("1.2.3rc2", cut=1, base=True))
        '1.2'

    Returns:
        A comparable version
    """

    if base and cut is None:
        cut = 0
    if cut is not None and (cut < 0 or not isinstance(cut, int)):
        raise ValueError("cut must be a positive integer")

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


def is_stable(version: Union[str, Version]) -> bool:
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


def is_release(version: Union[str, Version]) -> bool:
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


def is_prerelease(version: Union[str, Version]) -> bool:
    """
    >>> is_prerelease("1.2.3a")
    True
    >>> is_prerelease("1.2.3b")
    True
    >>> is_prerelease("1.2.3rc1")
    True
    >>> is_prerelease("1.2.3.dev1")
    True
    >>> is_prerelease("1.2.3")
    False
    """
    if isinstance(version, str):
        version = get_comparable_version(version)
    return version.is_prerelease


def normalize_version(version: str) -> str:
    """
    >>> normalize_version("1.2.3+")
    '1.2.3'
    >>> normalize_version("v1.2.3")
    '1.2.3'
    >>> normalize_version("1.2.3")
    '1.2.3'
    """

    # Debian has the python version set to 2.7.15+ which is not PEP440 compliant (bug 914072)
    if version.endswith("+"):
        version = version[:-1]

    if version[0].lower() == "v":
        version = version[1:]

    return version.strip()
