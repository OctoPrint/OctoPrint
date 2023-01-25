__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

import requests

from ..exceptions import CannotCheckOffline, ConfigurationInvalid, NetworkError

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.jsondata")


def get_latest(target, check, online=True, *args, **kwargs):
    if not online:
        raise CannotCheckOffline()

    url = check.get("jsondata")
    current = check.get("current")

    if url is None:
        raise ConfigurationInvalid("jsondata version check needs jsondata set")

    try:
        with requests.get(url, timeout=(3.05, 7)) as r:
            data = r.json()
    except Exception as exc:
        raise NetworkError(cause=exc)

    latest = data.get("version")

    information = {
        "local": {"name": current if current else "-", "value": current},
        "remote": {"name": latest if latest else "-", "value": latest},
    }

    logger.debug(
        "Target: {}, local: {}, remote: {}".format(
            target, information["local"]["name"], information["remote"]["name"]
        )
    )

    return information, current is None or current == latest or latest is None
