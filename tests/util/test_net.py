__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import socket
from unittest import mock

import pytest

import octoprint.util.net


def patched_interfaces():
    return ["eth0"]


def patched_ifaddresses(addr, netmask):
    if addr == "eth0":
        return {
            socket.AF_INET: [
                {"addr": "192.168.123.10", netmask: "255.255.255.0"},
                {"addr": "12.1.1.10", netmask: "255.0.0.0"},
            ],
            socket.AF_INET6: [
                {"addr": "2a01:4f8:1c0c:6958::1", netmask: "ffff:ffff:ffff:ffff::/64"}
            ],
        }

    return {}


def patched_ifaddresses_mask(addr):
    return patched_ifaddresses(addr, "mask")


def patched_ifaddresses_netmask(addr):
    return patched_ifaddresses(addr, "netmask")


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
        ("11.1.2.3", ["11.0.0.0/8"], True),
        ("12.1.1.123", [], True),
        ("2a01:4f8:1c0c:6958::1:23", [], True),
        ("fe80::89f3:31bb:ced0:2093%wlan0", [], True),
        (None, [], True),
    ],
)
def test_is_lan_address(input_address, input_additional, expected):
    with mock.patch(
        "netifaces.interfaces", side_effect=patched_interfaces
    ), mock.patch.object(octoprint.util.net, "HAS_V6", True):
        for side_effect in (patched_ifaddresses_mask, patched_ifaddresses_netmask):
            with mock.patch("netifaces.ifaddresses", side_effect=side_effect):
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
    "address,expected",
    [
        ({"mask": "192.168.0.0/24"}, "192.168.0.0/24"),
        ({"netmask": "192.168.0.0/24"}, "192.168.0.0/24"),
    ],
)
def test_get_netmask(address, expected):
    assert octoprint.util.net.get_netmask(address) == expected


def test_get_netmask_broken_address():
    with pytest.raises(ValueError):
        octoprint.util.net.get_netmask({"nm": "192.168.0.0/24"})


@pytest.mark.parametrize(
    "remote_addr,header,trusted_proxies,expected",
    [
        (
            "127.0.0.1",
            None,
            ["127.0.0.1", "::1"],
            "127.0.0.1",
        ),  # direct access via ipv4 localhost
        (
            "::1",
            None,
            ["127.0.0.1", "::1"],
            "::1",
        ),  # direct access via ipv6 localhost
        (
            "192.168.1.10",
            None,
            ["127.0.0.1", "::1"],
            "192.168.1.10",
        ),  # direct access via lan
        (
            "127.0.0.1",
            "192.168.1.10",
            ["127.0.0.1", "::1"],
            "192.168.1.10",
        ),  # access through reverse proxy on 127.0.0.1
        (
            "127.0.0.1",
            "10.1.2.3, 192.168.1.10",
            ["127.0.0.1", "::1", "192.168.1.10"],
            "10.1.2.3",
        ),  # access through trusted reverse proxies on 127.0.0.1 and 192.168.1.10
        (
            "127.0.0.1",
            "10.1.2.3, 192.168.1.10",
            ["127.0.0.1", "::1", "192.168.1.0/24"],
            "10.1.2.3",
        ),  # access through trusted reverse proxies on 127.0.0.1 and something on 192.168.1.0/24
        (
            "127.0.0.1",
            "10.1.2.3, 192.168.1.10",
            ["127.0.0.1", "::1", "unknown", "192.168.1.0/24"],
            "10.1.2.3",
        ),  # access through trusted reverse proxies on 127.0.0.1 and something on 192.168.1.0/24, invalid proxy in between
        (
            "::1",
            "fd12:3456:789a:2::1, fd12:3456:789a:1::1",
            ["127.0.0.1", "::1", "fd12:3456:789a:1::/64"],
            "fd12:3456:789a:2::1",
        ),  # access through trusted reverse proxies on ::1 and something on fd12:3456:789a:1::/64
        (
            "127.100.100.1",
            "10.1.2.3, 192.168.1.10",
            ["0.0.0.0/0"],
            "127.100.100.1",
        ),  # everything is trusted (BAD IDEA!)
        (
            "192.168.1.10",
            "127.0.0.1",
            ["127.0.0.1", "::1"],
            "192.168.1.10",
        ),  # spoofing attempt #1: direct access via lan, spoofed to 127.0.0.1
        (
            "::ffff:192.168.1.10",
            "::1",
            ["127.0.0.1", "::1"],
            "192.168.1.10",
        ),  # spoofing attempt #2: direct access via lan, spoofed to ::1
        (
            "127.0.0.1",
            "127.0.0.1, 192.168.1.10",
            ["127.0.0.1", "::1"],
            "192.168.1.10",
        ),  # spoofing attempt #3: access through reverse proxy on 127.0.0.1, real ip 192.168.1.10, spoofed to 127.0.0.1
        (
            "::1",
            "::1, ::ffff:192.168.1.10",
            ["127.0.0.1", "::1"],
            "192.168.1.10",
        ),  # spoofing attempt #4: access through reverse proxy on ::1, real ip 192.168.1.10, spoofed to ::1
        (
            "127.0.0.1",
            "127.0.0.1, 10.1.2.3, 192.168.1.10",
            ["127.0.0.1", "::1", "192.168.1.10"],
            "10.1.2.3",
        ),  # spoofing attempt #5: access through trusted reverse proxies on 127.0.0.1 and 192.168.1.10, real ip 10.1.2.3, spoofed to 127.0.0.1
        (
            "::1",
            "::1, fd12:3456:789a:2::1, fd12:3456:789a:1::1",
            ["127.0.0.1", "::1", "fd12:3456:789a:1::/64"],
            "fd12:3456:789a:2::1",
        ),  # spoofing attempt #6: access through trusted reverse proxies on ::1 and something on fd12:3456:789a:1::/64, spoofed to ::1
    ],
)
def test_get_http_client_ip(remote_addr, header, trusted_proxies, expected):
    assert (
        octoprint.util.net.get_http_client_ip(remote_addr, header, trusted_proxies)
        == expected
    )


@pytest.mark.parametrize(
    "proxies,add_localhost,expected",
    [
        (["10.0.0.1"], True, ["127.0.0.0/8", "::1", "10.0.0.1"]),
        ([], True, ["127.0.0.0/8", "::1"]),
        (None, True, ["127.0.0.0/8", "::1"]),
        (["10.0.0.1"], False, ["10.0.0.1"]),
        (None, False, []),
    ],
)
def test_usable_trusted_proxies(proxies, add_localhost, expected):
    assert octoprint.util.net.usable_trusted_proxies(proxies, add_localhost) == expected


def test_usable_trusted_proxies_from_settings():
    settings = mock.Mock()
    settings.get.return_value = ["10.0.0.1"]
    settings.getBoolean.return_value = True

    with mock.patch.object(octoprint.util.net, "usable_trusted_proxies") as patched:
        octoprint.util.net.usable_trusted_proxies_from_settings(settings)

        settings.get.assert_called_once_with(["server", "reverseProxy", "trustedProxies"])
        settings.getBoolean.assert_called_once_with(
            ["server", "reverseProxy", "trustLocalhostProxies"]
        )
        patched.assert_called_once_with(["10.0.0.1"], add_localhost=True)
