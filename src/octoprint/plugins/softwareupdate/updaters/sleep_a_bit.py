__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


import time


def can_perform_update(target, check, online=True):
    return True


def perform_update(target, check, target_version, log_cb=None, online=True, force=False):
    duration = check.get("duration", 30)

    now = time.monotonic()
    end = now + duration
    while now < end:
        log_cb([f"{end - now}s left..."], prefix=">", stream="output")
        time.sleep(5)
        now = time.monotonic()
