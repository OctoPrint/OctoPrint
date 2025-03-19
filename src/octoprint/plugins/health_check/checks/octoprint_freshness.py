from packaging.version import Version, parse

if __name__ == "__main__":
    __package__ = "octoprint.plugins.health_check.checks.octoprint_freshness"

from . import CheckResult, HealthCheck, Result


class OctoPrintFreshnessCheck(HealthCheck):
    key = "octoprint_freshness"

    def __init__(self, settings: dict = None):
        super().__init__(settings)

        self._versions = None

    @property
    def versions(self):
        if self._versions is None:
            self._versions = _fetch_versions()

        return self._versions

    def perform_check(self, force: bool = False) -> CheckResult:
        from octoprint.util.version import get_octoprint_version

        if force:
            self._versions = _fetch_versions()

        octoprint = get_octoprint_version(base=True)

        # octoprint = parse("1.8.6")  # for testing
        # octoprint = parse("0+unknown")  # for testing

        if octoprint.major == 0:
            # 0+unknown and similar get ignored
            return

        newer = _newer_versions(octoprint, self.versions)
        if not newer:
            return

        latest_per_minor = _latest_per_minor(newer)

        context = {
            "version": str(octoprint),
            "newer": [str(x) for x in newer],
            "latest": [str(x) for x in latest_per_minor],
        }

        if len(newer) >= 2:
            return CheckResult(result=Result.WARNING, context=context)


def _fetch_versions() -> list[Version]:
    import requests

    r = requests.get(
        "https://pypi.org/simple/octoprint",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        timeout=(3.05, 7),
    )
    r.raise_for_status()

    data = r.json()
    versions = [parse(version) for version in data["versions"]]
    return versions


def _newer_versions(version: Version, versions: list[Version]) -> list[Version]:
    """
    >>> versions = [parse("1.0.0"), parse("1.1.0"), parse("1.1.1"), parse("1.2.0rc1"), parse("1.2.0")]
    >>> _newer_versions(parse("1.1.0"), versions)
    [<Version('1.2.0')>, <Version('1.1.1')>]
    >>> _newer_versions(parse("1.2.0"), versions)
    []
    >>> _newer_versions(parse("1.1.0.rc2"), versions)
    [<Version('1.2.0')>, <Version('1.1.1')>, <Version('1.1.0')>]
    """

    return sorted(
        filter(
            lambda x: x > version and not x.is_prerelease,
            versions,
        ),
        reverse=True,
    )


def _latest_per_minor(versions: list[Version]) -> list[Version]:
    """
    >>> versions = [parse("1.0.0"), parse("1.0.1"), parse("1.0.2"), parse("1.1.0"), parse("1.1.1"), parse("1.2.0"), parse("2.0.0"), parse("2.0.1")]
    >>> _latest_per_minor(versions)
    [<Version('2.0.1')>, <Version('1.2.0')>, <Version('1.1.1')>, <Version('1.0.2')>]
    """
    result = []
    major = minor = -1
    for version in sorted(versions, reverse=True):
        if version.major != major or version.minor != minor:
            major = version.major
            minor = version.minor
            result.append(version)
    return result


if __name__ == "__main__":
    print("Versions:")
    versions = _fetch_versions()
    print(repr(versions))

    print("Newer:")
    newer = _newer_versions(parse("1.8.6"), versions)
    # newer = _newer_versions(parse("0+unknown"), versions)
    print(repr(newer))

    print("Latest per minor:")
    latest_per_minor = _latest_per_minor(newer)
    print(repr(latest_per_minor))
