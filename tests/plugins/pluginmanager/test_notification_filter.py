import unittest

import ddt


@ddt.ddt
class NotificationFilterTest(unittest.TestCase):
    @ddt.data(
        (
            {"plugin": "foo", "text": "text", "date": "2020-09-15 00:00:00Z"},
            "1.0.0",
            "1.5.0",
            True,
        ),
        (
            {
                "plugin": "foo",
                "text": "text",
                "date": "2020-09-15 00:00:00Z",
                "pluginversions": [">=1.0.0"],
            },
            "1.0.0",
            "1.5.0",
            True,
        ),
        (
            {
                "plugin": "foo",
                "text": "text",
                "date": "2020-09-15 00:00:00Z",
                "pluginversions": [">=2.0.0", "0.9.0", "0.9.1", "1.0.0"],
            },
            "1.0.0",
            "1.5.0",
            True,
        ),
        (
            {
                "plugin": "foo",
                "text": "text",
                "date": "2020-09-15 00:00:00Z",
                "pluginversions": [">=2.0.0", "0.9.0", "0.9.1", "1.0.0"],
            },
            "1.1.0",
            "1.5.0",
            False,
        ),
        (
            {
                "plugin": "foo",
                "text": "text",
                "date": "2020-09-15 00:00:00Z",
                "versions": ["0.9.0", "0.9.1", "1.0.0", "1.0.1"],
            },
            "1.0.0",
            "1.5.0",
            True,
        ),
        (
            {
                "plugin": "foo",
                "text": "text",
                "date": "2020-09-15 00:00:00Z",
                "versions": ["0.9.0", "0.9.1", "1.0.0", "1.0.1"],
            },
            "1.1.0",
            "1.5.0",
            False,
        ),
        (
            {
                "plugin": "foo",
                "text": "text",
                "date": "2020-09-15 00:00:00Z",
                "octoversions": ["1.5.0"],
            },
            "1.0.0",
            "1.5.0",
            True,
        ),
        (
            {
                "plugin": "foo",
                "text": "text",
                "date": "2020-09-15 00:00:00Z",
                "octoversions": ["==1.4.2"],
            },
            "1.0.0",
            "1.5.0",
            False,
        ),
    )
    @ddt.unpack
    def test_notification_filter(
        self, notification, plugin_version, octoprint_version, expected
    ):
        from octoprint.plugins.pluginmanager import _filter_relevant_notification

        result = _filter_relevant_notification(
            notification, plugin_version, octoprint_version
        )

        self.assertEqual(expected, result)
