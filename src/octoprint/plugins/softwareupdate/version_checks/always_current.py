# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


def get_latest(target, check, online=True, *args, **kwargs):
    current_version = check.get("current_version", "1.0.0")

    information = {
        "local": {"name": current_version, "value": current_version},
        "remote": {"name": current_version, "value": current_version},
    }

    return information, True
