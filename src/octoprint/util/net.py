# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import socket
import sys

HAS_V6 = socket.has_ipv6

if hasattr(socket, "IPPROTO_IPV6") and hasattr(socket, "IPV6_V6ONLY"):
	# Dual stack support, hooray!
	IPPROTO_IPV6 = socket.IPPROTO_IPV6
	IPV6_V6ONLY = socket.IPV6_V6ONLY
else:
	if sys.platform == "win32":
		# Python 2.7 on Windows lacks IPPROTO_IPV6, but supports the socket options just fine, let's redefine it
		IPPROTO_IPV6 = 41
		IPV6_V6ONLY = 27
	else:
		# Whatever we are running on here, it we don't want to use V6 on here due to lack of dual stack support
		HAS_V6 = False
