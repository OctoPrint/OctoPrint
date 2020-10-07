# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

"""
This module bundles platform specific flags and implementations.
"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import sys

try:
    import fcntl
except ImportError:
    fcntl = None

# set_close_exec

if fcntl is not None and hasattr(fcntl, "FD_CLOEXEC"):

    def set_close_exec(handle):
        """Set ``close_exec`` flag on handle, if supported by the OS."""
        flags = fcntl.fcntl(handle, fcntl.F_GETFD)
        flags |= fcntl.FD_CLOEXEC
        fcntl.fcntl(handle, fcntl.F_SETFD, flags)


elif sys.platform == "win32":

    def set_close_exec(handle):
        """Set ``close_exec`` flag on handle, if supported by the OS."""
        import ctypes
        import ctypes.wintypes

        # see https://msdn.microsoft.com/en-us/library/ms724935(v=vs.85).aspx
        SetHandleInformation = ctypes.windll.kernel32.SetHandleInformation
        SetHandleInformation.argtypes = (
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD,
        )
        SetHandleInformation.restype = ctypes.c_bool

        HANDLE_FLAG_INHERIT = 0x00000001

        result = SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0)
        if not result:
            raise ctypes.GetLastError()


else:

    def set_close_exec(handle):
        """Set ``close_exec`` flag on handle, if supported by the OS."""
        # no-op
        pass


# default close_fds settings
CLOSE_FDS = True
"""
Default setting for close_fds parameter to Popen/sarge.run.

Set ``close_fds`` on every sub process to this to ensure file handlers will be closed
on child processes on platforms that support this (anything Python 3.7+ or anything
but win32 in earlier Python versions).
"""

if sys.platform == "win32" and sys.version_info < (3, 7):
    # close_fds=True is only supported on win32 with enabled stdout/stderr
    # capturing starting with Python 3.7
    CLOSE_FDS = False

# current os

_OPERATING_SYSTEMS = {
    "windows": ["win32"],
    "linux": lambda x: x.startswith("linux"),
    "macos": ["darwin"],
    "freebsd": lambda x: x.startswith("freebsd"),
}
OPERATING_SYSTEM_UNMAPPED = "unmapped"


def get_os():
    """
    Returns a canonical OS identifier.

    Currently the following OS are recognized: ``win32``, ``linux`` (``sys.platform`` = ``linux*``),
    ``macos`` (``sys.platform`` = ``darwin``) and ``freebsd`` (``sys.platform`` = ``freebsd*``).

    Returns:
            (str) mapped OS identifier
    """
    for identifier, platforms in _OPERATING_SYSTEMS.items():
        if (callable(platforms) and platforms(sys.platform)) or (
            isinstance(platforms, list) and sys.platform in platforms
        ):
            return identifier
    else:
        return OPERATING_SYSTEM_UNMAPPED


def is_os_compatible(compatibility_entries, current_os=None):
    """
    Tests if the ``current_os`` or ``sys.platform`` are blacklisted or whitelisted in ``compatibility_entries``

    Returns:
            (bool) True if the os is compatible, False otherwise
    """
    if len(compatibility_entries) == 0:
        # shortcut - no compatibility info means we are compatible
        return True

    if current_os is None:
        current_os = get_os()

    negative_entries = list(
        map(lambda x: x[1:], filter(lambda x: x.startswith("!"), compatibility_entries))
    )
    positive_entries = list(
        filter(lambda x: not x.startswith("!"), compatibility_entries)
    )

    negative_match = False
    if negative_entries:
        # check if we are blacklisted
        negative_match = current_os in negative_entries or any(
            map(lambda x: sys.platform.startswith(x), negative_entries)
        )

    positive_match = True
    if positive_entries:
        # check if we are whitelisted
        positive_match = current_os in positive_entries or any(
            map(lambda x: sys.platform.startswith(x), positive_entries)
        )

    return positive_match and not negative_match
