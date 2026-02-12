"""
Unit tests for ``octoprint.server.api`` /util/test API endpoint.
"""

import unittest
from unittest import mock

from flask import Flask


class MockResponse:
    def __init__(self, status_code, content_type):
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestUrlContentTypeFiltering(unittest.TestCase):
    """Tests for _test_url content type allowlist and blocklist."""

    def setUp(self):
        self.app = Flask(__name__)

    def _call(self, content_type, **filter_keys):
        from octoprint.server.api import _test_url

        with mock.patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse(
                status_code=200, content_type=content_type
            )
            data = {"url": "http://example.com/test", **filter_keys}
            with self.app.app_context():
                return _test_url(data).get_json()["result"]

    # allowlist: exact match

    def test_allowlist_exact_allows(self):
        self.assertTrue(self._call("image/png", content_type_allowlist=["image/png"]))

    def test_allowlist_exact_blocks(self):
        self.assertFalse(self._call("image/png", content_type_allowlist=["text/html"]))

    # allowlist: wildcard match

    def test_allowlist_wildcard_allows(self):
        self.assertTrue(self._call("image/png", content_type_allowlist=["image/*"]))

    def test_allowlist_wildcard_blocks(self):
        self.assertFalse(self._call("image/png", content_type_allowlist=["text/*"]))

    # blocklist: exact match

    def test_blocklist_exact_blocks(self):
        self.assertFalse(self._call("image/png", content_type_blocklist=["image/png"]))

    def test_blocklist_exact_allows(self):
        self.assertTrue(self._call("image/png", content_type_blocklist=["text/html"]))

    # blocklist: wildcard match

    def test_blocklist_wildcard_blocks(self):
        self.assertFalse(self._call("image/png", content_type_blocklist=["image/*"]))

    def test_blocklist_wildcard_allows(self):
        self.assertTrue(self._call("image/png", content_type_blocklist=["text/*"]))

    # legacy keys

    def test_legacy_whitelist_key(self):
        self.assertFalse(self._call("image/png", content_type_whitelist=["text/*"]))

    def test_legacy_blacklist_key(self):
        self.assertFalse(self._call("image/png", content_type_blacklist=["image/*"]))

    # combined

    def test_in_allowlist_and_blocklist_blocks(self):
        self.assertFalse(
            self._call(
                "image/png",
                content_type_allowlist=["image/*"],
                content_type_blocklist=["image/png"],
            )
        )

    # no filters

    def test_no_filters_allows_all(self):
        self.assertTrue(self._call("image/png"))


if __name__ == "__main__":
    unittest.main()
