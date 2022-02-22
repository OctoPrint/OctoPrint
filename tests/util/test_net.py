__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import socket
import unittest
from unittest import mock

import ddt

import octoprint.util.net


def patched_interfaces():
    return ["eth0"]


def patched_ifaddresses(addr):
    if addr == "eth0":
        return {
            socket.AF_INET: [
                {"addr": "192.168.123.10", "netmask": "255.255.255.0"},
                {"addr": "12.1.1.10", "netmask": "255.0.0.0"},
            ],
            socket.AF_INET6: [
                {"addr": "2a01:4f8:1c0c:6958::1", "netmask": "ffff:ffff:ffff:ffff::/64"}
            ],
        }

    return {}


@ddt.ddt
class UtilNetTest(unittest.TestCase):
    @ddt.data(
        ("127.0.0.1", [], True),
        ("192.168.123.234", [], True),
        ("172.24.0.1", [], True),
        ("10.1.2.3", [], True),
        ("fc00::1", [], True),
        ("::1", [], True),
        ("::ffff:192.168.1.1", [], True),
        ("::ffff:8.8.8.8", [], False),
        ("11.1.2.3", [], False),
        ("11.1.2.3", ["11/8"], True),
        ("12.1.1.123", [], True),
        ("2a01:4f8:1c0c:6958::1:23", [], True),
        ("fe80::89f3:31bb:ced0:2093%wlan0", [], True),
        (None, [], True),
    )
    @ddt.unpack
    @mock.patch("netifaces.interfaces", side_effect=patched_interfaces)
    @mock.patch("netifaces.ifaddresses", side_effect=patched_ifaddresses)
    @mock.patch.object(octoprint.util.net, "HAS_V6", True)
    def test_is_lan_address(self, input_address, input_additional, expected, nifa, nifs):
        actual = octoprint.util.net.is_lan_address(
            input_address, additional_private=input_additional
        )
        self.assertEqual(expected, actual)

    @ddt.data(
        ("fe80::89f3:31bb:ced0:2093%wlan0", "fe80::89f3:31bb:ced0:2093"),
        ("2a01:4f8:1c0c:6958::1:23", "2a01:4f8:1c0c:6958::1:23"),
        ("10.1.2.3", "10.1.2.3"),
    )
    @ddt.unpack
    def test_strip_interface_tag(self, address, expected):
        actual = octoprint.util.net.strip_interface_tag(address)
        self.assertEqual(expected, actual)

    @ddt.data(
        ("::ffff:192.168.1.1", "192.168.1.1"),
        ("::ffff:2a01:4f8", "::ffff:2a01:4f8"),
        ("2a01:4f8:1c0c:6958::1:23", "2a01:4f8:1c0c:6958::1:23"),
        ("11.1.2.3", "11.1.2.3"),
    )
    @ddt.unpack
    def test_unmap_v4_in_v6(self, address, expected):
        actual = octoprint.util.net.unmap_v4_as_v6(address)
        self.assertEqual(expected, actual)
