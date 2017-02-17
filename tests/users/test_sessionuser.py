# coding=utf-8
"""
Unit tests for octoprint.users.SessionUser
"""
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import octoprint.users

class SessionUserTestCase(unittest.TestCase):

	def setUp(self):
		self.user = octoprint.users.User("username", "passwordHash", True, ("user",), apikey="apikey", settings=dict(key="value"))

	def test_two_sessions(self):
		session1 = octoprint.users.SessionUser(self.user)
		session2 = octoprint.users.SessionUser(self.user)

		self.assertNotEqual(session1.get_session(), session2.get_session())
		self.assertEqual(session1._user, session2._user)
		self.assertEqual(session1._username, session2._username)

	def test_settings_change_propagates(self):
		user = octoprint.users.SessionUser(self.user)
		self.user.set_setting("otherkey", "othervalue")

		self.assertDictEqual(dict(key="value", otherkey="othervalue"), user.get_all_settings())

	def test_repr(self):
		user = octoprint.users.SessionUser(self.user)
		expected = "SessionUser(id=username,name=username,active=True,user=True,admin=False,session={},created={})".format(user._session, user._created)
		self.assertEqual(expected, repr(user))
