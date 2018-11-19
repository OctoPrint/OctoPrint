# coding=utf-8
"""
Unit tests for ``octoprint.server.api`` folders.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import json
from mock import MagicMock
import psutil
from random import randint
import unittest

from octoprint.settings import settings
from octoprint.server import app
from octoprint.server.api import api

# Initialize settings
settings(init=True)

# Set up app for testing and register api
app.testing = True
app.register_blueprint(api, url_prefix="/api")

class UsageStub():
    """Stub return object for psutil.disk_usage"""
    def __init__(self, free=1, total=2):
        self.free = free
        self.total = total

class GetFolderUsageTest(unittest.TestCase):

    def setUp(self):
        # Use Flask's test client for our test.
        self.test_app = app.test_client()

    def test_readUsageForFolder(self):
        usage_stub = UsageStub(free=randint(0, 100), total=randint(200, 1000))
        psutil.disk_usage = MagicMock(return_value=usage_stub)

        response = self.test_app.get('/api/folders/local/uploads/usage')
        data = json.loads(response.data)

        self.assertEquals(response.status, '200 OK')
        self.assertEquals(data['folder'], 'uploads')
        self.assertEquals(data['free'], usage_stub.free)
        self.assertEquals(data['total'], usage_stub.total)
