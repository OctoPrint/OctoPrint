__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from ..exceptions import ApiCheckError, RateLimitCheckError
from . import (  # noqa: F401
    always_current,
    bitbucket_commit,
    commandline,
    forgejo_release,
    git_commit,
    github_commit,
    github_release,
    httpheader,
    jsondata,
    never_current,
    pypi_release,
    python_checker,
)


def check_apiresponse(logger, r, error_cls, ok_codes=None):
    if ok_codes is None:
        ok_codes = (200,)

    if r.status_code not in ok_codes:
        try:
            data = r.json()
            message = data.get("message", "Unknown error")
        except Exception:
            message = "Not a valid JSON response"

        exc = error_cls(r.status_code, message)
        logger.error(exc.message)
        raise exc


# ~~~ GitHub


class GitHubApiError(ApiCheckError):
    API = "GitHub API"


def check_github_apiresponse(logger, r, ok_codes=None):
    return check_apiresponse(logger, r, GitHubApiError, ok_codes=ok_codes)


class GitHubRateLimitCheckError(RateLimitCheckError):
    def __init__(self, remaining, ratelimit, reset):
        if reset:
            message = f"GitHub rate limit exceeded, reset at {reset}"
        else:
            message = "GitHub rate limit exceeded"
        super().__init__(message, remaining=remaining, limit=ratelimit, reset=reset)


def check_github_ratelimit(logger, r):
    try:
        ratelimit = int(r.headers.get("X-RateLimit-Limit", None))
    except Exception:
        ratelimit = None

    try:
        remaining = int(r.headers.get("X-RateLimit-Remaining", None))
    except Exception:
        remaining = None

    reset = r.headers["X-RateLimit-Reset"] if "X-RateLimit-Reset" in r.headers else None
    try:
        import time

        reset = time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(reset)))
    except Exception:
        reset = None

    logger.debug(
        "Github rate limit: {}/{}, reset at {}".format(
            remaining if remaining is not None else "?",
            ratelimit if ratelimit is not None else "?",
            reset if reset is not None else "?",
        )
    )

    if remaining == 0:
        raise GitHubRateLimitCheckError(remaining, ratelimit, reset)


# ~~~ Forgejo


class ForgejoApiError(ApiCheckError):
    API = "Forgejo API"


def check_forgejo_apiresponse(logger, r, ok_codes=None):
    return check_apiresponse(logger, r, ForgejoApiError, ok_codes=ok_codes)
