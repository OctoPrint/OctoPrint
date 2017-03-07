# coding=utf-8
"""
Unit tests for octoprint.users.User
"""
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import ddt

import octoprint.users
from octoprint.util import dict_merge

default_settings = dict(key="value", sub=dict(subkey="subvalue"))

@ddt.ddt
class UserTestCase(unittest.TestCase):
	def setUp(self):
		self.user = octoprint.users.User("user", "passwordHash", True, ("user",), apikey="apikey_user", settings=default_settings)
		self.admin = octoprint.users.User("admin", "passwordHash", True, ("user","admin"), apikey="apikey_admin", settings=default_settings)
		self.inactive = octoprint.users.User("inactive", "passwordHash", False, ("user",), apikey="apikey_inactive", settings=default_settings)

	@ddt.data(
		("user",     dict(name="user",
		                  active=True,
		                  admin=False,
		                  user=True,
		                  apikey="apikey_user",
		                  settings=default_settings)),
		("admin",    dict(name="admin",
		                  active=True,
		                  admin=True,
		                  user=True,
		                  apikey="apikey_admin",
		                  settings=default_settings)),
		("inactive", dict(name="inactive",
		                  active=False,
		                  admin=False,
		                  user=True,
		                  apikey="apikey_inactive",
		                  settings=default_settings))
	)
	@ddt.unpack
	def test_as_dict(self, uservar, expected):
		user = getattr(self, uservar)
		self.assertDictEqual(expected, user.asDict())

	@ddt.data(
		("key", "value"),
		(["sub", "subkey"], "subvalue"),
		("doesntexist", None)
	)
	@ddt.unpack
	def test_get_setting(self, key, expected):
		value = self.user.get_setting(key)
		self.assertEqual(expected, value)

	@ddt.data(
		("otherkey", "othervalue", dict(otherkey="othervalue"), True),
		(["sub", "othersubkey"], "othersubvalue", dict(sub=dict(othersubkey="othersubvalue")), True),
		("booleankey", True, dict(booleankey=True), True),
		(["newsub", "newsubkey"], "newsubvalue", dict(newsub=dict(newsubkey="newsubvalue")), True),
		# ["sub", "subkey"] is already existing and gets overwritten
		(["sub", "subkey", "subsubkey"], "42", dict(sub=dict(subkey=dict(subsubkey="42"))), True),
		(["sub"], "overwrite", dict(sub="overwrite"), True)
	)
	@ddt.unpack
	def test_set_setting_string(self, key, value, update, expected_returnvalue):
		returnvalue = self.user.set_setting(key, value)

		expected = dict_merge(default_settings, update)

		self.assertDictEqual(expected, self.user.get_all_settings())
		self.assertEqual(expected_returnvalue, returnvalue)

	def test_check_password(self):
		self.assertTrue(self.user.check_password("passwordHash"))
		self.assertFalse(self.user.check_password("notThePasswordHash"))

	@ddt.data(
		("user", "User(id=user,name=user,active=True,user=True,admin=False)"),
		("admin", "User(id=admin,name=admin,active=True,user=True,admin=True)"),
		("inactive", "User(id=inactive,name=inactive,active=False,user=True,admin=False)")
	)
	@ddt.unpack
	def test_repr(self, uservar, output):
		self.assertEqual(output, repr(getattr(self, uservar)))
