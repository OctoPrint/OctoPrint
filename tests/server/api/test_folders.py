# coding=utf-8
"""
Unit tests for ``octoprint.server.api`` folders.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import unittest
import ddt
import json

import octoprint.settings
from octoprint.server import app
app.testing = True

from octoprint.settings import settings

from octoprint.server.api import api
app.register_blueprint(api, url_prefix="/api")

@ddt.ddt
class GetFolderUsageTest(unittest.TestCase):

    def setUp(self):
        # Use Flask's test client for our test.
        self.test_app = app.test_client()

    def test_readUsageForFolder(self):
        response = self.test_app.get('/api/folders/local/uploads/usage')
        self.assertEquals(response.status, '200 OK')
        self.assertEquals(response.body, json.dumps({'folder': 'uploads', 'free': 10, 'total': 20}))
