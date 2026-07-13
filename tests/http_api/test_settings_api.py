import pytest
import urllib3

pytestmark = pytest.mark.http_api


def _verify_tree_restricted(tree: dict, expected: dict = None):
    if expected is None:
        expected = {}

    for key in tree:
        value = tree[key]
        exp = expected.get(key)

        if exp is not None and not isinstance(exp, dict):
            if callable(exp):
                exp(value)
            else:
                assert value == exp

        else:
            if isinstance(value, dict):
                _verify_tree_restricted(value, exp)
            elif isinstance(value, list):
                assert len(value) == 0
            else:
                assert value is None


def _not_none(value):
    assert value is not None


def test_user(base_url, user_credentials):
    hdrs = {
        "Authorization": f"Bearer {user_credentials['apikey']}",
        "X-OctoPrint-Api-Version": "2.0.0",
    }

    resp = urllib3.request("GET", base_url + "/api/settings", headers=hdrs)
    data = resp.json()

    _verify_tree_restricted(data["accessControl"])
    _verify_tree_restricted(data["api"])
    _verify_tree_restricted(data["devel"])
    _verify_tree_restricted(data["folder"])
    _verify_tree_restricted(data["server"])
    _verify_tree_restricted(data["system"])
    _verify_tree_restricted(data["scripts"])

    assert data["feature"]["pollWatched"] is None
    assert data["gcodeAnalysis"]["runAt"] is None
    assert data["webcam"]["bitrate"] is None
    assert data["webcam"]["ffmpegPath"] is None
    assert data["webcam"]["ffmpegCommandline"] is None
    assert data["webcam"]["ffmpegThreads"] is None
    assert data["webcam"]["watermark"] is None

    # serial connector
    _verify_tree_restricted(
        data["plugins"]["serial_connector"],
        {"log": _not_none, "ignoreEmptyPorts": _not_none},
    )

    # API version 2.0.0
    assert "printerConnection" in data
    assert "serial" not in data
    assert "autoUppercaseBlocklist" in data["feature"]
    assert "autoUppercaseBlacklist" not in data["feature"]
    assert "pluginBlocklist" in data["server"]
    assert "pluginBlacklist" not in data["server"]
    assert "events" not in data.get("system", {})


def test_user_pre_2_0_0(base_url, user_credentials):
    hdrs = {"Authorization": f"Bearer {user_credentials['apikey']}"}

    resp = urllib3.request("GET", base_url + "/api/settings", headers=hdrs)
    data = resp.json()

    # API version <2.0.0
    assert "printerConnection" not in data
    assert "autoUppercaseBlacklist" in data["feature"]
    assert "autoUppercaseBlocklist" not in data["feature"]
    assert "pluginBlacklist" in data["server"]
    assert "pluginBlocklist" not in data["server"]
    assert "events" in data["system"]

    _verify_tree_restricted(
        data["serial"], {"log": _not_none, "ignoreEmptyPorts": _not_none}
    )


def test_admin(base_url, admin_credentials):
    hdrs = {
        "Authorization": f"Bearer {admin_credentials['apikey']}",
        "X-OctoPrint-Api-Version": "2.0.0",
    }

    resp = urllib3.request("GET", base_url + "/api/settings", headers=hdrs)
    data = resp.json()

    assert "accessControl" in data
    assert data["accessControl"]["autologinLocal"] is not None
    assert data["accessControl"]["autologinHeadsupAcknowledged"] is not None
    assert data["accessControl"]["defaultReauthenticationTimeout"] is not None

    assert "api" in data
    assert "key" in data["api"]
    assert data["api"]["allowCrossOrigin"] is not None
