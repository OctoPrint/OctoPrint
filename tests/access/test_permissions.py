# coding=utf-8
"""
Unit tests for octoprint.access.permissions
"""
from __future__ import absolute_import, division, print_function

import unittest
import ddt

from octoprint.access.permissions import Permissions, OctoPrintPermission

class PermissionsTest(unittest.TestCase):
	def test_find(self):
		permission = Permissions.find("ADMIN")
		self.assertIsNotNone(permission)
		self.assertEqual(permission.get_name(), "Admin")

	def test_find_fail(self):
		permission = Permissions.find("doesntexist")
		self.assertIsNone(permission)
