# coding=utf-8
"""
Unit tests for octoprint.users.UserManager
"""

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import ddt

import octoprint.users

@ddt.ddt
class UserManagerTest(unittest.TestCase):

	def test_createPasswordHash_nonascii(self):
		"""Test for issue #1891"""

		password = u"password with ümläutß"
		salt = "abc"

		# should not throw an exception
		octoprint.users.UserManager.createPasswordHash(password, salt=salt)
