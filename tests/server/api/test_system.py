# coding=utf-8
"""
Unit tests for ``octoprint.server.api`` system.
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import json
# from mock import MagicMock
import mock
import psutil
import unittest

import octoprint.users
from octoprint.settings import settings
from octoprint.server import app
from octoprint.server.api import api
import octoprint.server.util

# import flask
from flask import session

# Set up app for testing and register api
app.testing = True
app.register_blueprint(api, url_prefix="/api")


from contextlib import contextmanager
from flask import appcontext_pushed, g

@contextmanager
def user_set(app, user):
    def handler(sender, **kwargs):
        g.user = user
    with appcontext_pushed.connected_to(handler, app):
        yield

def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)

class GetFolderUsageTest(unittest.TestCase):

    def setUp(self):
        self.settings_patcher = mock.patch("octoprint.server.api.system.s") # needs to be adjusted to import
        self.settings_getter = self.settings_patcher.start()
        self.settings = mock.create_autospec(octoprint.settings.Settings)
        self.settings_getter.return_value = self.settings
        settings(self.settings)

        # Add an app secret for sessions
        app.config['SECRET_KEY'] = 'sekrit!'
        # Use Flask's test client for our test.
        self.test_app = app.test_client()

    def cleanUp(self):
        self.settings_patcher.stop()

    def test_readUsageForFolder(self):
        apikey = settings().get(["api", "key"])
        print("apikey: %s" % apikey)
        with mock.patch("psutil.disk_usage") as disk_usage_mock:
            disk_usage_mock.free = 50
            disk_usage_mock.total = 512

        # with user_set(app, self.user):
        # with app.test_client() as c:
        with self.test_app as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 'admin'
                sess['apikey'] = apikey
                print('Session:')
                print(sess)

            response = client.get('/api/system/usage', headers={ 'X-Api-Key': apikey })
            print("Response: ")
            print(response)
            self.assertEquals(response.status, '200 OK')

            data = json.loads(response.data)
            self.assertEquals(data['usage']['uploads']['free'], 50)
            self.assertEquals(data['usage']['uploads']['total'], 512)
