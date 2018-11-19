# coding=utf-8
"""
Unit tests for ``octoprint.server.api`` folders.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import ddt
import json
from mock import MagicMock
import psutil
import unittest

from octoprint.settings import settings
from octoprint.server import app
from octoprint.server.api import api

settings(init=True)
app.testing = True
app.register_blueprint(api, url_prefix="/api")

class UsageStub(object):
    pass

@ddt.ddt
class GetFolderUsageTest(unittest.TestCase):

    def setUp(self):
        # Use Flask's test client for our test.
        self.test_app = app.test_client()

    def test_readUsageForFolder(self):
        usage_stub = UsageStub()
        usage_stub.free = 10
        usage_stub.total = 20

        psutil.disk_usage = MagicMock(return_value=usage_stub)

        response = self.test_app.get('/api/folders/local/uploads/usage')
        data = json.loads(response.data)

        self.assertEquals(response.status, '200 OK')
        self.assertEquals(data['folder'], 'uploads')
        self.assertEquals(data['free'], 10)
        self.assertEquals(data['total'], 20)
