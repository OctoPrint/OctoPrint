__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import socket
from unittest import mock

import pytest

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


@pytest.mark.parametrize(
    "input_address,input_additional,expected",
    [
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
    ],
)
def test_is_lan_address(input_address, input_additional, expected):
    with mock.patch("netifaces.interfaces", side_effect=patched_interfaces), mock.patch(
        "netifaces.ifaddresses", side_effect=patched_ifaddresses
    ), mock.patch.object(octoprint.util.net, "HAS_V6", True):
        assert (
            octoprint.util.net.is_lan_address(
                input_address, additional_private=input_additional
            )
            == expected
        )


@pytest.mark.parametrize(
    "address,expected",
    [
        ("fe80::89f3:31bb:ced0:2093%wlan0", "fe80::89f3:31bb:ced0:2093"),
        ("2a01:4f8:1c0c:6958::1:23", "2a01:4f8:1c0c:6958::1:23"),
        ("10.1.2.3", "10.1.2.3"),
    ],
)
def test_strip_interface_tag(address, expected):
    assert octoprint.util.net.strip_interface_tag(address) == expected


@pytest.mark.parametrize(
    "address,expected",
    [
        ("::ffff:192.168.1.1", "192.168.1.1"),
        ("::ffff:2a01:4f8", "::ffff:2a01:4f8"),
        ("2a01:4f8:1c0c:6958::1:23", "2a01:4f8:1c0c:6958::1:23"),
        ("11.1.2.3", "11.1.2.3"),
    ],
)
def test_unmap_v4_in_v6(address, expected):
    assert octoprint.util.net.unmap_v4_as_v6(address) == expected


@pytest.mark.parametrize(
    "remote_addr,header,trusted_proxies,expected",
    [
        ("127.0.0.1", None, ["127.0.0.1"], "127.0.0.1"),  # direct access via localhost
        ("192.168.1.10", None, ["127.0.0.1"], "192.168.1.10"),  # direct access via lan
        (
            "127.0.0.1",
            "192.168.1.10",
            ["127.0.0.1"],
            "192.168.1.10",
        ),  # access through reverse proxy on 127.0.0.1
        (
            "127.0.0.1",
            "10.1.2.3, 192.168.1.10",
            ["127.0.0.1", "192.168.1.10"],
            "10.1.2.3",
        ),  # access through trusted reverse proxies on 127.0.0.1 and 192.168.1.10
        (
            "192.168.1.10",
            "127.0.0.1",
            ["127.0.0.1"],
            "192.168.1.10",
        ),  # spoofing attempt #1: direct access via lan, spoofed to 127.0.0.1
        (
            "127.0.0.1",
            "127.0.0.1, 192.168.1.10",
            ["127.0.0.1"],
            "192.168.1.10",
        ),  # spoofing attempt #2: access through reverse proxy on 127.0.0.1, real ip 192.168.1.10, spoofed to 127.0.0.1
        (
            "127.0.0.1",
            "127.0.0.1, 10.1.2.3, 192.168.1.10",
            ["127.0.0.1", "192.168.1.10"],
            "10.1.2.3",
        ),  # spoofing attempt #3: access through trusted reverse proxies on 127.0.0.1 and 192.168.1.10, real ip 10.1.2.3, spoofed to 127.0.0.1
    ],
)
def test_get_http_client_ip(remote_addr, header, trusted_proxies, expected):
    assert (
        octoprint.util.net.get_http_client_ip(remote_addr, header, trusted_proxies)
        == expected
    )
