__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
from unittest import mock

from octoprint.util import TemporaryDirectory

RSS_EXAMPLE = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
 <title>RSS Title</title>
 <description>This is an example of an RSS feed</description>
 <link>https://www.example.com/main.html</link>
 <copyright>2020 Example.com All rights reserved</copyright>
 <lastBuildDate>Mon, 06 Sep 2010 00:01:00 +0000</lastBuildDate>
 <pubDate>Sun, 06 Sep 2009 16:20:00 +0000</pubDate>
 <ttl>1800</ttl>
 <item>
  <title>Example entry</title>
  <description>Here is some text containing an interesting description.</description>
  <link>https://www.example.com/blog/post/1</link>
  <guid isPermaLink="false">7bd204c6-1655-4c27-aeee-53f933c5395f</guid>
  <pubDate>Sun, 06 Sep 2009 16:20:00 +0000</pubDate>
 </item>
</channel>
</rss>
"""


class TestAnnouncements(unittest.TestCase):
    def test_caches(self):
        from octoprint.plugins.announcements import AnnouncementPlugin

        plugin = AnnouncementPlugin()
        plugin._logger = mock.MagicMock()

        with TemporaryDirectory() as data_folder:
            plugin._data_folder = data_folder
            with mock.patch("requests.get") as mock_get:
                mock_get.return_value = mock.MagicMock(status_code=200)
                mock_get.return_value.text = RSS_EXAMPLE

                network_response = plugin._get_channel_data_from_network(
                    "test", {"url": "https://example.com/feed.xml"}
                )

            cache_response = plugin._get_channel_data_from_cache("test", {"ttl": 1000})

            self.maxDiff = 100000
            self.assertDictEqual(network_response, cache_response)
