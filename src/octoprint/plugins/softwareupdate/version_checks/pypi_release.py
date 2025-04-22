__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

import requests
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version
from packaging.version import parse as parse_version

from octoprint.util.version import (
    get_comparable_version,
    safe_get_package_version,
)

INDEX_URL = "https://pypi.org/simple/{package}"

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.pypi_release")


@dataclass
class ReleaseFile:
    filename: str
    python_requires: str


@dataclass
class Release:
    version: Version
    python_requires: Optional[SpecifierSet]


def _fetch_files(package: str) -> Iterable[ReleaseFile]:
    from ..exceptions import NetworkError

    try:
        r = requests.get(
            INDEX_URL.format(package=package),
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            timeout=(3.05, 7),
        )
        r.raise_for_status()
    except requests.ConnectionError as exc:
        raise NetworkError(cause=exc) from exc

    data = r.json()
    files = data.get("files", [])
    return [ReleaseFile(x["filename"], x.get("requires-python")) for x in files]


def _parse_version_from_filename(filename) -> Version:
    """
    >>> _parse_version_from_filename("importlib_metadata-8.4.0.tar.gz")
    <Version('8.4.0')>
    >>> _parse_version_from_filename("zeroconf-0.133.0-pp39-pypy39_pp73-win_amd64.whl")
    <Version('0.133.0')>
    >>> _parse_version_from_filename("OctoPrint-1.10.0rc4.sdist.tar.gz")
    <Version('1.10.0rc4')>
    >>> _parse_version_from_filename("example-0.1.foo.bar.fnord.baz.blub.tar.gz")
    <Version('0.1')>
    >>> _parse_version_from_filename("example.tar.gz")
    >>> _parse_version_from_filename("example-a-b-c.tar.gz")
    """
    # filename format: project-version[.tar.gz|[-build]-python-abi-platform.whl]
    parts = filename.split("-")
    if len(parts) < 2:
        return None

    version = parts[1]

    while version:
        try:
            return parse_version(version)
        except ValueError:
            if "." in version:
                former = version
                version, _ = version.rsplit(".", 1)
                if version == former:
                    break
            else:
                break

    return None


def _releases_from_files(files: Iterable[ReleaseFile]) -> Iterable[Release]:
    """
    >>> file1 = ReleaseFile("example-0.1.tar.gz", ">=3.7")
    >>> file2 = ReleaseFile("example-0.1-py3-any-none.whl", ">=3.7")
    >>> file3 = ReleaseFile("example-0.2.tar.gz", ">=3.8")
    >>> file4 = ReleaseFile("example-0.3-py3-any-non-whl", None)
    >>> _releases_from_files([file1, file2, file3, file4])
    [Release(version=<Version('0.1')>, python_requires=<SpecifierSet('>=3.7')>), Release(version=<Version('0.2')>, python_requires=<SpecifierSet('>=3.8')>), Release(version=<Version('0.3')>, python_requires=None)]
    """
    releases = {}

    for f in files:
        try:
            version = _parse_version_from_filename(f.filename)
        except ValueError:
            continue

        if version in releases:
            continue

        python_requires = None
        if f.python_requires:
            try:
                python_requires = SpecifierSet(f.python_requires)
            except InvalidSpecifier:
                continue

        releases[version] = Release(version, python_requires)

    return list(releases.values())


def _get_latest_release(package: str, include_prerelease: bool = False) -> Optional[str]:
    import platform

    python_version = platform.python_version()

    files = _fetch_files(package)
    releases = filter(
        lambda x: (not x.python_requires or python_version in x.python_requires)
        and (not x.version.is_prerelease or include_prerelease),
        _releases_from_files(files),
    )

    if not releases:
        return None

    releases = sorted(releases, key=lambda x: x.version, reverse=True)
    latest = releases[0]
    return str(latest.version)


def _is_current(release_information):
    if release_information["remote"]["value"] is None:
        return True

    local_version = get_comparable_version(release_information["local"]["value"])
    remote_version = get_comparable_version(release_information["remote"]["value"])

    return remote_version <= local_version


def get_latest(target, check, online=True, *args, **kwargs):
    from ..exceptions import CannotUpdateOffline

    if not online and not check.get("offline", False):
        raise CannotUpdateOffline()

    package = check.get("package")
    local_version = safe_get_package_version(package)

    remote_version = _get_latest_release(
        package, include_prerelease=check.get("prerelease", False)
    )

    information = {
        "local": {"name": local_version, "value": local_version},
        "remote": {"name": remote_version, "value": remote_version},
    }

    logger.debug(
        "Target: {}, local: {}, remote: {}".format(
            target, information["local"]["name"], information["remote"]["name"]
        )
    )

    return information, _is_current(information)


if __name__ == "__main__":
    __package__ = "octoprint.plugins.softwareupdate.version_checks"
    latest = _get_latest_release("pip", include_prerelease=True)
    print(repr(latest))
