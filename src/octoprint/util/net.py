# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import socket
import sys
import netaddr
import logging
import threading
import io
import os
import re

import netifaces
import requests

_cached_check_v6 = None
def check_v6():
	global _cached_check_v6

	def f():
		if not socket.has_ipv6:
			return False

		try:
			socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
		except Exception:
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
	if not address:
		# no address is LAN address
		return True

	try:
		address = unmap_v4_as_v6(address)
		address = strip_interface_tag(address)

		ip = netaddr.IPAddress(address)
		if ip.is_private() or ip.is_loopback():
			return True

		if additional_private is None or not isinstance(additional_private, (list, tuple)):
			additional_private = []

		subnets = netaddr.IPSet()
		for additional in additional_private:
			try:
				subnets.add(netaddr.IPNetwork(additional))
			except Exception:
				if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
					logging.getLogger(__name__).exception("Error while trying to add additional private network to local subnets: {}".format(additional))

		def to_ipnetwork(address):
			prefix = address["netmask"]
			if "/" in prefix:
				# v6 notation in netifaces output, e.g. "ffff:ffff:ffff:ffff::/64"
				_, prefix = prefix.split("/")

			addr = strip_interface_tag(address["addr"])
			return netaddr.IPNetwork("{}/{}".format(addr, prefix))

		for interface in netifaces.interfaces():
			addrs = netifaces.ifaddresses(interface)
			for v4 in addrs.get(socket.AF_INET, ()):
				try:
					subnets.add(to_ipnetwork(v4))
				except Exception:
					if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
						logging.getLogger(__name__).exception("Error while trying to add v4 network to local subnets: {!r}".format(v4))

			if HAS_V6:
				for v6 in addrs.get(socket.AF_INET6, ()):
					try:
						subnets.add(to_ipnetwork(v6))
					except Exception:
						if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
							logging.getLogger(__name__).exception("Error while trying to add v6 network to local subnets: {!r}".format(v6))

		if ip in subnets:
			return True

		return False

	except Exception:
		# we are extra careful here since an unhandled exception in this method will effectively nuke the whole UI
		logging.getLogger(__name__).exception("Error while trying to determine whether {} is a local address".format(address))
		return True


def strip_interface_tag(address):
	if "%" in address:
		# interface comment, e.g. "fe80::457f:bbee:d579:1063%wlan0"
		address = address[:address.find("%")]
	return address


def unmap_v4_as_v6(address):
	if address.lower().startswith("::ffff:") and "." in address:
		# ipv6 mapped ipv4 address, unmap
		address = address[len("::ffff:"):]
	return address


def interface_addresses(family=None):
	"""
	Retrieves all of the host's network interface addresses.
	"""

	import netifaces
	if not family:
		family = netifaces.AF_INET

	for interface in netifaces.interfaces():
		try:
			ifaddresses = netifaces.ifaddresses(interface)
		except Exception:
			continue
		if family in ifaddresses:
			for ifaddress in ifaddresses[family]:
				if not ifaddress["addr"].startswith("169.254."):
					yield ifaddress["addr"]


def address_for_client(host, port, timeout=3.05):
	"""
	Determines the address of the network interface on this host needed to connect to the indicated client host and port.
	"""

	for address in interface_addresses():
		try:
			if server_reachable(host, port, timeout=timeout, proto="udp", source=address):
				return address
		except Exception:
			continue


def server_reachable(host, port, timeout=3.05, proto="tcp", source=None):
	"""
	Checks if a server is reachable

	Args:
		host (str): host to check against
		port (int): port to check against
		timeout (float): timeout for check
		proto (str): ``tcp`` or ``udp``
		source (str): optional, socket used for check will be bound against this address if provided

	Returns:
		boolean: True if a connection to the server could be opened, False otherwise
	"""

	import socket

	if proto not in ("tcp", "udp"):
		raise ValueError("proto must be either 'tcp' or 'udp'")

	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if proto == "udp" else socket.SOCK_STREAM)
		sock.settimeout(timeout)
		if source is not None:
			sock.bind((source, 0))
		sock.connect((host, port))
		return True
	except Exception:
		return False

def resolve_host(host):
	import socket
	from octoprint.util import to_unicode

	try:
		return [to_unicode(x[4][0]) for x in socket.getaddrinfo(host, 80)]
	except Exception:
		return []


def download_file(url, folder, max_length=None):
	with requests.get(url, stream=True) as r:
		r.raise_for_status()
		if "Content-Disposition" in r.headers.keys():
			filename = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
		else:
			filename = url.split("/")[-1]

		assert len(filename) > 0

		# TODO check content-length against safety limit

		path = os.path.join(folder, filename)
		with io.open(path, 'wb') as f:
			for chunk in r.iter_content(chunk_size=8192):
				f.write(chunk)
	return path
