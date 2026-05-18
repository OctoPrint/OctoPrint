__author__ = "Gina Häußge <gina@octoprint.org>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2026 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

import requests

from octoprint.util import sv
from octoprint.util.version import get_comparable_version

RELEASE_URL = "{baseurl}/repos/{user}/{repo}/releases"

DEFAULT_BASEURLS = {"codeberg": "https://codeberg.org/api/v1"}

logger = logging.getLogger(
    "octoprint.plugins.softwareupdate.version_checks.forgejo_release"
)


def _filter_out_latest(releases, sort_key=None, include_prerelease=False, commitish=None):
    """
    Filters out the newest of all matching releases.

    Tests:

        >>> release_1_0_0 = {"name": "1.0.0", "tag_name": "1.0.0", "html_url": "some_url", "published_at": "2026-05-06T01:00:00Z", "prerelease": False, "target_commitish": "main"}
        >>> release_1_0_1 = {"name": "1.0.1", "tag_name": "1.0.1", "html_url": "some_url", "published_at": "2026-05-06T01:01:00Z", "prerelease": False, "target_commitish": "main"}
        >>> release_1_1_0 = {"name": "1.1.0", "tag_name": "1.1.0", "html_url": "some_url", "published_at": "2026-05-07T01:00:00Z", "prerelease": False, "target_commitish": "main"}
        >>> release_1_2_0rc1 = {"name": "1.2.0rc1", "tag_name": "1.2.0rc1", "html_url": "some_url", "published_at": "2026-05-08T01:00:00Z", "prerelease": True, "target_commitish": "next"}
        >>> release_1_2_0rc2 = {"name": "1.2.0rc2", "tag_name": "1.2.0rc2", "html_url": "some_url", "published_at": "2026-05-08T01:01:00Z", "prerelease": True, "target_commitish": "next"}
        >>> release_2_0_0rc1 = {"name": "2.0.0rc1", "tag_name": "2.0.0rc1", "html_url": "some_url", "published_at": "2026-05-09T01:00:00Z", "prerelease": True, "target_commitish": "future"}
        >>> releases = [release_1_0_0, release_1_0_1, release_1_1_0, release_1_2_0rc1, release_1_2_0rc2, release_2_0_0rc1]
        >>> _filter_out_latest(releases, include_prerelease=False)
        ('1.1.0', '1.1.0', 'some_url')
        >>> _filter_out_latest(releases, include_prerelease=True)
        ('2.0.0rc1', '2.0.0rc1', 'some_url')
        >>> _filter_out_latest(releases, include_prerelease=True, commitish=["future", "next"])
        ('2.0.0rc1', '2.0.0rc1', 'some_url')
        >>> _filter_out_latest(releases, include_prerelease=True, commitish=["next"])
        ('1.2.0rc2', '1.2.0rc2', 'some_url')
    """

    nothing = None, None, None

    if sort_key is None:
        sort_key = lambda release: sv(release.get("published_at", None))

    # filter out prereleases and drafts
    filter_function = lambda rel: not rel["prerelease"]
    if include_prerelease:
        if commitish:
            filter_function = (
                lambda rel: not rel["prerelease"] or rel["target_commitish"] in commitish
            )
        else:
            filter_function = lambda _: True

    releases = list(filter(filter_function, releases))

    if not releases:
        return nothing

    # sort by sort_key
    releases = sorted(releases, key=sort_key)

    # latest release = last in list
    latest = releases[-1]

    return latest["name"], latest["tag_name"], latest.get("html_url", None)


def _get_latest_release(
    baseurl,
    user,
    repo,
    compare_type,
    include_prerelease=False,
    commitish=None,
    force_base=True,
    apikey=None,
):
    from ..exceptions import NetworkError

    headers = {}
    if apikey:
        auth = "token " + apikey
        headers = {"Authorization": auth}

    query = "?draft=false"

    try:
        r = requests.get(
            RELEASE_URL.format(baseurl=baseurl, user=user, repo=repo) + query,
            timeout=(3.05, 30),
            headers=headers,
        )
    except requests.ConnectionError as exc:
        raise NetworkError(cause=exc) from exc

    from . import check_forgejo_apiresponse

    check_forgejo_apiresponse(logger, r)

    releases = r.json()

    # sanitize
    required_fields = {
        "name",
        "tag_name",
        "html_url",
        "published_at",
        "prerelease",
        "target_commitish",
    }
    releases = list(
        filter(lambda rel: set(rel.keys()) & required_fields == required_fields, releases)
    )

    comparable_factory = _get_comparable_factory(compare_type, force_base=force_base)
    sort_key = lambda release: comparable_factory(
        _get_sanitized_version(release["tag_name"])
    )

    return _filter_out_latest(
        releases,
        sort_key=sort_key,
        include_prerelease=include_prerelease,
        commitish=commitish,
    )


def _get_sanitized_version(version_string):
    """
    Removes "-..." suffix from version strings.

    Tests:
        >>> _get_sanitized_version(None)
        >>> _get_sanitized_version("1.2.15")
        '1.2.15'
        >>> _get_sanitized_version("1.2.15-dev12")
        '1.2.15'
    """

    if version_string is not None and "-" in version_string:
        version_string = version_string[: version_string.find("-")]
    return version_string


def _get_comparable_version_semantic(version_string, force_base=True):
    import semantic_version

    version = semantic_version.Version.coerce(version_string, partial=False)

    if force_base:
        version_string = f"{version.major}.{version.minor}.{version.patch}"
        version = semantic_version.Version.coerce(version_string, partial=False)

    return version


