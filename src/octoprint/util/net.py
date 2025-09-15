__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import socket
import sys
from collections.abc import Generator
from typing import Optional

import ifaddr
import netaddr
import requests
import werkzeug.http
from werkzeug.utils import secure_filename

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
        # Python on Windows lacks IPPROTO_IPV6, but supports the socket options just fine, let's redefine it
        IPPROTO_IPV6 = 41
        IPV6_V6ONLY = 27
    else:
        # Whatever we are running on here, we don't want to use V6 on here due to lack of dual stack support
        HAS_V6 = False


def get_netmask(address) -> int:
    if isinstance(address, ifaddr.IP):
        addr = address.ip[0] if address.is_IPv6 else address.ip
        prefix = address.network_prefix
        return str(netaddr.IPNetwork(f"{addr}/{prefix}", flags=netaddr.NOHOST))

    # netifaces2 - see #5005
    netmask = address.get("mask")
    if netmask:
        return netmask

    # netifaces (backwards comp)
    netmask = address.get("netmask")
    if netmask:
        return netmask

    raise ValueError(f"No netmask found in address: {address!r}")


def get_lan_ranges(
    additional_private: Optional[list[str]] = None,
) -> set[netaddr.IPNetwork]:
    logger = logging.getLogger(__name__)

    if additional_private is None or not isinstance(additional_private, (list, tuple)):
        additional_private = []

    def to_ipnetwork(address: ifaddr.IP) -> netaddr.IPNetwork:
        prefix = address.network_prefix
        addr = strip_interface_tag(address.ip[0] if address.is_IPv6 else address.ip)
        return netaddr.IPNetwork(f"{addr}/{prefix}", flags=netaddr.NOHOST)

    subnets = set()

    for interface in ifaddr.get_adapters():
        for ip in interface.ips:
            if ip.is_IPv4:
                try:
                    subnets.add(to_ipnetwork(ip))
                except Exception:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception(
                            "Error while trying to add v4 network to local subnets: {!r}".format(
                                ip
                            )
                        )

            if HAS_V6 and ip.is_IPv6:
                try:
                    subnets.add(to_ipnetwork(ip))
                except Exception:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception(
                            "Error while trying to add v6 network to local subnets: {!r}".format(
                                ip
                            )
                        )

    for additional in additional_private:
        try:
            subnets.add(netaddr.IPNetwork(additional))
        except Exception:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(
                    "Error while trying to add additional private network to local subnets: {}".format(
                        additional
                    )
                )

    subnets |= set(netaddr.ip.IPV4_PRIVATE_USE) | {
        netaddr.ip.IPV4_LOOPBACK,
        netaddr.ip.IPV4_LINK_LOCAL,
    }
    if HAS_V6:
        subnets |= {
            netaddr.ip.IPV6_UNIQUE_LOCAL,
            netaddr.ip.IPV6_LOOPBACK,
            netaddr.ip.IPV6_LINK_LOCAL,
        }

    return subnets


def usable_trusted_proxies(proxies, add_localhost=True):
    if proxies is None or not isinstance(proxies, list):
        logging.getLogger(__name__).warning("Invalid trusted proxies, using defaults")
        proxies = []

    if add_localhost:
        return ["127.0.0.0/8", "::1"] + proxies
    else:
        return proxies


def usable_trusted_proxies_from_settings(settings):
    configured_trusted_proxies = settings.get(
        ["server", "reverseProxy", "trustedProxies"]
    )
    trust_localhost_proxies = settings.getBoolean(
        ["server", "reverseProxy", "trustLocalhostProxies"]
    )
    return usable_trusted_proxies(
        configured_trusted_proxies, add_localhost=trust_localhost_proxies
    )


def is_lan_address(address, additional_private=None):
    if not address:
        # no address is LAN address
        return True

    try:
        address = sanitize_address(address)
        ip = netaddr.IPAddress(address)
        subnets = get_lan_ranges(additional_private=additional_private)

        if any(ip in subnet for subnet in subnets):
            return True

        return False

    except Exception:
        # we are extra careful here since an unhandled exception in this method will effectively nuke the whole UI
        logging.getLogger(__name__).exception(
            "Error while trying to determine whether {} is a local address".format(
                address
            )
        )
        return True


