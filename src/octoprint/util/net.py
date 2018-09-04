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

def is_lan_address(address, additional_private=None):
	import netaddr
	import netifaces

	ip = netaddr.IPAddress(address)
	if ip.is_private() or ip.is_loopback():
		return True

	if additional_private is None or not isinstance(additional_private, (list, tuple)):
		additional_private = []

	subnets = netaddr.IPSet()
	for additional in additional_private:
		try:
			subnets.add(netaddr.IPNetwork(additional))
		except:
			pass

	for interface in netifaces.interfaces():
		addrs = netifaces.ifaddresses(interface)
		for v4 in addrs.get(socket.AF_INET, ()):
			try:
				subnets.add(netaddr.IPNetwork(v4["addr"], v4["netmask"]))
			except:
				pass

		if HAS_V6:
			for v6 in addrs.get(socket.AF_INET6, ()):
				try:
					subnets.add(netaddr.IPNetwork(v6["addr"], v6["netmask"]))
				except:
					pass

	if ip in subnets:
		return True

	return False
