"""
Unit tests for octoprint.access.permissions
"""

import unittest

from octoprint.access.permissions import Permissions


class PermissionsTest(unittest.TestCase):
    def test_find(self):
        permission = Permissions.find("ADMIN")
        self.assertIsNotNone(permission)
        self.assertEqual(permission.get_name(), "Admin")

    def test_find_fail(self):
        permission = Permissions.find("doesntexist")
        self.assertIsNone(permission)