def _get_sanitized_compare_type(compare_type, custom=None):
    if (
        compare_type
        not in (
            "python",
            "python_unequal",
            "semantic",
            "semantic_unequal",
            "unequal",
            "custom",
        )
        or compare_type == "custom"
        and custom is None
    ):
        compare_type = "python"
    return compare_type


def _get_comparable_factory(compare_type, force_base=True):
    if compare_type in ("python", "python_unequal"):
        return lambda version: get_comparable_version(version, base=force_base)
    elif compare_type in ("semantic", "semantic_unequal"):
        return lambda version: _get_comparable_version_semantic(
            version, force_base=force_base
        )
    else:
        return lambda version: version


def _get_comparator(compare_type, custom=None):
    if compare_type in ("python", "semantic"):
        return lambda a, b: a >= b
    elif compare_type == "custom":
        return custom
    else:
        return lambda a, b: a == b


def _is_current(release_information, compare_type, custom=None, force_base=True):
    """
    Checks if the provided release information indicates the version being the most current one.

    Tests:

        >>> _is_current(dict(remote=dict(value=None)), "python")
        True
        >>> _is_current(dict(local=dict(value="1.2.15"), remote=dict(value="1.2.16")), "python")
        False
        >>> _is_current(dict(local=dict(value="1.2.16dev1"), remote=dict(value="1.2.16dev2")), "python")
        True
        >>> _is_current(dict(local=dict(value="1.2.16dev1"), remote=dict(value="1.2.16dev2")), "python", force_base=False)
        False
        >>> _is_current(dict(local=dict(value="1.2.16dev3"), remote=dict(value="1.2.16dev2")), "python", force_base=False)
        True
        >>> _is_current(dict(local=dict(value="1.2.16dev3"), remote=dict(value="1.2.16dev2")), "python_unequal", force_base=False)
        False
        >>> _is_current(dict(local=dict(value="1.3.0.post1+g1014712"), remote=dict(value="1.3.0")), "python")
        True

    """

    if release_information["remote"]["value"] is None:
        return True

    compare_type = _get_sanitized_compare_type(compare_type, custom=custom)
    comparable_factory = _get_comparable_factory(compare_type, force_base=force_base)
    comparator = _get_comparator(compare_type, custom=custom)

    sanitized_local = _get_sanitized_version(release_information["local"]["value"])
    sanitized_remote = _get_sanitized_version(release_information["remote"]["value"])

    try:
        return comparator(
            comparable_factory(sanitized_local), comparable_factory(sanitized_remote)
        )
    except Exception:
        logger.exception(
            "Could not check if version is current due to an error, assuming it is"
        )
        return True


def get_latest(
    target, check, custom_compare=None, online=True, credentials=None, *args, **kwargs
):
    from ..exceptions import ConfigurationInvalid

    forge = check.get("forge", None)
    user = check.get("user", None)
    repo = check.get("repo", None)
    current = check.get("current", None)
    if forge is None or user is None or repo is None or current is None:
        raise ConfigurationInvalid(
            "Update configuration for {} of type forgejo_release needs all of forge, user, repo and current set and not None".format(
                target
            )
        )

    information = {
        "local": {"name": current, "value": current},
        "remote": {"name": "?", "value": "?", "release_notes": None},
        "needs_online": not check.get("offline", False),
    }
    if not online and information["needs_online"]:
        return information, True

    include_prerelease = check.get("prerelease", False)
    prerelease_channel = check.get("prerelease_channel", None)

    # determine valid "commitish" values in case we track prereleases
    commitish = None
    if include_prerelease and prerelease_channel:
        prerelease_branches = check.get("prerelease_branches", None)
        if prerelease_branches:
            # fetch valid commitish list from configured prerelease_branches for selected channel
            commitishes = {
                x["branch"]: x.get("commitish", [x["branch"]])
                for x in prerelease_branches
            }
            commitish = commitishes.get(prerelease_channel, [prerelease_channel])

    force_base = check.get("force_base", False)
    compare_type = _get_sanitized_compare_type(
        check.get("release_compare", "python"), custom=custom_compare
    )

    forgejo_credentials = credentials.get("forgejo", {})
    apikey = None

    if forge in DEFAULT_BASEURLS:
        apikey = forgejo_credentials.get(forge)  # e.g. "codeberg: aabbcc..."
        forge = DEFAULT_BASEURLS[forge]

    if apikey is None:
        apikey = forgejo_credentials.get(
            forge
        )  # e.g. "https://codeberg.org/api/v1: aabbcc..."

    if not forge.startswith("http://") and not forge.startswith("https://"):
        # unknown forge and no baseurl provided, bail
        raise ConfigurationInvalid(
            "Update configuration for {} of type forgejo_release requires either a known forge or a full base url as its forge config".format(
                target
            )
        )

    remote_name, remote_tag, release_notes = _get_latest_release(
        forge,
        check["user"],
        check["repo"],
        compare_type,
        include_prerelease=include_prerelease,
        commitish=commitish,
        force_base=force_base,
        apikey=apikey,
    )

    if not remote_name:
        if remote_tag:
            remote_name = remote_tag
        else:
            remote_name = "-"

    information["remote"] = {
        "name": remote_name,
        "value": remote_tag,
        "release_notes": release_notes,
    }

    logger.debug(f"Target: {target}, local: {current}, remote: {remote_tag}")

    return information, _is_current(
        information, compare_type, custom=custom_compare, force_base=force_base
    )