def is_loopback_address(address):
    if not address:
        return False

    try:
        address = sanitize_address(address)
        ip = netaddr.IPAddress(address)
        return ip.is_loopback()
    except Exception:
        logging.get_logger(__name__).exception(
            f"Error while trying to determine whether {address} is a loopback address"
        )
        return False


def sanitize_address(address):
    address = unmap_v4_as_v6(address)
    address = strip_interface_tag(address)
    return address


def strip_interface_tag(address):
    if "%" in address:
        # interface comment, e.g. "fe80::457f:bbee:d579:1063%wlan0"
        address = address[: address.find("%")]
    return address


def unmap_v4_as_v6(address):
    if address.lower().startswith("::ffff:") and "." in address:
        # ipv6 mapped ipv4 address, unmap
        address = address[len("::ffff:") :]
    return address


def interface_addresses(
    family: Optional[int] = None,
    interfaces: Optional[list[str]] = None,
    ignored: Optional[list[str]] = None,
) -> Generator[str, None, None]:
    """
    Retrieves all of the host's network interface addresses.
    """

    if not family:
        family = socket.AF_INET

    assert family in (socket.AF_INET, socket.AF_INET6)

    if interfaces is None:
        interfaces = ifaddr.get_adapters()

    if ignored is not None:
        interfaces = [i for i in interfaces if i.name not in ignored]

    for interface in interfaces:
        ips = [
            ip
            for ip in interface.ips
            if (
                (family == socket.AF_INET and ip.is_IPv4)
                or (family == socket.AF_INET6 and ip.is_IPv6)
            )
        ]
        for ip in ips:
            ipstr = ip.ip if family == socket.AF_INET else ip.ip[0]
            address = netaddr.IPAddress(ipstr)
            if not address.is_link_local() and not address.is_loopback():
                yield ipstr


def address_for_client(
    host, port, timeout=3.05, addresses=None, interfaces=None, ignored=None
):
    """
    Determines the address of the network interface on this host needed to connect to the indicated client host and port.
    """

    if addresses is None:
        addresses = interface_addresses(interfaces=interfaces, ignored=ignored)

    for address in addresses:
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

    if HAS_V6:
        families = [socket.AF_INET6, socket.AF_INET]
    else:
        families = [socket.AF_INET]

    for family in families:
        try:
            sock = socket.socket(
                family, socket.SOCK_DGRAM if proto == "udp" else socket.SOCK_STREAM
            )
            sock.settimeout(timeout)
            if source is not None:
                sock.bind((source, 0))
            sock.connect((host, port))
            return True
        except Exception:
            pass
    return False


def resolve_host(host):
    import socket

    from octoprint.util import to_unicode

    try:
        return [to_unicode(x[4][0]) for x in socket.getaddrinfo(host, 80)]
    except Exception:
        return []


def download_file(url, folder, max_length=None, connect_timeout=3.05, read_timeout=7):
    with requests.get(url, stream=True, timeout=(connect_timeout, read_timeout)) as r:
        r.raise_for_status()

        filename = None
        if "Content-Disposition" in r.headers.keys():
            _, options = werkzeug.http.parse_options_header(
                r.headers["Content-Disposition"]
            )
            filename = options.get("filename")
        if filename is None:
            filename = url.split("/")[-1]

        filename = secure_filename(filename)
        assert len(filename) > 0

        # TODO check content-length against safety limit

        path = os.path.abspath(os.path.join(folder, filename))
        assert path.startswith(folder)

        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return path


def get_http_client_ip(remote_addr, forwarded_for, trusted_proxies):
    try:
        trusted_ip_set = netaddr.IPSet(trusted_proxies)
    except netaddr.AddrFormatError:
        # something's wrong with one of these addresses, let's add them one by one
        trusted_ip_set = netaddr.IPSet()
        for trusted_proxy in trusted_proxies:
            try:
                trusted_ip_set.add(trusted_proxy)
            except netaddr.AddrFormatError:
                logging.getLogger(__name__).error(
                    f"Trusted proxy {trusted_proxy} is not a correctly formatted IP address or subnet"
                )

    if forwarded_for is not None and sanitize_address(remote_addr) in trusted_ip_set:
        for addr in (
            sanitize_address(addr.strip()) for addr in reversed(forwarded_for.split(","))
        ):
            if addr not in trusted_ip_set:
                return addr
    return sanitize_address(remote_addr)
