# coding=utf-8
"""
Unit tests for octoprint.access.permissions
"""
from __future__ import absolute_import, division, print_function

import unittest
import ddt

from octoprint.access.permissions import Permissions, OctoPrintPermission

class PermissionsTest(unittest.TestCase):
	# Update on changes to the available core permissions!
	_COUNT_REGULAR = 17
	_COUNT_COMBINED = 5
	_COUNT_ALL = _COUNT_REGULAR + _COUNT_COMBINED

	def test_find(self):
		permission = Permissions.find("Admin")
		self.assertIsNotNone(permission)
		self.assertEqual(permission.get_name(), "Admin")

	def test_find_fail(self):
		permission = Permissions.find("doesntexist")
		self.assertIsNone(permission)

	def test_all(self):
		permissions = Permissions.all()
		self.assertEqual(len(permissions), self._COUNT_ALL)

	def test_regular(self):
		permissions = Permissions.regular()
		self.assertEqual(len(permissions), self._COUNT_REGULAR)

	def test_combined(self):
		permissions = Permissions.combined()
		self.assertEqual(len(permissions), self._COUNT_COMBINED)


@ddt.ddt
class PermissionTestCase(unittest.TestCase):
	def setUp(self):
		self.permission = OctoPrintPermission("Permission", "My Permission", "permission")
		self.permission_multi_need = OctoPrintPermission("PermissionMultiNeed", "My multi need Permission", "permission1", "permission2", "permission3")

	@ddt.data(
			("permission",
			 "OctoPrintPermission(\"Permission\", \"My Permission\", RoleNeed('permission'))"),
			("permission_multi_need",
			 "OctoPrintPermission(\"PermissionMultiNeed\", \"My multi need Permission\", RoleNeed('permission1'), RoleNeed('permission2'), RoleNeed('permission3'))"),
	)
	@ddt.unpack
	def test_repr(self, uservar, expected):
		self.assertEqual(expected, repr(getattr(self, uservar)))
