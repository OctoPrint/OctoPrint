__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
from urllib.parse import quote as url_quote

import requests

BRANCH_HEAD_URL = "{baseurl}/repos/{user}/{repo}/git/refs/{ref}"

from .common import FORGEJO_DEFAULT_BASEURLS

logger = logging.getLogger(
    "octoprint.plugins.softwareupdate.version_checks.forgejo_commit"
)


def _get_latest_commit(baseurl, user, repo, branch, apikey=None):
    from ..exceptions import NetworkError

    headers = {}
    if apikey:
        auth = "token " + apikey
        headers = {"Authorization": auth}

    ref = url_quote(f"heads/{branch}", safe="")

    try:
        r = requests.get(
            BRANCH_HEAD_URL.format(baseurl=baseurl, user=user, repo=repo, ref=ref),
            timeout=(3.05, 30),
            headers=headers,
        )
    except requests.ConnectionError as exc:
        raise NetworkError(cause=exc) from exc

    from . import check_forgejo_apiresponse

    check_forgejo_apiresponse(logger, r)

    references = r.json()
    for reference in references:
        if "object" not in reference:
            continue

        obj = reference["object"]
        if obj.get("type") != "commit":
            continue
        if "sha" not in obj:
            continue
        return obj["sha"]

    return None  # nothing found


def get_latest(target, check, online=True, credentials=None, *args, **kwargs):
    from ..exceptions import ConfigurationInvalid

    forge = check.get("forge")
    user = check.get("user")
    repo = check.get("repo")

    if forge is None or user is None or repo is None:
        raise ConfigurationInvalid(
            "Update configuration for {} of type github_commit needs user and repo set and not None".format(
                target
            )
        )

    branch = "main"
    if "branch" in check and check["branch"] is not None:
        branch = check["branch"]

    current = check.get("current")

    information = {
        "local": {
            "name": "Commit {commit}".format(
                commit=current if current is not None else "?"
            ),
            "value": current,
        },
        "remote": {"name": "?", "value": "?"},
        "needs_online": not check.get("offline", False),
    }
    if not online and information["needs_online"]:
        return information, True

    forgejo_credentials = credentials.get("forgejo", {})
    apikey = None

    if forge in FORGEJO_DEFAULT_BASEURLS:
        apikey = forgejo_credentials.get(forge)  # e.g. "codeberg: aabbcc..."
        forge = FORGEJO_DEFAULT_BASEURLS[forge]

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

    remote_commit = _get_latest_commit(
        forge, check["user"], check["repo"], branch, apikey=apikey
    )
    remote_name = f"Commit {remote_commit}" if remote_commit is not None else "-"

    information["remote"] = {"name": remote_name, "value": remote_commit}
    is_current = (
        current is not None and current == remote_commit
    ) or remote_commit is None

    logger.debug(f"Target: {target}, local: {current}, remote: {remote_commit}")

    return information, is_current
