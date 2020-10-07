# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


def can_perform_update(target, check, online=True):
    return (
        "python_updater" in check
        and check["python_updater"] is not None
        and hasattr(check["python_updater"], "perform_update")
        and (online or check.get("offline", False))
    )


def perform_update(target, check, target_version, log_cb=None, online=True):
    from ..exceptions import CannotUpdateOffline

    if not online and not check("offline", False):
        raise CannotUpdateOffline()

    try:
        return check["python_updater"].perform_update(
            target, check, target_version, log_cb=log_cb, online=online
        )
    except Exception:
        import inspect

        args, _, _, _ = inspect.getargspec(check["python_updater"].perform_update)
        if "online" not in args:
            # old python_updater footprint, simply leave out the online parameter
            return check["python_updater"].perform_update(
                target, check, target_version, log_cb=log_cb
            )

        # some other error, raise again
        raise
