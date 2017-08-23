# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import sys

try:
	import fcntl
except ImportError:
	fcntl = None

# set_close_exec

if fcntl is not None and hasattr(fcntl, "FD_CLOEXEC"):
	def set_close_exec(handle):
		flags = fcntl.fcntl(handle, fcntl.F_GETFD)
		flags |= fcntl.FD_CLOEXEC
		fcntl.fcntl(handle, fcntl.F_SETFD, flags)

elif sys.platform == "win32":
	def set_close_exec(handle):
		import ctypes
		import ctypes.wintypes

		# see https://msdn.microsoft.com/en-us/library/ms724935(v=vs.85).aspx
		SetHandleInformation = ctypes.windll.kernel32.SetHandleInformation
		SetHandleInformation.argtypes = (ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD)
		SetHandleInformation.restype = ctypes.c_bool

		HANDLE_FLAG_INHERIT = 0x00000001

		result = SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0)
		if not result:
			raise ctypes.GetLastError()

else:
	def set_close_exec(handle):
		# no-op
		pass
