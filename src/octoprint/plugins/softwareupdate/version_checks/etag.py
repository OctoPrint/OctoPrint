# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

import requests
import logging

from ..exceptions import ConfigurationInvalid, NetworkError, CannotCheckOffline

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.etag")

def get_latest(target, check, online=True):
	if not online:
		raise CannotCheckOffline()

	url = check.get("etag_url", check.get("url"))
	current = check.get("current")

	if url is None:
		raise ConfigurationInvalid("ETag version check needs etag_url or url set")

	try:
		with requests.head(url) as r:
			latest = r.headers.get("Etag")
	except Exception as exc:
		raise NetworkError(cause=exc)

	information = dict(local=dict(name="ETag {}".format(current if current else "-"), value=current),
	                   remote=dict(name="ETag {}".format(latest if latest else "-"), value=latest))

	logger.debug("Target: {}, local: {}, remote: {}".format(target, information["local"]["name"], information["remote"]["name"]))

	return information, current is None or current == latest or latest is None
