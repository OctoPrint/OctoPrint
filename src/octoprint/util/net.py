# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import socket
import sys
import netaddr
import netifaces
import logging

_cached_check_v6 = None
def check_v6():
	global _cached_check_v6

	def f():
		if not socket.has_ipv6:
			return False

		try:
			socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
		except:
			# "[Errno 97] Address family not supported by protocol" or anything else really...
			return False
		return True

	if _cached_check_v6 is None:
		_cached_check_v6 = f()
	return _cached_check_v6

HAS_V6 = check_v6()

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
		# Whatever we are running on here, we don't want to use V6 on here due to lack of dual stack support
		HAS_V6 = False

def is_lan_address(address, additional_private=None):
	try:
		if address.lower().startswith("::ffff:") and "." in address:
			# ipv6 mapped ipv4 address, unmap
			address = address[len("::ffff:"):]

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
				if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
					logging.getLogger(__name__).exception("Error while trying to add additional private network to local subnets: {}".format(additional))

		def to_ipnetwork(address):
			prefix = address["netmask"]
			if "/" in prefix:
				# v6 notation in netifaces output, e.g. "ffff:ffff:ffff:ffff::/64"
				_, prefix = prefix.split("/")

			addr = address["addr"]
			if "%" in addr:
				# interface comment in netifaces output, e.g. "fe80::457f:bbee:d579:1063%wlan0"
				addr = addr[:addr.find("%")]
			return netaddr.IPNetwork("{}/{}".format(addr, prefix))

		for interface in netifaces.interfaces():
			addrs = netifaces.ifaddresses(interface)
			for v4 in addrs.get(socket.AF_INET, ()):
				try:
					subnets.add(to_ipnetwork(v4))
				except:
					if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
						logging.getLogger(__name__).exception("Error while trying to add v4 network to local subnets: {!r}".format(v4))

			if HAS_V6:
				for v6 in addrs.get(socket.AF_INET6, ()):
					try:
						subnets.add(to_ipnetwork(v6))
					except:
						if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
							logging.getLogger(__name__).exception("Error while trying to add v6 network to local subnets: {!r}".format(v6))

		if ip in subnets:
			return True

		return False

	except:
		# we are extra careful here since an unhandled exception in this method will effectively nuke the whole UI
		logging.getLogger(__name__).exception("Error while trying to determine whether {} is a local address".format(address))
		return True
