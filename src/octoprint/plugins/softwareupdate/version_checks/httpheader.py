# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging

import requests

from ..exceptions import CannotCheckOffline, ConfigurationInvalid, NetworkError

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.etag")


def get_latest(target, check, online=True, *args, **kwargs):
    if not online:
        raise CannotCheckOffline()

    url = check.get("header_url", check.get("url"))
    header = check.get("header_name")

    if url is None or header is None:
        raise ConfigurationInvalid(
            "HTTP header version check needs header_url or url and header_name set"
        )

    current = check.get("current")
    method = check.get("header_method", "head")
    prefix = check.get("header_prefix", header)
    if prefix:
        prefix = "{} ".format(prefix)

    try:
        with requests.request(method, url) as r:
            latest = r.headers.get(header)
    except Exception as exc:
        raise NetworkError(cause=exc)

    information = {
        "local": {
            "name": "{}{}".format(prefix, current if current else "-"),
            "value": current,
        },
        "remote": {
            "name": "{}{}".format(prefix, latest if latest else "-"),
            "value": latest,
        },
    }

    logger.debug(
        "Target: {}, local: {}, remote: {}".format(
            target, information["local"]["name"], information["remote"]["name"]
        )
    )

    return information, current is None or current == latest or latest is None
