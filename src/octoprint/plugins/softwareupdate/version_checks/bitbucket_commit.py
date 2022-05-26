__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import base64
import logging

import requests

from . import ApiCheckError

BRANCH_HEAD_URL = (
    "https://api.bitbucket.org/2.0/repositories/{user}/{repo}/commit/{branch}"
)

logger = logging.getLogger(
    "octoprint.plugins.softwareupdate.version_checks.bitbucket_commit"
)


class BitbucketApiError(ApiCheckError):
    API = "Bitbucket API"


def check_bitbucket_api_response(logger, r, ok_codes=None):
    if ok_codes is None:
        ok_codes = [requests.codes.ok]

    if r.status_code not in ok_codes:
        try:
            data = r.json()
            message = data.get("message", "Unknown error")
        except Exception:
            message = "Not a valid JSON response"

        exc = BitbucketApiError(r.status_code, message)
        logger.error(exc.message)
        raise exc


def _get_latest_commit(user, repo, branch, api_user=None, api_password=None):
    from ..exceptions import NetworkError

    url = BRANCH_HEAD_URL.format(user=user, repo=repo, branch=branch)
    headers = {}
    if api_user is not None and api_password is not None:
        auth_value = base64.b64encode(
            b"{user}:{pw}".format(user=api_user, pw=api_password)
        )
        headers["authorization"] = f"Basic {auth_value}"

    try:
        r = requests.get(url, headers=headers, timeout=(3.05, 30))
    except requests.ConnectionError as exc:
        raise NetworkError(cause=exc)

    check_bitbucket_api_response(logger, r)

    reference = r.json()
    if "hash" not in reference:
        raise BitbucketApiError(r.status_code, "No commit hash found in response")

    return reference["hash"]


def get_latest(target, check, online=True, credentials=None, *args, **kwargs):
    from ..exceptions import ConfigurationInvalid

    if "user" not in check or "repo" not in check:
        raise ConfigurationInvalid(
            "Update configuration for %s of type bitbucket_commit needs all of user and repo"
            % target
        )

    branch = "master"
    if "branch" in check and check["branch"] is not None:
        branch = check["branch"]

    api_user = check.get("api_user")
    api_password = check.get("api_password")

    if api_user is None and api_password is None and credentials:
        api_user = credentials.get("bitbucket_user")
        api_password = credentials.get("bitbucket_password")

    current = check.get("current")

    information = {
        "local": {
            "name": "Commit {commit}".format(
                commit=current if current is not None else "unknown"
            ),
            "value": current,
        },
        "remote": {"name": "?", "value": "?"},
        "needs_online": not check.get("offline", False),
    }
    if not online and information["needs_online"]:
        return information, True

    remote_commit = _get_latest_commit(
        check["user"], check["repo"], branch, api_user, api_password
    )
    remote_name = f"Commit {remote_commit}" if remote_commit is not None else "-"

    information["remote"] = {"name": remote_name, "value": remote_commit}
    is_current = (
        current is not None and current == remote_commit
    ) or remote_commit is None

    logger.debug(f"Target: {target}, local: {current}, remote: {remote_commit}")

    return information, is_current
