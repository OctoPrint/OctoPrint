__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

import requests

BRANCH_HEAD_URL = "https://api.github.com/repos/{user}/{repo}/git/refs/heads/{branch}"

logger = logging.getLogger(
    "octoprint.plugins.softwareupdate.version_checks.github_commit"
)


def _get_latest_commit(user, repo, branch, apikey=None):
    from ..exceptions import NetworkError

    headers = {}
    if apikey:
        auth = "token " + apikey
        headers = {"Authorization": auth}

    try:
        r = requests.get(
            BRANCH_HEAD_URL.format(user=user, repo=repo, branch=branch),
            timeout=(3.05, 30),
            headers=headers,
        )
    except requests.ConnectionError as exc:
        raise NetworkError(cause=exc)

    from . import check_github_apiresponse, check_github_ratelimit

    check_github_ratelimit(logger, r)
    check_github_apiresponse(logger, r)

    reference = r.json()
    if "object" not in reference or "sha" not in reference["object"]:
        return None

    return reference["object"]["sha"]


def get_latest(target, check, online=True, credentials=None, *args, **kwargs):
    from ..exceptions import ConfigurationInvalid

    user = check.get("user")
    repo = check.get("repo")

    if user is None or repo is None:
        raise ConfigurationInvalid(
            "Update configuration for {} of type github_commit needs user and repo set and not None".format(
                target
            )
        )

    branch = "master"
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

    apikey = None
    if credentials:
        apikey = credentials.get("github")

    remote_commit = _get_latest_commit(
        check["user"], check["repo"], branch, apikey=apikey
    )
    remote_name = f"Commit {remote_commit}" if remote_commit is not None else "-"

    information["remote"] = {"name": remote_name, "value": remote_commit}
    is_current = (
        current is not None and current == remote_commit
    ) or remote_commit is None

    logger.debug(f"Target: {target}, local: {current}, remote: {remote_commit}")

    return information, is_current
