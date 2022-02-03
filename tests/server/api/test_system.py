"""
Unit tests for ``octoprint.server.api`` system.
"""


__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
from unittest import mock


class GetFolderUsageTest(unittest.TestCase):
    def test_readUsageForFolder(self):
        from octoprint.server.api.system import _usageForFolders

        with mock.patch("psutil.disk_usage") as disk_usage_mock:
            disk_usage = mock.MagicMock()
            disk_usage.free = 50
            disk_usage.total = 512
            disk_usage_mock.return_value = disk_usage

            with mock.patch("octoprint.server.api.system.s") as settings_mock:
                settings = mock.MagicMock()
                settings.get.return_value = {"uploads": "mocked"}
                settings.getBaseFolder.return_value = "mocked"
                settings_mock.return_value = settings

                data = _usageForFolders()
                self.assertEqual(data["uploads"]["free"], 50)
                self.assertEqual(data["uploads"]["total"], 512)
