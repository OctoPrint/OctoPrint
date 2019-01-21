# coding=utf-8
"""
Unit tests for ``octoprint.server.api`` system.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import json
import mock
import psutil
import unittest

import octoprint
from octoprint.settings import settings
from octoprint.server import app

from octoprint.server.api.system import readUsageForFolder

class GetFolderUsageTest(unittest.TestCase):

    def setUp(self):
        self.settings_patcher = mock.patch("octoprint.server.api.system.s")
        self.settings_getter = self.settings_patcher.start()
        self.settings = mock.create_autospec(octoprint.settings.Settings)
        self.settings_getter.return_value = self.settings
        settings(self.settings)

    def cleanUp(self):
        self.settings_patcher.stop()

    def test_readUsageForFolder(self):
        with mock.patch("psutil.disk_usage") as disk_usage_mock:
            disk_usage_mock.free = 50
            disk_usage_mock.total = 512

        with app.app_context():
            data = json.loads(readUsageForFolder())
            self.assertEquals(data['usage']['uploads']['free'], 50)
            self.assertEquals(data['usage']['uploads']['total'], 512)
