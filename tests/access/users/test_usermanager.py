"""
Unit tests for octoprint.access.users.UserManager
"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import ddt

import octoprint.access.users


@ddt.ddt
class UserManagerTest(unittest.TestCase):
    def test_createPasswordHash_nonascii(self):
        """Test for issue #1891"""

        password = "password with ümläutß"

        # should not throw an exception
        octoprint.access.users.UserManager.create_password_hash(password)
