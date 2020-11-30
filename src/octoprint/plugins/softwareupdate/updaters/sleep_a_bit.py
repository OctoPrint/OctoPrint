# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


import time

from octoprint.util import monotonic_time


def can_perform_update(target, check, online=True):
    return True


def perform_update(target, check, target_version, log_cb=None, online=True):
    duration = check.get("duration", 30)

    now = monotonic_time()
    end = now + duration
    while now < end:
        log_cb(["{}s left...".format(end - now)], prefix=">", stream="output")
        time.sleep(5)
        now = monotonic_time()
